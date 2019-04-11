from tinydb import TinyDB, Query
import pandas as pd

def uniform(correct, missing, wrong):
    return 0

class Mark:
    def __init__(self, datafile, outputfile):
        self.datafile = datafile
        self.outputfile = outputfile

    def mark(self):        
        with TinyDB(self.datafile) as db:
            data = []
            for exam in db.table('correction').all():
                correct_answers = list(map(set, exam['correct_answers']))
                given_answers = list(map(set, exam['given_answers']))
                points = 0
                current = { 'student_id': exam['student_id'] }
                if len(correct_answers) != len(given_answers):
                    raise RuntimeWarning("It seems that something went wrong, the number of correct answers and given answers do not match for student {}".format(exam['student_id']))
                for i in range(len(correct_answers)):
                    correct, missing, wrong = correct_answers[i] & given_answers[i], correct_answers[i] - given_answers[i], given_answers[i] - correct_answers[i]
                    points += uniform(correct, missing, wrong)
                    current['question_{}_correct'.format(i)] = len(correct)
                    current['question_{}_missing'.format(i)] = len(missing)
                    current['question_{}_wrong'.format(i)] = len(wrong)
                current['total_points'] = points
                data.append(current)
            pd.DataFrame.from_records(data).set_index('student_id').to_excel(self.outputfile)

