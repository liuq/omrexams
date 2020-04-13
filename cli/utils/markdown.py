import pylatex
from mistletoe import block_token, span_token, Document
from itertools import chain
from mistletoe.base_renderer import BaseRenderer
from mistletoe.html_renderer import HTMLRenderer
from mistletoe.latex_renderer import LaTeXRenderer
import random
from . crypt import vigenere_encrypt
import re
import logging
import click
import os
import xml.etree.ElementTree as ET
 
logger = logging.getLogger("omrexams")

class PreambleEnvironment(pylatex.base_classes.Environment):
    """
    A class representing a custom LaTeX environment for the preamble.
    """
    _latex_name = 'minipage'
    packages = []    
    escape = False
    content_separator = "\n"

    def __init__(self):
        super().__init__(arguments=[pylatex.NoEscape(r'\textwidth')])

class QuestionsEnvironment(pylatex.base_classes.Environment):
    """
    A class representing a custom LaTeX environment.

    This class represents a custom LaTeX environment named
    ``questions``.
    """

    _latex_name = 'questions'
    packages = []
    escape = False
    content_separator = "\n"

# Define a custom renderer back to markdown so that it can be further processed 
# into latex later
class QuestionMarker(span_token.SpanToken):
    pattern = re.compile(r"\[([ |x])\] {0,1}")

    def __init__(self, match):
        self.marker = match.group(1)

class QuestionTopic(span_token.SpanToken):
    pattern = re.compile(r"{topic:#([\w-]+)}")

    def __init__(self, match):
        self.id = match.group(1)

class Lines(span_token.SpanToken):
    pattern = re.compile(r"{lines:(\d*\.\d+|\d+)([^\d]+)}")

    def __init__(self, match):
        self.lines = r'\fillwithdottedlines{' + match.group(1) + match.group(2) + '}'

class OpenQuestion(span_token.SpanToken):
    pattern = re.compile(r"({open-question})")
        
class QuestionList(block_token.List):
    pattern = re.compile(r'(?:\d{0,9}[.)]|[+\-*]) {0,1}\[[ |x]\](?:[ \t]*$|[ \t]+)')

class QuestionBlock(block_token.BlockToken):
    """
    Question Block is identified by a horizontal rule with at least 3 elements at the very beginning of the line
    """
    pattern = re.compile(r'^(?:-{3,})\s*$')

    def __init__(self, lines):
        super().__init__(lines, block_token.tokenize)

    @classmethod
    def start(cls, line):        
        return cls.pattern.match(line)

    @classmethod
    def read(cls, lines):
        next(lines) # skip the first line
        line_buffer = [] 
        next_line = lines.peek()
        while next_line is not None and not cls.pattern.match(next_line):
            line_buffer.append(next(lines))
            next_line = lines.peek()        
        return line_buffer

