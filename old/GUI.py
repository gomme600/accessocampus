# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\gomme\Desktop\accessocampus\GUI.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!

#GPIO

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

#JSON
import json #Used for converting to and from json strings

#MQTT
import paho.mqtt.client as mqtt #import the mqtt client

#NFC
from py532lib.i2c import *
from py532lib.frame import *
from py532lib.constants import *

#PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
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
        mqtt_payload = {"door_id": 0, "auth_type": 0, "nfc_uid": uid, "passcode": code, "image": 0}
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
        if(str(message.payload.decode("utf-8")) == ("granted:" + DOOR_ID)):
            print("Acces Granted via MQTT!")
            self.signal_granted.emit()
        if(str(message.payload.decode("utf-8")) == ("denied:" + DOOR_ID)):
            print("Acces Denied via MQTT!")
            self.signal_denied.emit()

    # run method gets called when we start the thread
    def run(self):

       print("Thread!")
       #Start of the MQTT subscribing
       ########################################
       #We wait for the system to come up
       sleep(2)
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
              print("MQTT request signal sent!")
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
class Ui_MainWindow(object):

    #MQTT signal
    signal_acces_req_done = QtCore.pyqtSignal(str, str, name='uid')
       

    #Definition of an empty code
    code = ""

    def setupUi(self, MainWindow):

        MainWindow.setObjectName("MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(800, 480)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.toolBox = QtWidgets.QToolBox(self.centralwidget)
        self.toolBox.setGeometry(QtCore.QRect(0, 0, 801, 421))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.toolBox.setFont(font)
        self.toolBox.setObjectName("toolBox")
        self.page = QtWidgets.QWidget()
        self.page.setGeometry(QtCore.QRect(0, 0, 801, 327))
        self.page.setObjectName("page")
        self.label_scannez_carte = QtWidgets.QLabel(self.page)
        self.label_scannez_carte.setGeometry(QtCore.QRect(70, 180, 661, 101))
        font = QtGui.QFont()
        font.setPointSize(30)
        self.label_scannez_carte.setFont(font)
        self.label_scannez_carte.setObjectName("label_scannez_carte")
        self.label_logo = QtWidgets.QLabel(self.page)
        self.label_logo.setGeometry(QtCore.QRect(0, 0, 801, 171))
        self.label_logo.setText("")
        self.label_logo.setPixmap(QtGui.QPixmap(":/images/accessocampus_ressources/neocampus_logo.png"))
        self.label_logo.setScaledContents(True)
        self.label_logo.setObjectName("label_logo")
        self.toolBox.addItem(self.page, "")
        self.page_2 = QtWidgets.QWidget()
        self.page_2.setGeometry(QtCore.QRect(0, 0, 801, 327))
        self.page_2.setObjectName("page_2")
        self.label_code_acces = QtWidgets.QLabel(self.page_2)
        self.label_code_acces.setGeometry(QtCore.QRect(160, 10, 481, 71))
        font = QtGui.QFont()
        font.setPointSize(40)
        self.label_code_acces.setFont(font)
        self.label_code_acces.setObjectName("label_code_acces")
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.page_2)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(120, 80, 541, 61))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton_dig_1 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_1.setObjectName("pushButton_dig_1")
        self.horizontalLayout.addWidget(self.pushButton_dig_1)
        self.pushButton_dig_2 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_2.setObjectName("pushButton_dig_2")
        self.horizontalLayout.addWidget(self.pushButton_dig_2)
        self.pushButton_dig_3 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_3.setObjectName("pushButton_dig_3")
        self.horizontalLayout.addWidget(self.pushButton_dig_3)
        self.pushButton_dig_4 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_4.setObjectName("pushButton_dig_4")
        self.horizontalLayout.addWidget(self.pushButton_dig_4)
        self.pushButton_dig_5 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_5.setObjectName("pushButton_dig_5")
        self.horizontalLayout.addWidget(self.pushButton_dig_5)
        self.horizontalLayoutWidget_2 = QtWidgets.QWidget(self.page_2)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(120, 150, 541, 61))
        self.horizontalLayoutWidget_2.setObjectName("horizontalLayoutWidget_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushButton_dig_6 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_6.setObjectName("pushButton_dig_6")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_6)
        self.pushButton_dig_7 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_7.setObjectName("pushButton_dig_7")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_7)
        self.pushButton_dig_8 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_8.setObjectName("pushButton_dig_8")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_8)
        self.pushButton_dig_9 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_9.setObjectName("pushButton_dig_9")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_9)
        self.pushButton_dig_0 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_0.setObjectName("pushButton_dig_0")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_0)
        self.pushButton_dig_val = QtWidgets.QPushButton(self.page_2)
        self.pushButton_dig_val.setGeometry(QtCore.QRect(270, 220, 121, 61))
        self.pushButton_dig_val.setObjectName("pushButton_dig_val")
        self.pushButton_dig_val.clicked.connect(self.on_click_val)
        self.pushButton_dig_val_2 = QtWidgets.QPushButton(self.page_2)
        self.pushButton_dig_val_2.setGeometry(QtCore.QRect(400, 220, 121, 61))
        self.pushButton_dig_val_2.setObjectName("pushButton_dig_val_2")
        self.toolBox.addItem(self.page_2, "")
        self.label_statut_porte = QtWidgets.QLabel(self.centralwidget)
        self.label_statut_porte.setGeometry(QtCore.QRect(290, 420, 250, 50))
        font = QtGui.QFont()
        font.setPointSize(25)
        self.label_statut_porte.setFont(font)
        self.label_statut_porte.setObjectName("label_statut_porte")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.toolBox.setCurrentIndex(0)
        self.toolBox.layout().setSpacing(6)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.toolBox.setItemEnabled(1,False)

        MainWindow.showFullScreen()

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

        self.mqtt_thread = MQTTThread
        #self.signal_acces_req_done.connect(self.on_click_0)

    #@pyqtSlot()
    def on_click_val(self):
        self.toolBox.setCurrentIndex(0)
        if(self.code != ""):
        
            print("Checking code...")
            if(True):
              #We publish the output string
              #self.signal_acces_req_done.emit(self.mqtt_thread.publish(self.uid, self.code))
              self.signal_acces_req_done.emit()
              print("MQTT request signal sent!")
              sleep(4)
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

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Accessocampus"))
        self.label_scannez_carte.setText(_translate("MainWindow", "Scannez votre carte d\'acces"))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page), _translate("MainWindow", "NFC"))
        self.label_code_acces.setText(_translate("MainWindow", "Entrez Code d\'acces"))
        self.pushButton_dig_1.setText(_translate("MainWindow", "1"))
        self.pushButton_dig_2.setText(_translate("MainWindow", "2"))
        self.pushButton_dig_3.setText(_translate("MainWindow", "3"))
        self.pushButton_dig_4.setText(_translate("MainWindow", "4"))
        self.pushButton_dig_5.setText(_translate("MainWindow", "5"))
        self.pushButton_dig_6.setText(_translate("MainWindow", "6"))
        self.pushButton_dig_7.setText(_translate("MainWindow", "7"))
        self.pushButton_dig_8.setText(_translate("MainWindow", "8"))
        self.pushButton_dig_9.setText(_translate("MainWindow", "9"))
        self.pushButton_dig_0.setText(_translate("MainWindow", "0"))
        self.pushButton_dig_val.setText(_translate("MainWindow", "Valider"))
        self.pushButton_dig_val_2.setText(_translate("MainWindow", "Annuler"))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page_2), _translate("MainWindow", ""))
        self.label_statut_porte.setText(_translate("MainWindow", "Porte fermée"))
import accessocampus_GUI_rc

def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    #MQTT define
    mqtt_thread = MQTTThread()
    #NFC
    nfc_thread = NFCThread()
    nfc_thread.start()  # Finally starts the thread


    #NFC
    # Connect the signal from the thread to the finished method
    nfc_thread.signal_granted.connect(ui.acces_granted)
    nfc_thread.signal_denied.connect(ui.acces_denied)
    nfc_thread.signal_acces_req.connect(ui.change_tab_code)
    nfc_thread.signal_code_request.connect(ui.change_tab_code)
    
    #MQTT
    #mqtt_thread = MQTTThread()
    mqtt_thread.start()  # Finally starts the thread
    #MQTT
    # Connect the signal from the thread to the finished method
    mqtt_thread.signal_granted.connect(ui.acces_granted)
    mqtt_thread.signal_denied.connect(ui.acces_denied)
    mqtt_thread.signal_alive.connect(nfc_thread.mqtt_alive)
    mqtt_thread.signal_dead.connect(nfc_thread.mqtt_dead)

    sys.exit(app.exec_())
    GPIO.cleanup()


if __name__ == '__main__':
    main()
