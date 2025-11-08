import re
import numpy as np
import cv2
from . crypt import binary_decrypt
from . colors import *
from . image_utils import order_points
from ctypes.util import find_library
import logging
import click

logger = logging.getLogger("omrexams")


TOP_LEFT_REGEX = r'^(?P<id>[\d-]+),(?P<sequence>.+)$'
BOTTOM_RIGHT_REGEX = r'^\((?P<x0>\d+),\s*(?P<y0>\d+)\)-\((?P<x1>\d+),\s*(?P<y1>\d+)\)/\((?P<qrwidth>\d+),\s*(?P<qrheight>\d+)\)/(?P<bsize>\d+(?:\.\d+)?),\s*(?P<page>\d+)(?:,(?P<start>\d+)-(?P<end>\d+))?$'

available_libraries = ['openCV']
try:
    import zxingcpp
    available_libraries.append('zxingcpp')
except: 
    pass
try:
    from pyzbar import pyzbar
    if find_library('zbar'):
        available_libraries.append('pyzbar')
except:
    pass

def check_rotation(data):
    if re.search(TOP_LEFT_REGEX, data[0]) and re.search(BOTTOM_RIGHT_REGEX, data[1]):
        return False
    if re.search(BOTTOM_RIGHT_REGEX, data[0]) and re.search(TOP_LEFT_REGEX, data[1]):
        return True
    raise RuntimeError(f"Not meaningful qrcode content {data}")

def decode_bottom_right(data):
        m = re.search(BOTTOM_RIGHT_REGEX, data)
        if not m:
            return None
            
        p0, p1 = np.array([m.group('x0'), m.group('y0')], dtype=int), np.array([m.group('x1'), m.group('y1')], dtype=int)
        qrwidth = int(m.group('qrwidth'))
        qrheight = int(m.group('qrheight'))
        bsize = float(m.group('bsize'))
        
        return { 'p0': p0, 
                 'p1': p1, 
                 'qrwidth': qrwidth, 
                 'qrheight': qrheight,
                 'bsize': bsize,
                 'page': int(m.group('page')), 
                 'range': (int(m.group('start')), int(m.group('end')))
               }

def decode_top_left(data):
    m = re.search(TOP_LEFT_REGEX, data)
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


