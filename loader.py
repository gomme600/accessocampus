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

#Door ID - Type Str (can be anything. Ex: room number)
DOOR_ID = "92"

##########################
##----END  SETTINGS----###
##########################

##########################

#########IMPORTS##########
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")

import time

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
import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
##########################

#########UI IMPORT########

qtcreator_file  = "GUI.ui" # Enter file here.
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtcreator_file)

##########################

#############
#GPIO Setup##
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)

#NFC Setup###
pn532 = Pn532_i2c()
pn532.SAMconfigure()
#############

######THREADS######
#MQTT Thread
class MQTTThread(QThread):
    signal_granted = pyqtSignal()
    signal_denied = pyqtSignal()
    signal_alive = pyqtSignal()
    signal_dead = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def publish(self, uid, code):
        #We publish the output string
        print("Publishing message to topic", MQTT_request_topic)
        mqtt_payload = {"door_id": DOOR_ID, "auth_type": 0, "nfc_uid": uid, "passcode": code, "image": 0}
        self.client.publish(MQTT_request_topic, json.dumps(mqtt_payload)) 
        print("MQTT request sent...")

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

        if ( ("door_id" in inData) & ("command" in inData) ):

            if( (str(inData["door_id"]) == DOOR_ID) | (str(inData["door_id"]) == "ALL") ):

                if(str(inData["command"]) == "granted"):
                    print("Acces Granted via MQTT!")
                    self.signal_granted.emit()

                if(str(inData["command"]) == "denied"):
                    print("Acces Denied via MQTT!")
                    self.signal_denied.emit()

    # run method gets called when we start the thread
    def run(self):

       print("Thread!")
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
    signal_granted = pyqtSignal()
    signal_denied = pyqtSignal()
    signal_acces_req = pyqtSignal(str, name='uid')
    signal_code_request = pyqtSignal(str, name='uid')

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
       mqtt_thread = MQTTThread()

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
          if(self.MQTT_started == True):
              #We publish the output string
              #self.signal_acces_req.emit(card_id)
              self.signal_code_request.emit(card_id)
              print("Code request signal sent!")
              sleep(4)
          else:
              saved_uid  = open("cards.conf", "r")
    
              card_ok = False
              has_cards = False

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
                         if(card_id in line):
                             card_ok = True

                             print("Acces Granted!")
                             self.signal_granted.emit()
                             print("Signal emitted!")
                             sleep(5)
                         if(card_ok == False):
                              print("Acces Denied")
                              self.signal_denied.emit()
                              print("Signal emitted!")
                  else:
                      print("Checking next line...")

              saved_uid.close()
######

######

