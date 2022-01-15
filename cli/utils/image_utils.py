import numpy as np
import cv2

def order_points(pts):
        # initialize a list of coordinates that will be ordered
        # such that the first entry in the list is the top-left,
        # the second entry is the top-right, the third is the
        # bottom-right, and the fourth is the bottom-left
        rect = np.zeros((4, 2), dtype=pts.dtype)

        # the top-left point will have the smallest sum, whereas
        # the bottom-right point will have the largest sum
        s = pts.sum(axis = 1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # now, compute the difference between the points, the
        # top-right point will have the smallest difference,
        # whereas the bottom-left will have the largest difference
        diff = np.diff(pts, axis = 1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        # return the ordered coordinates
        return rect

def line_intersect(pts1, pts2):
    m1 = pts1[1] - pts1[0]
    m1 = m1[1] / m1[0] 
    m2 = pts2[1] - pts2[0]
    m2 = m2[1] / m2[0]
    h_line1 = np.array([-m1, 1, m1 * pts1[0][0] - pts1[0][1]])
    h_line2 = np.array([-m2, 1, m2 * pts2[0][0] - pts2[0][1]])
    intersection = np.cross(h_line1, h_line2)
    return intersection[:2] / intersection[2]

# TODO: temporarily abandoned idea, it would be useful for perspective transform
def search_for_markers(image, top_left, bottom_right, resolution):
    delta = 1.0 / (2.54 / resolution) # search in a square with semi-width 1.0cm
    center = line_intersect(top_left[[0, 1]], bottom_right[[1, 2]])
#    return top_left[[0, 1]], bottom_right[[1, 2]]
    top_right_area = np.array([center - delta, center + delta], dtype=int) 
    return top_right_area
    roi = image   
    # blurred = cv2.GaussianBlur(roi, (5, 5), 0)
    # _, thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)
    # # find contours in the thresholded image
    # contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
	#     cv2.CHAIN_APPROX_SIMPLE)
    return roi