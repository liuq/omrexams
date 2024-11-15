import time
import click
import random
import time
import logging
import glob
import os
import re
import io
from shutil import copy2, rmtree
import multiprocessing as mp
from functools import partial
from . utils.markdown import QuestionRenderer, DocumentStripRenderer, Document
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf._page import PageObject
import math
from datetime import datetime as dt
from tinydb import TinyDB
from . utils.directories import BASEDIR
from collections import deque
from itertools import zip_longest
import hashlib
import importlib.resources as pkg_resources

logger = logging.getLogger("omrexams")

QUESTION_MARKER_RE = re.compile(r'-{3,}\s*\n')
TITLE_RE = re.compile(r"#\s+.*")
QUESTION_RE = re.compile(r"##\s*(.+?)(?={topic:#|\n)({topic:#[\w-]+})?")
OPEN_QUESTION_RE = re.compile(r"#{3,}\s*(.+?)")
TOPIC_RE = re.compile(r"##\s*.*{topic:(#[\w-]+)}")

# A4 size, portrait is 595pt x 842pt
A4SIZE = { 'width': 595, 'height': 842 }
# A3 size, landscape is 1190pt x 842pt
A3SIZE = { 'width': 1190, 'height': 842 }

def assemble_booklet(pages):
    """assembles the booklet according to the order [-1, 0, 1, -2] and going in.

    Assumes an iterable with the length a multiple of 4"""
    pages = deque(pages)
    assert not len(pages) % 4, 'booklet length, must be a multiple of 4'
    while pages:
        selection = pages.pop(), pages.popleft(), pages.popleft(), pages.pop()
        yield from selection

def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks

    grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

def make_book(pages, booklet_length):
    '''Combines all the lists into one and returns the result.'''
    assert not booklet_length % 4, 'booklet length, must be a multiple of 4'
    for group in grouper(pages, booklet_length, fillvalue=None):
        yield tuple(assemble_booklet(group))
        # yield from assemble_booklet(group) # dependent on the output you want

