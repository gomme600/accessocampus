##########################
##----USER SETTINGS----###
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
DOOR_ID = "92"

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
SCALE_PERCENT = 80
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

#########UI IMPORT########

Ui_MainWindow, QtBaseClass = uic.loadUiType(QTCREATOR_FILE)

##########################

#############
#GPIO Setup##
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)

#NFC Setup###
pn532 = Pn532_i2c()
pn532.SAMconfigure()

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

##############################

#############

######THREADS######

#Face recognition Thread
class FACEThread(QThread):
    #PyQT Signals
    signal_show_cam = pyqtSignal(np.ndarray, name='cam')
    signal_face_found = pyqtSignal()
    signal_acces_req_done = QtCore.pyqtSignal(str, str, bytes, str, bool, name='uid')

    def __init__(self):
        QThread.__init__(self)
        self.activate_cam = False

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

    # run method gets called when we start the thread
    def run(self):

     print("Camera Thread!")
     while CAMERA_ENABLED == True:

      if(self.activate_cam == True):
       #Number of times we detected a face
       face_cpt = 0

       with Lepton() as l:
        while self.activate_cam == True:

         if(THERMAL_CAM == True):
             #Lepton thermal camera
             #Capture a frame
             a,_ = l.capture()
             cv2.normalize(a, a, 0, 65535, cv2.NORM_MINMAX) # extend contrast
             np.right_shift(a, 8, a) # fit data into 8 bits
    
             # perform an attempt to find the (x, y) coordinates of
             # the area of the image with the largest intensity value
             #after performing a GaussianBlur to be more precise
             a = cv2.GaussianBlur(a, (41, 41), 0)
             (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(a)
             cv2.circle(a, ((maxLoc[0]+THERMAL_OFFSET_X),(maxLoc[1]+THERMAL_OFFSET_Y)), 10, (0, 0, 204), 2)
             #Resize the thermal image to a better size
             a = cv2.resize(a, (320, 240))

         # take video frame
         ok, img = cam.read()

         #Get a 160x120px B&W camera image to quickly detect if a face is present
         gray_cam = cv2.cvtColor(cv2.resize(img, (160, 120)), cv2.COLOR_BGR2GRAY)

         # Detect faces
         faces = face_cascade.detectMultiScale(gray_cam, 1.1, 4)
         # Draw rectangle around the faces
         for (x, y, w, h) in faces:
            #Draw the rectangle, SCALE_FACTOR adjusts the rectangle to the chosen display resolution
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
                print("circle x: ", (2*SCALE_FACTOR)*(maxLoc[0]+0.1+THERMAL_OFFSET_X))
                print("circle y: ", (2*SCALE_FACTOR)*(maxLoc[1]+0.1+THERMAL_OFFSET_Y))

                #Thermal detection to check if it is a real person
                if(THERMAL_CAM == True):
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
                if(THERMAL_CAM == False):
                    self.signal_acces_req_done.emit(self.card_uid, "0", jpg_as_text, "cam", False)

                #Display 'Traitement...' and turn off camera
                img = np.zeros((CAM_WIDTH,CAM_HEIGHT,3), np.uint8)
                cv2.putText(img,'Traitement...', (10,700), cv2.FONT_HERSHEY_SIMPLEX, 3, (255,255,255), 8)
                self.activate_cam = False
                self.signal_face_found.emit()

         #If the thermal camera is present then overlay and display the images
         if(THERMAL_CAM == True):
                
             a = cv2.resize(a, (320, 240))
             color = cv2.cvtColor(np.uint8(a), cv2.COLOR_GRAY2BGR)
             img = cv2.resize(img, (320, 240))

             # add the 2 images
             added_image = cv2.addWeighted(img,0.9,color,0.4,0.2)

             # show image
             self.signal_show_cam.emit(added_image)

         #If the thermal camera isn't present then display the camera by itself
         if(THERMAL_CAM == False):
             img = cv2.resize(img, (320, 240))
             self.signal_show_cam.emit(img)

#MQTT Thread
class MQTTThread(QThread):
    #Define all of the signals
    signal_granted = pyqtSignal()
    signal_denied = pyqtSignal()
    signal_alive = pyqtSignal()
    signal_dead = pyqtSignal()
    signal_local_check = pyqtSignal(str, str, name='uid')
    signal_code_request = pyqtSignal(str, name='uid')

    #Timeout timer
    mqtt_waiting_timer = QTimer()

    def __init__(self):
        QThread.__init__(self)

    def timeout(self):
        #On MQTT timeout we decide what to do
        print("MQTT timed out!")
        if(self.auth_type == "code"):
            self.signal_local_check.emit(self.uid, self.code)
        if(self.auth_type == "cam"):
            self.signal_code_request.emit(self.uid)
        if(self.auth_type == "cam+thermal"):
            self.signal_code_request.emit(self.uid)
        self.mqtt_waiting_timer.stop()

    def publish(self, uid, code, image, type, thermal_detect=False):
        #Assemble the MQTT parameters based on the authorisation type
        if(type == "code"):
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

        #We publish the output string
        print("Publishing message to topic", MQTT_request_topic)
        mqtt_payload = {"door_id": DOOR_ID, "auth_type": self.auth_type, "nfc_uid": self.uid, "passcode": self.code, "thermal_detect": self.thermal_detect, "image": self.image}
        self.client.publish(MQTT_request_topic, json.dumps(mqtt_payload)) 
        print("MQTT request sent...")
        #We start waiting for a response
        self.mqtt_waiting = True
        self.mqtt_waiting_timer.timeout.connect(self.timeout)
        self.mqtt_waiting_timer.start(MQTT_TIMEOUT*1000)


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
        if ( ("door_id" in inData) & ("command" in inData) ):

            #We check if the received message is for us
            if( (str(inData["door_id"]) == DOOR_ID) | (str(inData["door_id"]) == "ALL") ):

                #Stop the timeout timer as we received a response (if it was running)
                self.mqtt_waiting_timer.stop()
                self.mqtt_waiting = False
                
                #Actions to perform based on what command we received
                if(str(inData["command"]) == "granted"):
                    print("Acces Granted via MQTT!")
                    self.signal_granted.emit()

                if(str(inData["command"]) == "denied"):
                    print("Acces Denied via MQTT!")
                    self.signal_denied.emit()

                if(str(inData["command"]) == "ask_code"):
                    print("Code requested via MQTT!")
                    self.signal_code_request.emit(self.uid)

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

#NFC Thread
class NFCThread(QThread):
    #Signal definitions
    signal_granted = pyqtSignal()
    signal_denied = pyqtSignal()
    signal_acces_req = pyqtSignal(str, name='uid')
    signal_code_request = pyqtSignal(str, name='uid')
    signal_activate_cam = pyqtSignal(bool, str, name='cam_on')
    signal_tab_cam = pyqtSignal(str, name='uid')

    def mqtt_alive(self):
        print("MQTT alive received!")
        self.MQTT_started = True

    def mqtt_dead(self):
        print("MQTT dead received!")
        self.MQTT_started = False

    def __init__(self):
        QThread.__init__(self)
        

    # run method gets called when we start the thread
    def run(self):
        
       print("Thread!")

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
          #We publish the output string
          self.signal_tab_cam.emit(card_id)
          if(CAMERA_ENABLED == True):
              self.signal_activate_cam.emit(True, card_id)
              print("Cam request sent!")
          if(CAMERA_ENABLED == False):
              self.signal_code_request.emit(card_id)
              print("Code request signal sent!")
          #We sleep to avoid reading a card multiple times
          time.sleep(4)
######

######

#MainWindow#
class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    #MQTT signal definitions
    signal_acces_req_done = QtCore.pyqtSignal(str, str, str, str, name='uid')
    signal_activate_cam = QtCore.pyqtSignal(bool, name='cam_on')

    #Variables
    face_detected = False

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

    #PyQt5 slots

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

    #Actions to perform when the validate button is clicked
    def on_click_val(self):
        #Sets us back to the homepage
        self.toolBox.setCurrentIndex(0)
        #Checks that a code was entered and checks it
        if(self.code != ""):

            print("Checking code...")
            self.signal_acces_req_done.emit(self.nfc_uid, self.code, "0", "code")
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
    def open_door(self):
        print("Opening door!")
        GPIO.output(RELAY_PIN, GPIO.LOW)
        self.label_statut_porte.setText("Porte ouverte")
        self.open_timer.start(OPEN_TIME*1000)
        self.change_tab_nfc()

    #Function to change to the code entry screen
    def change_tab_code(self, uid):
        self.toolBox.setCurrentIndex(1)
        self.nfc_uid = uid
        self.timer_cam.stop()
        self.timer_code.timeout.connect(self.change_tab_nfc)
        self.timer_code.start(CODE_TIMEOUT*1000)

    #Function to change to the homescreen
    def change_tab_nfc(self):
        self.toolBox.setCurrentIndex(0)
        self.code = ""

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

    #Function to change to the camera screen
    def change_tab_cam(self, uid):
        print("Changing to cam tab and setting up timer")
        self.toolBox.setCurrentIndex(2)
        self.timer_cam.start(CAMERA_TIMEOUT*1000)
        self.nfc_uid = uid

    #Function to check id locally
    def local_check(self, uid, code):
              ID = DOOR_ID
              print("Checking local database!")

              card_ok = False
              has_cards = False

              saved_uid  = open("cards.conf", "r")

              if("---new card---" in saved_uid.read()):
                  has_cards = True
                  print("Loaded saved cards!") 
              else:
                  print("No saved cards!")

              saved_uid.close()
              saved_uid  = open("cards.conf", "r")

              for line in saved_uid:
                  print(line)
                  if("---new card---" in line):
                      if(has_cards == True):
                         if("#DOOR_ID:" + ID + "#" in line):
                             if("#CARD_UID:" + uid + "#" in line):
                                 if("#PASSCODE:" + code + "#" in line):
                                     card_ok = True

                                     print("Acces Granted!")
                                     GPIO.output(RELAY_PIN, GPIO.LOW)
                                     self.label_statut_porte.setText("Porte ouverte! (Verification hors ligne)") 
                                     self.open_timer.timeout.connect(self.close_door)
                                     self.open_timer.start(5000)
                  else:
                      print("Checking next line...")

                  if(card_ok == False):
                                 print("Acces Denied")
                                 GPIO.output(RELAY_PIN, GPIO.HIGH)
                                 self.label_statut_porte.setText("Acces Interdit! (Verification hors ligne)") 
                                 self.close_timer.timeout.connect(self.close_door)
                                 self.close_timer.start(5000)

              saved_uid.close()


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
    nfc_thread.signal_granted.connect(MainWindow.acces_granted)
    nfc_thread.signal_denied.connect(MainWindow.acces_denied)
    nfc_thread.signal_acces_req.connect(MainWindow.change_tab_code)
    nfc_thread.signal_code_request.connect(MainWindow.change_tab_code)

    #MQTT
    mqtt_thread.start()  # Finally starts the thread

    # Connect the signal from the thread to the finished method
    mqtt_thread.signal_granted.connect(MainWindow.acces_granted)
    mqtt_thread.signal_denied.connect(MainWindow.acces_denied)
    mqtt_thread.signal_alive.connect(nfc_thread.mqtt_alive)
    mqtt_thread.signal_dead.connect(nfc_thread.mqtt_dead)
    mqtt_thread.signal_local_check.connect(MainWindow.local_check)
    mqtt_thread.signal_code_request.connect(MainWindow.change_tab_code)

    #Face recognition
    face_thread.start()  # Finally starts the thread

    # Connect the signal from the thread to the finished method
    face_thread.signal_show_cam.connect(MainWindow.show_image)
    nfc_thread.signal_activate_cam.connect(face_thread.activate_cam_fct)
    nfc_thread.signal_tab_cam.connect(MainWindow.change_tab_cam)
    face_thread.signal_acces_req_done.connect(mqtt_thread.publish)
    face_thread.signal_face_found.connect(MainWindow.face_found)

    #MainWindow
    MainWindow.signal_acces_req_done.connect(mqtt_thread.publish)
    MainWindow.signal_activate_cam.connect(face_thread.activate_cam_fct)

    sys.exit(app.exec_())
    GPIO.cleanup()


if __name__ == '__main__':
    main()
