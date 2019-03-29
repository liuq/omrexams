import cv2
import numpy as np
from scipy.spatial import cKDTree
from pyzbar import pyzbar
import re
from wand.image import Image
from wand.color import Color
import io
import math
from skimage.feature import peak_local_max
from . utils.crypt import vigenere_decrypt

class Correct:
    """
    This class will operate on a directory with a set of pages and perform the correction 
    according to the information stored in the qrcodes
    """
    pass