#MainWindow#
class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    #MQTT signal
    signal_acces_req_done = QtCore.pyqtSignal(str, str, name='uid')

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        
        #MQTT signal
        #signal_acces_req_done = QtCore.pyqtSignal(str, str, name='uid')
       

        #Definition of an empty code
        self.code = ""
        
        self.toolBox.setItemEnabled(1,False)

        #self.MainWindow.showFullScreen()

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

        #self.mqtt_thread = MQTTThread
        #self.signal_acces_req_done.connect(mqtt_thread.publish)

    #@pyqtSlot()
    def on_click_val(self):
        self.toolBox.setCurrentIndex(0)
        if(self.code != ""):
        
            print("Checking code...")
            if(True):
              #We publish the output string
              #self.signal_acces_req_done.emit(self.mqtt_thread.publish(self.uid, self.code))
              self.signal_acces_req_done.emit(self.nfc_uid, self.code)
              self.code = ""
              self.label_statut_porte.setText("Demande en cours...")
              print("MQTT request signal sent!")
            else:
              saved_code  = open("codes.conf", "r")
    
              code_ok = False
              has_codes = False

              if("---new code---" in saved_code.read()):
                has_codes = True
                print("Loaded saved codes!") 
              else:
                print("No saved codes!")

              saved_code.close()
              saved_code  = open("codes.conf", "r")

              for line in saved_code:
               print(line)
               if("---new code---" in line):
                  if(has_codes == True):
                     if(self.code in line):
                          code_ok = True

                          print("Acces Granted!")
                          GPIO.output(RELAY_PIN, GPIO.LOW)
                          self.label_statut_porte.setText("Porte ouverte") 
                          self.timer = QTimer()
                          self.timer.timeout.connect(self.close_door)
                          self.timer.start(5000)
                     if(code_ok == False):
                          print("Acces Denied")
                          GPIO.output(RELAY_PIN, GPIO.HIGH)
                          self.label_statut_porte.setText("Acces Interdit!") 
                          self.timer = QTimer()
                          self.timer.timeout.connect(self.close_door)
                          self.timer.start(5000)
               else:
                  print("Checking next line...")

              saved_code.close()
              self.code = ""
        else:
            self.label_statut_porte.setText("Entrez code!")
            self.timer = QTimer()
            self.timer.timeout.connect(self.close_door)
            self.timer.start(5000)
            self.code = ""

    def on_click_ann(self):
        self.code = ""
        self.label_statut_porte.setText("Porte fermée")
        self.toolBox.setCurrentIndex(0)

    def on_click_0(self):
        self.code = self.code + "0"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_1(self):
        self.code = self.code + "1"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_2(self):
        self.code = self.code + "2"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()  

    def on_click_3(self):
        self.code = self.code + "3"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_4(self):
        self.code = self.code + "4"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_5(self):
        self.code = self.code + "5"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_6(self):
        self.code = self.code + "6"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_7(self):
        self.code = self.code + "7"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_8(self):
        self.code = self.code + "8"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def on_click_9(self):
        self.code = self.code + "9"
        self.label_statut_porte.setText(self.code)
        self.timer_code.stop()

    def acces_granted(self):
        print("acces_granted")
        GPIO.output(RELAY_PIN, GPIO.LOW)
        self.label_statut_porte.setText("Porte ouverte") 
        self.timer = QTimer()
        self.timer.timeout.connect(self.close_door)
        self.timer.start(5000)

    def acces_denied(self):
        print("acces_denied")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        self.label_statut_porte.setText("Acces Interdit!") 
        self.timer = QTimer()
        self.timer.timeout.connect(self.close_door)
        self.timer.start(5000)

    def close_door(self):
        print("Close door")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        self.label_statut_porte.setText("Porte fermée")
        self.timer.stop()

    def change_tab_code(self, uid):
        self.toolBox.setCurrentIndex(1)
        self.nfc_uid = uid
        self.timer_code = QTimer()
        self.timer_code.timeout.connect(self.change_tab_nfc)
        self.timer_code.start(10000)

    def change_tab_nfc(self):
        self.toolBox.setCurrentIndex(0)

def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = MyWindow()
    #ui = Ui_MainWindow()
    #ui.setupUi(MainWindow)
    MainWindow.showFullScreen()
    #MainWindow.show()
    #MQTT define
    mqtt_thread = MQTTThread()
    #NFC
    nfc_thread = NFCThread()
    nfc_thread.start()  # Finally starts the thread


    #NFC
    # Connect the signal from the thread to the finished method
    nfc_thread.signal_granted.connect(MainWindow.acces_granted)
    nfc_thread.signal_denied.connect(MainWindow.acces_denied)
    nfc_thread.signal_acces_req.connect(MainWindow.change_tab_code)
    nfc_thread.signal_code_request.connect(MainWindow.change_tab_code)
    
    #MQTT
    #mqtt_thread = MQTTThread()
    mqtt_thread.start()  # Finally starts the thread
    #MQTT
    # Connect the signal from the thread to the finished method
    mqtt_thread.signal_granted.connect(MainWindow.acces_granted)
    mqtt_thread.signal_denied.connect(MainWindow.acces_denied)
    mqtt_thread.signal_alive.connect(nfc_thread.mqtt_alive)
    mqtt_thread.signal_dead.connect(nfc_thread.mqtt_dead)

    #MainWindow
    MainWindow.signal_acces_req_done.connect(mqtt_thread.publish)

    sys.exit(app.exec_())
    GPIO.cleanup()


if __name__ == '__main__':
    main()