class QuestionRenderer(LaTeXRenderer):   
    def __init__(self, *extras, **kwargs):
        """
        Args:
            extras (list): allows subclasses to add even more custom tokens.
        KeywordArgs:
            language: document language (to be used with polyglossia)
            student_no: matriculation number of the student
            student_name: name of the student
            exam: exam name
            date: exam date
        """
        self.record_answers = False
        self.questions = []
        # TODO: check parameter coherence
        self.parameters = kwargs
        super().__init__(*chain([QuestionMarker, QuestionTopic, QuestionList, QuestionBlock, Lines], extras))
        
    def render_question_marker(self, token):
        if not self.record_answers:
            raise ValueError("Probably a misplaced question marker has been used (i.e., a list not starting with it) for question \"{}\"".format(self.questions[-1]['question']))
        if token.marker != ' ':
            self.questions[-1]['answers'].append(True)
        else:
            self.questions[-1]['answers'].append(False)            
        return ''

    def render_question_topic(self, token):
        if not self.parameters.get('test', False):
            return ''
        else:
            return '\\fbox{' + token.id + '}'

    
    def render_lines(self, token):
        return token.lines

    def render_image(self, token):
        self.packages['graphicx'] = []
        self.packages['adjustbox'] = ['export']
        path = os.path.realpath(token.src)
        if not os.path.isabs(path):
            path = os.path.join(self.parameters.get('basedir'), path)
        return '\n\\includegraphics[max width=\\linewidth]{{{}}}\n'.format(path)

    def render_question_block(self, token):
        # possibly, the first question could start without a marker 
        # and could contain the heading of the section
        self.questions.append({ 'question': "", 'answers': [], 'permutation': [] })
        inner = self.render_inner(token)
        return '\n\\begin{{minipage}}{{\\linewidth}}\n{inner}\n\\end{{minipage}}\n'.format(inner=inner)

    def render_table_row(self, token):
        cells = [self.render(child) for child in token.children]
        return ' & '.join(cells) + ' \\\\\n'
    
    def render_heading(self, token):
        if not self.parameters.get('test', False):
            if token.level > 2:
                inner = self.render_inner(token).strip()
                return '{inner}\n\\newline'.format(inner=inner)
            elif token.level == 1:
                return ''
            template = "\question\n{inner}"
            inner = self.render_inner(token).strip()
            self.questions[-1]['question'] = inner 
            return template.format(inner=inner)  
        else:
            if token.level != 2:
                return super().render_heading(token)
            else:
                template = "\question\n{inner}"
                inner = self.render_inner(token).strip()
                self.questions[-1]['question'] = inner                                    
                return template.format(inner=inner)  

    def render_list(self, token):
        self.packages['listings'] = []
        template = '\\begin{{{tag}}}\n{inner}\\end{{{tag}}}\n'
        tag = 'enumerate' if token.start is not None else 'itemize'
        inner = self.render_inner(token)
        if inner:
            return template.format(tag=tag, inner=inner)
        else:
            return ""

    def custom_render_list_item(self, token):
        inner = self.render_inner(token)
        if inner:
            return '\t\\item {}\n'.format(inner)
        else:
            return ""

    def render_question_list(self, token):
        if not self.parameters.get('test', False):
            template = " \\omrchoices{{{choiceno}}}\n\\begin{{choices}}\n{inner}\n\\end{{choices}}\n"
        else:
            template = "\n\\begin{{choices}}\n{inner}\n\\end{{choices}}\n"
        if self.parameters.get('oneparchoices', False):
            template = template.replace('{choices}', '{oneparchoices}')
            template = template.replace('\\begin', '\\par\n\\begin')
            template += '\n\\vspace{{\\baselineskip}}\n'
        self.record_answers = True
        # TODO: get a random permutation, the same for both the multiple choices and the answers
        answers = ['\n\t\\choice {inner}'.format(inner=self.render_list_item(child)) for child in token.children]
        if len(answers) != len(self.questions[-1]['answers']):
            raise ValueError("Answers mismatch for question \"{}\" ({}/{})".format(self.questions[-1]['question'], 
                len(answers), len(self.questions[-1]['answers'])))
        self.record_answers = False
        if self.parameters.get('test', False):
            answers = list(map(lambda i: answers[i] if not self.questions[-1]['answers'][i] else answers[i].replace('\\choice', '\\correctchoice'), range(len(answers))))
        if not any(self.questions[-1]['answers']):
            click.secho("Warning: question \"{}\" has no correct answer".format(self.questions[-1]['question']), fg='yellow')
            logger.warning("No correct answer for current question")
        permutation = list(range(len(answers)))
        if self.parameters.get('shuffle', True):
            random.shuffle(permutation)
            self.questions[-1]['answers'] = [self.questions[-1]['answers'][permutation[i]] for i in range(len(answers))]
            answers = [answers[permutation[i]] for i in range(len(answers))]
        self.questions[-1]['permutation'] = permutation
        inner = ''.join(answers)
        return template.format(inner=inner, choiceno=len(self.questions[-1]['answers']))

    def render_block_code(self, token):
        self.packages['listings'] = []
        template = ('\n\\begin{{lstlisting}}{language}\n'
                    '{}'
                    '\\end{{lstlisting}}\n')
        inner = self.render_raw_text(token.children[0], False)
        if token.language:
            return template.format(inner, language="[language={}]".format(token.language))
        else:
            return template.format(inner, language="")
    
    def render_list_item(self, token):
        if not self.record_answers:
            return self.custom_render_list_item(token)
        else:
            return "".join(self.render(child) for child in token.children)
        #    raise Error("Once a question list is started all the list items must be questions")                               

    def render_document(self, token):
        if not self.parameters.get('test', False):
            return self.render_exam(token)
        else:
            return self.render_test(token)

    def render_exam(self, token):
        self.footnotes.update(token.footnotes)
        inner = self.render_inner(token)    
        solutions = []
        # get rid of the last, empty, question if is present
        if self.questions[-1]['question'] == '':
            self.questions.pop(-1)
        for q in self.questions:
            current = ""
            for i in range(len(q['answers'])):
                if q['answers'][i]:
                    current += chr(ord('A') + i)
            solutions.append(current)
        # encryption of the solution is the default option
        if self.parameters.get('encrypt', True): 
            solutions = vigenere_encrypt(','.join(solutions), self.parameters['student_no'])
        else:
            solutions = ','.join(solutions)        
        options = []
        if self.parameters.get('circled', False):
            options.append('circled')
        if self.parameters.get('usesf'):
            options.append('sflabel')
            
        doc = pylatex.Document('basic')
        doc.documentclass = pylatex.Command('documentclass',
            options=options,
            arguments=['omrexam']
        )
