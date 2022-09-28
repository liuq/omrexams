import re
import numpy as np
import cv2
from . crypt import vigenere_decrypt
import math
from . colors import *
from . image_utils import order_points
from pyzbar import pyzbar
from ctypes.util import find_library

def decode_bottom_right(data):
        m = re.search(r'\((?P<x0>\d+),(?P<y0>\d+)\)-\((?P<x1>\d+),(?P<y1>\d+)\)/\((?P<width>\d+),(?P<height>\d+)\)/(?P<size>\d+(?:\.\d+)?),(?P<page>\d+)(?:,(?P<start>\d+)-(?P<end>\d+))?', data)
        if not m:
            return None
            
        p0, p1 = np.array([m.group('x0'), m.group('y0')], dtype=int), np.array([m.group('x1'), m.group('y1')], dtype=int)
        width = int(m.group('width'))
        height = int(m.group('height'))
        size = float(m.group('size'))
        
        return { 'p0': p0, 
                 'p1': p1, 
                 'width': width, 
                 'height': height,
                 'size': size,
                 'page': int(m.group('page')), 
                 'range': (int(m.group('start')), int(m.group('end')))
               }

def decode_top_left(data):
    m = re.search(r'(?P<id>\d+),(?P<date>\d+/\d+/\d+),\[(?P<sequence>[^\]]+)\]', data)
    if not m:
        return None
    # check if the correct sequence is encoded or in clear
    if not m.group('sequence'):
        correct = []
    elif ',' in m.group('sequence'):
        correct = m.group('sequence').split(',')
    else:
        correct = vigenere_decrypt(m.group('sequence'), m.group('id')).upper().split(',')
    return { 
        # CHECK: removed int across student_id
        'student_id': m.group('id'),
        'date': m.group('date'),
        'correct': correct
    }


