from PyPDF2 import PdfFileReader, PdfFileWriter
from . utils import qrdecoder
from wand.image import Image
from wand.color import Color
import io
import glob
import os
import multiprocessing as mp
import click
import cv2
import numpy as np
import re
import pandas as pd

class Sort:
    """
    This class is responsible of dispatching the scanned exams from a PDF into
    a set of files, one for each single student, to be further processed later.
    """
    def __init__(self, scanned, sorted, doublecheck):
        self.scanned = scanned
        self.sorted = sorted
        self.doublecheck = doublecheck.name

    def sort(self, resolution):
        if not os.path.exists(self.sorted):
            click.secho('Creating directory {}'.format(self.sorted), )
            os.mkdir(self.sorted)
        self.resolution = resolution
        self.tasks_queue = mp.JoinableQueue()
        self.results_mutex = mp.RLock()
        self.task_done = mp.Condition(self.results_mutex)
        self.results = mp.Value('i', 0, lock=self.results_mutex)
        pages = 0
        for fn in glob.glob(os.path.join(self.scanned, '*.pdf')):
            with open(fn, 'rb') as f:
                pdf_file = PdfFileReader(f)
                for p in range(pdf_file.numPages):
                    self.tasks_queue.put((fn, p))
                pages += pdf_file.numPages
        with click.progressbar(length=pages, label='Dispatching scanned exams',
                               bar_template='%(label)s |%(bar)s| %(info)s',
                               fill_char=click.style(u'█', fg='cyan'),
                               empty_char=' ', show_pos=True) as bar:
            for _ in range(mp.cpu_count()):
                self.tasks_queue.put((None, None))
            pool = mp.Pool(mp.cpu_count(), self.worker_main)
            pool.close()
            prev = 0
            while not self.tasks_queue.empty():
                self.results_mutex.acquire()
                self.task_done.wait_for(lambda: prev < self.results.value)
                bar.update(self.results.value - prev)
                prev = self.results.value
                self.results_mutex.release()
        click.secho('Finished', fg='red', underline=True)

    def worker_main(self):    
        # TODO: outsource in a utils file (also in generate is used)
        def code_answer(answers):
                current = ""
                for i in range(len(answers)):
                    if answers[i]:
                        current += chr(ord('A') + i)
                return ",".join(current)      
        doublecheck = None
        if self.doublecheck:
            doublecheck = pd.read_excel(self.doublecheck)
            doublecheck.set_index('id', inplace=True)
        while True:
            filename, page = self.tasks_queue.get()
            if filename is None:
                break
            try:
                metadata = self.process(filename, page)
                if doublecheck is not None:
                    answers = ''.join(code_answer(a) for a in metadata['correct'])
                    assert doublecheck.loc[int(metadata['student_id']), 'answer_list'] == answers
            except Exception as e:
                print(str(e))
            finally:
                self.results_mutex.acquire()
                self.results.value += 1
                self.task_done.notify()
                self.results_mutex.release()
                self.tasks_queue.task_done()

    def process(self, filename, page):
        dst_pdf = PdfFileWriter()
        with open(filename, 'rb') as f:
            dst_pdf.addPage(PdfFileReader(f).getPage(page))
            pdf_bytes = io.BytesIO()
            dst_pdf.write(pdf_bytes)
            pdf_bytes.seek(0)
        with Image(file=pdf_bytes, resolution=self.resolution) as img:
            img.background_color = Color('white')
            img.alpha_channel = 'remove'
            img_buffer = np.asarray(bytearray(img.make_blob('bmp')), dtype=np.uint8)
            image = cv2.imdecode(img_buffer, cv2.IMREAD_UNCHANGED)
            #_retval, binary = cv2.threshold(image, 128, 255, cv2.THRESH_BINARY)            
            try:
                metadata = qrdecoder.decode(image)
                with img.convert('png') as converted:
                    with open(os.path.join(self.sorted, '{}-{}.png'.format(metadata['student_id'], metadata['page'])), 'wb') as f:                
                        converted.save(f)
                return metadata
            except Exception as e:
                raise RuntimeError("Error processing file {}, page {} \n{}".format(filename, page, str(e)))        
            

            