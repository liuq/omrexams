#!/usr/bin/env python3

import glob
import platform
from ctypes.util import find_library
import os

# This hack is needed to take care of non-export of DYLD_LIBRARY_PATH using the env 
if platform.system() == 'Darwin' and platform.processor() == 'arm' and not find_library('zbar'):
    os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = '/opt/homebrew/lib'

import click
from datetime import datetime as dt
import dateparser as dp
import yaml
from omrexams import Generate, Sort, Correct, Mark, MoodleConverter, UpdateCorrected, MarkdownConverter, __version__ #, main_ui
import pandas as pd
import xlrd
import re
import logging
import click_log
import sys
import math
from tinydb import TinyDB, Query, where
import json
from .mark import custom_correction
import numpy as np
from tabulate import tabulate

logger = logging.getLogger("omrexams")
click_log.basic_config(logger)

class Datetime(click.ParamType):
    '''
    A datetime object parsed via dateparser.parse.
    '''

    name = 'date'

    def convert(self, value, param, ctx):
        if value is None:
            return value

        if isinstance(value, dt):
            return value

        if not isinstance(value, str):
            self.fail(f'The provided date is not a string "{value}', param, ctx)

        result = dp.parse(value)
        if result is None:
            self.fail(f'Could not parse datetime string "{value}"', param, ctx)
        return result

class OptionRequiredIf(click.Option):
    """
    Option is required if the context has `option` set to `value`
    """

    def __init__(self, *a, **k):
        try:
            option = k.pop('option')            
            value  = k.pop('value')
        except KeyError:
            raise(KeyError("OptionRequiredIf needs the option and value "
                           "keywords arguments"))

        click.Option.__init__(self, *a, **k)
        self._option = option
        self._value = value

    def full_process_value(self, ctx, value):
        value = super(OptionRequiredIf, self).full_process_value(ctx, value)
        if value is None and ctx.params[self._option] == self._value:
            msg = f'Required if --{self._option}={self._value}'
            raise click.MissingParameter(ctx=ctx, param=self, message=msg)
        return value

DATETIME = Datetime()

@click.group()
@click.version_option(version=__version__)
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, debug):
    """Manage multiple-choice OMR exams.
    """
    if not debug:
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.WARN)

