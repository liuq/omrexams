from tinydb import TinyDB, Query
import pandas as pd
import math

def uniform(correct, marked, missing, wrong, size):
    if len(marked) < 1:
        return 0
    else:
        return -len(wrong) / (size - 1) + len(correct)

def custom(correct, marked, missing, wrong, size):
    if len(marked) == 0:
        return 0
    if len(marked) == size:
        return 0
    else:
        return len(correct) / (len(correct) + len(missing))

def correct_only(correct, marked, missing, wrong, size):
    if len(marked) < 1:
        return 0
    else:
        return len(correct) / (len(correct) + len(missing))

class Mark:
    def __init__(self, datafile, outputfile):
        self.datafile = datafile
        self.outputfile = outputfile

    def mark(self, marking_function=custom, include_missing=True):        
        with TinyDB(self.datafile) as db:
            data = []
            Exam = Query()
            for exam in db.table('correction').all():
                e = db.table('exams').get(Exam.student_id == exam['student_id'])
                question_size = list(map(lambda q: len(q[3]), e['questions']))
                correct_answers = list(map(set, exam['correct_answers']))
                given_answers = list(map(set, exam['given_answers']))
                points = 0
                current = { 'student_id': exam['student_id'] }
                if len(correct_answers) != len(given_answers):
                    raise RuntimeWarning("It seems that something went wrong, the number of correct answers and given answers do not match for student {}".format(exam['student_id']))
                for i in range(len(correct_answers)):
                    marked, correct, missing, wrong = given_answers[i], correct_answers[i] & given_answers[i], correct_answers[i] - given_answers[i], given_answers[i] - correct_answers[i]
                    q_size = question_size[i]
                    points += marking_function(correct, marked, missing, wrong, q_size)
                    current['question_{:02d}_correct'.format(i + 1)] = len(correct)
                    current['question_{:02d}_missing'.format(i + 1)] = len(missing)
                    current['question_{:02d}_wrong'.format(i + 1)] = len(wrong)
                    current['question_{:02d}_size'.format(i + 1)] = q_size
                current['total_points'] = points
                current['tentative_mark'] = math.ceil(30.0 * points / len(correct_answers))
                data.append(current)
            df = pd.DataFrame.from_records(data)
            if include_missing:
                for exam in db.table('exams').all():
                    e = db.table('correction').get(Exam.student_id == exam['student_id'])
                    if not e:
                        df = df.append({ 'student_id': exam['student_id'], 'total_points': 'ASS', 'tentative_mark': 'ASS' }, ignore_index=True)
            df = df.sort_values('student_id')
            df.set_index('student_id').to_excel(self.outputfile)
