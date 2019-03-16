#!/usr/bin/env python3

import click
from datetime import datetime as dt
import dateparser as dp
import yaml
from cli import Generate
import pandas as pd
import xlrd
import re
import logging
import click_log
import sys

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
            self.fail('The provided date is not a string "{datetime_str}'.format(
                datetime_str=value), param, ctx)

        result = dp.parse(value)
        if result is None:
            self.fail('Could not parse datetime string "{datetime_str}"'.format(
                datetime_str=value), param, ctx)
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
            msg = 'Required if --{}={}'.format(self._option, self._value)
            raise click.MissingParameter(ctx=ctx, param=self, message=msg)
        return value

DATETIME = Datetime()

@click.group()
@click.version_option(version='0.1')
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, debug):
    """Manage multiple-choice OMR exams.
    """
    if not debug:
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)

@cli.command()
@click.option('--config', type=click.File(), required=False, default=lambda: open('config.yaml', 'r'))
@click.option('--students', '-s', type=click.File(), required=False)
@click.argument('questions', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--count', '-n', type=int, option='students', value=None, cls=OptionRequiredIf)
@click.option('--serial', type=int, default=100)
@click.option('--output', '-o', type=click.File(mode='w'), default=lambda: open('exam.pdf', 'wb'))
@click.option('--date', '-d', type=DATETIME, prompt='Enter the exam date',  
    default=lambda: dt.now().strftime("%Y-%m-%d"))
@click.option('--seed', '-r', type=int, default=int(dt.now().strftime('%s')))
@click.pass_context
def generate(ctx, config, students, questions, count, serial, output, date, seed):
    """
    Generates the set of exams for the given amount of students (either personalized or anonymous).
    """
    config = yaml.load(config)

    if students:
        try:    
            click.secho('Reading excel file', fg='red', underline=True)
            skip = 0
            # check whether the file needs to be partially skipped
            if 'data_marker' in config['excel']:
                marker = config['excel']['data_marker'].get('skip_until')
                click.secho('Searching for data marker "{}"'.format(marker), fg='cyan')
                wb = xlrd.open_workbook(students.name)
                sheet = wb.sheet_by_index(0)
                for i in range(sheet.nrows):
                    row = sheet.row(i)
                    cell = row[config['excel'].get('on_column', 0)]
                    if re.match(marker, cell.value):
                        skip = i + 1
                        break
            if skip > 0:
                click.secho('Skipping {} rows'.format(skip), fg='cyan')
            student_list = pd.read_excel(students.name, skiprows=skip)
            fields = config['excel']['fields']
            student_list[fields.get('fullname', 'Full Name')] = student_list[fields.get('name')] + ' ' + student_list[fields.get('surname')]
            student_list.reset_index(inplace=True)
            student_list = [tuple(r) for r in student_list[[fields.get('id'), fields.get('fullname', 'Full Name')]].to_records(index=False)] 
            click.secho('Processing done, {} students found'.format(len(student_list)), fg='cyan')
        except Exception as e:
            logger.error("While reading the students excel file {filename}: {}".format(str(e), filename=students.name))
            sys.exit(-1)
        students.close()
    else:
        click.secho('Creating anonymous exams for {} students'.format(count), fg='red', underline=True)
        click.secho('Starting serials from {}'.format(serial), fg='cyan')
        student_list = list(map(lambda s: (s, ""), range(serial, serial + count)))
    click.secho('Seed used for the random generator {}'.format(seed), fg='magenta')

    generator = Generate(config, student_list, questions, output, date, seed)
    generator.process()

if __name__ == '__main__':
    cli(obj={})