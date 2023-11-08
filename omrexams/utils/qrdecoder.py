import re
import numpy as np
import cv2
from . crypt import binary_decrypt
import math
from . colors import *
from . image_utils import order_points
from ctypes.util import find_library
import logging
import click

use_zbar = False

try:
    from pyzbar import pyzbar
    if find_library('zbar'):
        use_zbar = True
except:
    pass

def decode_bottom_right(data):
        m = re.search(r'^\((?P<x0>\d+),(?P<y0>\d+)\)-\((?P<x1>\d+),(?P<y1>\d+)\)/\((?P<width>\d+),(?P<height>\d+)\)/(?P<size>\d+(?:\.\d+)?),(?P<page>\d+)(?:,(?P<start>\d+)-(?P<end>\d+))?$', data)
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
    m = re.search(r'^(?P<id>\d+),(?P<sequence>.+)$', data)
    if not m:
        return None
    # check if the correct sequence is encoded or in clear
    allowed_in_clear = ("".join(chr(i + ord('a')) for i in range(8)) + ",").upper()
    if not m.group('sequence'):
        correct = []
    elif all(c.upper() in allowed_in_clear for c in m.group('sequence')):
        correct = m.group('sequence').split(',')
    else:
        correct = list(c.upper() for c in binary_decrypt(m.group('sequence'), m.group('id')))

    return { 
        # CHECK: removed int across student_id
        'student_id': m.group('id'),
        'correct': correct
    }


