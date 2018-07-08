import cv2

from duckietown_utils.parameters import Configurable
import numpy as np

from .line_detector_interface import (Detections,
                                      LineDetectorInterface)
import copy


class LineDetectorHSV(Configurable, LineDetectorInterface):
    """ LineDetectorHSV """

    def __init__(self, configuration):
        # Images to be processed
        self.bgr = np.empty(0)
        self.hsv = np.empty(0)
        self.edges = np.empty(0)

        param_names = [
            'hsv_white1',
            'hsv_white2',
            'hsv_yellow1',
            'hsv_yellow2',
            'hsv_red1',
            'hsv_red2',
            'hsv_red3',
            'hsv_red4',
            'dilation_kernel_size',
            'canny_thresholds',
            'hough_threshold',
            'hough_min_line_length',
            'hough_max_line_gap',
        ]
        configuration = copy.deepcopy(configuration)
        Configurable.__init__(self, param_names, configuration)

        self.dilation_kernel_size = 3
        self.canny_thresholds = [80,200]
        self.hough_threshold = 2
        self.hough_min_line_length = 3
        self.hough_max_line_gap = 1
     
        self.hsv_white1 = [0,0,150]
        self.hsv_white2 = [180,60,255]
        self.hsv_yellow1 = [165,140,100]
        self.hsv_yellow2 = [180,255,255]
        self.hsv_red1 = [0,140,100]
        self.hsv_red2 = [15,255,255]
        self.hsv_red3 = [25,140,100]
        self.hsv_red4 = [45,255,255]

    def _colorFilter(self, color):
        # threshold colors in HSV space
        if color == 'white':
            bw = cv2.inRange(self.hsv, self.hsv_white1, self.hsv_white2)
        elif color == 'yellow':
            bw = cv2.inRange(self.hsv, self.hsv_yellow1, self.hsv_yellow2)
        elif color == 'red':
            bw1 = cv2.inRange(self.hsv, self.hsv_red1, self.hsv_red2)
            bw2 = cv2.inRange(self.hsv, self.hsv_red3, self.hsv_red4)
            bw = cv2.bitwise_or(bw1, bw2)
        else:
            raise Exception('Error: Undefined color strings...')

        # binary dilation
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(self.dilation_kernel_size, self.dilation_kernel_size))
        bw = cv2.dilate(bw, kernel)
        
        # refine edge for certain color
        edge_color = cv2.bitwise_and(bw, self.edges)

        return bw, edge_color

    def _findEdge(self, gray):
        edges = cv2.Canny(gray, self.canny_thresholds[0], self.canny_thresholds[1], apertureSize = 3)
        return edges

    def _HoughLine(self, edge):
        lines = cv2.HoughLinesP(edge, 1, np.pi/180, self.hough_threshold, np.empty(1), self.hough_min_line_length, self.hough_max_line_gap)
        if lines is not None:
            lines = np.array(lines[:,0])
        else:
            lines = []
        return lines
 
    def _findNormal(self, bw, lines):
#########
# MISE: COMPLETE THIS
#########
        return centers, normals, lines

    def detectLines(self, color):
        bw, edge_color = self._colorFilter(color)
        lines = self._HoughLine(edge_color)
        centers, normals, lines = self._findNormal(bw, lines)
        return Detections(lines=lines, normals=normals, area=bw, centers=centers)

    def setImage(self, bgr):
        self.bgr = np.copy(bgr)
        self.hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        self.edges = self._findEdge(self.bgr)
  
    def getImage(self):
        return self.bgr
