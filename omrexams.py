#!/usr/bin/env python3

import click
import random
import time
from datetime import datetime as dt
import dateparser as dp

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

@cli.command()
@click.option('--config', type=click.File(), required=False, default=lambda: open('config.yaml', 'r'))
@click.argument('students', type=click.File(), required=False)
@click.argument('questions', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--count', '-n', type=int, option='students', value=None, cls=OptionRequiredIf)
@click.option('--serial', type=int, default=100)
@click.option('--output', '-o', type=click.File(mode='w'))
@click.option('--date', '-d', type=DATETIME, prompt='Enter the exam date',  
    default=lambda: dt.now().strftime("%Y-%m-%d"))
@click.option('--seed', '-r', type=int, default=int(dt.now().strftime('%s')))
@click.pass_context
def generate(ctx, config, students, questions, count, serial, output, date, seed):
    """
    Generates the set of exams for the given amount of students (either personalized or anonymous).
    """

    def process_slowly(item):
        time.sleep(0.002 * random.random())

    click.echo(click.style('Generating', fg='red', underline=True))
    with click.progressbar(length=1000, label='Counting {}'.format(seed),
                           bar_template='%(label)s  %(bar)s | %(info)s',
                           fill_char=click.style(u'█', fg='cyan'),
                           empty_char=' ') as bar:
        for item in bar:
            process_slowly(item)

if __name__ == '__main__':
    cli(obj={})