from tinydb import TinyDB, Query
import pandas as pd
import numpy as np
import click

def uniform(correct, marked, missing, wrong, size):
    if len(marked) == 0:
        return np.array([0.0, 1.0])
    else:
        return np.array([-len(wrong) / (size - len(correct) - len(missing) - 1) + len(correct), 1.0])

def weighted_custom(correct, marked, missing, wrong, size):
    if len(marked) == 0:
        return np.array([0.0, 1.0])
    if len(marked) == size:
        return np.array([0.0, 1.0])
    else:
        return np.array([len(correct), len(correct) + len(missing)])

def correct_only(correct, marked, missing, wrong, size):
    if len(marked) == 0:
        return np.array([0.0, 1.0])
    if len(marked) == size:
        return np.array([0.0, 1.0])
    else:
        return np.array([len(correct) / (len(correct) + len(missing)), 1.0])

def custom_correction(correct, marked, missing, wrong, size):
    penalty = 0.0
    if len(marked) > (len(correct) + len(missing)):
        penalty = (len(wrong) / (size - len(correct) - 1))
    return np.array([max(0.0, len(correct) / (len(correct) + len(missing)) - penalty), 1.0])

class Mark:
    def __init__(self, datafile, outputfile):
        self.datafile = datafile
        self.outputfile = outputfile

    def mark(self, marking_function=custom_correction, include_missing=False, weights={}):        
        with TinyDB(self.datafile) as db:
            df = pd.DataFrame()
            Exam = Query()
            for exam in db.table('correction').all():
                e = db.table('exams').get(Exam.student_id == exam['student_id'])
                if e is None:
                    click.secho(f"Student {exam['student_id']} not present in the exams table", fg="yellow")
                question_size = list(map(lambda q: len(q[3]), e['questions']))
                question_source = list(map(lambda q: q[0], e['questions']))
                correct_answers = list(map(set, exam['correct_answers']))
                # Check if the correct_answers in q[2] are the same, if not it might
                # mean that an update-corrected has been performed
                questions_correct_answers = list(map(lambda q: set(q[2]), e['questions']))
                if correct_answers != questions_correct_answers:
                    click.secho(f"Warning: correct answers in the db for student {exam['student_id']} do not match with those on the sheet, if you performed an update-corrected ignore this warning", fg="yellow")
                    correct_answers = questions_correct_answers
                given_answers = list(map(set, exam['given_answers']))
                p = np.array([0.0, 0.0])
                current = pd.DataFrame([{ 'student_id': exam['student_id'] }])
                if len(correct_answers) != len(given_answers):
                    raise RuntimeWarning(f"It seems that something went wrong, the number of correct answers and given answers do not match for student {exam['student_id']}")
                for i in range(len(correct_answers)):
                    marked, correct, missing, wrong = given_answers[i], correct_answers[i] & given_answers[i], correct_answers[i] - given_answers[i], given_answers[i] - correct_answers[i]
                    q_size = question_size[i]                        
                    c = marking_function(correct, marked, missing, wrong, q_size) 
                    p += c * weights.get(question_source[i], 1.0)
                    n = 1
                    while f'{question_source[i]}_{n:02d} A correct' in current.columns:
                        n += 1
                    source = f'{question_source[i]}_{n:02d}'                       
                    current[f'{source} A correct'] = len(correct)
                    current[f'{source} B missing'] = len(missing)
                    current[f'{source} C wrong'] = len(wrong)
                    current[f'{source} D size'] = q_size
                    current[f'{source} E question'] = e['questions'][i][1]
                current = current[sorted(current.columns)]
                current['A total_points'] = p[0]
                current['B tentative_mark'] = p[0] / p[1]
                df = pd.concat([df, current])
            if include_missing:
                for exam in db.table('exams').all():
                    e = db.table('correction').get(Exam.student_id == exam['student_id'])
                    if not e:
                        pd.concat([df, pd.DataFrame([{ 'student_id': exam['student_id'], 'total_points': 'ASS', 'tentative_mark': 'ASS' }]) ])
            df = df.sort_values('student_id')
            df = df.rename({'A total_points': 'total_points', 'B tentative_mark': 'tentative_mark'}, axis="columns")
            df.set_index('student_id').to_excel(self.outputfile)
