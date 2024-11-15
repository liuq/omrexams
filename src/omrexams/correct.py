import cv2
import numpy as np
from scipy.spatial import cKDTree
import re
import io
import math
from skimage.feature import peak_local_max
import click
from . utils import qrdecoder
import multiprocessing as mp
import glob
import pandas as pd
import os
from . utils.colors import *
import logging
from collections import Counter
from itertools import combinations
import img2pdf
from pypdf import PdfReader, PdfWriter
from tinydb import TinyDB, Query
from shutil import copy2, rmtree
import tempfile
import inflect
import traceback

logger = logging.getLogger("omrexams")

p = inflect.engine()

def decode_answers(answers, permutation):
    res = []
    for i in range(len(permutation)):
        c = chr(ord('A') + i)
        res.append(c in answers)
    return list(bool(a) for a in np.array(res)[permutation])

class Correct:
    """
    This class will operate on a directory with a set of pages and perform the correction 
    according to the information stored in the qrcodes
    """
    def __init__(self, sorted, corrected, data_filename, resolution, compression, use_page_answers=False):
        self.sorted = sorted
        self.corrected = corrected
        self.data_filename = data_filename
        self.resolution = resolution
        self.compression = compression
        self.use_page_answers = use_page_answers

    def correct(self):
        logger.info('Creating and preparing tmp directory')
        if os.path.exists('tmp'):
            rmtree('tmp')
        os.mkdir('tmp')
        with TinyDB(f"{self.data_filename}.tmp") as db:
            if 'correction' in db.tables():
                db.drop_table('correction')
        self.tasks_queue = mp.JoinableQueue()
        self.watch_queue = mp.Queue()
        self.results_mutex = mp.RLock()
        self.task_done = mp.Condition(self.results_mutex)
        self.results = mp.Value('i', 0, lock=self.results_mutex)
        files = 0
        for f in sorted(glob.glob(os.path.join(self.sorted, '*.png'))):
            self.tasks_queue.put(f)
            files += 1
        click.secho(f"Correcting {files} pages", fg='red', underline=True)
        with click.progressbar(length=files, label='Correcting',
                               bar_template='%(label)s |%(bar)s| %(info)s',
                               fill_char=click.style(u'█', fg='cyan'),
                               empty_char=' ', show_pos=True) as bar:
            for _ in range(mp.cpu_count()):
                self.tasks_queue.put(None)
            pool = mp.Pool(mp.cpu_count(), self.worker_main)
            pool.close()
            prev = 0
            while not self.tasks_queue.empty():
                self.results_mutex.acquire()
                self.task_done.wait_for(lambda: prev <= self.results.value)
                bar.update(self.results.value - prev)
                prev = self.results.value
                self.results_mutex.release()
        click.secho('Correction finished', fg='red', underline=True)
        delete_default = True
        watch = set()
        if not self.watch_queue.empty():
            click.secho('Some exams deserve attention because of highly incoherent detection:', fg='red', blink=True)
            while not self.watch_queue.empty():
                watch.add(self.watch_queue.get())
            delete_default = False
            for w in watch:
                filename = os.path.basename(w[0])
                filename = os.path.join('tmp', ".".join(filename.split(".")[:-1]) + ".jpg")
                click.secho(f'\t{filename} {w[1]}', fg='yellow')   
        # Collecting all corrected exams into a single pdf file
        click.secho("Collecting all corrected exams into a single pdf file", fg="green")
        files = sorted(glob.glob(os.path.join('tmp', "*.jpg")))
        output_pdf = PdfWriter()
        old_student_id = None
        with click.progressbar(length=len(files), label="Merging corrections",
                               bar_template='%(label)s |%(bar)s| %(info)s',
                               fill_char=click.style(u'█', fg='cyan'),
                               empty_char=' ', show_pos=True) as bar:
            for i, filename in enumerate(files):
                with io.BytesIO() as f:
                    f.write(img2pdf.convert(filename))              
                    f.seek(0)
                    student_id = os.path.basename(filename).split("-")[0]  
                    if student_id != old_student_id:                
                        output_pdf.append(PdfReader(f, strict=False), outline_item=f'Student {student_id}')
                        old_student_id = student_id
                    else:
                        output_pdf.append(PdfReader(f, strict=False))
                bar.update(1)
        click.secho("Writing pdf file", fg="green")
        with open(self.corrected, 'wb') as f:
            output_pdf.write(f)

        # TODO: seems not to work, to be tested (the pages with images are rendered as blank files)
        # Marking collected pdf with the student_id
        
        #with open(self.corrected + '.tmp' + '.pdf', 'rb') as f:
        #     input_pdf = PdfReader(f, strict=False)
        #     if len(files) != len(input_pdf.pages):
        #         raise RuntimeError("The collected pdf file seems not to contain all the pages")
        #     for i, filename in enumerate(files):
        #         student_id = os.path.basename(filename).split("-")[0]
        #         output_pdf.append(input_pdf.pages[i])
        #         output_pdf.addBookmark(student_id, i)
        # with open(self.corrected, 'wb') as f:
        #     output_pdf.write(f)
        # TODO: remove tmp file
        if (click.prompt("Remove temporary image files and directory tmp?", type=bool, default='y' if delete_default else 'n')):
            for filename in files:
                os.remove(filename)
            os.rmdir('tmp')
        # Update the data file and output the corrected excel file
        click.secho("Updating the database file", fg="green")
        data = {}
        with TinyDB(f"{self.data_filename}.tmp") as db1, TinyDB(self.data_filename) as db2:
            table = db1.table('correction')
            students = set()
            for item in table.all():
                students.add(item['student_id'])
            Correction = Query()
            for student in students:
                data[student] = { 'correct_answers': [], 'given_answers': [] }
                results = table.search(Correction.student_id == student)
                results = sorted(results, key=lambda r: int(r['page']))
                for page in results:
                    data[student]['correct_answers'] += list(map(list, page['correct_answers']))
                    data[student]['given_answers'] += list(map(list, page['detected_answers']))
            if 'correction' in db2.tables():
                db2.drop_table('correction')
            table = db2.table('correction')
            for student in data:
                table.insert({ 'student_id': student, **data[student] })   
            db2.drop_table('statistics')
            statistics = db2.table('statistics')    
            Statistics = Query()       
            # check consistency of correct answers (apriori/encoded)
            for exam in db2.table('exams').all():
                data = table.get(Correction.student_id == exam['student_id'])
                if data is not None and any(set(d) != set(e) for d, e in zip(data['correct_answers'], exam['answers'])):                    
                    for i, (d, e) in enumerate(zip(data['correct_answers'], exam['answers'])):
                        if set(e) != set(d):
                            message = f"Warning: correct answers in {self.data_filename} for student {exam['student_id']}, question {i + 1} do not match with those encoded in the exam sheets: {set(d)} in the sheet, {set(e)} in db"
                            click.secho(message, fg="yellow")
                elif data is None:
                    continue               
                for i, q in enumerate(exam['questions']):
                    question = statistics.get((Statistics.question_file == q[0]) & (Statistics.index == q[1]))
                    given_answer = decode_answers(data['given_answers'][i], q[3])
                    correct_answer = decode_answers(data['correct_answers'][i], q[3])

                    if question is None:
                        question = { 
                            'question_file': q[0], 
                            'index': q[1], 
                            'answers': [0] * len(q[3]), 
                            'correct_answers': correct_answer,
                            'total': 0,
                            'incorrect': 0, 
                            'correct': 0, 
                            'partially_correct': 0,
                            'unanswered': 0
                        }
                    question['total'] += 1
                    if all(g == c for g, c in zip(given_answer, correct_answer)):
                        question['correct'] += 1
                    elif any(c and g == c for g, c in zip(given_answer, correct_answer)):
                        question['partially_correct'] += 1
                    if any(not c and g != c for g, c in zip(given_answer, correct_answer)): 
                        question['incorrect'] += 1                     
                    if not any(g for g in given_answer):
                        question['unanswered'] += 1
                    for i in range(len(given_answer)):
                        if given_answer[i]:
                            question['answers'][i] += 1 
                    statistics.upsert(question, (Statistics.question_file == q[0]) & (Statistics.index == q[1]))
        click.secho("Removing temporary files", fg="green")
        os.remove(f"{self.data_filename}.tmp")
                        
        
    def worker_main(self):    
        while True:
            filename = self.tasks_queue.get()
            if filename is None:
                break
            try:
                detected_answers, correct_answers = self.process(filename)
                if correct_answers: # probably no question in current file           
                    *student, page = ".".join(os.path.basename(filename).split(".")[:-1]).split("-")
                    # this is due because of old-style matriculation numbers
                    student = "-".join(student)
                    self.results_mutex.acquire()
                    self.append_correction(student, page, list(map(list, detected_answers)), list(map(list, correct_answers)))
                    self.results_mutex.release()
            except Exception as e:
                click.secho(f"\nIn file {filename}\n" + str(e), fg="yellow")
            finally:
                self.results_mutex.acquire()
                self.results.value += 1
                self.task_done.notify()
                self.results_mutex.release()
                self.tasks_queue.task_done()

    def process(self, filename):
        offset = 5
        image = cv2.imread(filename)
        metadata = qrdecoder.decode(image, True)
        if metadata.get('rotated', False):
            image = cv2.rotate(image, cv2.ROTATE_180)

        if metadata['range'] == (0, 0): # no question and markers in current page
            self.write(filename, image)
            return [], []
        tl, br = metadata['top_left'], metadata['bottom_right']
        # prepare roi
        p0 = np.round(np.dot(metadata['p0'], metadata['scaling'])).astype(int) + tl 
        p1 = np.round(np.dot(metadata['p1'], metadata['scaling'])).astype(int) + tl        
        roi_width = p1[0] - p0[0]
        roi_height = p1[1] - p0[1]
        # this fix was needed since sometimes the roi was too close to objects and some detector did not work
        expand_x = int(roi_width * 0.05 / 2)
        expand_y = 0 #int(roi_height * 0.05 / 2)
        p0 = np.array([max(0, p0[0] - expand_x), max(0, p0[1] - expand_y)])
        p1 =  np.array([min(image.shape[1], p1[0] + expand_x), min(image.shape[0], p1[1] + expand_y)])
        roi = image[p0[1]:p1[1], p0[0]:p1[0]] 
        cv2.rectangle(image, tuple(map(int, p0 - offset)), tuple(map(int, p1 + offset)), BLUE, 3)        

        page_answers = None
        if self.data_filename and self.use_page_answers:
            Exam = Query()
            with TinyDB(self.data_filename) as db:
                exam = db.table('exams').search(Exam.student_id == metadata['student_id'])
                if len(exam) > 0:
                    page_answers = exam[0]['answers'][metadata['range'][0] - 1:metadata['range'][1]]
        # contour detection
        correction = [None] * 4    
        try:
            binary, circles, empty_circles = Correct.detect_circles_edges(roi, metadata)
            # process result        
            correction[0], mask = Correct.process_circles(roi, binary, circles, empty_circles, metadata, page_answers)
            image = Correct.add_superimposed(image, mask, roi, p0, p1, 'Contour')
        except Exception as e:
            click.secho(f"\nFailed Contour Detection for {filename}", fg="yellow")
            click.echo(str(e))
        # blob detection
        # TODO: temporarily disabled, seems to have some troubles that need further investigation
        try:
            binary, circles, empty_circles = Correct.detect_circles_blob(roi, metadata)            
            correction[1], mask = Correct.process_circles(roi, binary, circles, empty_circles, metadata, page_answers)            
            image = Correct.add_superimposed(image, mask, roi, p0, p1, 'Blob')
        except Exception as e:
            click.secho(f"\nFailed Blob for {filename}", fg="yellow")
            click.echo(f"{e}")
        # laplacian detection
        try:
            binary, circles, empty_circles = Correct.detect_circles_laplacian(roi, metadata)
            correction[2], mask = Correct.process_circles(roi, binary, circles, empty_circles, metadata, page_answers)
            image = Correct.add_superimposed(image, mask, roi, p0, p1, 'Laplacian')
        except Exception as e:
            click.secho(f"Failed Laplacian for {filename}", fg="yellow")
            click.echo(str(e))
        # hough detection
        try:
            binary, circles, empty_circles = Correct.detect_circles_hough(roi, metadata)
            correction[3], mask = Correct.process_circles(roi, binary, circles, empty_circles, metadata, page_answers)
            image = Correct.add_superimposed(image, mask, roi, p0, p1, 'Hough')
        except Exception as e:
            click.secho(f"Failed Hough for {filename}", fg="yellow")
            click.echo(f"{e}")
