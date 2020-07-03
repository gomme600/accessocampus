#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   NeOCampus Accessocampus client
   Displays a fullscreen GUI and checks for NFC/face/code to allow the opening of a door/gate
   Makes access requests via MQTT to the server side application
   Supports local checking if the MQTT server doesn't respond
   Author : Sebastian Lucas 2019-2020
"""

##########################
##-LEGACY USER SETTINGS###
##########################

#Connection variables, change as required
MQTT_server = "neocampus.univ-tlse3.fr"
MQTT_user = "test"
MQTT_password = "test"
#The MQTT topic where we find the authorisations
MQTT_auth_topic = "TestTopic/auth"

#The MQTT topic to publish requests
MQTT_request_topic = "TestTopic/req"

#Pin used for the door relay (BCM layout)
RELAY_PIN = 21

#Time in seconds to open the relay when a person is authorised
OPEN_TIME = 5

#Door ID - Type STR (can be anything. Ex: room number)
unitID = "92"

#Code entry page timeout in seconds
CODE_TIMEOUT = 10

#MQTT timeout interval (in seconds)
MQTT_TIMEOUT = 5

#Do we want to use a pi camera?
CAMERA_ENABLED = True

#How long to look for faces before asking for a code (in seconds)?
CAMERA_TIMEOUT = 10

#Face recognition image size
CAM_WIDTH = 960
CAM_HEIGHT = 720
#Face recognition is performed at 160X120px so we set a scale factor based on the capture size (example: 4 if capture:$
SCALE_FACTOR = 6
#MQTT image quality/scale
#percent by which the image is resized
SCALE_PERCENT = 40
#Do we have a thermal camera?
THERMAL_CAM = True
#Is there an offset compared to the normal camera (offset based on the original 80x60px image)?
THERMAL_OFFSET_X = 0
THERMAL_OFFSET_Y = 0

##########################
###----DEV SETTINGS----###
##########################

#File containing the GUI
QTCREATOR_FILE  = "GUI.ui"

#Number of times we have to detect a face before sending the photo
FACE_DETECTION_THRESHOLD = 10

#Display rectangle around detected face
FACE_DISPLAY = True

#Display circle around thermal detection zone
THERMAL_DISPLAY = True

##########################
##----END  SETTINGS----###
##########################

##########################

#########IMPORTS##########
#Raspberry pi GPIO
try:
 import RPi.GPIO as GPIO

#Basic imports
 import time
 import sys
 import subprocess

#CV2 and Lepton thermal camera
 import cv2
 import os
 import numpy as np
 from pylepton import Lepton

#Base64
 import base64

#Ressource file
 import accessocampus_GUI_rc

#JSON
 import json #Used for converting to and from json strings

#MQTT
 import paho.mqtt.client as mqtt #import the mqtt client

#NFC
 from py532lib.i2c import *
 from py532lib.frame import *
 from py532lib.constants import *

#PyQt5
 from PyQt5 import QtCore, QtGui, QtWidgets, uic
 from PyQt5.QtCore import QThread, pyqtSignal, QTimer

except RuntimeError:
    print("Import Error! Check requirements.txt!")
##########################

#######PROGRAM PATH#######
cur_path = os.path.abspath(os.path.dirname(sys.argv[0]))
##########################

#########UI IMPORT########

Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(cur_path, QTCREATOR_FILE))

##########################

##########################
#LOAD SETTINGS
##########################
import configparser
config = configparser.ConfigParser()
try:
  config.read('settings.ini')
  print("Loaded settings.ini !")
  try:
    if('MQTT' in config):
        MQTT_server = config['MQTT'].get('MQTT_server', MQTT_server)
        MQTT_user = config['MQTT'].get('MQTT_user', MQTT_user)
        MQTT_password = config['MQTT'].get('MQTT_password', MQTT_password)
        MQTT_auth_topic = config['MQTT'].get('MQTT_auth_topic', MQTT_auth_topic)
        MQTT_request_topic = config['MQTT'].get('MQTT_request_topic', MQTT_request_topic)
        print("MQTT settings loaded from ini !")
  except:
    print("Failed to load MQTT settings from ini !")

  try:
    if('PINS' in config):
        RELAY_PIN = int(config['PINS'].get('RELAY_PIN', RELAY_PIN))
        print("PIN settings loaded from ini !")
  except:
    print("Failed to load PIN settings from ini !")

  try:
    if('TIME' in config):
        OPEN_TIME = int(config['TIME'].get('OPEN_TIME', OPEN_TIME))
        CODE_TIMEOUT = int(config['TIME'].get('CODE_TIMEOUT', CODE_TIMEOUT))
        MQTT_TIMEOUT = int(config['TIME'].get('MQTT_TIMEOUT', MQTT_TIMEOUT))
        CAMERA_TIMEOUT = int(config['TIME'].get('CAMERA_TIMEOUT', CAMERA_TIMEOUT))
        print("TIME settings loaded from ini !")
  except:
    print("Failed to load TIME settings from ini !")

  try:
    if('ID' in config):
        unitID = config['ID'].get('unitID', unitID)
        print("ID settings loaded from ini !")
  except:
    print("Failed to load ID settings from ini !")

  try:
    if('CAMERA' in config):
        CAMERA_ENABLED = config['TIME'].getboolean('CAMERA_ENABLED', fallback=CAMERA_ENABLED)
        CAM_WIDTH = int(config['TIME'].get('CAM_WIDTH', CAM_WIDTH))
        CAM_HEIGHT = int(config['TIME'].get('CAM_HEIGHT', CAM_HEIGHT))
        SCALE_FACTOR = int(config['TIME'].get('SCALE_FACTOR', SCALE_FACTOR))
        SCALE_PERCENT = int(config['TIME'].get('SCALE_PERCENT', SCALE_PERCENT))
        THERMAL_CAM = config['TIME'].getboolean('THERMAL_CAM', fallback=THERMAL_CAM)
        THERMAL_OFFSET_X = int(config['TIME'].get('THERMAL_OFFSET_X', THERMAL_OFFSET_X))
        THERMAL_OFFSET_Y = int(config['TIME'].get('THERMAL_OFFSET_Y', THERMAL_OFFSET_Y))
        print("CAMERA settings loaded from ini !")
  except:
    print("Failed to load CAMERA settings from ini !")

  try:
    if('QT' in config):
        QTCREATOR_FILE = config['QT'].get('QTCREATOR_FILE', QTCREATOR_FILE)
        print("QT settings loaded from ini !")
  except:
    print("Failed to load QT settings from ini !")

  try:
    if('FACE' in config):
        FACE_DETECTION_THRESHOLD = int(config['FACE'].get('FACE_DETECTION_THRESHOLD', FACE_DETECTION_THRESHOLD))
        FACE_DISPLAY = config['FACE'].getboolean('FACE_DISPLAY', fallback=FACE_DISPLAY)
        THERMAL_DISPLAY = config['FACE'].getboolean('THERMAL_DISPLAY', fallback=THERMAL_DISPLAY)
        print("FACE settings loaded from ini !")
  except:
    print("Failed to load FACE settings from ini !")

except:
    print("Error loading settings.ini !")

#############
#GPIO Setup##
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)

#Default Status#
mqtt_status = "waiting"
camera_status = "waiting"
thermal_camera_status = "waiting"
nfc_status = "waiting"

####Face recognition setup####
if(CAMERA_ENABLED == True):
    # Load the face recognition cascade
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

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    camera_status = "OK"
else:
    camera_status = "off"

    #cam.set(cv2.CAP_PROP_BUFFERSIZE,1)
##############################

#############

######THREADS######
##########################################################
##########################################################
#Face recognition Thread
class FACEThread(QThread):
    #PyQT Signals
    signal_show_cam = pyqtSignal(np.ndarray, name='cam')
    signal_face_found = pyqtSignal()
    signal_acces_req_done = QtCore.pyqtSignal(str, str, bytes, str, bool, name='acces_req_done')

    def __init__(self):
        QThread.__init__(self)
        #Default values on startup
        self.activate_cam = False
        self.cam_startup = 0
        self.lepton_timed_out = False
        self.THERMAL_CAM = THERMAL_CAM
        self.lepton_error_count = 0
        self.old_a = np.zeros((60,80), np.uint8)
        self.thermal_camera_status = thermal_camera_status

    def activate_cam_fct(self, cam_on, uid=None):
        print("Camera on/off: ")
        print(cam_on)
        self.activate_cam = cam_on
        if(uid != None):
            self.card_uid = uid

    def camera_off(self):
        print("Camera on/off: ")
        print(False)
        self.activate_cam = False

    def lepton_timeout(self):
        print("Lepton capture timed out! Disabeling!")
        self.lepton_timed_out = True

    # run method gets called when we start the thread
    def run(self):

     global thermal_camera_status
     global camera_status

     print("Camera Thread!")
     while CAMERA_ENABLED == True:

      if(self.activate_cam == True):
       #Number of times we detected a face
       face_cpt = 0

       with Lepton() as l:
        while self.activate_cam == True:

         if(self.THERMAL_CAM == True):
             thermal_camera_status = "OK"
             #Lepton thermal camera
             #Capture a frame
             a,_ = l.capture(None, False, False, False)
             print("Frame number: ", _)
             print("Line 20: ", a[20, 0].byteswap(True) & 0xFF0F)

             #Lepton error checking, if the camera disconnects we disable it
             if((a[20, 0].byteswap(True) & 0xFF0F) == [0]):
                 print("Lepton error!")
                 self.lepton_error_count = self.lepton_error_count + 1
                 #We reuse the old frame to avoid false detections
                 a = self.old_a
                 #if( (self.lepton_error_count == 4) or (self.lepton_error_count == 5) ):
                 #    print("Resetting SPI")
                 #    subprocess.call(['rmmod', 'spi_bcm2835'])
                 #    sleep(2)
                 #    subprocess.call(['modprobe', 'spi_bcm2835'])
                 #    print("SPI reset")
                 #    sleep(10)
                 if(self.lepton_error_count > 8):
                     print("Lepton error, disabeling!")
                     thermal_camera_status = "KO"
                     self.THERMAL_CAM = False
             else:
                 self.lepton_error_count = 0

             #Stores the current frame for next cycle
             self.old_a = a

             if(self.THERMAL_CAM == True):
                 cv2.normalize(a, a, 0, 65535, cv2.NORM_MINMAX) # extend contrast
                 np.right_shift(a, 8, a) # fit data into 8 bits

                 # perform an attempt to find the (x, y) coordinates of
                 # the area of the image with the largest intensity value
                 #after performing a GaussianBlur to be more precise
                 a = cv2.GaussianBlur(a, (41, 41), 0)
                 (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(a)
                 if(THERMAL_DISPLAY == True):
                     cv2.circle(a, ((maxLoc[0]+THERMAL_OFFSET_X),(maxLoc[1]+THERMAL_OFFSET_Y)), 10, (0, 0, 204), 2)
                 #Resize the thermal image to a better size
                 a = cv2.resize(a, (320, 240))

         # take video frame
         ok, img = cam.read()

         #Get a 160x120px B&W camera image to quickly detect if a face is present
         gray_cam = cv2.cvtColor(cv2.resize(img, (160, 120)), cv2.COLOR_BGR2GRAY)

         #Make sur that we dont detect faces from the old buffer
         if(self.cam_startup > 8):
          # Detect faces
          faces = face_cascade.detectMultiScale(gray_cam, 1.1, 4)
          # Draw rectangle around the faces
          for (x, y, w, h) in faces:
            #Draw the rectangle, SCALE_FACTOR adjusts the rectangle to the chosen display resolution
            if(FACE_DISPLAY == True):
                cv2.rectangle(img, (SCALE_FACTOR*x, SCALE_FACTOR*y), (SCALE_FACTOR*x+SCALE_FACTOR*w, SCALE_FACTOR*y+SCALE_FACTOR*h), (255, 0, 0), 2)
            print("Found face!")
            print(faces)
            #Increment the face counter, this helps to stop false positifs
            face_cpt = face_cpt+1
            #If we have seen a face multiple times we assume that someone is really here
            if(face_cpt > FACE_DETECTION_THRESHOLD):
                #Reset the face counter
                face_cpt = 0
                #Crop the image to just the detected face
                crop_img = img[SCALE_FACTOR*y:SCALE_FACTOR*y+SCALE_FACTOR*h, SCALE_FACTOR*x:SCALE_FACTOR*x+SCALE_FACTOR*w]
                
                #calculate the requested scale of original dimensions to save on file size
                crop_width = int(crop_img.shape[1] * SCALE_PERCENT / 100)
                crop_height = int(crop_img.shape[0] * SCALE_PERCENT / 100)

                # resize image to the requested scale
                crop_img = cv2.resize(crop_img, (crop_width, crop_height) )

                #Convert the cropped image of just the face to jpeg
                retval, img_buf = cv2.imencode('.jpg', crop_img)

                # Convert the image to base64 encoding
                jpg_as_text = base64.b64encode(img_buf)

                #Print detection locations for debugging
                print("Face Values:")
                print("rectangle x: ", SCALE_FACTOR*x)
                print("rectangle y: ", SCALE_FACTOR*y)
                print("rectangle x+w: ", SCALE_FACTOR*x+SCALE_FACTOR*w)
                print("rectangle y+h: ", SCALE_FACTOR*y+SCALE_FACTOR*h)
                if(self.THERMAL_CAM == True):
                    print("circle x: ", (2*SCALE_FACTOR)*(maxLoc[0]+0.1+THERMAL_OFFSET_X))
                    print("circle y: ", (2*SCALE_FACTOR)*(maxLoc[1]+0.1+THERMAL_OFFSET_Y))

                #Thermal detection to check if it is a real person
                if(self.THERMAL_CAM == True):
                    #We use the scale factor*2 because the resolution of the thermal camera is half of the pi camera for detection (80x60px vs 160x120px)
                    if(((SCALE_FACTOR*x) <= ((2*SCALE_FACTOR)*(maxLoc[0]+0.1+THERMAL_OFFSET_X)) <= (SCALE_FACTOR*x+SCALE_FACTOR*w)) & ((SCALE_FACTOR*y) <= ((2*SCALE_FACTOR)*(maxLoc[1]+0.1+THERMAL_OFFSET_Y)) <= (SCALE_FACTOR*y+SCALE_FACTOR*h))):
                        print("Thermal max on face")
                        thermal_detect = True
                    else:
                        print("Thermal max not on face")
                        thermal_detect = False
                    #Send all of the information including a photo and thermal detect status to the MQTT handeler
                    self.signal_acces_req_done.emit(self.card_uid, "0", jpg_as_text, "cam+thermal", thermal_detect) 

                #Send all of the information including a photo but without thermal detect status to the MQTT handeler
                if(self.THERMAL_CAM == False):
                    self.signal_acces_req_done.emit(self.card_uid, "0", jpg_as_text, "cam", False)

                #Display 'Traitement...' and turn off camera
                img = np.zeros((CAM_WIDTH,CAM_HEIGHT,3), np.uint8)
                cv2.putText(img,'Traitement...', (10,700), cv2.FONT_HERSHEY_SIMPLEX, 3, (255,255,255), 8)
                self.cam_startup = 0
                self.activate_cam = False
                self.signal_face_found.emit()

         #Show a blank screen to avoid disclosing last persons face on startup
         if((self.cam_startup < 8) & (self.activate_cam == True)):
             img = np.zeros((CAM_WIDTH,CAM_HEIGHT,3), np.uint8)
             cv2.putText(img,'Demarrage...', (10,700), cv2.FONT_HERSHEY_SIMPLEX, 3, (255,255,255), 8)

         #If the thermal camera is present then overlay and display the images
         if(self.THERMAL_CAM == True):
                
             a = cv2.resize(a, (320, 240))
             color = cv2.cvtColor(np.uint8(a), cv2.COLOR_GRAY2BGR)
             img = cv2.resize(img, (320, 240))

             # add the 2 images
             added_image = cv2.addWeighted(img,0.9,color,0.4,0.2)

             # show image
             self.signal_show_cam.emit(added_image)
             self.cam_startup = self.cam_startup + 1

         #If the thermal camera isn't present then display the camera by itself
         if(self.THERMAL_CAM == False):
             img = cv2.resize(img, (320, 240))
             self.signal_show_cam.emit(img)
             self.cam_startup = self.cam_startup + 1
##########################################################
##########################################################
#MQTT Thread
class MQTTThread(QThread):
    #Define all of the signals
    signal_granted = pyqtSignal()
    signal_denied = pyqtSignal()
    signal_alive = pyqtSignal()
    signal_dead = pyqtSignal()
    signal_local_check = pyqtSignal(str, str, name='local_check')
    signal_code_request = pyqtSignal(str, name='code_req')
    signal_force_open = pyqtSignal()
    signal_force_close = pyqtSignal()
    signal_normal_op = pyqtSignal()
    signal_status_request = pyqtSignal()

    global thermal_camera_status
    global camera_status
    global mqtt_status
    global nfc_status

    def __init__(self):
        QThread.__init__(self)
        #Timeout timer
        self.mqtt_waiting_timer = QTimer()
        #Timer setup
        self.mqtt_waiting_timer.timeout.connect(self.timeout)
        #Waiting variable setup
        self.mqtt_waiting = False

    def timeout(self):
        #On MQTT timeout we decide what to do
        print("MQTT timed out!")
        if(self.auth_type == "code"):
            self.signal_local_check.emit(self.uid, self.code)
        if(self.auth_type == "code_only"):
            self.signal_local_check.emit(self.uid, self.code)
        if(self.auth_type == "cam"):
            self.signal_code_request.emit(self.uid)
        if(self.auth_type == "cam+thermal"):
            self.signal_code_request.emit(self.uid)
        self.mqtt_waiting_timer.stop()
        self.mqtt_waiting = False

    def publish(self, uid, code, image, type, thermal_detect=False):
        #Assemble the MQTT parameters based on the authorisation type
        if(type == "code"):
            self.uid = uid
            self.auth_type = type
            self.code = code
            self.image = 0
            self.thermal_detect = thermal_detect

        if(type == "code_only"):
            self.uid = uid
            self.auth_type = type
            self.code = code
            self.image = 0
            self.thermal_detect = thermal_detect

        if(type == "cam"):
            self.uid = uid
            self.auth_type = type
            self.code = "0"
            self.image = list(image)
            self.thermal_detect = thermal_detect

        if(type == "cam+thermal"):
            self.uid = uid
            self.auth_type = type
            self.code = "0"
            self.image = list(image)
            self.thermal_detect = thermal_detect

        if(type == "status"):
            self.thermal_status = thermal_camera_status
            self.camera_status = camera_status
            self.mqtt_status = mqtt_status
            self.nfc_status = nfc_status

        if((type == "code") or (type == "code_only") or (type == "cam") or (type == "cam+thermal")):
            #We publish the output string
            print("Publishing message to topic", MQTT_request_topic)
            self.seq_id = str(round(time.time()))
            mqtt_payload = {"unitID": unitID, "seq_id": self.seq_id, "auth_type": self.auth_type, "nfc_uid": self.uid, "passcode": self.code, "thermal_detect": self.thermal_detect, "image": self.image}
            self.client.publish(MQTT_request_topic, json.dumps(mqtt_payload)) 
            print("MQTT request sent...")
            #We start waiting for a response
            if(self.mqtt_waiting == False):
                self.mqtt_waiting = True
                self.mqtt_waiting_timer.start(MQTT_TIMEOUT*1000)

        if(type == "status"):
            #We publish the output string
            print("Publishing message to topic", MQTT_request_topic)
            mqtt_payload = {"mqtt_status": self.mqtt_status, "nfc_status": self.nfc_status, "camera_status": self.camera_status, "thermal_status": self.thermal_status}
            self.client.publish(MQTT_request_topic, json.dumps(mqtt_payload))
            print("MQTT request sent...")

    #On connect code
    def on_connect(self, bus, obj, flags, rc):

        global mqtt_status

        if rc == 0:
            self.signal_alive.emit()
            print("MQTT connected!")
            mqtt_status = "OK"
        else:
            self.mqtt_status = "KO"
        if rc == 1:
            self.signal_dead.emit()
            print("Incorrect MQTT protocol!")
        if rc == 2:
            self.signal_dead.emit()
            print("MQTT client ID wrong!")
        if rc == 3:
            self.signal_dead.emit()
            print("MQTT server not available!")
        if rc == 4:
            self.signal_dead.emit()
            print("MQTT credentials wrong!")
        if rc == 5:
            self.signal_dead.emit()
            print("MQTT connection refused!")

    #Outputs log messages and call-backs in the console
    def on_log(self, mqttc, obj, level, string):
        print(string)

    #Code to execute when any MQTT message is received
    def on_message(self, client, userdata, message):
        #Display the received message in the console
        print("message received!")
        print("message received " ,str(message.payload.decode("utf-8")))
        print("message topic=",message.topic)

        #We convert the loop JSON string to a python dictionary
        inData = json.loads(str(message.payload.decode("utf-8")))
        print("We loaded the JSON data!")
        #We load the data from the dictionary using the keys

        #We check if the received message is in the correct format
        if ( ("unitID" in inData) & ("command" in inData) ):

            #We check if the received message is for us
            if( (str(inData["unitID"]) == unitID) | (str(inData["unitID"]) == "ALL") ):

              #Stop the timeout timer as we received a response (if it was running)
              self.mqtt_waiting_timer.stop()
              self.mqtt_waiting = False
              
              if("seq_id" in inData):  
                #Actions to perform based on what command we receive
                print(str(inData["seq_id"]))
                print(self.seq_id)
                print(str(inData["seq_id"]) == self.seq_id)
                if((str(inData["command"]) == "grant") and (str(inData["seq_id"]) == self.seq_id)):
                    print("Acces Granted via MQTT!")
                    self.signal_granted.emit()

                if((str(inData["command"]) == "deny") and (str(inData["seq_id"]) == self.seq_id)):
                    print("Acces Denied via MQTT!")
                    self.signal_denied.emit()

                if((str(inData["command"]) == "ask_code") and (str(inData["seq_id"]) == self.seq_id)):
                    print("Code requested via MQTT!")
                    self.signal_code_request.emit(self.uid)
              else:

                if(str(inData["command"]) == "force_open"):
                    print("Asked to force open!")
                    self.signal_force_open.emit()

                if(str(inData["command"]) == "force_close"):
                    print("Asked to force close!")
                    self.signal_force_close.emit()

                if(str(inData["command"]) == "normal"):
                    print("Asked to resume normal operation!")
                    self.signal_normal_op.emit()

                if(str(inData["command"]) == "status"):
                    print("Asked for status!")
                    self.signal_status_request.emit()

    # run method gets called when we start the thread
    def run(self):

       print("MQTT Thread!")
       #Start of the MQTT subscribing
       ########################################
       #We wait for the system to come up
       #sleep(2)
       self.signal_dead.emit()
       #MQTT address
       broker_address=MQTT_server
       print("creating new MQTT instance")
       self.client = mqtt.Client("P1") #create new instance
       self.client.on_message=self.on_message #attach function to callback
       self.client.on_log=self.on_log #attach logging to log callback
       self.client.on_connect = self.on_connect #attach on connect to callback

       # Auth
       self.client.username_pw_set(username=MQTT_user,password=MQTT_password)

       # now we connect
       print("connecting to MQTT broker")
       self.client.connect(broker_address) #connect to broker

       #Subscribe to all the weather topics we need
       print("Subscribing to topic",MQTT_auth_topic)
       self.client.subscribe(MQTT_auth_topic)

       #Tell the MQTT client to subscribe forever
       print("MQTT alive!")
       self.signal_alive.emit()
       self.client.loop_forever()
       print("MQTT dead!")
       self.signal_dead.emit()
##########################################################
##########################################################
#NFC Thread
class NFCThread(QThread):
    #Signal definitions
    signal_code_request = pyqtSignal(str, name='code_req')
    signal_activate_cam = pyqtSignal(bool, str, name='cam_on')
    signal_change_tab_cam = pyqtSignal(str, name='cam_req')
    signal_card_detected = pyqtSignal()

    def mqtt_alive(self):
        print("MQTT alive received!")
        self.MQTT_started = True

    def mqtt_dead(self):
        print("MQTT dead received!")
        self.MQTT_started = False

    def __init__(self):
        QThread.__init__(self)
        self.nfc_status = nfc_status

    # run method gets called when we start the thread
    def run(self):
        
       print("NFC Thread!")
       #NFC Setup###
       global nfc_status
       nfc_status = "KO"
       pn532 = Pn532_i2c()
       pn532.SAMconfigure()
       nfc_status = "OK"

       while True:
          # Check if a card is available to read
          uid = pn532.read_mifare().get_data()
          # Try again if no card is available.
          if uid is None:
             continue
          print('Found card with UID:', [hex(i) for i in uid])
          card = list(uid)
          card_id = ""
          for block in card:  
              card_id += str(block)
          print("Checking card...")
          print(card_id)
          self.signal_card_detected.emit()
          #We publish the output string
          if(CAMERA_ENABLED == True):
              self.signal_activate_cam.emit(True, card_id)
              self.signal_change_tab_cam.emit(card_id)
              print("Cam request sent!")
          if(CAMERA_ENABLED == False):
              self.signal_code_request.emit(card_id)
              print("Code request signal sent!")
          #We sleep to avoid reading a card multiple times
          time.sleep(4)
##########################################################

##########################################################

#MainWindow#
class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    #MQTT signal definitions
    signal_acces_req_done = QtCore.pyqtSignal(str, str, str, str, name='acces_req_done')
    signal_activate_cam = QtCore.pyqtSignal(bool, name='cam_on')

    #Variables
    face_detected = False
    forced_closed = False
    forced_open = False

    #Timers
    timer_cam = QTimer()
    timer_code = QTimer()
    open_timer = QTimer()
    close_timer = QTimer()

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        
        #Timer setup
        self.open_timer.timeout.connect(self.close_door)
        self.close_timer.timeout.connect(self.close_door)
        self.timer_cam.timeout.connect(self.cam_off)
        self.timer_code.timeout.connect(self.change_tab_nfc)

        #Define an empty code on startup
        self.code = ""
        
        #Disable hidden tabs (code, face detection)
        self.toolBox.setItemEnabled(1,False)
        self.toolBox.setItemEnabled(2,False)

        #Connect all of the push buttons
        self.pushButton_dig_val.clicked.connect(self.on_click_val)
        self.pushButton_dig_val_2.clicked.connect(self.on_click_ann)
        self.pushButton_dig_0.clicked.connect(self.on_click_0)
        self.pushButton_dig_1.clicked.connect(self.on_click_1)
        self.pushButton_dig_2.clicked.connect(self.on_click_2)
        self.pushButton_dig_3.clicked.connect(self.on_click_3)
        self.pushButton_dig_4.clicked.connect(self.on_click_4)
        self.pushButton_dig_5.clicked.connect(self.on_click_5)
        self.pushButton_dig_6.clicked.connect(self.on_click_6)
        self.pushButton_dig_7.clicked.connect(self.on_click_7)
        self.pushButton_dig_8.clicked.connect(self.on_click_8)
        self.pushButton_dig_9.clicked.connect(self.on_click_9)
        self.code_button.clicked.connect(self.change_tab_code_manual)
        self.reboot_button.clicked.connect(self.reboot)

    #PyQt5 slots
    ##########################################################

    def reboot(self):
        os.system('sudo reboot')

    #Face detection
    #Sets a variable to say that we found a face via camera
    def face_found(self):
        self.face_detected = True

    #Toggles the camera
    def cam_toggle(self, cam_bool):
        self.signal_activate_cam.emit(cam_bool)

    #Displays the camera image
    def show_image(self, image):
        self.image = image
        self.image = QtGui.QImage(self.image.data, self.image.shape[1], self.image.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        self.label_cam_img.setPixmap(QtGui.QPixmap.fromImage(self.image))
        
    #Function to turn the camera off
    def cam_off(self):
        print("Requesting to turn cam off")
        self.signal_activate_cam.emit(False)
        self.timer_cam.stop()
        self.toolBox.setCurrentIndex(0)
        if(self.face_detected == False):
            self.change_tab_code(self.nfc_uid)
        if(self.face_detected == True):
            self.change_tab_nfc()
        self.face_detected = False
    ##########################################################
    ##########################################################
    #DOOR CONTROL
    #Function for when acces is granted
    def acces_granted(self):
        print("acces_granted")
        self.open_door()

    #Function for when acces is denied
    def acces_denied(self):
        print("acces_denied")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        self.label_statut_porte.setText("Acces Interdit!")
        self.close_timer.start(OPEN_TIME*1000)
        self.change_tab_nfc()

    #Function to close the door
    def close_door(self):
        print("Close door")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        self.label_statut_porte.setText("Porte fermée")
        self.open_timer.stop()
        self.close_timer.stop()
        self.change_tab_nfc()

    #Function to open the door
    def open_door(self, infinite_open = False):
        print("Opening door!")
        if((self.forced_open == False) and (infinite_open == False) and (self.forced_closed == False)):
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.label_statut_porte.setText("Porte ouverte")
            self.open_timer.start(OPEN_TIME*1000)
            self.change_tab_nfc()

        if((self.forced_open == False) and (infinite_open == True) and (self.forced_closed == False)):
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.label_statut_porte.setText("Porte forcée ouverte")
            self.forced_open = True
            self.change_tab_nfc()

        if((self.forced_open == False) and self.forced_closed == True):
            print("Door cannot be opened (set to force close)")
            self.label_statut_porte.setText("Ouverture impossible! Porte desactivée!")
            self.change_tab_nfc()

        if((self.forced_open == False) and (infinite_open == True) and (self.forced_closed == True)):
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.label_statut_porte.setText("Porte réactivée!")
            self.change_tab_nfc()

        if(self.forced_open == True):
            print("Porte deja forcee ouverte!")

    def force_open(self):
        if(self.forced_closed == True):
            self.forced_closed = False
        self.open_door(True)

    def force_close(self):
        if(self.forced_open == True):
            self.forced_open = False
        self.forced_closed = True
        self.close_door()

    def normal_op(self):
        if(self.forced_closed == True):
            self.forced_closed = False

        if(self.forced_open == True):
            self.forced_open = False
            self.close_door()

    def status_request(self):
        print("Sending status report!")
        self.signal_acces_req_done.emit("0", "0", "0", "status")

    ##########################################################
    ##########################################################
    #TAB CONTROL
    #Function to change to the code entry screen
    def change_tab_code(self, uid):
        self.toolBox.setCurrentIndex(1)
        self.nfc_uid = uid
        self.timer_cam.stop()
        self.timer_code.start(CODE_TIMEOUT*1000)

    def change_tab_code_manual(self):
        self.toolBox.setCurrentIndex(1)
        self.nfc_uid = None
        self.timer_cam.stop()
        self.timer_code.start(CODE_TIMEOUT*1000)

    #Function to change to the homescreen
    def change_tab_nfc(self):
        self.toolBox.setCurrentIndex(0)
        self.code = ""

    #Function to change to the camera screen
    def change_tab_cam(self, uid):
        print("Changing to cam tab and setting up timer")
        self.toolBox.setCurrentIndex(2)
        self.timer_cam.start(CAMERA_TIMEOUT*1000)
        self.nfc_uid = uid
    ##########################################################
    ##########################################################
    #NFC
    #Actions to perform when an NFC card is detected
    def card_detected_actions(self):
        self.label_statut_porte.setText("Carte detectée!")
        self.code = ""
    ##########################################################
    ##########################################################
    #BUTTONS
    #Actions to perform when the validate button is clicked
    def on_click_val(self):
        #Sets us back to the homepage
        self.toolBox.setCurrentIndex(0)
        #Checks that a code was entered and checks it
        if(self.code != ""):

            print("Checking code...")
            if(self.nfc_uid != None):
                self.signal_acces_req_done.emit(self.nfc_uid, self.code, "0", "code")
            else:
                self.signal_acces_req_done.emit(self.code, self.code, "0", "code_only")
            self.code = ""
            self.label_statut_porte.setText("Demande en cours...")
            print("MQTT request signal sent!")

    #Actions to perform when the cancel button is clicked
    def on_click_ann(self):
        self.code = ""
        self.label_statut_porte.setText("Porte fermée")
        self.toolBox.setCurrentIndex(0)

    #Actions to perform when the 0 button is clicked
    def on_click_0(self):
        self.code = self.code + "0"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 1 button is clicked
    def on_click_1(self):
        self.code = self.code + "1"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 2 button is clicked
    def on_click_2(self):
        self.code = self.code + "2"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 3 button is clicked
    def on_click_3(self):
        self.code = self.code + "3"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 4 button is clicked
    def on_click_4(self):
        self.code = self.code + "4"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 5 button is clicked
    def on_click_5(self):
        self.code = self.code + "5"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 6 button is clicked
    def on_click_6(self):
        self.code = self.code + "6"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 7 button is clicked
    def on_click_7(self):
        self.code = self.code + "7"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 8 button is clicked
    def on_click_8(self):
        self.code = self.code + "8"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    #Actions to perform when the 9 button is clicked
    def on_click_9(self):
        self.code = self.code + "9"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()
    ##########################################################
    ##########################################################
    #OTHER
    #Function to check id locally
    def local_check(self, uid, code):
              ID = unitID
              print("Checking local database!")

              card_ok = False
              has_cards = False

              saved_uid  = open(os.path.join(cur_path, "cards.conf"), "r")

              if("---new card---" in saved_uid.read()):
                  has_cards = True
                  print("Loaded saved cards!") 
              else:
                  print("No saved cards!")

              saved_uid.close()
              saved_uid  = open(os.path.join(cur_path, "cards.conf"), "r")

              for line in saved_uid:
                  print(line)
                  if("---new card---" in line):
                      if(has_cards == True):
                         if("#unitID:" + ID + "#" in line):
                             if("#CARD_UID:" + uid + "#" in line):
                                 if("#PASSCODE:" + code + "#" in line):
                                     card_ok = True

                                     print("Acces Granted!")
                                     self.acces_granted()
                                     self.label_statut_porte.setText("Porte ouverte! (Verification hors ligne)")
                  else:
                      print("Checking next line...")

                  if(card_ok == False):
                                 print("Acces Denied")
                                 self.acces_denied()
                                 self.label_statut_porte.setText("Acces Interdit! (Verification hors ligne)") 

              saved_uid.close()
    ##########################################################
    ##########################################################
    
def main():
    #Define the app window
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = MyWindow()
    #Display the window fullscreen
    MainWindow.showFullScreen()

    #MQTT define
    mqtt_thread = MQTTThread()

    #NFC define
    nfc_thread = NFCThread()

    #FACE define
    face_thread = FACEThread()

    #NFC
    nfc_thread.start()  # Finally starts the thread

    # Connect the signal from the thread to the finished method
    nfc_thread.signal_code_request.connect(MainWindow.change_tab_code)
    nfc_thread.signal_activate_cam.connect(face_thread.activate_cam_fct)
    nfc_thread.signal_change_tab_cam.connect(MainWindow.change_tab_cam)
    nfc_thread.signal_card_detected.connect(MainWindow.card_detected_actions)

    #MQTT
    mqtt_thread.start()  # Finally starts the thread

    # Connect the signal from the thread to the finished method
    mqtt_thread.signal_granted.connect(MainWindow.acces_granted)
    mqtt_thread.signal_denied.connect(MainWindow.acces_denied)
    mqtt_thread.signal_alive.connect(nfc_thread.mqtt_alive)
    mqtt_thread.signal_dead.connect(nfc_thread.mqtt_dead)
    mqtt_thread.signal_local_check.connect(MainWindow.local_check)
    mqtt_thread.signal_code_request.connect(MainWindow.change_tab_code)
    mqtt_thread.signal_force_open.connect(MainWindow.force_open)
    mqtt_thread.signal_force_close.connect(MainWindow.force_close)
    mqtt_thread.signal_normal_op.connect(MainWindow.normal_op)
    mqtt_thread.signal_status_request.connect(MainWindow.status_request)

    #Face recognition
    face_thread.start()  # Finally starts the thread

    # Connect the signal from the thread to the finished method
    face_thread.signal_show_cam.connect(MainWindow.show_image)
    face_thread.signal_acces_req_done.connect(mqtt_thread.publish)
    face_thread.signal_face_found.connect(MainWindow.face_found)

    #MainWindow
    MainWindow.signal_acces_req_done.connect(mqtt_thread.publish)
    MainWindow.signal_activate_cam.connect(face_thread.activate_cam_fct)

    sys.exit(app.exec_())
    GPIO.cleanup()


if __name__ == '__main__':
    main()
