import numpy as np
import cv2

def order_points(pts):
    # it works for rotations angles < 45°
    # the order will be top-left, top-right, bottom-right, bottom-left
    rect = np.zeros((4, 2), dtype=int)

    center = pts.mean(axis=0)
    for p in pts:
        if p[0] < center[0] and p[1] < center[1]:
            rect[0] = p
        elif p[0] > center[0] and p[1] < center[1]:
            rect[1] = p
        elif p[0] > center[0] and p[1] > center[1]:
            rect[2] = p
        else:
            rect[3] = p
 
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