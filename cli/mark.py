from tinydb import TinyDB, Query
import pandas as pd

def uniform(correct, marked, missing, wrong, size):
    if len(marked) != 1:
        return 0
    else:
        return -len(wrong) / (size - 1) + len(correct)

class Mark:
    def __init__(self, datafile, outputfile):
        self.datafile = datafile
        self.outputfile = outputfile

    def mark(self):        
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
                    points += uniform(correct, marked, missing, wrong, q_size)
                    current['question_{}_correct'.format(i)] = len(correct)
                    current['question_{}_missing'.format(i)] = len(missing)
                    current['question_{}_wrong'.format(i)] = len(wrong)
                    current['question_{}_size'.format(i)] = q_size
                current['total_points'] = points
                data.append(current)
            df = pd.DataFrame.from_records(data)
            for exam in db.table('exams').all():
                e = db.table('correction').get(Exam.student_id == exam['student_id'])
                if not e:
                    df = df.append({ 'student_id': exam['student_id'], 'total_points': 'ASS' }, ignore_index=True)
            df.set_index('student_id').to_excel(self.outputfile)