@cli.command()
@click.option('--config', type=click.Path(exists=True, resolve_path=True), required=True, default=os.path.join('.', 'config.yaml'))
@click.option('--students', '-s', type=click.Path(exists=True, resolve_path=True), required=False)
@click.argument('questions_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True), default=os.path.join('.', 'questions'), required=True)
@click.option('--count', '-n', type=int, option='students', value=None, cls=OptionRequiredIf)
@click.option('--serial', type=int, default=1)
@click.option('--output_prefix', '-o', type=click.Path(resolve_path=True), required=False, 
    help='The output prefix (i.e., the name of the pdf and json data files) [default: \'exam-{date}{{.pdf|.json}}\'')
@click.option('--date', '-d', type=DATETIME, prompt='Enter the exam date',  
    default=lambda: dt.now().strftime("%Y-%m-%d"))
@click.option('--seed', '-r', type=int, default=int(dt.now().strftime('%s')))
@click.option('--additional', '-a', type=int, required=False, default=0, help='Number of additional exam sheets')
@click.option('--paper', '-p', type=click.Choice(['A4', 'A3'], case_sensitive=False), default='A4', required=False)
@click.option('--folded/--no-folded', is_flag=True, default=None, help='State whether the exam sheets are folded (only for A3 paper)')
@click.option('--rotated/--no-rotated', is_flag=True, default=None, help='State whether the exam folded sheets are alternatively rotated (only for A3 paper)')
@click.option('--split', type=int, help='Divide the output into multiple files by splitting', required=False)
@click.option('--yes', '-y', is_flag=True, type=bool, required=False, default=False, help='Answer yes to all prompt requests')
@click.pass_context
def generate(ctx, config, students, questions_dir, count, serial, output_prefix, date, seed, additional, paper, folded, rotated, split, yes):
    """
    Generates the set of exams for the given amount of students (either personalized or anonymous).
    """
    if split is not None and split < 0:
        click.secho("The --split option must be a positive integer", fg='red')
        sys.exit(-1)

    if folded is None and paper.upper() == 'A3':
        click.secho("The --folded option with A3 format is not specified, assuming folded sheets", fg='yellow')
        folded = True
    
    if paper.upper() == 'A3' and rotated is None:
        click.secho("The --rotated option with A3 format is not specified, assuming not rotated sheets", fg='yellow')
        rotated = False

    if folded and paper.upper() != 'A3':
        click.secho("The --folded option can be used only with A3 paper", fg='red')
        sys.exit(-1)

    if rotated and paper.upper() != 'A3':
        click.secho("The --rotated option can be used only with A3 paper", fg='red')
        sys.exit(-1)

    config_file = config
    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.Loader)
    config['basedir'] = os.path.dirname(config_file)

    if not output_prefix:        
        output_prefix = f'exam-{date.strftime("%Y-%m-%d")}'

    if additional is None and students is not None:
        additional = click.prompt("Generate a number of additional exams?", default=5)

    if paper is None:
        paper = config.get('paper', 'A4')
    paper = paper.upper()    

    if split is None and os.path.exists(f"{output_prefix}.pdf"):
        if yes or click.confirm(f"Data output {output_prefix}.pdf exists, overwrite it?", default=True):
            os.remove(f"{output_prefix}.pdf")
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)
    elif split is not None and glob.glob(f"{output_prefix}*.pdf"):
        if yes or click.confirm(f"Data output {output_prefix}*.pdf exist, overwrite the split files?", default=True):
            for f in glob.glob(f"{output_prefix}*.pdf"):
                os.remove(f)
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)
    
    if os.path.exists(f"{output_prefix}.json"):
        if yes or click.confirm(f"Data output {output_prefix}.json exists, overwrite it?", default=True):
            os.remove(f"{output_prefix}.json")
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)

    if not students and not count:
        click.secho("You should provide either an excel file with the student list or the number of exams to generate", fg='red')
        sys.exit(-1)

    if students:
        try:    
            click.secho('Reading excel file', fg='red', underline=True)
            skip = 0
            # check whether the file needs to be partially skipped
            if config['excel'].get('data_marker') is not None:
                marker = config['excel']['data_marker'].get('skip_until')
                column = config['excel']['data_marker'].get('on_column', 0)
                click.secho(f'Searching for data marker "{marker} in column {column}"', fg='cyan')
                wb = xlrd.open_workbook(students)
                sheet = wb.sheet_by_index(0)
                for i in range(sheet.nrows):
                    row = sheet.row(i)
                    cell = row[column]
                    value = cell.value if isinstance(cell.value, str) else str(cell.value)
                    if re.match(marker, value):
                        skip = i
                        break
            if skip > 0:
                click.secho(f'Skipping {skip} rows', fg='cyan')
            student_list = pd.read_excel(students, skiprows=skip + 1)
            click.secho(f'Columns found: {student_list.columns.tolist()}', fg='cyan')
            fields = config['excel']['fields']
            student_list[fields.get('fullname', 'Full Name')] = student_list[fields.get('name')] + ' ' + student_list[fields.get('surname')]
            student_list.reset_index(inplace=True)
            student_list = [tuple(r) for r in student_list[[fields.get('id'), fields.get('fullname', 'Full Name')]].to_records(index=False)] 
            click.secho(f'Processing done, {len(student_list)} students found', fg='cyan')
            if additional > 0:                
                student_list += [(i, "Additional student") for i in range(additional)]
                click.secho(f'Added further {additional} students', fg='cyan')
        except Exception as e:
            logger.error(f"While reading the students excel file {students}: {str(e)}")
            sys.exit(-1)
    else:
        click.secho(f'Creating anonymous exams for {count} students', fg='red', underline=True)
        click.secho(f'Starting serials from {serial}', fg='cyan')
        f = f"{{:0{math.ceil(math.log10(serial + count))}}}"
        student_list = list(map(lambda s: (f.format(s), ""), range(serial, serial + count)))
        click.secho(f'Seed used for the random generator {seed}', fg='magenta')

    generator = Generate(config, questions_dir, output_prefix, students=student_list, 
                         exam_date=date, seed=seed, paper=paper, folded=folded, rotated=rotated, split=split)
    generator.process()

