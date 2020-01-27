#!/usr/bin/env python3
import cv2
import os
import time
import numpy as np
from pylepton import Lepton

# Load the cascade
#face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
# setup pi camera 
if os.path.exists('/dev/video0') == False:
  path = 'sudo modprobe bcm2835-v4l2'
  os.system (path)
  time.sleep(1)
path = 'v4l2-ctl --set-ctrl=auto_exposure=0'
os.system (path)
  
# start video
cam = cv2.VideoCapture(0)

cam.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
# setup window
winName = "Scope"
cv2.namedWindow(winName)

# read foreground image
#foreground = cv2.imread('target.jpg')

with Lepton() as l:
  while True:
    # take video frame
    ok, img = cam.read()
 
    gray_cam = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_cascade.detectMultiScale(gray_cam, 1.1, 4)
    # Draw rectangle around the faces
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)

    #Lepton
    a,_ = l.capture()
    a = cv2.resize(a, (160, 120))
    cv2.normalize(a, a, 0, 65535, cv2.NORM_MINMAX) # extend contrast
    np.right_shift(a, 8, a) # fit data into 8 bits
    #cv2.imwrite("output.jpg", np.uint8(a)) # write it!
    
    # perform a naive attempt to find the (x, y) coordinates of
    # the area of the image with the largest intensity value
    a = cv2.GaussianBlur(a, (41, 41), 0)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(a)
    cv2.circle(a, maxLoc, 41, (0, 0, 204), 2)

    color = cv2.cvtColor(np.uint8(a), cv2.COLOR_GRAY2BGR)

    # add the 2 images
    #added_image = cv2.addWeighted(img,0.9,np.uint8(a),0.4,0.2)
    added_image = cv2.addWeighted(img,0.9,color,0.4,0.2)
    #added_image = img
    # show image
    cv2.imshow( winName,added_image)
    # wait
    key = cv2.waitKey(10)
    # press Esc to EXIT
    if key == 27:
       cv2.destroyWindow(winName)
       break