class Generate:
    """
    This class is responsible of creating the individual exams for a number of students 
    or an overall testing document for checking the questions and their answers.
    """    

    def __init__(self, config, questions, output_prefix, **kwargs):
        self.config = config
        self.questions_path = questions
        self.output_pdf_filename = f"{output_prefix}.pdf"
        self.test = kwargs.get('test', False)
        self.paper = kwargs.get('paper', 'A4')
        if self.paper not in ('A4', 'A3'):
            raise AttributeError('paper value should be either "A3" or "A4"')
        # TODO: emit logging if these parameters are not set
        if not self.test:
            self.output_list_filename = f"{output_prefix}.json"
            self.students = kwargs.get('students', [])
            self.exam_date = kwargs.get('date', dt.now())
            self.topics = {}   
            self.seed = kwargs.get('seed', 0)
            with TinyDB(self.output_list_filename) as db:
                db.drop_table('metadata')
                db.table('metadata').insert({ 'seed': self.seed, 'generation_date': dt.now().strftime("%F") })

    def load_rules(self):
        rules = self.config.get('questions', [{ "from": "*.md", "use": 1 }])
        rules_expanded = {}
        # first expand the generic rules, then the more specific ones
        for rule in filter(lambda r: re.search(r'[\*\?]', r['from']), rules):
            for filename in glob.glob(os.path.join(self.questions_path, rule['from'])):
                rules_expanded[filename] = rule['draw']
        for rule in filter(lambda r: not re.search(r'[\*\?]', r['from']), rules):
            rules_expanded[os.path.join(self.questions_path, rule['from'])] = rule['draw']
        return rules_expanded

    def load_questions(self, filename):
        with open(filename, 'r') as f:
            questions = list(filter(lambda q: not TITLE_RE.match(q) and not OPEN_QUESTION_RE.match(q), QUESTION_MARKER_RE.split(f.read())))
            return questions

    def load_open_questions(self, filename):
        with open(filename, 'r') as f:
            questions = list(filter(lambda q: OPEN_QUESTION_RE.match(q), QUESTION_MARKER_RE.split(f.read())))
            return questions
    
    def load_topics(self, filename):
        with open(filename, 'r') as f:            
            questions_with_topics = filter(lambda q: TOPIC_RE.match(q), QUESTION_MARKER_RE.split(f.read()))
            topics = set()
            for q in questions_with_topics:
                topics.add(TOPIC_RE.match(q).group(1))
            return topics
    
    def process(self):
        if not self.test:
            self.generate_exams()
        else:
            self.generate_test()    

    def generate_exams(self):
        rules = self.load_rules()
        self.questions = {}
        self.open_questions = {}
        for r in sorted(rules.keys()):
            self.questions[os.path.basename(r)] = { 'content': self.load_questions(r), 'draw': rules[r] }
            self.open_questions[os.path.basename(r)] = { 'content': self.load_open_questions(r), 'draw': rules[r] }
        logger.info('Creating and preparing tmp directory')
        if self.open_questions:
            logger.info('There are open questions')
        if os.path.exists('tmp'):
            rmtree('tmp')
        os.mkdir('tmp')        
        with pkg_resources.path("omrexams.texmf", "omrexam.cls") as template_path:
            # Copy the file to the temporary directory
            click.secho(f'Copying omrexam.cls to tmp', fg='yellow')
            copy2(template_path, 'tmp')
        click.secho(f'Generating {len(self.students)} exams (this may take a while)', fg='red', underline=True)
        with click.progressbar(length=len(self.students), label='Generating exams',
                               bar_template='%(label)s |%(bar)s| %(info)s',
                               fill_char=click.style(u'█', fg='cyan'),
                               empty_char=' ', show_pos=True) as bar:
            self.tasks_queue = mp.JoinableQueue()
            self.results_mutex = mp.RLock()
            self.task_done = mp.Condition(self.results_mutex)
            self.results = mp.Value('i', 0, lock=self.results_mutex)
            self.error = mp.Value('b', False, lock=self.results_mutex)
            for i, student in enumerate(self.students):
                self.tasks_queue.put((i, student))
            for _ in range(mp.cpu_count()):
                self.tasks_queue.put((None, None))
            pool = mp.Pool(mp.cpu_count(), self.worker_main)
            pool.close()
            prev = 0
            while not self.tasks_queue.empty():
                self.results_mutex.acquire()
                self.task_done.wait_for(lambda: prev <= self.results.value)
                bar.update(self.results.value - prev)
                prev = self.results.value
                self.results_mutex.release()
        click.secho('Collating PDF', fg='red', underline=True)
        if self.paper == "A4":
            # This is for A4 management            
            merger = PdfWriter()
            _blank = PdfWriter()
            _blank.add_blank_page(**A4SIZE)    
            blank = io.BytesIO()
            _blank.write(blank)   
            pdf_files = sorted(glob.glob(os.path.join('tmp', '*.pdf')))
            with click.progressbar(length=len(pdf_files), label='Exam files',
                               bar_template='%(label)s |%(bar)s| %(info)s',
                               fill_char=click.style(u'█', fg='cyan'),
                               empty_char=' ', show_pos=True) as bar:
                for exam in pdf_files:
                    pdf = PdfReader(open(exam, 'rb'), strict=False)  
                    merger.append(pdf)
                    if len(pdf.pages) % 2 == 1:
                        merger.append(blank)
                    bar.update(1)
            with open(self.output_pdf_filename, 'wb') as f:
                merger.write(f)
        else:
            # This is for A3 management
            writer = PdfWriter()
            a3page = None
            pdf_files = sorted(glob.glob(os.path.join('tmp', '*.pdf')))
            with click.progressbar(length=len(pdf_files), label='Collating files ',
                               bar_template='%(label)s |%(bar)s| %(info)s',
                               fill_char=click.style(u'█', fg='cyan'),
                               empty_char=' ', show_pos=True) as bar:
                for exam in pdf_files:
                    pdf = PdfReader(open(exam, 'rb'), strict=False)
                    a3page = PageObject.create_blank_page(**A3SIZE)                    
                    left = True
                    sheets = math.ceil(len(pdf.pages) / 4) 
                    booklet = next(make_book(range(1, len(pdf.pages) + 1), sheets * 4))
                    for p in booklet:
                        if p is not None:
                            page = pdf.pages[p - 1]
                        else:
                            page = None
                        if left:
                            # page left
                            if page is not None:
                                a3page.merge_page(page) 
                            left = False
                        else:
                            # page right
                            if page is not None:
                                transformation = Transformation().translate(A3SIZE['width'] / 2, 0)
                                a3page.merge_transformed_page(page, transformation, expand=False) 
                            left = True
                        if left:
                            # add page 
                            writer.add_page(a3page)
                            a3page = PageObject.create_blank_page(**A3SIZE)  
                    bar.update(1)
            with open(self.output_pdf_filename, 'wb') as f:
                writer.write(f)
        
        if not self.error.value:
            click.secho('Removing tmp', fg='yellow')
            rmtree('tmp')
        click.secho('Finished', fg='red', underline=True)

    def worker_main(self):
        while True:
            task, student = self.tasks_queue.get()
            if task is None:
                break
            logger.info(f'Started processing student {student[0]} {student[1]}')
            try:
                s = int(student[0])
            except:
                # To capture strange matriculation numbers
                hashed_result = hashlib.md5(student[0].encode()).hexdigest()
                s = ord(hashed_result[0])
            random.seed(self.seed + s)
            done = False
            try:
                for _ in range(50):
                    document, questions, answers = self.create_exam(student)
                    digits = math.ceil(math.log10(len(self.students)))
                    f = f'{{:0{digits}d}}-{{}}-{{}}'
                    filename = os.path.join('tmp', f"{task:0{digits}d}-{student[0]}-{student[1].replace(' ', '_')}")
                    document.generate_pdf(filepath=filename, 
                                        compiler='latexmk', 
                                        compiler_args=['-xelatex', '-shell-escape'])
                    # get rid of the xdv file, if any
                    if os.path.exists(f"{filename}.xdv"):
                        os.remove(f"{filename}.xdv")
                    # check the generated output in terms of pages 
                    # TODO: it should be done also in terms of the qrcode, number of questions, coherence of answers
                    with open(f"{filename}.pdf", 'rb') as f:
                        pdf_file = PdfReader(f, strict=False)
                        if len(pdf_file.pages) <= self.config['exam'].get('page_limits', 2):
                            done = True
                            break                     
                if not done:
                    click.secho(f"Couldn't get an exam with at most {self.config['exam'].get('page_limits', 2)} pages for student {student[0]} {student[1]}", fg='red', blink=True)
                    logger.warning(f"Couldn't get an exam with at most {self.config['exam'].get('page_limits', 2)} pages for student {student[0]} {student[1]}")                        
            except Exception as e:
                raise e
                print(e)
                self.results_mutex.acquire()
                self.error.value = True
                self.results_mutex.release()
            finally:
                self.results_mutex.acquire()
                self.results.value += 1
                # append to list of exams
                if done:
                    self.append_exam(student, questions, answers)
                self.task_done.notify()
                self.results_mutex.release()
                self.tasks_queue.task_done()


    def draw_questions(self, Q):
        questions = []
        for filename, topic in Q:
            candidate_questions = list((q, i) for i, q in enumerate(topic['content']))
            current_questions = []
            while candidate_questions:
                t = candidate_questions.pop()
                topic_mutually_exclusive = [t]
                q = re.search(QUESTION_RE, t[0])
                if not q:
                    raise RuntimeError(f"Apparently, question \"{t[0]}\" in filename {filename} has no text")                
                q_id = q.group(2).strip() if q.group(2) else None
                q = q.group(1).strip().lower()
                j = 0
                while j < len(candidate_questions):
                    cq = re.search(QUESTION_RE, candidate_questions[j][0])
                    if not cq:
                        raise RuntimeError(f"Apparently, question \"{topic['content'][j]}\" in filename {filename} has no text")
                    cq_id = cq.group(2).strip() if cq.group(2) else None
                    if q == cq.group(1).strip().lower() or (q_id is not None and  q_id == cq_id):
                        topic_mutually_exclusive.append(candidate_questions.pop(j))                        
                    else:
                        j = j + 1
                current_questions += random.sample(topic_mutually_exclusive, 1)
            sample = random.sample(list(range(len(current_questions))), min(topic['draw'], len(current_questions)))
            questions += list(map(lambda index: (filename, current_questions[index][1], current_questions[index][0]), sample))
        return questions


    def create_exam(self, student):     
        def code_answer(answers):
                current = ""
                for i in range(len(answers)):
                    if answers[i]:
                        current += chr(ord('A') + i)
                return current
        logger.info(f'Creating exam {student[0]} {student[1]}') 
        # randomly select a given number of questions from each file
        # however, avoid to select more than once the questions with the same text
        questions = self.draw_questions(self.questions.items())        
        if self.config['exam'].get('shuffle_questions', False):
            random.shuffle(questions)
        if self.config['exam'].get('max_questions', False):
            questions = questions[:self.config['exam'].get('max_questions')]

        open_questions = self.draw_questions(self.open_questions.items())
        if self.config['exam'].get('shuffle_questions', False):
            random.shuffle(open_questions)
        if self.config['exam'].get('max_open_questions', False):
            open_questions = open_questions[:self.config['exam'].get('max_open_questions')]        

        if self.config.get('header'):
            with DocumentStripRenderer(basedir=self.config.get('basedir')) as renderer:
                header = renderer.render(Document(self.config.get('header')))
        else:
            header = ''
        if self.config.get('preamble'):
            with DocumentStripRenderer(basedir=self.config.get('basedir')) as renderer:
                preamble = renderer.render(Document(self.config.get('preamble')))
        else:
            preamble = ''
        if self.config.get('footer'):
            with DocumentStripRenderer(basedir=self.config.get('basedir')) as renderer:
                footer = renderer.render(Document(self.config.get('footer')))
        else:
            footer = ''
        with QuestionRenderer(language=self.config['exam'].get('language'), 
                              date=self.exam_date, exam=self.config['exam'].get('name'), 
                              student_no=student[0],
                              student_name=student[1] if student[1] != 'Additional student' else '_' * 20, 
                              header=header, 
                              preamble=preamble,
                              footer=footer,
                              packages=self.config.get('packages', {}),
                              shuffle=self.config['exam'].get('shuffle_answers', True),
                              dyslexia=self.config.get('choices', {}).get('dyslexia', False),
                              circled=self.config.get('choices', {}).get('circled', False),
                              usesf=self.config.get('choices', {}).get('usesf', False),
                              basedir=os.path.realpath(self.questions_path)) as renderer:
            content = '---\n' + '\n---\n'.join(map(lambda q: q[2], questions)) + '\n---\n'
            if open_questions:
                content += '\n---\n'.join(map(lambda q: q[2], open_questions)) + '\n---\n'
            document = renderer.render(Document(content))   
            tmp = list(map(lambda i: (*questions[i][:2], code_answer(renderer.questions[i]['answers']), renderer.questions[i]['permutation']), range(len(questions))))