#        pylatex.Document(documentclass='omrexam', 
#            inputenc=None, lmodern=False, fontenc=None, textcomp=None,
#            options=options)
        doc.preamble.append(pylatex.Package('polyglossia'))
        doc.preamble.append(pylatex.Command('setdefaultlanguage', self.parameters.get('language', '').lower()))
        for package in self.packages.keys():
            if not self.packages[package]:
                doc.preamble.append(pylatex.Package(package))
            else:
                doc.preamble.append(pylatex.Package(package, options=self.packages[package]))
        doc.preamble.append(pylatex.Package('listings'))
        doc.preamble.append(pylatex.Command('examname', self.parameters['exam']))
        doc.preamble.append(pylatex.Command('student', 
            arguments=[self.parameters['student_no'], self.parameters['student_name']]))
        doc.preamble.append(pylatex.Command('date', self.parameters['date'].strftime('%d/%m/%Y')))
        doc.preamble.append(pylatex.Command('solution', solutions))
        doc.preamble.append(pylatex.Command('header', pylatex.NoEscape(self.parameters['header'])))
        doc.preamble.append(pylatex.Command('lstset', pylatex.NoEscape(r"basicstyle=\ttfamily,breaklines=true")))
        doc.append("\n")
        with doc.create(PreambleEnvironment()):
            doc.append(self.parameters['preamble'])
        doc.append(pylatex.Command('vspace', '0.75em'))
        with doc.create(QuestionsEnvironment()):
            doc.append(inner)
        return doc

    def render_test(self, token):
        self.footnotes.update(token.footnotes)
        inner = self.render_inner(token)                
        doc = pylatex.Document(documentclass='omrexam', 
            inputenc=None, lmodern=False, fontenc=None, textcomp=None)
        doc.preamble.append(pylatex.Package('polyglossia'))
        doc.preamble.append(pylatex.Command('setdefaultlanguage', self.parameters['language']))
        doc.preamble.append(pylatex.Package('listings'))
        doc.preamble.append(pylatex.Command('examname', self.parameters['exam']))
        doc.preamble.append(pylatex.Command('student', 
            arguments=["00000", "Student Name"]))
        doc.preamble.append(pylatex.Command('date', self.parameters['date'].strftime('%d/%m/%Y')))
        doc.preamble.append(pylatex.Command('solution', ''))
        doc.preamble.append(pylatex.Command('header', pylatex.NoEscape(self.parameters['header'])))
        doc.preamble.append(pylatex.Command('lstset', pylatex.NoEscape(r"basicstyle=\ttfamily,breaklines=true")))
        doc.preamble.append(pylatex.Command('printanswers'))
        doc.append("\n")
        with doc.create(PreambleEnvironment()):
            doc.append(self.parameters['preamble'])
        doc.append(pylatex.Command('vspace', '1em'))
        with doc.create(QuestionsEnvironment()):
            doc.append(inner)
        return doc
            
