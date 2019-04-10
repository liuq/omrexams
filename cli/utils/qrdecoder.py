import re
import numpy as np
import cv2
from . crypt import vigenere_decrypt
import math
from . colors import *
from pyzbar import pyzbar
from . image_utils import order_points


def decode(image, highlight=False, offset=5):
    qrcodes = pyzbar.decode(image)
    if len(qrcodes) != 2:
        raise RuntimeError("Each page should have exactly two qrcodes, found {}".format(len(qrcodes)))
    qrcodes.sort(key=lambda b: b.rect[0])
    if highlight:
        for qrcode in qrcodes:
            # extract the bounding box location of the qrcode and draw a green 
            # frame around them
            (x, y, w, h) = qrcode.rect
            # currently assumes that the image has the right orientation 
            # if this is not the case, the qrcode.polygon can be inspected
            # and possibly used for rotation
            cv2.rectangle(image, (x - offset, y - offset), (x + w + offset, y + h + offset), GREEN, 3)
    tl = np.array(qrcodes[0].rect[:2])
    br = np.array(qrcodes[1].rect[:2]) + np.array(qrcodes[1].rect[2:])
    # extract information from the qrcodes
    metadata = { 
        **decode_top_left(str(qrcodes[0].data)),
        **decode_bottom_right(str(qrcodes[1].data)),
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
        # TODO: remove, it was fixing a bug in omr generation
        # if metadata['page'] == 1:
        #     metadata['page_correction'] = metadata['correct'][:metadata['range'][1] - 1]
        # else:
        #     metadata['page_correction'] = metadata['correct'][metadata['range'][0] - 2:]
    return metadata

def decode_bottom_right(data):
        m = re.search(r'\((?P<x0>\d+),(?P<y0>\d+)\)-\((?P<x1>\d+),(?P<y1>\d+)\)/\((?P<width>\d+),(?P<height>\d+)\)/(?P<size>\d+(?:\.\d+)?),(?P<page>\d+)(?:,(?P<start>\d+)-(?P<end>\d+))?', data)
        if not m:
            raise RuntimeError("Bottom-right qrcode encoded information do not comply with the expected format:\nfound {}".format(data))
            
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
        raise RuntimeError("Top-left qrcode encoded information do not comply with the expected format:\nfound {}".format(data))
    # check if the correct sequence is encoded or in clear
    if not m.group('sequence'):
        correct = []
    elif ',' in m.group('sequence'):
        correct = m.group('sequence').split(',')
    else:
        correct = vigenere_decrypt(m.group('sequence'), m.group('id')).upper().split(',')
    return { 
        'student_id': int(m.group('id')),
        'date': m.group('date'),
        'correct': correct
    }