def decode(image, highlight=False, offset=5):   
    def opencv_decode(image, highlight=False, offset=5):
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
        ret_code, decoded_text, qrcodes, _ = cv2.QRCodeDetector().detectAndDecodeMulti(image)    
        # Try to detect (and skip) blank images
        if not ret_code or qrcodes.shape[0] < 2:
            _retval, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if cv2.countNonZero(binary) >= (image.shape[0] * image.shape[1]) * 0.99: # Blank image
                return None
        # adaptively change threshold to detect the qrcode
        t = 255
        while t > 0 and (not ret_code or qrcodes.shape[0] < 2 or not all(d for d in decoded_text)):
            t = int(t / 1.61803398875)
            _retval, binary = cv2.threshold(image, 255 - t, 255, cv2.THRESH_BINARY)
            ret_code, decoded_text, qrcodes, _ = cv2.QRCodeDetector().detectAndDecodeMulti(binary)

        if qrcodes.shape[0] < 2:
            raise RuntimeError("Each page should have at least two qrcodes, found {}".format(len(qrcodes)))
        if qrcodes.shape[0] > 2:
            raise RuntimeError("Found more than two qrcodes {}".format(qrcodes))     

        # TODO: maybe np.lexsort could be used
        x = qrcodes[0, 0, 0], qrcodes[1, 0, 0]
        y = qrcodes[0, 0, 1], qrcodes[1, 0, 1]
        if x[0] > x[1] or (x[0] == x[1] and y[0] > y[1]):
            qrcodes[[0, 1]] = qrcodes[[1, 0]]
            decoded_text = tuple(reversed(decoded_text))

        if highlight:
            for qrcode in qrcodes:
                # extract the bounding box location of the qrcode and draw a green 
                # frame around them
                t = order_points(qrcode.astype('int'))
                # currently assumes that the image has the right orientation 
                # if this is not the case, the qrcode.polygon can be inspected
                # and possibly used for rotation
                cv2.rectangle(image, t[0] - offset, t[2] + offset, GREEN, 3)
        # extract information from the qrcode    
        top_left_decode = decode_top_left(decoded_text[0])
        if top_left_decode is None:
            # TODO: possibly handle 180deg rotation
            raise ValueError(f"Cannot properly decode top left qrcode content: {decoded_text[0]}")
        bottom_right_decode = decode_bottom_right(decoded_text[1]) 
        if bottom_right_decode is None:
            raise ValueError(f"Cannot properly decode bottom right qrcode content: {decoded_text[1]}")            
        
        t = order_points(np.array([q for qrcode in qrcodes for q in qrcode]))
        tl = t[0].astype('int')
        br = t[2].astype('int')

        metadata = { 
            **top_left_decode,
            **bottom_right_decode,
            'top_left': tl,
            'bottom_right': br,
            'top_left_rect': order_points(qrcodes[0].astype('int')),
            'bottom_right_rect': order_points(qrcodes[1].astype('int'))
        }
        s = image[tl[1]:br[1], tl[0]:br[0]].shape
        scaling = np.diag([s[1] / metadata['width'], s[0] / metadata['height']])
        metadata['scaling'] = scaling
        if metadata['range'][0] is not None and metadata['range'][1] is not None:
            metadata['page_correction'] = metadata['correct'][metadata['range'][0] - 1:metadata['range'][1]]

        return metadata

    def pyzbar_decode(image, highlight=False, offset=5):
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
        qrcodes = pyzbar.decode(image, symbols=[pyzbar.ZBarSymbol.QRCODE])
         # Try to detect (and skip) blank images
        if len(qrcodes) < 2:
            _retval, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if cv2.countNonZero(binary) >= (image.shape[0] * image.shape[1]) * 0.99: # Blank image
                return None
        # adaptively change threshold to detect the qrcode
        t = 255
        while t > 0 and len(qrcodes) < 2:
            t = int(t / 1.61803398875)
            _retval, binary = cv2.threshold(image, 255 - t, 255, cv2.THRESH_BINARY)
            qrcodes = pyzbar.decode(binary, symbols=[pyzbar.ZBarSymbol.QRCODE])

        if len(qrcodes) < 2:
            raise RuntimeError("Each page should have at least two qrcodes, found {}".format(len(qrcodes)))
        if len(qrcodes) > 2:
            raise RuntimeError("Found more than two qrcodes {}".format(qrcodes))
        qrcodes.sort(key=lambda b: b.rect[0])

        if highlight:
            for qrcode in qrcodes:
                # extract the bounding box location of the qrcode and draw a green 
                # frame around them
                (x, y, w, h) = qrcode.rect
                cv2.rectangle(image, (int(x - offset), int(y - offset)), (int(x + w + offset), int(y + h + offset)), GREEN, 3)
        # extract information from the qrcode
        top_left_decode = decode_top_left(str(qrcodes[0].data))
        bottom_right_decode = decode_bottom_right(str(qrcodes[1].data))        

        tl = np.array(qrcodes[0].rect[:2])
        br = np.array(qrcodes[1].rect[:2]) + np.array(qrcodes[1].rect[2:])

        metadata = { 
            **top_left_decode,
            **bottom_right_decode,
            'top_left': tl,
            'bottom_right': br,
            'top_left_rect': order_points(np.array(list(map(lambda p: np.array([p.x, p.y]), qrcodes[0].polygon)))),
            'bottom_right_rect': order_points(np.array(list(map(lambda p: np.array([p.x, p.y]), qrcodes[1].polygon))))
        }
        s = image[tl[1]:br[1], tl[0]:br[0]].shape
        scaling = np.diag([s[1] / metadata['width'], s[0] / metadata['height']])
        metadata['scaling'] = scaling
        if metadata['range'][0] is not None and metadata['range'][1] is not None:
            metadata['page_correction'] = metadata['correct'][metadata['range'][0] - 1:metadata['range'][1]]

        return metadata        
    
    if find_library('zbar'):
        return pyzbar_decode(image, highlight, offset)
    else:
        return opencv_decode(image, highlight, offset)