#            tmp += list(map(lambda i: (*open_questions[i][:2], code_answer(renderer.questions[i + len(questions)]['answers']), renderer.questions[i + len(questions)]['permutation']), range(len(open_questions))))
            overall_answers = list(code_answer(q['answers']) for q in renderer.questions)
            return document, tmp, overall_answers
    
    def append_exam(self, student, questions, answers):  
        data = { 
            "student_id": str(student[0]),
            "fullname": student[1],                        
            "questions": []
        }
        for q in questions:
            data['questions'].append(q)
        data['answers'] = answers
        with TinyDB(self.output_list_filename) as db:
#            import json
#            print(json.dumps(data))
            db.table('exams').insert(data)

    def generate_test(self):
        rules = self.load_rules()
        self.topics = {}
        for r in sorted(rules.keys()):
            self.topics[os.path.basename(r)] = self.load_topics(r)
        for n, t in self.topics.items():
            click.secho(f"Topics of {n} {len(t)}")
        if self.config.get('header'):
            with DocumentStripRenderer(basedir=self.config.get('basedir')) as renderer:
                header = renderer.render(Document(self.config.get('header')))
        else:
            header = ''
        if self.config.get('preamble'):
            with DocumentStripRenderer(basedir=self.config.get('basedir')) as renderer:
                preamble = renderer.render(Document(self.config.get('preamble')))
        else:
            preamble = ''
        if self.config.get('footer'):
            with DocumentStripRenderer(basedir=self.config.get('basedir')) as renderer:
                footer = renderer.render(Document(self.config.get('footer')))
        else:
            footer = ''

        questions = ""
        for r in sorted(rules.keys()):
            click.secho(f'Testing {os.path.basename(r)}', fg='cyan')
            with open(r, 'r') as f:
                current_questions = f.read()
            with QuestionRenderer(language=self.config['exam'].get('language'), 
                              date=dt.now(), 
                              exam=self.config['exam'].get('name'), 
                              header=header, 
                              preamble=preamble,
                              footer=footer,
                              packages=self.config.get('packages', {}),
                              test=True,
                              circled=self.config.get('choices', {}).get('circled', False),
                              basedir=os.path.realpath(self.questions_path)) as renderer:
                renderer.render(Document(current_questions))
            questions += current_questions + "\n\n"

        logger.info('Creating and preparing tmp directory')
        if not os.path.exists('tmp'):
           os.mkdir('tmp')
        with pkg_resources.path("omrexams.texmf", "omrexam.cls") as template_path:
            # Copy the file to the temporary directory
            click.secho(f'Copying omrexam.cls to tmp', fg='yellow')
            copy2(template_path, 'tmp')
        with QuestionRenderer(language=self.config['exam'].get('language'), 
                              date=dt.now(), 
                              exam=self.config['exam'].get('name'), 
                              student_no=0,
                              student_name="", 
                              header=header, 
                              preamble=preamble,
                              footer=footer,
                              packages=self.config.get('packages', {}),
                              test=True,
                              circled=self.config.get('choices', {}).get('circled', False),
                              basedir=os.path.realpath(self.questions_path)) as renderer:
            document = renderer.render(Document(questions)) 
        click.secho('Generating PDF with all corrected questions', fg='red', underline=True)
        filename = ".".join(os.path.basename(self.output_pdf_filename).split(".")[:-1])
        document.generate_pdf(filepath=os.path.join("tmp", filename), 
                              compiler='latexmk', 
                              compiler_args=['-xelatex'])
        copy2(os.path.join('tmp',  f"{filename}.pdf"), '.')


