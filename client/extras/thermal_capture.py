import argparse
import numpy as np
import cv2
from pylepton import Lepton
import time

with Lepton() as l:
  while(True):
    a,_ = l.capture()
    a = cv2.resize(a, (400, 300))
    cv2.normalize(a, a, 0, 65535, cv2.NORM_MINMAX) # extend contrast
    np.right_shift(a, 8, a) # fit data into 8 bits
    #cv2.imwrite("output.jpg", np.uint8(a)) # write it!
    
    # perform a naive attempt to find the (x, y) coordinates of
    # the area of the image with the largest intensity value
    a = cv2.GaussianBlur(a, (41, 41), 0)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(a)
    cv2.circle(a, maxLoc, 41, (0, 0, 204), 2)

    cv2.imshow('image',np.uint8(a))
    cv2.waitKey(50)
