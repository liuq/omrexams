from pypdf import PdfReader, PdfWriter
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
import math
from . utils.colors import *
from tinydb import TinyDB, Query
import copy
from shutil import rmtree
import logging

logger = logging.getLogger("omrexams")

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
            click.secho(f'Creating directory {self.sorted}')
            os.mkdir(self.sorted)
        else: # clean previous content
            click.secho(f'Cleaning directory {self.sorted}')
            for f in glob.glob(os.path.join(self.sorted, '*')):
                os.remove(f)
        self.resolution = resolution
        self.offset = int(1.0 / (2.54 / resolution))
        self.tasks_queue = mp.JoinableQueue()
        self.results_mutex = mp.RLock()
        self.task_done = mp.Condition(self.results_mutex)
        self.results = mp.Value('i', 0, lock=self.results_mutex)   
        self.page_leftovers = mp.Queue()

        pages = 0

        if paper == "A4":
            for fn in self.scanned:
                with open(fn, 'rb') as f:
                    pdf_file = PdfReader(f)
                    for p in range(len(pdf_file.pages)):
                        self.tasks_queue.put((fn, p))
                    pages += len(pdf_file.pages)
        else:
            if not os.path.exists('split_tmp'):
                click.secho(f'Creating directory {"split_tmp"}')
                os.mkdir('split_tmp')

            for fn in self.scanned:
                with open(fn, 'rb') as f, open(os.path.join('split_tmp', os.path.basename(fn)), 'wb') as sf:
                    pdf_file = Sort.split_pages(PdfReader(f))
                    merger = PdfWriter()
                    merger.append(pdf_file)
                    merger.write(sf)
                    for p in range(len(pdf_file.pages)):
                        self.tasks_queue.put((os.path.join('split_tmp', os.path.basename(fn)), p))
                    pages += len(pdf_file.pages)

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
                with self.results_mutex:
                    self.task_done.wait_for(lambda: prev <= self.results.value)
                    bar.update(self.results.value - prev)
                    prev = self.results.value
        with self.results_mutex:
            if not self.page_leftovers.empty():
                click.secho('There are page leftovers, merging them', fg='red', err=True)
                dst_pdf = PdfWriter()
                while not self.page_leftovers.empty():                    
                    p = PdfReader(io.BytesIO(self.page_leftovers.get()))
                    dst_pdf.append(p)
                with open('leftovers.pdf', 'wb') as f:
                    dst_pdf.write(f)
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
                        result = table.get(Exam.student_id == str(metadata['student_id']))
                        if not result: 
                            raise RuntimeError(f"Error double checking: student {metadata['student_id']} is not present in the data file")
                        answers = metadata['correct']
                        if result['answers'] != answers:                    
                            raise RuntimeError(f"Expected correct answers for student {metadata['student_id']} do not match\ncoded: {answers}/{metadata['correct']}\nexpected: {result[0]['answers']}")
            except Exception as e:
                print("\n", str(e))
            finally:
                with self.results_mutex:
                    self.results.value += 1
                    self.task_done.notify()
                    self.tasks_queue.task_done()

    def process(self, filename, page):
        dst_pdf = PdfWriter()
        with open(filename, 'rb') as f:
            current_page = PdfReader(f).pages[page]
            dst_pdf.add_page(current_page)
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
                if metadata.get('rotated', False):
                    image = cv2.rotate(image, cv2.ROTATE_180)
                # perform a rotation and image cropping to the qrcodes
                tl = metadata['top_left_rect'][0]
                br = metadata['bottom_right_rect'][2]
                width, height = br - tl
                rotation = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float64)
                # FIXME: currently the rotation is not working properly, possibly because the stored precision is not enough
                if False and metadata.get('qrheight') is not None and metadata.get('qrwidth') is not None:
                    detected_diag_angle = math.atan(height / width) * 360 / (2 * math.pi) 
                    expected_diag_angle = math.atan(metadata['qrheight'] / metadata['qrwidth']) * 360 / (2 * math.pi)
                    if not np.isclose(detected_diag_angle, expected_diag_angle):
                        logger.debug(f"Correcting rotation by {detected_diag_angle - expected_diag_angle} degrees")
                        rotation = cv2.getRotationMatrix2D(tuple(map(int, tl)),
                            detected_diag_angle - expected_diag_angle, 1.0)          
                rows, cols = image.shape[:2]
                image = cv2.warpAffine(image, rotation, (cols, rows), borderValue=WHITE)
                # the image could be flipped, therefore here we restore the right qrcode order
                cv2.imwrite(os.path.join(self.sorted, f'{metadata["student_id"]}-{metadata["page"]}.png'), image)
                return metadata
            except Exception as e:        
                with self.results_mutex:
                    pdf_bytes.seek(0)                    
                    self.page_leftovers.put(pdf_bytes.getvalue())        
                raise RuntimeError(f"Error processing file {filename}, page {page + 1} \n{str(e)}")        
            
    @staticmethod
    def split_pages(reader):
        writer = PdfWriter()

        for i in range(len(reader.pages)):
            p = copy.copy(reader.pages[i])
            q = copy.copy(reader.pages[i])

            p.mediabox = copy.copy(p.cropbox)
            q.mediabox = copy.copy(p.cropbox)

            x1, x2 = tuple(map(math.floor, p.mediabox.lower_left))
            x3, x4 = tuple(map(math.floor, p.mediabox.upper_right))

            if x3 - x1 > x4 - x2:
                # horizontal
                m = x1 + math.floor((x3 - x1) / 2)
                q.mediabox.upper_right = (m, x4)
                q.mediabox.lower_left = (x1, x2)

                p.mediabox.upper_right = (x3, x4)
                p.mediabox.lower_left = (m, x2)
            else:
                # vertical
                m = x2 + math.floor((x4 - x2) / 2)
                p.mediabox.upper_right = (x3, x4)
                p.mediabox.lower_left = (x1, m)

                q.mediabox.upper_right = (x3, m)
                q.mediabox.lower_left = (x1, x2)

            p.artbox = p.mediabox
            p.bleedbox = p.mediabox
            p.cropbox = p.mediabox

            q.artbox = q.mediabox
            q.bleedbox = q.mediabox
            q.cropbox = q.mediabox

            writer.add_page(q)
            writer.add_page(p)

        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        return PdfReader(buf)
