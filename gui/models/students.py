"""
A model for handling the list of students.
"""

from pubsub import pub
import pandas as pd
import os

# TODO: add config for fields

config = {
    'name': 'Nome',
    'surname': 'Cognome',
    'id': 'Matricola',
    'sort': 'Cognome',
    'skip': 20
}

class Students(object):
    def __init__(self, filename=None):
        if filename is not None:
            self.load(filename)
        else:
            self.filename = None
            self.students = pd.DataFrame()

    def load(self, filename):
        pub.sendMessage("file.loading", status="loading", file=os.path.basename(filename))
        try:    
            students = pd.read_excel(filename, skiprows=config['skip'])
            students['FullName'] = students[config['name']] + ' ' + students[config['surname']]
            students.sort_values(config['sort'], inplace=True)
            students.reset_index(inplace=True)
            self.filename = filename
            self.students = students
            pub.sendMessage("file.loaded", status="loaded", file=os.path.basename(self.filename))
        except Exception as e:
            pub.sendMessage("file.error", status="error", error=str(e))
