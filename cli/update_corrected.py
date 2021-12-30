
import logging
import re
import os
from . utils.markdown import QuestionRenderer, Document
from datetime import datetime as dt
from tinydb import TinyDB, Query
from tinydb.operations import set
import click

logger = logging.getLogger("omrexams")

QUESTION_MARKER_RE = re.compile(r'-{3,}\s*\n')
TITLE_RE = re.compile(r"#\s+.*")
QUESTION_RE = re.compile(r"##\s*(.+?)(?={topic:#|\n)({topic:#[\w-]+})?")
OPEN_QUESTION_RE = re.compile(r"#{2,}\s*(.+?)(?={open-question})")

class UpdateCorrected:

    def __init__(self, questions, datafile, **kwargs):
        self.questions_files = questions
        self.datafile = datafile

    def process(self, dry_run=True):
        def code_answer(answers):
                current = ""
                for i in range(len(answers)):
                    if answers[i]:
                        current += chr(ord('A') + i)
                return current
        self.questions = {}
        for filename in self.questions_files:
            with open(filename) as f:
                questions = f.read()
                    
            with QuestionRenderer(test=False,
                                  shuffle=False,
                                  student_no=0,
                                  exam='',
                                  student_name='',
                                  date=dt.now(),
                                  basedir=os.path.realpath(os.path.dirname(filename))) as renderer:
                renderer.render(Document(questions))
                new_questions = renderer.questions

            filename = os.path.basename(filename)
            with TinyDB(self.datafile) as db:
                Exam = Query()
                for exam in db.table('exams'):
                    for i, question in enumerate(exam['questions']):
                        if question[0] != filename:
                            continue
                        k, perm = question[1], question[3]
                        ref_question = new_questions[k]
                        ref_answers = code_answer(list(map(lambda p: ref_question['answers'][p], perm)))
                        if question[2] != ref_answers:
                            click.secho(f"⚠️ For student {exam['student_id']}, {question[:2]} wrongly reports {question[2]} instead of {ref_answers}", fg='red')                            
                            if not dry_run:
                                click.secho('Updating record', fg='green')
                                exam['questions'][i][2] = ref_answers
                                db.table('exams').update(set('questions', exam['questions']), Exam.student_id == exam['student_id']) 
                        if exam['answers'][i] != ref_answers:
                            click.secho(f"⚠️ For student {exam['student_id']}, answer {i} wrongly reports {exam['answers'][i]} instead of {ref_answers}", fg='red')
                            if not dry_run:
                                click.secho('Updating record', fg='green')
                                exam['answers'][i] = ref_answers
                                db.table('exams').update(set('answers', exam['answers']), Exam.student_id == exam['student_id'])
                                                                                
                            