@cli.command()
@click.option('--config', type=click.Path(exists=True, resolve_path=True), required=True, default=os.path.join('.', 'config.yaml'))
@click.argument('questions_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True), default=os.path.join('.', 'questions'))
@click.option('--output', '-o', type=click.Path(resolve_path=True), default=os.path.join('.', 'exam-test.pdf'))
@click.option('--yes', '-y', is_flag=True, type=bool, required=False, default=False, help='Answer yes to all prompt requests')
@click.pass_context
def test(ctx, config, questions_dir, output, yes):
    """
    Generates a comprehensive pdf file with all the questions.
    """
    config_file = config
    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.Loader)
    config['basedir'] = os.path.dirname(config_file)


    if os.path.exists(output):
        if yes or click.confirm(f"Data output {output} exists, overwrite it?", default=True):
            os.remove(output)
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)

    generator = Generate(config, questions_dir, ".".join(output.split(".")[:-1]), test=True)
    generator.process()

@cli.command()
@click.argument('scanned', type=click.Path(exists=True, file_okay=True, dir_okay=True, resolve_path=True),  nargs=-1, required=True)
@click.option('--sorted_dir', '-s', type=click.Path(exists=False, file_okay=False, resolve_path=True), default='sorted', prompt='Enter the directory name where to store the sorted exams')
@click.option('--datafile', '-d', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True), required=False)
@click.option('--resolution', '-r', default=300)
@click.option('--paper', '-p', type=click.Choice(['A4', 'A3'], case_sensitive=False), default='A4', required=False)
@click.option('--yes', '-y', is_flag=True, type=bool, required=False, default=False, help='Answer yes to all prompt requests')
@click.pass_context
def sort(ctx, scanned, sorted_dir, datafile, resolution, paper, yes):
    """
    Sorts a set of pdf scanned documents into a series of png images, one for each sheet.
    """
    if os.path.exists(sorted_dir):
        if yes or click.confirm(f"Sorted directory {sorted_dir} exists, overwrite its content?", default=True):
            pass
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)

    sorter = Sort(scanned, sorted_dir, datafile)
    sorter.sort(resolution, paper.upper())


