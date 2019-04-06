"""
A model for the list of questions
"""

import wx
from pubsub import pub
import logging
import gettext
_ = gettext.gettext
import mistletoe
import yaml
import re
import shutil
from pathlib import Path
import glob

YAML_HEADER_REGEX = re.compile(r'---([\s\S]+?)---', re.MULTILINE)
QUESTION_DELIMITER_REGEX = re.compile(r"\n---")

class Questions(object):
    def __init__(self, directory=None):
        self.directory = directory
        self.questions = {}
        self.logger = wx.GetApp().logger

    def load_questions(self, directory, config='config.md'):
        pub.sendMessage('questions.load.started')
        try:
            source_dir = Path(directory) 
            with open(source_dir / config, 'r') as f:                
                content = f.read()
                m = re.match(YAML_HEADER_REGEX, content)
                self.configuration = yaml.load(m.group(1))
                self.exam_header = content[m.end(1):]
            self.configuration["config"] = config
            self.questions = []
            filenames = filter(lambda f: f != source_dir / config, source_dir.glob('**/*.md'))
            for filename in filenames:
                self.questions.append(self.load_question_file(filename, source_dir))
            pub.sendMessage('questions.load.loaded', number=len(self.questions))
        except Exception as e:
            self.logger.log(logging.ERROR, str(e))
            pub.sendMessage('questions.load.error', error=str(e))
    
    def load_question_file(self, filename, directory):
        with open(filename, 'r') as f:
            content = f.read()
            m = re.match(YAML_HEADER_REGEX, content)
            settings = yaml.load(m.group(1))
            questions = QUESTION_DELIMITER_REGEX.split(content[m.end(1):])
            return { 
                'filename': str(filename.relative_to(directory)),
                'settings': settings,
                'content': list(map(lambda s: s.strip(), questions)) 
            }

    def write_question_file(self, question):        
        pub.sendMessage('questions.save.saving')
        try:
            template = '---\n{settings}\n---\n{content}'
            shutil.copy2(question['filename'], "{}.bak".format(question['filename']))
            with open(question['filename'], 'w') as f:
                f.write(template.format(**question))
            pub.sendMessage('questions.save.saved')
        except Exception as e:
            self.logger.log(logging.ERROR, str(e))
            pub.sendMessage('questions.save.error', error=str(e))
        