def decode(image, highlight=False, offset=5):   
    def search_qrcodes_opencv(image):
        ret_code, decoded_text, qrcodes, _ = cv2.QRCodeDetector().detectAndDecodeMulti(image)     
        # Try to detect (and skip) blank images
        if not ret_code or qrcodes.shape[0] < 2:
            _retval, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if cv2.countNonZero(binary) >= (image.shape[0] * image.shape[1]) * 0.99: # Blank image
                return None, None
        # adaptively change threshold to detect the qrcode
        t = 255
        while t > 0 and (not ret_code or qrcodes.shape[0] < 2 or not all(d for d in decoded_text)):
            t = int(t / 1.61803398875)
            _retval, binary = cv2.threshold(image, 255 - t, 255, cv2.THRESH_BINARY)
            ret_code, decoded_text, qrcodes, _ = cv2.QRCodeDetector().detectAndDecodeMulti(binary)

        if t == 0 or qrcodes is None:
            raise RuntimeError(f"Cannot find qrcodes in page")

        if qrcodes.shape[0] < 2:
            raise RuntimeError(f"Each page should have at least two qrcodes, found {len(qrcodes)}")
        if qrcodes.shape[0] > 2:
            raise RuntimeError(f"Found more than two qrcodes {len(qrcodes)}")     
            
        # TODO: maybe np.lexsort could be used
        x = qrcodes[0, 0, 0], qrcodes[1, 0, 0]
        y = qrcodes[0, 0, 1], qrcodes[1, 0, 1]
        if x[0] > x[1] or (x[0] == x[1] and y[0] > y[1]):
            qrcodes[[0, 1]] = qrcodes[[1, 0]]
            decoded_text = tuple(reversed(decoded_text))

        return decoded_text, qrcodes

    def opencv_decode(image, highlight=False, offset=5):
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
        
        decoded_text, qrcodes = search_qrcodes_opencv(image)

        if decoded_text is None and qrcodes is None:
            # Empty page detected
            return None

        # extract information from the qrcode    
        top_left_decode = decode_top_left(decoded_text[0])
        bottom_right_decode = decode_bottom_right(decoded_text[1])    
        rotated = False    
        if top_left_decode is None or bottom_right_decode is None:            
            # Try a 180deg rotation
            image = cv2.rotate(image, cv2.ROTATE_180)
            decoded_text, qrcodes = search_qrcodes(image)
            top_left_decode = decode_top_left(decoded_text[0])
            bottom_right_decode = decode_bottom_right(decoded_text[1]) 
            rotated = True
        if top_left_decode is None:
            raise ValueError(f"Cannot properly decode top left qrcode content: {decoded_text[0]}")         
        if bottom_right_decode is None:
            raise ValueError(f"Cannot properly decode bottom right qrcode content: {decoded_text[1]}")            
        
        t = order_points(np.array([q for qrcode in qrcodes for q in qrcode]))
        tl = t[0].astype('int')
        br = t[2].astype('int')

        if highlight:
            for qrcode in qrcodes:
                # extract the bounding box location of the qrcode and draw a green 
                # frame around them
                t = order_points(qrcode.astype('int'))
                # currently assumes that the image has the right orientation 
                # if this is not the case, the qrcode.polygon can be inspected
                # and possibly used for rotation
                cv2.rectangle(image, t[0] - offset, t[2] + offset, GREEN, 3)

        metadata = { 
            **top_left_decode,
            **bottom_right_decode,
            'top_left': tl,
            'bottom_right': br,
            'top_left_rect': order_points(qrcodes[0].astype('int')),
            'bottom_right_rect': order_points(qrcodes[1].astype('int')),
            'rotated': rotated
        }
        s = image[tl[1]:br[1], tl[0]:br[0]].shape
        scaling = np.diag([s[1] / metadata['width'], s[0] / metadata['height']])
        metadata['scaling'] = scaling
        if metadata['range'][0] is not None and metadata['range'][1] is not None:
            metadata['page_correction'] = metadata['correct'][metadata['range'][0] - 1:metadata['range'][1]]

        return metadata
    
    def search_qrcodes_pyzbar(image):
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

        return qrcodes

    def pyzbar_decode(image, highlight=False, offset=5):                        
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)         

        qrcodes = search_qrcodes_pyzbar(image)
      
        # extract information from the qrcode
        top_left_decode = decode_top_left(qrcodes[0].data.decode('ascii'))
        bottom_right_decode = decode_bottom_right(qrcodes[1].data.decode('ascii'))        
        rotated = False    
        if top_left_decode is None or bottom_right_decode is None:            
            # Try a 180deg rotation
            image = cv2.rotate(image, cv2.ROTATE_180)
            qrcodes = search_qrcodes_pyzbar(image)
            top_left_decode = decode_top_left(qrcodes[0].data.decode('ascii'))
            bottom_right_decode = decode_bottom_right(qrcodes[1].data.decode('ascii'))
            rotated = True
        if top_left_decode is None:
            raise ValueError(f"Cannot properly decode top left qrcode content: {qrcodes[0].data}")         
        if bottom_right_decode is None:
            raise ValueError(f"Cannot properly decode bottom right qrcode content: {qrcodes[1].data}")     

        tl = np.array(qrcodes[0].rect[:2])
        br = np.array(qrcodes[1].rect[:2]) + np.array(qrcodes[1].rect[2:])

        if highlight:
            for qrcode in qrcodes:
                # extract the bounding box location of the qrcode and draw a green 
                # frame around them
                (x, y, w, h) = qrcode.rect
                cv2.rectangle(image, (int(x - offset), int(y - offset)), (int(x + w + offset), int(y + h + offset)), GREEN, 3)

        metadata = { 
            **top_left_decode,
            **bottom_right_decode,
            'top_left': tl,
            'bottom_right': br,
            'top_left_rect': order_points(np.array(list(map(lambda p: np.array([p.x, p.y]), qrcodes[0].polygon)))),
            'bottom_right_rect': order_points(np.array(list(map(lambda p: np.array([p.x, p.y]), qrcodes[1].polygon)))),
            'rotated': rotated
        }
        s = image[tl[1]:br[1], tl[0]:br[0]].shape
        scaling = np.diag([s[1] / metadata['width'], s[0] / metadata['height']])
        metadata['scaling'] = scaling
        if metadata['range'][0] is not None and metadata['range'][1] is not None:
            metadata['page_correction'] = metadata['correct'][metadata['range'][0] - 1:metadata['range'][1]]

        return metadata        
    
    if use_zbar:
        return pyzbar_decode(image, highlight, offset)
    else:
        return opencv_decode(image, highlight, offset)

