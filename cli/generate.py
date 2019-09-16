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
from PyPDF2 import PdfFileReader, PdfFileMerger, PdfFileWriter
import math
from datetime import datetime as dt
from tinydb import TinyDB
from . utils.directories import BASEDIR

logger = logging.getLogger("omrexams")

class Generate:
    """
    This class is responsible of creating the individual exams for a number of students 
    or an overall testing document for checking the questions and their answers.
    """
    QUESTION_MARKER_RE = re.compile(r'-{3,}\s*\n')
    TITLE_RE = re.compile(r"#\s+.*")
    QUESTION_RE = re.compile(r"##\s*(.+?)(?={topic:#|\n)({topic:#[\w-]+})?")

    def __init__(self, config, questions, output_prefix, **kwargs):
        self.config = config
        self.questions_path = questions
        self.output_pdf_filename = "{}.pdf".format(output_prefix)
        self.test = kwargs.get('test', False)
        self.oneparchoices = kwargs.get('oneparchoices', False)
        # TODO: emit logging if these parameters are not set
        if not self.test:
            self.output_list_filename = "{}.json".format(output_prefix)
            self.students = kwargs.get('students', [])
            self.exam_date = kwargs.get('date', dt.now())
            self.topics = {}   
            self.seed = kwargs.get('seed', 0)
            with TinyDB(self.output_list_filename) as db:
                db.purge_table('metadata')
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
            questions = list(filter(lambda q: not Generate.TITLE_RE.match(q), Generate.QUESTION_MARKER_RE.split(f.read())))
            return questions
    
    def process(self):
        if not self.test:
            self.generate_exams()
        else:
            self.generate_test()

    def generate_exams(self):
        rules = self.load_rules()
        self.questions = {}
        for r in sorted(rules.keys()):
            self.questions[os.path.basename(r)] = { 'content': self.load_questions(r), 'draw': rules[r] }    
        logger.info('Creating and preparing tmp directory')
        if os.path.exists('tmp'):
            rmtree('tmp')
        os.mkdir('tmp')        
        click.secho('Copying {} to tmp'.format(os.path.join('texmf', 'omrexam.cls')), fg='yellow')
        copy2(os.path.join(BASEDIR, 'texmf', 'omrexam.cls'), 'tmp')
        click.secho('Generating {} exams (this may take a while)'.format(len(self.students)), fg='red', underline=True)
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
        merger = PdfFileMerger()
        _blank = PdfFileWriter()
        # A4 size il 595pt x 842pt
        _blank.addBlankPage(width=595, height=842)    
        blank = io.BytesIO()
        _blank.write(blank)   
        for exam in sorted(glob.glob(os.path.join('tmp', '*.pdf'))):
            pdf = PdfFileReader(open(exam, 'rb'))                
            merger.append(pdf)
            if pdf.getNumPages() % 2 == 1:
                merger.append(blank)
        with open(self.output_pdf_filename, 'wb') as f:
            merger.write(f)
        if not self.error.value:
            click.secho('Removing tmp', fg='yellow')
            rmtree('tmp')
        click.secho('Finished', fg='red', underline=True)

    def worker_main(self):
        while True:
            task, student = self.tasks_queue.get()
            if task is None:
                break
            logger.info("Started processing student {} {}".format(*student))
            if type(student[0]) == str:
                s = ord(student[0][-1])
            else:
                s = student[0]
            random.seed(self.seed + s)
            done = False
            try:
                for _ in range(5):
                    document, questions, answers = self.create_exam(student)
                    digits = math.ceil(math.log10(len(self.students)))
                    f = '{{:0{}d}}-{{}}-{{}}'.format(digits)
                    filename = os.path.join('tmp', f.format(task, student[0], student[1].replace(" ", "_")))
                    document.generate_pdf(filepath=filename, 
                                        compiler='latexmk', 
                                        compiler_args=['-xelatex'])
                    # get rid of the xdv file, if any
                    if os.path.exists("{}.xdv".format(filename)):
                        os.remove("{}.xdv".format(filename))
                    # check the generated output in terms of pages 
                    # TODO: it should be done also in terms of the qrcode, number of questions, coherence of answers
                    with open("{}.pdf".format(filename), 'rb') as f:
                        pdf_file = PdfFileReader(f)
                        if pdf_file.getNumPages() <= self.config['exam'].get('page_limits', 2):
                            done = True
                            break 
                if not done:
                    click.secho("Couldn't get an exam with at most {} pages for student {} {}".format(self.config['exam'].get('page_limits', 2), *student), fg='red', blink=True)
                    logger.warning("Couldn't get an exam with at most {} pages for student {} {}".format(self.config['exam'].get('page_limits', 2), *student))
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

    def create_exam(self, student):     
        def code_answer(answers):
                current = ""
                for i in range(len(answers)):
                    if answers[i]:
                        current += chr(ord('A') + i)
                return current
        logger.info("Creating exam {} {}".format(*student)) 
        # randomly select a given number of questions from each file
        # however, avoid to select more than once the questions with the same text
        questions = []

        for filename, topic in self.questions.items():
            candidate_questions = list((q, i) for i, q in enumerate(topic['content']))
            current_questions = []
            while candidate_questions:
                t = candidate_questions.pop()
                topic_mutually_exclusive = [t]
                q = re.search(Generate.QUESTION_RE, t[0])
                if not q:
                    raise RuntimeError("Apparently, question \"{}\" has no text".format(t))                
                q_id = q.group(2).strip() if q.group(2) else None
                q = q.group(1).strip().lower()
                j = 0
                while j < len(candidate_questions):
                    cq = re.search(Generate.QUESTION_RE, candidate_questions[j][0])
                    if not cq:
                        raise RuntimeError("Apparently, question \"{}\" has no text".format(topic['content'][j]))
                    cq_id = cq.group(2).strip() if cq.group(2) else None
                    if q == cq.group(1).strip().lower() or (q_id is not None and  q_id == cq_id):
                        topic_mutually_exclusive.append(candidate_questions.pop(j))                        
                    else:
                        j = j + 1
                current_questions += random.sample(topic_mutually_exclusive, 1)
            sample = random.sample(list(range(len(current_questions))), topic['draw'])
            questions += list(map(lambda index: (filename, current_questions[index][1], current_questions[index][0]), 
                sample))
        if self.config['exam'].get('shuffle_questions', False):
            random.shuffle(questions)
        if self.config['exam'].get('max_questions', False):
            questions = questions[:self.config['exam'].get('max_questions')]
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
        with QuestionRenderer(language=self.config['exam'].get('language'), 
                              date=self.exam_date, exam=self.config['exam'].get('name'), 
                              student_no=student[0],
                              student_name=student[1] if student[1] != 'Additional student' else '_' * 20, header=header, 
                              preamble=preamble,
                              shuffle=self.config['exam'].get('shuffle_answers', True),
                              oneparchoices=self.oneparchoices,
                              circled=self.config.get('choices', {}).get('circled', False),
                              usesf=self.config.get('choices', {}).get('usesf', False),
                              basedir=os.path.realpath(self.questions_path)) as renderer:
            content = '---\n' + '\n---\n'.join(map(lambda q: q[2], questions)) + '\n---\n'
            document = renderer.render(Document(content))   
            tmp = map(lambda i: (*questions[i][:2], code_answer(renderer.questions[i]['answers']), renderer.questions[i]['permutation']), range(len(questions)))                        
            overall_answers = list(code_answer(q['answers']) for q in renderer.questions)
            return document, list(tmp), overall_answers
    
    def append_exam(self, student, questions, answers):  
        data = { 
            "student_id": student[0],
            "fullname": student[1],                        
            "questions": []
        }
        for q in questions:
            data['questions'].append(q)
        data['answers'] = answers
        with TinyDB(self.output_list_filename) as db:
            db.table('exams').insert(data)

    def generate_test(self):
        rules = self.load_rules()
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

        questions = ""
        for r in sorted(rules.keys()):
            click.secho('Testing {}'.format(os.path.basename(r)), fg='cyan')
            with open(r, 'r') as f:
                current_questions = f.read()
            with QuestionRenderer(language=self.config['exam'].get('language'), 
                              date=dt.now(), 
                              exam=self.config['exam'].get('name'), 
                              header=header, 
                              preamble=preamble,
                              test=True,
                              oneparchoices=self.oneparchoices,
                              basedir=os.path.realpath(self.questions_path)) as renderer:
                renderer.render(Document(current_questions))
            questions += current_questions + "\n\n"

        logger.info('Creating and preparing tmp directory')
        if not os.path.exists('tmp'):
           os.mkdir('tmp')
        click.secho('Copying {} to tmp'.format(os.path.join('texmf', 'omrexam.cls')), fg='yellow')
        copy2(os.path.join(BASEDIR, 'texmf', 'omrexam.cls'), 'tmp')
        with QuestionRenderer(language=self.config['exam'].get('language'), 
                              date=dt.now(), 
                              exam=self.config['exam'].get('name'), 
                              student_no=0,
                              student_name="", 
                              header=header, 
                              preamble=preamble,
                              test=True,
                              oneparchoices=self.oneparchoices,
                              basedir=os.path.realpath(self.questions_path)) as renderer:
            document = renderer.render(Document(questions)) 
        click.secho('Generating PDF with all corrected questions', fg='red', underline=True)
        filename = ".".join(os.path.basename(self.output_pdf_filename).split(".")[:-1])
        document.generate_pdf(filepath=os.path.join("tmp", filename), 
                              compiler='latexmk', 
                              compiler_args=['-xelatex'])
        copy2(os.path.join('tmp',  "{}.pdf".format(filename)), '.')
        
        
