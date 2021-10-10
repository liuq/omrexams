from PyPDF2 import PdfFileReader, PdfFileWriter, PdfFileMerger
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
import math
from . utils import image_utils as iu
from . utils.colors import *
from tinydb import TinyDB, Query
import copy
from shutil import rmtree

class Sort:
    """
    This class is responsible of dispatching the scanned exams from a PDF into
    a set of files, one for each single student, to be further processed later.
    """
    def __init__(self, scanned, sorted, doublecheck):
        self.scanned = scanned
        self.sorted = sorted
        self.offset = 10 # cropping offset, TODO: become a parameter
        self.doublecheck = doublecheck

    def sort(self, resolution, paper="A4"):
        if not os.path.exists(self.sorted):
            click.secho('Creating directory {}'.format(self.sorted))
            os.mkdir(self.sorted)
        else: # clean previous content
            click.secho('Cleaning directory {}'.format(self.sorted))
            for f in glob.glob(os.path.join(self.sorted, '*')):
                os.remove(f)
        self.resolution = resolution
        self.offset = int(1.0 / (2.54 / resolution))
        self.tasks_queue = mp.JoinableQueue()
        self.results_mutex = mp.RLock()
        self.task_done = mp.Condition(self.results_mutex)
        self.results = mp.Value('i', 0, lock=self.results_mutex)

        pages = 0

        if paper == "A4":
            for fn in self.scanned:
                with open(fn, 'rb') as f:
                    pdf_file = PdfFileReader(f)
                    for p in range(pdf_file.numPages):
                        self.tasks_queue.put((fn, p))
                    pages += pdf_file.numPages
        else:
            for fn in self.scanned:
                click.secho('Creating directory {}'.format('split_tmp'))
                os.mkdir('split_tmp')
                with open(fn, 'rb') as f, open(os.path.join('split_tmp', os.path.basename(fn)), 'wb') as sf:
                    pdf_file = Sort.split_pages(PdfFileReader(f))
                    merger = PdfFileMerger()
                    merger.append(pdf_file)
                    merger.write(sf)
                    for p in range(pdf_file.numPages):
                        self.tasks_queue.put((os.path.join('split_tmp', os.path.basename(fn)), p))
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
                self.task_done.wait_for(lambda: prev <= self.results.value)
                bar.update(self.results.value - prev)
                prev = self.results.value
                self.results_mutex.release()
        if paper == "A3":
            rmtree("split_tmp")
        click.secho('Finished', fg='red', underline=True)

    def worker_main(self):                        
        while True:
            filename, page = self.tasks_queue.get()
            if filename is None:
                break
            try:
                metadata = self.process(filename, page)
                if metadata and self.doublecheck is not None:                    
                    with TinyDB(self.doublecheck) as db:
                        Exam = Query()
                        table = db.table('exams')
                        result = table.get(Exam.student_id == metadata['student_id'])
                        if not result: 
                            raise RuntimeError("Error double checking: student {} is not present in the data file".format(metadata['student_id']))
                        answers = metadata['correct']
                        if result['answers'] != answers:                    
                            raise RuntimeError("Expected correct answers for student {} do not match\ncoded: {}/{}\nexpected: {}".format(metadata['student_id'], answers, metadata['correct'], result[0]['answers']))
            except Exception as e:
                print("\n", str(e))
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
            image = cv2.imdecode(img_buffer, cv2.IMREAD_GRAYSCALE)   
            try:
                metadata = qrdecoder.decode(image)
                if metadata is None:
                    return None
                # perform a rotation and image cropping to the qrcodes
                tl = metadata['top_left_rect'][0]
                br = metadata['bottom_right_rect'][2]
                width, height = br - tl
                detected_diag_angle = math.atan(height / width) * 360 / (2 * math.pi) 
                expected_diag_angle = math.atan(metadata['height'] / metadata['width']) * 360 / (2 * math.pi)
                rows, cols = image.shape[:2]
                rotation = cv2.getRotationMatrix2D(tuple(map(int, tl)),
                    detected_diag_angle - expected_diag_angle, 1.0)
                image = cv2.warpAffine(image, rotation, (cols, rows), borderValue=WHITE)

                # the image could be flipped, therefore here we restore the right qrcode order
                cv2.imwrite(os.path.join(self.sorted, '{}-{}.png'.format(metadata['student_id'], metadata['page'])), image)
                return metadata
            except Exception as e:
                raise RuntimeError("Error processing file {}, page {} \n{}".format(filename, page + 1, str(e)))        
            
    @staticmethod
    def split_pages(reader):
        writer = PdfFileWriter()

        for i in range(reader.numPages):
            p = copy.copy(reader.getPage(i))
            q = copy.copy(reader.getPage(i))

            p.mediaBox = copy.copy(p.cropBox)
            q.mediaBox = copy.copy(p.cropBox)

            x1, x2 = tuple(map(math.floor, p.mediaBox.lowerLeft))
            x3, x4 = tuple(map(math.floor, p.mediaBox.upperRight))

            if x3 - x1 > x4 - x2:
                # horizontal
                m = x1 + math.floor((x3 - x1) / 2)
                q.mediaBox.upperRight = (m, x4)
                q.mediaBox.lowerLeft = (x1, x2)

                p.mediaBox.upperRight = (x3, x4)
                p.mediaBox.lowerLeft = (m, x2)
            else:
                # vertical
                m = x2 + math.floor((x4 - x2) / 2)
                p.mediaBox.upperRight = (x3, x4)
                p.mediaBox.lowerLeft = (x1, m)

                q.mediaBox.upperRight = (x3, m)
                q.mediaBox.lowerLeft = (x1, x2)

            p.artBox = p.mediaBox
            p.bleedBox = p.mediaBox
            p.cropBox = p.mediaBox

            q.artBox = q.mediaBox
            q.bleedBox = q.mediaBox
            q.cropBox = q.mediaBox

            writer.addPage(q)
            writer.addPage(p)

        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        return PdfFileReader(buf)
                