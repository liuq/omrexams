import xml.dom as xml
from . generate import QUESTION_MARKER_RE, TITLE_RE, QUESTION_RE, OPEN_QUESTION_RE
from . utils.markdown import MoodleRenderer, Document
import os
import glob

class MoodleConverter:
    def __init__(self, questions_dir, single, penalty):
        self.questions_path = questions_dir
        self.single = single
        self.penalty = penalty

    def convert(self):
        for filename in glob.glob(os.path.join(self.questions_path, '*.md')):
            output_file = os.path.basename(filename).split('.')[0]
            questions = self.load_questions(filename)
            if questions:
                document = self.generate_xml(output_file, questions)
                document.write(output_file + '.xml', xml_declaration=True, encoding='utf-8')
            open_questions = self.load_open_questions(filename)
            if open_questions:
                document = self.generate_xml(output_file + '-open', open_questions)
                document.write(output_file + '-open.xml', xml_declaration=True, encoding='utf-8')

    def load_questions(self, filename):
        with open(filename, 'r') as f:
            content = f.read()

        questions = list(filter(lambda q: not TITLE_RE.match(q) and not OPEN_QUESTION_RE.match(q), QUESTION_MARKER_RE.split(content)))
        return questions
    
    def load_open_questions(self, filename):
        with open(filename, 'r') as f:
            questions = list(filter(lambda q: OPEN_QUESTION_RE.match(q), QUESTION_MARKER_RE.split(f.read())))
            return questions
        return []

    def generate_xml(self, category, questions):
        with MoodleRenderer(basedir=os.path.realpath(self.questions_path), single=self.single, penalty=self.penalty, category=category) as renderer:
            content = '---\n' + '\n---\n'.join(map(lambda q: q, questions)) + '\n---\n'
            document = renderer.render_questions(Document(content))
            return document