class DocumentStripRenderer(LaTeXRenderer):
    def __init__(self, *extras, **kwargs):
        """
        Args:
            extras (list): allows subclasses to add even more custom tokens.
        KeywordArgs:
            basedir: the base directory for relative paths
        """
        self.record_answers = False
        self.questions = []
        # TODO: check parameter coherence
        self.parameters = kwargs
        super().__init__(*chain([], extras))

    def render_table_row(self, token):
        cells = [self.render(child) for child in token.children]
        return ' & '.join(cells) + ' \\\\\n'
    
    def render_document(self, token):
        return self.render_inner(token)

    def render_image(self, token):
        self.packages['graphicx'] = []
        self.packages['adjustbox'] = ['export']
        path = os.path.realpath(token.src)
        if not os.path.isabs(path):
            path = os.path.join(self.parameters.get('basedir'), path)
        return '\n\\includegraphics[max width=\\linewidth]{{{}}}\n'.format(path)

"""
Provides MathJax support for rendering Markdown with LaTeX to html.
"""

from mistletoe.html_renderer import HTMLRenderer
from mistletoe.latex_renderer import LaTeXRenderer

class CheckmarkRenderer(HTMLRenderer, LaTeXRenderer):
    def __init__(self, *extras, **kwargs):
        """
        Args:
            extras (list): allows subclasses to add even more custom tokens.
        """
        self.record_answers = False
        self.questions = []
        # TODO: check parameter coherence
        self.parameters = kwargs
        super().__init__(*chain([QuestionMarker], extras))

    """
    MRO will first look for render functions under HTMLRenderer,
    then LaTeXRenderer.
    """
    mathjax_src = '<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js?config=TeX-MML-AM_CHTML"></script>\n'

    def render_math(self, token):
        """
        Ensure Math tokens are all enclosed in two dollar signs.
        """
        if token.content.startswith('$$'):
            return self.render_raw_text(token)
        return '${}$'.format(self.render_raw_text(token))

    def render_document(self, token):
        """
        Append CDN link for MathJax to the end of <body>.
        """
        return super().render_document(token) + self.mathjax_src

    def render_question_marker(self, token):
        template = '<input type="checkbox" {}/>'
        if token.marker != ' ':
            return template.format('checked')
        else:
            return template.format('')


