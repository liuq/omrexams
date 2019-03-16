import time
import click
import random
import time
import logging
import glob
import os
import re
import io
from shutil import copy2
import multiprocessing as mp
from functools import partial
from . utils.markdown import QuestionRenderer, DocumentStripRenderer, Document
from PyPDF2 import PdfFileReader, PdfFileMerger, PdfFileWriter
import math

logger = logging.getLogger("omrexams")

class Generate:
    question_re = re.compile(r"\n-{3,}\n")
    title_re = re.compile(r"#\s+.*")

    def __init__(self, config, students, questions, output, date, seed):
        self.config = config
        self.students = students
        self.questions_path = questions
        self.output_pdf = output
        self.exam_date = date
        self.seed = seed 
        self.topics = {}     

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
            return list(filter(lambda q: not Generate.title_re.match(q), Generate.question_re.split(f.read())))
    
    def process(self):
        rules = self.load_rules()
        self.questions = {}
        for r in rules.keys():
            self.questions[r] = { 'content': self.load_questions(r), 'draw': rules[r] }    
        logger.info('Creating and preparing tmp directory')
        if not os.path.exists('tmp'):
           os.mkdir('tmp')
        click.secho('Copying {} to tmp'.format(os.path.join('texmf', 'omrexam.cls')), fg='yellow')
        copy2(os.path.join('texmf', 'omrexam.cls'), 'tmp')
        click.secho('Generating {} exams (this may take a while)'.format(len(self.students)), fg='red', underline=True)
        with click.progressbar(length=len(self.students), label='Generating exams',
                               bar_template='%(label)s |%(bar)s| %(info)s',
                               fill_char=click.style(u'█', fg='cyan'),
                               empty_char=' ', show_pos=True) as bar:   
            self.tasks_queue = mp.JoinableQueue()
            self.results_mutex = mp.RLock()
            self.task_done = mp.Condition(self.results_mutex)
            self.results = mp.Value('i', 0, lock=self.results_mutex)
            for i, student in enumerate(self.students):
                self.tasks_queue.put((i, student))
            for _ in range(mp.cpu_count()):
                self.tasks_queue.put((None, None))
            pool = mp.Pool(mp.cpu_count(), self.worker_main)
            pool.close()
            prev = 0
            while not self.tasks_queue.empty():
                self.results_mutex.acquire()
                self.task_done.wait_for(lambda: prev < self.results.value)
                bar.update(self.results.value - prev)
                prev = self.results.value
                self.results_mutex.release()
        click.secho('Collating PDF', fg='red', underline=True)
        merger = PdfFileMerger()
        _blank = PdfFileWriter()
        # A4
        _blank.addBlankPage(width=595, height=842)    
        blank = io.BytesIO()
        _blank.write(blank)   
        for exam in sorted(glob.glob(os.path.join('tmp', '*.pdf'))):
            pdf = PdfFileReader(open(exam, 'rb'))                
            merger.append(pdf)
            if pdf.getNumPages() % 2 == 1:
                merger.append(blank)
        merger.write(self.output_pdf)
        click.secho('Finished', fg='red', underline=True)

    def worker_main(self):
        while True:
            task, student = self.tasks_queue.get()
            if task is None:
                break
            logger.info("Started processing student {} {}".format(*student))
            done = False
            for _ in range(5):
                document = self.create_exam(student)
                digits = math.ceil(math.log10(len(self.students)))
                f = '{{:0{}d}}-{{}}-{{}}'.format(digits)
                filename = os.path.join('tmp', f.format(task, student[0], student[1].replace(" ", "_")))
                document.generate_pdf(filepath=filename, 
                                      compiler='latexmk', 
                                      compiler_args=['-xelatex'])
                # get rid of the xdv file
                os.remove("{}.xdv".format(filename))
                # check the generated output in terms of pages 
                # TODO: it should be done also in terms of the qrcode, number of questions, coherence of answers
                with open("{}.pdf".format(filename), 'rb') as f:
                    pdf_file = PdfFileReader(f)
                    if pdf_file.getNumPages() <= self.config['exam'].get('page_limits', 2):
                        done = True
                        break 
            if not done:
                logger.warning("Couldn't get an exam with at most {} pages for student {} {}".format(self.config['exam'].get('page_limits', 2), *student))
            self.results_mutex.acquire()
            self.results.value += 1
            self.task_done.notify()
            self.results_mutex.release()
            self.tasks_queue.task_done()

    def create_exam(self, student):       
        logger.info("Creating exam".format(*student)) 
        # randomly select a given number of questions from each file
        questions = []
        for topic in self.questions.values():
            questions += random.sample(topic['content'], topic['draw'])
        if self.config['exam'].get('shuffle_questions', False):
            random.shuffle(questions)
        if self.config['exam'].get('max_questions', False):
            questions = questions[:self.config['exam'].get('max_questions')]
        if self.config.get('header'):
            with DocumentStripRenderer() as renderer:
                header = renderer.render(Document(self.config.get('header')))
        else:
            header = ''
        if self.config.get('preamble'):
            with DocumentStripRenderer() as renderer:
                preamble = renderer.render(Document(self.config.get('preamble')))
        else:
            preamble = ''
        with QuestionRenderer(language=self.config['exam'].get('language'), 
                              date=self.exam_date, exam=self.config['exam'].get('name'), 
                              student_no=student[0],
                              student_name=student[1], header=header, 
                              preamble=preamble) as renderer:
            content = '\n'.join(questions)
            document = renderer.render(Document(content))
            return document