# Preprocess the image to improve QR code detection
# Not used yet, but could be useful in some cases, to be cheked
def prepare_image_for_decoding(image):
    if len(image.shape) > 2:
        g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        g = image
    # 1. Adaptive contrast equalization (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    g = clahe.apply(g)

    # 2. Light correction (division normalization)
    blur = cv2.GaussianBlur(g, (61,61), 0)
    blur = np.clip(blur, 1, 255).astype(np.float32)
    norm = (g.astype(np.float32) / blur) * 128
    g = np.clip(norm, 0, 255).astype(np.uint8)

    # 3. Micro-contrast boosting (unsharp mask)
    sharp = cv2.GaussianBlur(g, (0,0), sigmaX=1.0)
    g = cv2.addWeighted(g, 1.5, sharp, -0.5, 0)

    # 4. Adaptive threshold and merge (useful when QR too light)
    bw1 = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 10)
    bw2 = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 35, 7)
    bw = cv2.bitwise_and(bw1, bw2)

    # 5. Morph close for removing small holes 
    # TODO: check if needed
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)

    return bw


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
        while not np.isclose(t, 0.0) and (not ret_code or qrcodes.shape[0] < 2 or not all(d for d in decoded_text)):
            t = int(t / 1.61803398875)
            _, binary = cv2.threshold(image, 255 - t, 255, cv2.THRESH_BINARY)
            ret_code, decoded_text, qrcodes, _ = cv2.QRCodeDetector().detectAndDecodeMulti(binary)

        if qrcodes is None:
            raise RuntimeError(f"Cannot find qrcodes in page")

        if qrcodes.shape[0] < 2:
            raise RuntimeError(f"Each page should have at least two qrcodes, found {len(qrcodes)}")
        if qrcodes.shape[0] == 4:
            click.secho("Found 4 qrcodes in page, probably it is an A3 printed exam, therefore you should use --paper a3 in sorting", color="red")
            raise RuntimeError("Found 4 qrcodes, probably you should use --paper a3 in sorting")
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
        
        # decide for rotation
        rotated = check_rotation(decoded_text)
        if rotated:
            image = cv2.rotate(image, cv2.ROTATE_180)
            decoded_text, qrcodes = search_qrcodes_opencv(image)

        # extract information from the qrcode    
        top_left_decode = decode_top_left(decoded_text[0])
        bottom_right_decode = decode_bottom_right(decoded_text[1])                     
        
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
        scaling = np.diag([s[1] / metadata['qrwidth'], s[0] / metadata['qrheight']])
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
            raise RuntimeError(f"Each page should have at least two qrcodes, found {len(qrcodes)}")
        if len(qrcodes) == 4:
            click.secho("Found 4 qrcodes in page, probably it is an A3 printed exam, therefore you should use --paper a3 in sorting", color="red")
            raise RuntimeError("Found 4 qrcodes, probably you should use --paper a3 in sorting")
        if len(qrcodes) > 2:
            raise RuntimeError(f"Found more than two qrcodes {qrcodes}")
        qrcodes.sort(key=lambda b: b.rect[0])

        return qrcodes

    def pyzbar_decode(image, highlight=False, offset=5):                        
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)                 

        qrcodes = search_qrcodes_pyzbar(image)
        if len(qrcodes) < 2:
            raise RuntimeError(f"Each page should have at least two qrcodes, found {len(qrcodes)}")
        if len(qrcodes) == 4:
            click.secho("Found 4 qrcodes in page, probably it is an A3 printed exam, therefore you should use --paper a3 in sorting", color="red")
            raise RuntimeError("Found 4 qrcodes, probably you should use --paper a3 in sorting")
        if len(qrcodes) > 2:
            raise RuntimeError(f"Found more than two qrcodes {qrcodes}")
      
        rotated = check_rotation(list(map(lambda x: x.data.decode('ascii'), qrcodes)))
        if rotated:
            image = cv2.rotate(image, cv2.ROTATE_180)
            qrcodes = search_qrcodes_pyzbar(image)

        # extract information from the qrcode
        top_left_decode = decode_top_left(qrcodes[0].data.decode('ascii'))
        bottom_right_decode = decode_bottom_right(qrcodes[1].data.decode('ascii'))           

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
        scaling = np.diag([s[1] / metadata['qrwidth'], s[0] / metadata['qrheight']])
        metadata['scaling'] = scaling
        if metadata['range'][0] is not None and metadata['range'][1] is not None:
            metadata['page_correction'] = metadata['correct'][metadata['range'][0] - 1:metadata['range'][1]]

        return metadata            
    
    def search_qrcodes_zxing(image, highlight=False, offset=5):
        return zxingcpp.read_barcodes(image)

    def zxing_decode(image, highlight=False, offset=5):
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)                 

        qrcodes = search_qrcodes_zxing(image)
        if len(qrcodes) < 2:
            raise RuntimeError(f"Each page should have at least two qrcodes, found {len(qrcodes)}")
        if len(qrcodes) == 4:
            click.secho("Found 4 qrcodes in page, probably it is an A3 printed exam, therefore you should use --paper a3 in sorting", color="red")
            raise RuntimeError("Found 4 qrcodes, probably you should use --paper a3 in sorting")
        if len(qrcodes) > 2:
            raise RuntimeError(f"Found more than two qrcodes {qrcodes}")
      
        rotated = check_rotation(list(map(lambda x: x.text, qrcodes)))
        if rotated:
            image = cv2.rotate(image, cv2.ROTATE_180)
            qrcodes = search_qrcodes_zxing(image)

        # extract information from the qrcode
        top_left_decode = decode_top_left(qrcodes[0].text)
        bottom_right_decode = decode_bottom_right(qrcodes[1].text)    

        tl = np.array([qrcodes[0].position.top_left.x, qrcodes[0].position.top_left.y])
        br = np.array([qrcodes[1].position.bottom_right.x, qrcodes[1].position.bottom_right.y])

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
            'top_left_rect': np.array([[qrcodes[0].position.top_left.x, qrcodes[0].position.top_left.y], [qrcodes[0].position.top_right.x, qrcodes[0].position.top_right.y], [qrcodes[0].position.bottom_left.x, qrcodes[0].position.bottom_left.y], [qrcodes[0].position.bottom_right.x, qrcodes[0].position.bottom_right.y]]),
            'bottom_right_rect': np.array([[qrcodes[1].position.top_left.x, qrcodes[1].position.top_left.y], [qrcodes[1].position.top_right.x, qrcodes[1].position.top_right.y], [qrcodes[1].position.bottom_left.x, qrcodes[1].position.bottom_left.y], [qrcodes[1].position.bottom_right.x, qrcodes[1].position.bottom_right.y]]),
            'rotated': rotated
        }
        s = image[tl[1]:br[1], tl[0]:br[0]].shape
        scaling = np.diag([s[1] / metadata['qrwidth'], s[0] / metadata['qrheight']])
        metadata['scaling'] = scaling
        if metadata['range'][0] is not None and metadata['range'][1] is not None:
            metadata['page_correction'] = metadata['correct'][metadata['range'][0] - 1:metadata['range'][1]]

        return metadata     

    # Go in order of performance
    if 'zxingcpp' in available_libraries:
        try:
            return zxing_decode(image, highlight, offset)
        except:
            pass
    if 'pyzbar' in available_libraries:
        try:
            return pyzbar_decode(image, highlight, offset)
        except:
            pass
    # FALLBACK to opencv
    assert 'openCV' in available_libraries, "OpenCV should be always available"
    try:
        return opencv_decode(image, highlight, offset)
    except:
        pass
    # FALLBACK
    if len(image.shape) > 2:
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray_img = image
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_image = clahe.apply(gray_img)
    return opencv_decode(clahe_image, highlight, offset)


        