@cli.command()
@click.argument('sorted_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True), default='sorted')
@click.option('--corrected', '-c', type=click.Path(exists=False, file_okay=True, resolve_path=True), default=os.path.join('.', 'corrected-exam.pdf'))
@click.option('--datafile', '-d', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.option('--resolution', '-r', default=300)
@click.option('--compression', '-z', type=int, default=50)
@click.option('--yes', '-y', is_flag=True, type=bool, required=False, default=False, help='Answer yes to all prompt requests')
@click.pass_context
def correct(ctx, sorted_dir, corrected, datafile, resolution, compression, yes):  
    """
    Corrects a set of pages creating a (compressed) corrected pdf file and storing the correction data into a .json file
    """

    if os.path.exists(corrected):
        if yes or click.confirm(f"Corrected file {corrected} exists, overwrite its content?", default=True):
            pass
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)

    corrector = Correct(sorted_dir, corrected, datafile, resolution, compression)
    corrector.correct()

@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.option('--output', '-o', type=click.Path(exists=False, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.option('--weights', '-w', type=click.Path(exists=False, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=False)
@click.option('--include_missing', '-m', type=bool, required=False, default=False, help='Include also missing exams in the report')
@click.option('--yes', '-y', is_flag=True, type=bool, required=False, default=False, help='Answer yes to all prompt requests')
@click.pass_context
def mark(ctx, datafile, output, weights, include_missing, yes):
    """
    Performs the marking of corrected exams and produces an excel file with the grading
    """
    if os.path.exists(output):
        if yes or click.confirm(f"Marking file {output} exists, overwrite its content?", default=True):
            pass
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)
    marker = Mark(datafile, output)
    if weights:
        with open(weights) as f:
            w = json.load(f)
            marker.mark(include_missing=include_missing, weights=w)
    else:
        marker.mark(include_missing=include_missing)


@cli.command()
@click.argument('questions_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True), default=os.path.join('.', 'questions'), required=True)
@click.option('-s', '--single', is_flag=True, default=False, help='State whether the questions have a single correct answer (a radio button will be rendered in moodle)')
@click.option('-p', '--penalty', type=int, help='Penalty (in percentage) to be applied to wrong answers')
@click.pass_context
def to_moodle(ctx, questions_dir, single, penalty):
    """
    Converts the questions database in the moodle XML format
    """
    moodle_converter = MoodleConverter(questions_dir, single, penalty)
    moodle_converter.convert()


@cli.command()
@click.argument('moodle_file', type=click.Path(exists=True, file_okay=True, resolve_path=True, writable=True), required=True)
@click.argument('questions_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True), default=os.path.join('.', 'questions'), required=True)
@click.option('--yes', '-y', is_flag=True, type=bool, required=False, default=False, help='Answer yes to all prompt requests')
@click.pass_context
def from_moodle(ctx, moodle_file, questions_dir, yes):
    """
    Converts a moodle XML file into a questions database 
    """      
    markdown_converter = MarkdownConverter(moodle_file, questions_dir)    
    if os.path.exists(markdown_converter.file_name):
        if yes or click.confirm(f"Questions file {markdown_converter.file_name} exists, overwrite its content?", default=True):
            os.remove(markdown_converter.file_name)
        else:
            click.secho("Nothing done", fg='bright_yellow')
            sys.exit(0)  
    markdown_converter.convert()

@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.option('--output', '-o', type=click.Path(exists=False, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.option('--yes', '-y', is_flag=True, type=bool, required=False, default=False, help='Answer yes to all prompt requests')
@click.pass_context
def report(ctx, datafile, output, yes):
    """
    Generates a report with the different questions and the correct/wrong/unanswered ratio
    """
    with TinyDB(datafile) as db:
            df = pd.DataFrame()
            Exam = Query()
            for exam in db.table('correction').all():
                e = db.table('exams').get(Exam.student_id == exam['student_id'])
                correct_answers = list(map(set, exam['correct_answers']))
                given_answers = list(map(set, exam['given_answers']))
                question_size = list(map(lambda q: len(q[3]), e['questions']))
                for i in range(len(correct_answers)):
                    marked, correct, missing, wrong = given_answers[i], correct_answers[i] & given_answers[i], correct_answers[i] - given_answers[i], given_answers[i] - correct_answers[i]
                    df = pd.concat([df, pd.DataFrame([{ 'filename': e['questions'][i][0], 'question': e['questions'][i][1], 'correct_ratio': len(correct) / len(correct_answers[i]), 'missing_ratio': len(missing) / len(correct_answers[i]), 'wrong_ratio': len(wrong) / len(correct_answers[i]), 'options': question_size[i], 'no_correct_answers': len(correct_answers[i]) }])])                    
            df = df.groupby(['filename', 'question']).agg({ 'correct_ratio': ['count', 'sum', 'mean', 'std'], 'missing_ratio': ['mean', 'std'], 'wrong_ratio': ['mean', 'std'], 'options': 'min', 'no_correct_answers': 'min' })
            df.to_excel(output)
            
@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.argument('student_id', type=str, required=True)
@click.argument('question', type=int, required=True)
@click.argument('given_answers', type=str, required=True)
@click.pass_context
def force_answer(ctx, datafile, student_id, question, given_answers):
    """
    Forces the given answers for student_id and question. The answers should be expressed as a string without spaces, e.g. AEF
    """
    with TinyDB(datafile) as db:
        Exam = Query()
        exam = db.table('exams').get(Exam.student_id == student_id)
        correction = db.table('correction').get(Exam.student_id == student_id)
        if not correction:
            # table = db.table('correction')
            # table.insert({ 'student_id': student_id, 'given_answers': [""] * len(exam['answers']), 'correct_answers': exam['answers'] })
            # correction = db.table('correction').get(Exam.student_id == student_id)
            correction = { 'student_id': student_id, 'given_answers': [""] * len(exam['answers']), 'correct_answers': exam['answers'] }
        try:
            given = correction['given_answers'][question - 1]
            new_given = list(given_answers.upper())
            if (set(given) == set(new_given)):
                click.secho(f"The current and the updated given answers for question {question} and student {student_id} are equal {set(given)}, nothing to do", fg="yellow")
                sys.exit(0)
            new_given_order = map(lambda l: ord(l) - ord('A'), new_given)
            question_size = len(exam['questions'][question - 1][3])
            if any(o not in range(question_size) for o in new_given_order):
                click.secho(f"Question {question} for student {student_id} admits answers from 'A' to {chr(question_size - 1 + ord('A'))} but given {set(new_given)}", fg="red")
                sys.exit(-1)
            click.secho(f"Updating question {question} for student {student_id} with answers {set(new_given)} instead of {set(given)}", fg="green")
            correction['given_answers'][question - 1] = new_given
            db.table('correction').upsert(correction, where('student_id') == student_id)
        except IndexError as e:
            click.secho(f"Question {question} is not appearing in the list of given answers for student {student_id}", fg="red")
            sys.exit(-1)   

@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.argument('student_id', type=str, required=True)
@click.pass_context
def force_answers(ctx, datafile, student_id):
    """
    Forces the given answers for student_id. It prompts the answers for each question. The answers should be expressed as a string without spaces, e.g. AEF
    """
    with TinyDB(datafile) as db:
        Exam = Query()
        exam = db.table('exams').get(Exam.student_id == student_id)
        correction = db.table('correction').get(Exam.student_id == student_id)
        if not correction:
            correction = { 'student_id': student_id, 'given_answers': [""] * len(exam['answers']), 'correct_answers': exam['answers'] }
        for i, (q, reference_correct, given) in enumerate(zip(exam['questions'], correction['correct_answers'], correction['given_answers'])): 
            click.secho(f"Question {i + 1} from {q[0]}/{q[1]}; stored answer {given}", fg="cyan")
            given_answers = click.prompt("Enter the updated value (format single string, e.g., AC): ", type=str, default="".join(sorted(given)))
            #given = correction['given_answers'][question - 1]
            new_given = list(given_answers.upper())
            if (set(given) == set(new_given)):
                click.secho(f"The current and the updated given answers for question {i + 1} and student {student_id} are equal {set(given)}, nothing to do", fg="yellow")
                continue
            new_given_order = map(lambda l: ord(l) - ord('A'), new_given)
            question_size = len(q[3])
            if any(o not in range(question_size) for o in new_given_order):
                click.secho(f"Question {i + 1} for student {student_id} admits answers from 'A' to {chr(question_size - 1 + ord('A'))} but given {set(new_given)}", fg="red")
                sys.exit(-1)
            click.secho(f"Updating question {i + 1} for student {student_id} with answers {set(new_given)} instead of {set(given)}", fg="green")
            correction['given_answers'][i] = new_given
            db.table('correction').upsert(correction, where('student_id') == student_id)

@cli.command()
@click.argument('question_files', type=click.Path(exists=True, file_okay=True, resolve_path=True), required=True, nargs=-1)
@click.option('--datafile', '-d', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.option('--dry-run/--exec', type=bool, required=False, help='If set, choices are constrained to be in the same paragraph', default=True)
@click.pass_context
def update_corrected(ctx, question_files, datafile, dry_run):
    """
    Updates the set of corrected answers according to a modification of the questions (e.g., because an inversion of cases). It works only if the answers do not change (neither in order nor in their meaning) but the correct one(s) have been changed.
    """
    update_corrected = UpdateCorrected(question_files, datafile)
    update_corrected.process(dry_run)

@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.argument('question_file', type=str, required=True)
@click.argument('question', type=int, required=True)
@click.pass_context
def students_with_question(ctx, datafile, question_file, question):
    """
    Returns the ids of the students having a specific question
    """
    with TinyDB(datafile) as db:
        for e in db.table('exams'):
            for q in e['questions']:
                if q[0] == question_file and q[1] == question:
                    print(e['student_id'])
                    break

@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.argument('student_id', type=str, required=True)
@click.pass_context
def get_correction_mask(ctx, datafile, student_id):
    """
    Gets the correction mask for a given student
    """
    with TinyDB(datafile) as db:
        Exam = Query()
        exam = db.table('exams').get(Exam.student_id == student_id)
        for i, q in enumerate(exam['questions']):
            print(i + 1, q[2])

@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.argument('student_id', type=str, required=True)
@click.option('--markdown', is_flag=True, help='Output the result in markdown format')
@click.option('--excel', type=click.Path(resolve_path=True, writable=True), help='Output the result in an excel file')
@click.pass_context
def get_answers(ctx, datafile, student_id, markdown, excel):
    """
    Gets the answers for a given student
    """
    with TinyDB(datafile) as db:
        Exam = Query()
        Correction = Query()
        exam = db.table('exams').get(Exam.student_id == student_id)    
        correction = db.table('correction').get(Correction.student_id == student_id)  
        p = np.array([0.0, 0.0])
        table = []
        for i, (q, reference_correct, given) in enumerate(zip(exam['questions'], correction['correct_answers'], correction['given_answers'])): 
            q_size = len(q[3])
            marked, correct, missing, wrong = set(given), set(reference_correct) & set(given), set(reference_correct) - set(given), set(given) - set(reference_correct)
            c = custom_correction(correct, marked, missing, wrong, q_size) 
            table.append([i + 1, q[0], c, set(reference_correct), marked, correct, missing, wrong])
        
        if markdown:
            print(tabulate(table, headers=["Question", "File", "Marking", "Correct Ref", "Marked", "Correct", "Missing", "Wrong"], tablefmt="pipe"))
        elif excel:
            df = pd.DataFrame(table, columns=["Question", "File", "Marking", "Correct Ref", "Marked", "Correct", "Missing", "Wrong"])
            df.to_excel(excel, index=False)
        else:
            print(tabulate(table, headers=["Question", "File", "Marking", "Correct Ref", "Marked", "Correct", "Missing", "Wrong"], tablefmt="simple_grid"))

@cli.command()
@click.argument('datafile', type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, writable=True), required=True)
@click.argument('question_file', type=str, required=True)
@click.argument('question', type=int, required=True)
@click.option('--markdown', is_flag=True, help='Output the result in markdown format')
@click.option('--excel', type=click.Path(resolve_path=True, writable=True), help='Output the result in an excel file')
@click.pass_context
def review_question(ctx, datafile, question_file, question, markdown, excel):
    """
    Returns the ids of the students having a specific question
    """
    with TinyDB(datafile) as db:
        students = []
        for e in db.table('exams'):
            for i, q in enumerate(e['questions']):
                if q[0] == question_file and q[1] == question:
                    students.append((e['student_id'], i))
                    break
        table = []
        for student_id, i in students:
            Exam, Correction = Query(), Query()
            exam = db.table('exams').get(Exam.student_id == student_id)    
            correction = db.table('correction').get(Correction.student_id == student_id) 
            if correction is None:
                continue
            q, given =  exam['questions'][i], correction['given_answers'][i]
            q_size = len(q[3])
            reference_correct = set(q[2])
            marked, correct, missing, wrong = set(given), set(reference_correct) & set(given), set(reference_correct) - set(given), set(given) - set(reference_correct)
            table.append([student_id, i + 1, (q[0], q[1]), set(reference_correct), marked, correct, missing, wrong])
        
        if markdown:
            print(tabulate(table, headers=["Student ID", "Question", "File", "Correct Ref", "Marked", "Correct", "Missing", "Wrong"], tablefmt="pipe"))
        elif excel:
            df = pd.DataFrame(table, columns=["Student ID", "Question", "File", "Correct Ref", "Marked", "Correct", "Missing", "Wrong"])
            df.to_excel(excel, index=False)
        else:
            print(tabulate(table, headers=["Student ID", "Question", "File", "Correct Ref", "Marked", "Correct", "Missing", "Wrong"], tablefmt="simple_grid"))

def main_cli():
    cli(obj={})

if __name__ == '__main__':
    main_cli()