#            click.echo(f"{traceback.format_exc()}")

        # TODO: currently here just to check, before becoming another method
        # def non_max_suppression(boxes, overlap_thresh=0.8):
        #     if len(boxes) == 0:
        #         return []
        #     pick = []
        #     x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
        #     area = (x2 - x1 + 1) * (y2 - y1 + 1)
        #     idxs = np.argsort(y2)
        #     while len(idxs) > 0:
        #         last = len(idxs) - 1
        #         i = idxs[-1]
        #         pick.append(i)
        #         suppress = [last]
        #         for pos in range(0, last):
        #             j = idxs[pos]
        #             xx1, yy1 = max(x1[i], x1[j]), max(y1[i], y1[j])
        #             xx2, yy2 = min(x2[i], x2[j]), min(y2[i], y2[j])
        #             w, h = max(0, xx2 - xx1 + 1), max(0, yy2 - yy1 + 1)
        #             overlap = float(w * h) / area[j] if area[j] > 0 else 0
        #             if overlap > overlap_thresh:
        #                 suppress.append(pos)
        #         idxs = np.delete(idxs, suppress)
        #     return boxes[pick]
                    
        # ss = cv2.ximgproc.segmentation.createSelectiveSearchSegmentation()
        # scale = 300 / roi.shape[1] 
        # tw, th = int(roi.shape[1] * scale), int(roi.shape[0] * scale)
        # ss.setBaseImage(cv2.resize(roi, (tw, th)))
        # ss.switchToSingleStrategy() 
        # rects = non_max_suppression(ss.process())
        # for i, rect in enumerate(rects):
        #     if i < 1000:
        #         x, y, w, h = map(lambda s: int(s / scale), rect)
        #         x = x + p0[0]
        #         y = y + p0[1]
        #         cv2.rectangle(image, (x, y), (x + w, y + h), RED, 1, cv2.LINE_AA)

        majority, correct = self.majority_correction(filename, correction)  
        given_text = f"Given answers: {' '.join(','.join(a) for a in majority)}"
        correct_text = f"Correct answers: {' '.join(','.join(a) for a in correct)}"
        (width, height), _ =  cv2.getTextSize(given_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 3)
        cv2.putText(image, given_text, (metadata['bottom_right'][0] // 4, metadata['bottom_right'][1] - 4 * height), cv2.FONT_HERSHEY_SIMPLEX, 1, MAGENTA, 3)
        cv2.putText(image, correct_text, (metadata['bottom_right'][0] // 4, metadata['bottom_right'][1] - height), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 3)
        self.write(filename, image)

        return majority, correct
        
    def majority_correction(self, filename, correction):
        correction = list(filter(lambda c: c is not None, correction))
        correct_answers = list(map(lambda c: c[1], correction[0]))
        correction = [list(map(lambda c: c[0], correction[i])) for i in range(len(correction))]
        if not all(len(c) == len(correct_answers) for c in correction):
            raise RuntimeError("Uneven number of answers (not matching with the correct ones)")
        majority = []
        span = len(correct_answers)
        for i in range(span):
            counter = Counter()
            for c in correction:
                for a in c[i]:
                    counter[a] += 1
            tmp = []
            for a in counter:
                if counter[a] >= len(correction) / 2:
                    tmp.append(a)
            if all(c1[i] != c2[i] for c1, c2 in combinations(correction, 2)):
                self.watch_queue.put((filename, i))
            majority.append(set(tmp))                        
        return majority, correct_answers

    @staticmethod
    def add_superimposed(image, mask, roi, p0, p1, method):
        superimposed = cv2.bitwise_and(mask, roi)
        prev_x = image.shape[1]
        image = cv2.copyMakeBorder(image, 0, 0, 0, superimposed.shape[1], cv2.BORDER_CONSTANT, value=WHITE)
        image[p0[1]:p1[1], prev_x:prev_x + superimposed.shape[1]] = superimposed
        cv2.putText(image, method, (prev_x, p0[1]), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 3)
        return image
    
    def write(self, filename, image):
        filename = os.path.join('tmp', os.path.basename(filename))
        filename = ".".join(filename.split(".")[:-1]) + ".jpg"
        # rescale to 72 dpi to save space
        image = cv2.resize(image, None, fx=72.0 / self.resolution, fy=72.0 / self.resolution, interpolation=cv2.INTER_AREA)
        cv2.imwrite(filename, image, [cv2.IMWRITE_JPEG_QUALITY, self.compression])


    def append_correction(self, student, page, detected_answers, correct_answers):
        with TinyDB(f"{self.data_filename}.tmp") as db:
            table = db.table('correction')
            data = { 
                "student_id": student, 
                "page": page, 
                "detected_answers": detected_answers,
                "correct_answers": correct_answers
            }
            table.insert(data)

    @staticmethod
    def circle_filled_area(binary, c):
        area = 0
        cx, cy = c[:2]
        radius = c[2]
        xbounds = (max(0, int(cx - radius)), min(binary.shape[1], int(cx + radius) + 1))
        w = xbounds[1] - xbounds[0]
        ybounds = (max(0, int(cy - radius)), min(binary.shape[0], int(cy + radius) + 1))
        h = ybounds[1] - ybounds[0]
        enclosing_box = binary[ybounds[0]:ybounds[1], xbounds[0]:xbounds[1]]
        y, x = np.ogrid[-h // 2 : h // 2, -w // 2 : w // 2]
        mask = x * x + y * y > radius * radius

        return np.count_nonzero(np.ma.masked_array(enclosing_box, mask).ravel())

    @staticmethod
    def detect_circles_edges(roi, metadata, area_threshold=0.45):    

        # in order to detect the contours in the roi, a blur and an adaptive thresholding is used
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) > 2 else roi
        gray = cv2.GaussianBlur(gray, (5, 5), 2)
        binary_for_edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        # get the contours
        contours, _ = cv2.findContours(binary_for_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        # get a more precise binary image for computing area
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        binary += binary_for_edges

        # try to construct the circles
        circles = []
        empty_circles = []
        scaling = metadata['scaling']
        bubble_radius = np.max(np.dot(metadata['size'], scaling) / 2.0)
        # for each detcted contour
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            # try to simplify it
            approx = cv2.approxPolyDP(contour, 0.01 * perimeter, True)
            # and check whether it is a candidate to be a circle (in that case append it)
            if len(approx) >= 8:                        
                (cx, cy), radius = cv2.minEnclosingCircle(contour)
                if 0.75 * bubble_radius <= radius <= 1.8 * bubble_radius:
                    if Correct.circle_filled_area(binary, (int(cx), int(cy), int(radius))) > area_threshold * bubble_radius * bubble_radius * math.pi:
                        circles.append((int(cx), int(cy), int(radius)))
                    else:
                        empty_circles.append((int(cx), int(cy), int(radius)))
        # sort circles according to the x component (leftmost first, topmost after)
        return binary, circles, empty_circles

    @staticmethod
    def circle_intersection_area(c1, c2):
        r1, r2 = c1[2], c2[2]
        d = np.linalg.norm(np.array(c1[:2]) - np.array(c2[:2])) + np.finfo(float).eps
        if r1 < r2: # ensure that r1 >= r2    
            r1, r2 = r2, r1
        if (d > r1 + r2):
            return 0.0        
        if d < r1 - r2: # the circle whose radius is r2 is contained in the circle whose radius is r1
            return math.pi * r2 * r2
        r1s = r1 * r1
        r2s = r2 * r2
        d1 = (r1s - r2s  + d * d) / (2.0 * d)
        d2 = d - d1
        return r1s * math.acos(d1 / r1) - d1 * math.sqrt(r1s - d1 * d1) + \
            r2s * math.acos(d2 / r2) - d2 * math.sqrt(r2s - d2 * d2)

    @staticmethod 
    def highlight_circle(target, c, color, offset=5, **kwargs):
        if "shape" in kwargs and kwargs["shape"] == "rectangle":
            return cv2.rectangle(target, tuple(np.array(c[:2]) - (c[2] + offset)), tuple(np.array(c[:2]) + (c[2] + offset)), color, 3)
        else:
            return cv2.circle(target, c[:2], c[2] + offset, color, 3)

    @staticmethod
    def process_circles(roi, binary, circles, empty_circles, metadata, page_answers=None, offset=5, xdistance=1.25):                        
        mask = np.ones((*roi.shape[:2], 3), np.uint8) * 255
        # identify the reference_circles first, assuming the leftmost/topmost is the reference one
        circles = sorted(circles)
        pivot = circles[0]
        # the reference circles are those whose center is almost in the same column as the pivot
        reference_circles = [c for c in circles if abs(c[0] - pivot[0]) <= pivot[2]]
        reference_radius = np.max(np.dot(metadata['size'], metadata['scaling']) / 2)
        reference_area = reference_radius * reference_radius * math.pi
        # all the other are the answer circles
        other_circles = [c for c in circles if abs(c[0] - pivot[0]) > pivot[2]]
        # highlight the reference circles
        for c in reference_circles:
            Correct.highlight_circle(mask, c, CYAN)
            filled_area = Correct.circle_filled_area(binary, c) / reference_area
            #text = f"{filled_area:.0%}"
            #cv2.putText(mask, text, tuple(np.array(c[:2]) - np.array([c[2], c[2] + 2 * offset])), 
            #            cv2.FONT_HERSHEY_SIMPLEX, 0.8, CYAN, 3)
        # maintain the information as a mapping between the reference circle and all the
        # answer circles on the same row
        answer_circles = {c: [] for c in reference_circles}
        # process the answer circles
        for c in other_circles:
            # find the closest reference circle, w.r.t. y coordinate
            ydist = np.fromiter((abs(c[1] - rc[1]) for rc in reference_circles), int)
            reference_circle = reference_circles[np.argmin(ydist)]
            answer_circles[reference_circle].append(tuple(list(c) + [True]))
        # and the empty ones (they are meaningful only for edge detection)
        for c in empty_circles:
            # find the closest reference circle, w.r.t. y coordinate
            ydist = np.fromiter((abs(c[1] - rc[1]) for rc in reference_circles), int)
            reference_circle = reference_circles[np.argmin(ydist)]
            answer_circles[reference_circle].append(tuple(list(c) + [False]))
        # now consider each reference circle from the topmost one down
        answer_circles = sorted(answer_circles.items(), key=lambda item: item[0][1])
        # check whether questions and the expected sequence of answers match
        if len(reference_circles) != len(metadata['page_correction']):
            raise RuntimeError(f"Warning: Number of detected answers {len(reference_circles)} ({metadata['student_id']}-{metadata['page']}) and number of answers {len(metadata['page_correction'])} do not match (debugging: radius {reference_radius:.02f})")
        # go through the questions (reference circles) and check the answers
        correction = []            
        for i, ac in enumerate(answer_circles):  
            # This will override the coded page corrections if provided
            # it is needed to force correction when answers are corrected
            # in the questions database through the update-corrected command
            if page_answers is None:       
                correct_res = set(metadata['page_correction'][i])
            else:
                correct_res = set(page_answers[i])
            all_res = set()
            answers_res = set()   
            # now sort again answer circles from the leftmost to the rightmost
            # and check whether there are missing ones (e.g., due to a “wrong” filling)
            # each circle has a distance ratio specified by the xdistance parameter from the
            # previous one
            reference_circle = ac[0]
            given_answers = sorted(ac[1])
            for c in given_answers:
                Correct.highlight_circle(mask, c, ORANGE, shape="rectangle")
            # TODO: assumption that the line of answers is almost horizontal, it could be detected
            #       another assumption is that the maximum number of answers is 10
            phantom_circles = []
            for j in range(1, 11):
                # this is a phantom circle that should be present in the image
                c = np.array(reference_circle[:2]) + [j * xdistance * 2 * reference_radius, 0]
                c = tuple(list(c) + [reference_radius]) 
                # check if the phantom circle is outside the roi image or there's nothing below the circle
                # TODO: the first check is not working anymore, consider fixing it later
                #if c[0] + c[2] > binary.shape[0] or Correct.circle_filled_area(binary, c) < 0.1 * reference_area:
                if Correct.circle_filled_area(binary, c) < 0.1 * reference_area:
                    break
                phantom_circles.append(c)
            
            # let's check if the phantom circles have a detected counterpart
            for a in given_answers:
                distances = np.fromiter((np.linalg.norm(np.array(c[:2]) - np.array(a[:2])) for c in phantom_circles), float)
                if len(distances) > 0:
                    closer_phantom_circle = np.argmin(distances)
                    if distances[closer_phantom_circle] < reference_radius:
                        del phantom_circles[closer_phantom_circle]            
            for c in phantom_circles:
                c = tuple(list(map(int, c)) + [False])
                Correct.highlight_circle(mask, c, GRAY)
                given_answers.append(c)                               
            given_answers = sorted(given_answers)
            for j, c in enumerate(given_answers):
                r = chr(j + ord('A'))
                all_res.add(r)
                filled_area = Correct.circle_filled_area(binary, c) / reference_area
                text = f"{filled_area:0>4.0%}"
                cv2.putText(mask, text, tuple(np.array(c[:2]) - np.array([c[2], c[2] + 2 * offset])), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, MAGENTA, 2)
                cv2.circle(mask, c[:2], c[2], alpha(YELLOW, 0.3), -1)
                if c[3]:
                    answers_res.add(r)
                    if r in correct_res:
                        cv2.circle(mask, c[:2], c[2], alpha(GREEN, 1.0), -1)
                    else:
                        cv2.circle(mask, c[:2], c[2], alpha(RED, 1.0), -1)
                else:
                    if r in correct_res:
                        cv2.circle(mask, c[:2], c[2], alpha(ORANGE, 1.0), -1)
            # check if there are missing answers on the paper-sheet
            missing_answers = correct_res - all_res
            if len(missing_answers) > 0:
                click.secho(f"Warning: For question {i}/({metadata['student_id']}-{metadata['page']}), the correct {p.plural('answer', len(missing_answers))} {missing_answers} {p.plural_verb('was', len(missing_answers))} not printed on the sheet", fg="yellow")
                ytop = round(reference_circle[1] - 1.3 * reference_circle[2])
                ybottom = round(reference_circle[1] + 1.3 * reference_circle[2])
                cv2.rectangle(mask, (0, ytop), (roi.shape[1], ybottom), RED, 7)
                p = np.array(reference_circle[:2]) + [-reference_circle[2], -reference_circle[2] - 40]
                cv2.putText(mask, f"Missing {missing_answers} found {all_res}", tuple(p), cv2.FONT_HERSHEY_SIMPLEX, 1, RED, 3)
            # write a text with the given answers and the correct ones close to each reference circle
            p = np.array(reference_circle[0:2]) + [-reference_circle[2], reference_circle[2] - 100]
            tmp = ("".join(sorted(a for a in answers_res)) if answers_res else "None")
            tmp += "/" + ("".join(sorted(a for a in correct_res)) if correct_res else "None")
            cv2.putText(mask, tmp, tuple(p), cv2.FONT_HERSHEY_SIMPLEX, 1, MAGENTA, 3)
            correction.append((answers_res, correct_res))
        return correction, mask

    @staticmethod
    def detect_circles_blob(roi, metadata):
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) > 2 else roi
        gray = cv2.GaussianBlur(gray, (9, 9), 2)
        
        params = cv2.SimpleBlobDetector_Params()
        scaling = metadata['scaling']
        bubble_radius = np.max(np.dot(metadata['size'], scaling) / 2.0)
        params.minDistBetweenBlobs = bubble_radius * 2.0
        #params.filterByColor = False
        #blobColor = 0 

        # Filter by Area.
        params.filterByArea = True
        params.minArea = bubble_radius * bubble_radius * np.pi * 0.8
        params.maxArea = bubble_radius * bubble_radius * np.pi * 1.8

        # Change thresholds
        params.minThreshold = 160
        params.maxThreshold = 255

        # Filter by Circularity
        #params.filterByCircularity = True
        #params.minCircularity = 0.7

        # Filter by Inertia
        params.filterByInertia = False
        #params.minInertiaRatio = 0.7

        # Filter by Convexity
        params.filterByConvexity = False
        #params.minConvexity = 0.95
        
        detector = cv2.SimpleBlobDetector_create(params)
        keypoints = detector.detect(gray)
        if keypoints is not None:
            circles = list(map(lambda k: (int(k.pt[0]), int(k.pt[1]), int(bubble_radius)), keypoints))
        else:
            circles = []
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY_INV, 11, 2)
        binary += cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)[1]
        
        return binary, circles, []

    @staticmethod
    def detect_circles_laplacian(roi, metadata):
        def round_up_to_odd(f):
            return math.ceil(f) // 2 * 2 + 1 
        
        def collapse_identical_circles(candidates, radius, threshold=0.3):            
            fusion = True
            next_centers = set(candidates)
            while fusion:
                fusion = False
                prev_centers = next_centers
                next_centers = set()
                done = set()
                for c1 in prev_centers:  
                    if c1 in done:
                        continue              
                    identical = []
                    done.add(c1)
                    for c2 in prev_centers - done:
                        if np.linalg.norm(np.array(c1[:2]) - np.array(c2[:2])) < threshold * radius:
                            identical.append(c2)                
                    if identical:
                        fusion = True
                        for c in identical + [c1]:
                            if c in next_centers:
                                next_centers.remove(c)
                            done.add(c)
                        next_centers.add(tuple(np.mean(identical + [c1], axis=0)))
                    else:
                        next_centers.add(c1)
            return next_centers                                                                   

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) > 2 else roi
        gray = cv2.GaussianBlur(gray, (11, 11), 2)
        
        s = np.max(np.dot(metadata['size'], metadata['scaling']) / 2.0)

        s1 = s / 1.4142 # stretto
        # some denoising
        im1 = cv2.GaussianBlur(gray, (round_up_to_odd(1 + 5 * s1), round_up_to_odd(1 + 5 * s1)), s1)

        s2 = s * 1.4142 #largo
        # some denoising
        im2 = cv2.GaussianBlur(gray, (round_up_to_odd(1 + 5 * s2), round_up_to_odd(1 + 5 * s2)), s2)

        response = im2.astype(float) - im1.astype(float)  #largo - stretto
        response = cv2.normalize(response, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1)
        
        y, x = np.ogrid[-s // 2 : s // 2, -s // 2 : s // 2]
        mask = x * x + y * y <= s * s    
        
        peak_indexes = peak_local_max(response, footprint=mask, #min_distance=s, 
                                      exclude_border=False, threshold_rel=0.5) 
        maxima = np.zeros_like(response, dtype=int)
        maxima[tuple(peak_indexes.T)] = 255        
        maxima = cv2.normalize(maxima, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1)
        
        contours, _ = cv2.findContours(maxima, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        candidates = []
        for contour in contours:
            (cx, cy), _ = cv2.minEnclosingCircle(contour)
            candidates.append((cx, cy, s))
        circles = list(map(lambda c: tuple(map(int, c)), collapse_identical_circles(candidates, s)))
            
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY_INV, 11, 2)
        binary += cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)[1]    
        
        return binary, circles, []

    @staticmethod
    def detect_circles_hough(roi, metadata):
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) > 2 else roi
        gray = cv2.GaussianBlur(gray, (9, 9), 2)

        scaling = metadata['scaling']
        bubble_radius = np.max(np.dot(metadata['size'], scaling) / 2.0)

        # Set parameters for Hough Circle Transform
        min_radius = int(bubble_radius * 0.8)
        max_radius = int(bubble_radius * 1.2)

        # Apply Hough Circle Transform
        candidates = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,  # Inverse ratio of accumulator resolution to image resolution
            minDist=bubble_radius * 2.0,  # Minimum distance between circle centers
            param1=100,  # Higher threshold for Canny edge detection
            param2=30,   # Accumulator threshold for circle centers
            minRadius=min_radius,
            maxRadius=max_radius
        )

        candidates = list(map(tuple, np.round(candidates[0, :]).astype("int")))

        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY_INV, 11, 2)
        binary += cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)[1]


        bubble_area = bubble_radius * bubble_radius * math.pi
        circles, empty_circles = [], []
        for c in candidates:
            if Correct.circle_filled_area(binary, c) >= 0.7 * bubble_area:
                circles.append(c)
            else:
                empty_circles.append(c)
        
        return binary, circles, empty_circles