class MoodleRenderer(BaseRenderer):   
    def __init__(self, *extras, **kwargs):
        """
        Args:
            extras (list): allows subclasses to add even more custom tokens.
        KeywordArgs:
            basedir: the base directory for relative paths
            section: the name of the section
        """
        self.questions = []
        self.open_questions = []
        # TODO: check parameter coherence
        self.parameters = kwargs
        super().__init__(*chain([QuestionMarker, QuestionTopic, QuestionList, QuestionBlock, OpenQuestion], extras))
        
    def render_question_marker(self, token):
        if not self.record_answers:
            raise ValueError("Probably a misplaced question marker has been used (i.e., a list not starting with it) for question \"{}\"".format(self.questions[-1]['question']))
        if token.marker != ' ':
            self.questions[-1]['answers'].append(True)
        else:
            self.questions[-1]['answers'].append(False)            
        return ''

    def render_question_topic(self, token):
        return ''
        # if not self.parameters.get('test', False):
        #     return ''
        # else:
        #     return '\\fbox{' + token.id + '}'

    
    def render_open_question(self, token):
        return ''

    def render_image(self, token):
        path = os.path.realpath(token.src)
        if not os.path.isabs(path):
            path = os.path.join(self.parameters.get('basedir'), path)
        # TODO: insert image as a base64 encoded file
        return ''

    def render_question_block(self, token):
        # possibly, the first question could start without a marker 
        # and could contain the heading of the section
        self.questions.append({ 'question': "", 'choices': [], 'answers': [] })
        inner = self.render_inner(token)
        return inner

    def render_table_row(self, token):
        cells = [self.render(child) for child in token.children]
        return ' | '.join(cells) + '\n'
    
    def render_heading(self, token):
        if token.level == 1:            
            return ''
        inner = self.render_inner(token).strip()
        if any(lambda c: type(c) == OpenQuestion for c in token.children):
            self.open_questions.append(inner)
        else:
            self.questions[-1]['question'] = inner 
        return ''  

    def render_list(self, token):
        inner = self.render_inner(token)
        if inner:
            return inner
        else:
            return ''

    def custom_render_list_item(self, token):
        inner = self.render_inner(token)
        if inner:
            return '- {}\n'.format(inner)
        else:
            return ""

    def render_question_list(self, token):
        self.record_answers = True
        answers = [self.render_list_item(child) for child in token.children]
        self.record_answers = False
        if not any(self.questions[-1]['answers']):
            click.secho("Warning: question \"{}\" has no correct answer".format(self.questions[-1]['question']), fg='yellow')
            logger.warning("No correct answer for current question")
        inner = ''.join(answers)
        return inner

    def render_block_code(self, token):
        template = ('```{language}\n'
                    '{}'
                    '```\n')
        inner = self.render_raw_text(token.children[0])
        if token.language:
            return template.format(inner, language=token.language)
        else:
            return template.format(inner, language="")
    
    def render_list_item(self, token):
        if not self.record_answers:
            return self.custom_render_list_item(token)
        else:
            self.questions[-1]['choices'].append(" ".join(self.render(child) for child in token.children))
            return ''
        #    raise Error("Once a question list is started all the list items must be questions")                               

    def render_questions(self, token):    
        def render_question(question):
            q = ET.Element('question', type='multichoice')
            name = ET.Element('name')
            _ = ET.SubElement(name, 'text')
            _.text = (question['question'][:30] + '...') if len(question['question']) > 33 else question['question']
            q.append(name)
            qtext = ET.Element('questiontext', format='markdown')
            _ = ET.SubElement(qtext, 'text')
            _.text = question['question']            
            q.append(qtext)
            _ = ET.Element('shuffleanswers')
            _.text = 'true'
            q.append(_)
            _ = ET.Element('answernumbering')
            _.text = 'ABCD'
            q.append(_)
            _ = ET.Element('single')
            n_correct = sum(filter(lambda a: a, question['answers'])) 
            if self.parameters.get('single', False):
                _.text = 'true'
                if n_correct != 1:
                    logger.warning(f'Question {question["question"]} has {n_correct} correct answers but the --single flag was specified')
            else:
                _.text = 'false'
            q.append(_)
            n = len(question['choices'])
            for i in range(n):
                choice, correct = question['choices'][i], question['answers'][i]
                if correct:
                    fraction = round(100 / n_correct)
                else:
                    fraction = round(self.parameters.get('penalty', -10))
                a = ET.Element('answer', format='markdown', fraction=f"{fraction}")
                _ = ET.SubElement(a, 'text')
                _.text = choice
                q.append(a)
            return q        


        self.footnotes.update(token.footnotes)
        inner = self.render_inner(token)    
        # get rid of the last, empty, question if is present
        if len(self.questions) > 1 and self.questions[-1]['question'] == '':
            self.questions.pop(-1)

        root = ET.Element('quiz')
        category = ET.SubElement(root, 'question', type='category')
         
        _ = ET.SubElement(category, 'category')
        _ = ET.SubElement(_, 'text')
        category = self.parameters.get('category', 'default')
        category = (category[:20] + "...") if len(category) >= 23 else category
        _.text = f"$course$/{category}"

        for q in self.questions:
            root.append(render_question(q))

        return ET.ElementTree(root)


    def render_open_questions(self, token):    
        def render_open_question(question):
            q = ET.Element('question', type='essay')
            name = ET.Element('name')
            _ = ET.SubElement(name, 'text')
            _.text = (question[:30] + '...') if len(question) > 33 else question
            q.append(name)
            qtext = ET.Element('questiontext', format='markdown')
            _ = ET.SubElement(qtext, 'text')
            _.text = question          
            q.append(qtext)
            _ = ET.Element('responseformat')
            _.text = 'editor'
            q.append(_)
            _ = ET.Element('responserequired')
            _.text = str(1)
            q.append(_)
            _ = ET.Element('responsefieldlines')
            _.text = str(15)
            q.append(_)
            _ = ET.Element('attachments')
            _.text = str(0)
            q.append(_)
            return q        

        self.footnotes.update(token.footnotes)
        inner = self.render_inner(token)    
        # get rid of the last, empty, question if is present
        if len(self.open_questions) > 1 and self.open_questions[-1] == '':
            self.open_questions.pop(-1)

        root = ET.Element('quiz')
        category = ET.SubElement(root, 'question', type='category')
            
        _ = ET.SubElement(category, 'category')
        _ = ET.SubElement(_, 'text')
        category = self.parameters.get('category', 'default')
        category = (category[:20] + "...") if len(category) >= 23 else category
        _.text = f"$course$/{category}"

        for q in self.open_questions:
            root.append(render_open_question(q))

        return ET.ElementTree(root)


        