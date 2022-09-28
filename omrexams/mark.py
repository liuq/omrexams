from tinydb import TinyDB, Query
import pandas as pd
import numpy as np

def uniform(correct, marked, missing, wrong, size):
    if len(marked) == 0:
        return np.array([0.0, 1.0])
    else:
        return np.array([-len(wrong) / (size - 1) + len(correct), 1.0])

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

class Mark:
    def __init__(self, datafile, outputfile):
        self.datafile = datafile
        self.outputfile = outputfile

    def mark(self, marking_function=correct_only, include_missing=False, weights={}):        
        with TinyDB(self.datafile) as db:
            df = pd.DataFrame()
            Exam = Query()
            for exam in db.table('correction').all():
                e = db.table('exams').get(Exam.student_id == exam['student_id'])
                question_size = list(map(lambda q: len(q[3]), e['questions']))
                question_source = list(map(lambda q: q[0], e['questions']))
                correct_answers = list(map(set, exam['correct_answers']))
                given_answers = list(map(set, exam['given_answers']))
                p = np.array([0.0, 0.0])
                current = { 'student_id': exam['student_id'] }
                if len(correct_answers) != len(given_answers):
                    raise RuntimeWarning("It seems that something went wrong, the number of correct answers and given answers do not match for student {}".format(exam['student_id']))
                for i in range(len(correct_answers)):
                    marked, correct, missing, wrong = given_answers[i], correct_answers[i] & given_answers[i], correct_answers[i] - given_answers[i], given_answers[i] - correct_answers[i]
                    q_size = question_size[i]                        
                    c = marking_function(correct, marked, missing, wrong, q_size) 
                    p += c * weights.get(question_source[i], 1.0)
                    current[f'{question_source[i]} correct'] = len(correct)
                    current[f'{question_source[i]} missing'] = len(missing)
                    current[f'{question_source[i]} wrong'] = len(wrong)
                    current[f'{question_source[i]} size'] = q_size
                    current[f'{question_source[i]} question'] = e['questions'][i][1]
                current['A total_points'] = p[0]
                current['B tentative_mark'] = p[0] / p[1]
                df = df.append(current, ignore_index=True)          
            if include_missing:
                for exam in db.table('exams').all():
                    e = db.table('correction').get(Exam.student_id == exam['student_id'])
                    if not e:
                        df = df.append({ 'student_id': exam['student_id'], 'total_points': 'ASS', 'tentative_mark': 'ASS' }, ignore_index=True)
            df = df.sort_values('student_id')
            df = df.rename({'A total_points': 'total_points', 'B tentative_mark': 'tentative_mark'}, axis="columns")
            df.set_index('student_id').to_excel(self.outputfile)
