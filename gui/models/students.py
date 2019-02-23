"""
A model for handling the list of students.
"""

from pubsub import pub
import pandas as pd
import os
import gettext
_ = gettext.gettext

# TODO: add config for fields

config = {
    'name': 'Nome',
    'surname': 'Cognome',
    'fullname': 'Nominativo',
    'id': 'Matricola',
    'sort': 'Cognome',
    'columns': ['Matricola', 'Nominativo'],
    'skip': 20
}

class Students(object):
    def __init__(self, filename=None):
        if filename is not None:
            self.load(filename)
        else:
            self.filename = None
            self.data = pd.DataFrame()

    def load(self, filename):
        pub.sendMessage("file.loading", status="loading", file=os.path.basename(filename))
        try:    
            students = pd.read_excel(filename, skiprows=config['skip'])
            students[config['fullname']] = students[config['name']] + ' ' + students[config['surname']]
            students.sort_values(config['sort'], inplace=True)
            students.reset_index(inplace=True)
            self.filename = filename
            self.data = students[config['columns']]
            pub.sendMessage("file.loaded", status="loaded", file=os.path.basename(self.filename))
        except Exception as e:
            pub.sendMessage("file.error", status="error", error=str(e))
