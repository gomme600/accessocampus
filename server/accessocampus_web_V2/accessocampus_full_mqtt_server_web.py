#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   NeOCampus mqtt accessocampus server with image recognition
   Author : Sebastian Lucas 2019-2020
"""

############
#Imports
import paho.mqtt.client as mqtt #import the mqtt client
import time #Used for the timing
import json #Used for converting to and from json strings
#import re
import math
import cv2
import base64
import os
import scipy #Used for wind average
import numpy as np #Used for converting list to array
import face_recognition
from app import db
from app.models import User, Post, UID
from datetime import datetime
import re
from werkzeug.security import check_password_hash
############

##########################
##----USER SETTINGS----###
##########################

#Connection variables, change as required
MQTT_server = "neocampus.univ-tlse3.fr"
MQTT_user = "test"
MQTT_password = "test"
#The MQTT topic where we find the weewx default loop topic: example: TestTopic/_meteo
MQTT_topic = "TestTopic/req"

#The MQTT topic to publish outdoor data into (weather station data)
MQTT_auth_topic = "TestTopic/auth"

#Number of faces in directory("AUTO" or number of faces)
FACES_NUMBER = "AUTO"

#Faces folder name
FACES_FOLDER = "faces"

##########################
##----END  SETTINGS----###
##########################

#Globals
card_holder_name = "UNKNOWN"

#Autodetection of faces in folder
if(FACES_NUMBER == "AUTO"):
    FACES_NUMBER = sum([len(files) for r, d, files in os.walk(FACES_FOLDER + "/")])
    print("Auto detected " + str(FACES_NUMBER) + " images in faces folder")

#Faces
my_face_encoding = []

for x in range(FACES_NUMBER):
    picture_of_me = face_recognition.load_image_file(FACES_FOLDER + "/" + str(x)+".jpg")
    my_face_encoding.append(face_recognition.face_encodings(picture_of_me)[0])
    print("Loaded face: " + str(x))
print("Loaded " + str(x+1) + " faces from database")

#Outputs log messages and call-backs in the console
def on_log(mqttc, obj, level, string):
    print(string)

#Code to execute when any MQTT message is received
def on_message(client, userdata, message):

    #Global inports
    global card_holder_name

    #Display the received message in the console
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)

    #Check if the message topic is "loop" and decode the weather data
    if(message.topic == MQTT_topic):

      #We convert the loop JSON string to a python dictionary
      inData = json.loads(str(message.payload.decode("utf-8")))
      print("We loaded the JSON data!")
      #We load the data from the dictionary using the keys

      #if(True):
      if ( ("unit_id" in inData) & ("auth_type" in inData) & ("nfc_uid" in inData) & ("passcode" in inData) & ("image" in inData) ):
              
              print("Format correct!")
              ID = str(inData["unit_id"])
              uid = str(inData["nfc_uid"])
              code = str(inData["passcode"])
              image = np.asarray(inData["image"])
              auth_type = str(inData["auth_type"])
              thermal_detected = str(inData["thermal_detect"])
              print("Loaded parameters!")
              
              #Reset previous user name
              card_holder_name = "UNKNOWN"
              
              if((auth_type == "cam") or (auth_type == "cam+thermal")):
                  # Convert back to binary
                  print(len(image))
                  print(image)
                  received_image = base64.b64decode(bytearray(image))
                  print(len(received_image))
                  print(received_image)
                  

                  # Write to a file to show conversion worked
                  with open('received_image.jpg', 'wb') as f_output:
                      f_output.write(received_image)
                  with open("received_image.jpg", "rb") as img_file:
                      received_image_B64 = base64.b64encode(img_file.read())
                  received_image_B64 = str(received_image_B64)[2:-1]
                  received_image_B64 = "data:image/jpeg;base64," + received_image_B64
                  print(received_image_B64)
                  
                  unknown_picture = face_recognition.load_image_file("received_image.jpg")
                  unknown_face_encoding = face_recognition.face_encodings(unknown_picture)[0]
                  # Now we can see the two face encodings are of the same person with `compare_faces`!
                  for x in range(FACES_NUMBER):
                      print("checking face: " + str(x))
                      face_detection_results = face_recognition.compare_faces([my_face_encoding[x]], unknown_face_encoding)
                      if face_detection_results[0] == True:
                          print("We got a match on face: " + str(x))
                          break

                  if face_detection_results[0] == True:
                      print("Person in database!")
                  else:
                      print("Person not in database!")

              if(auth_type == "code"):

                card_ok = False 

                uidDB = UID.query.all()
                print("Got database results!")
                
                # getting length of list 
                length = len(uidDB) 
                
                # Iterating the index 
                # same as 'for i in range(len(list))' 
                for i in range(length): 
                    print("Checking entry: "+str(i))
                    if("<UID " + uid + ">" in str(uidDB[i])):
                        print("Found UID in database!")
                        m = re.search('<NAME (.+?)>', str(uidDB[i]))
                        if m:
                            card_holder_name = m.group(1)
                        if("<DOOR " + ID + ">" in str(uidDB[i])):
                            print("UID allowed to access requested door!")
                            #if("<CODE " + code + ">" in str(uidDB[i])):
                            m = re.search('<CODE (.+?)>', str(uidDB[i]))
                            if m: 
                                code_hash = m.group(1)
                            if(check_password_hash(code_hash, code) ==  True):
                                print("Code OK!")
                                print("Welcome, " + card_holder_name)
                                card_ok = True
                                break
                            else:
                                print("Invalid code!")
                        else:
                            print("UID not allowed to access requested door!")
                            
                if(card_ok == False):
                    print("Acces Denied via code!")
                    state = "Acces Denied via code!"
                    mqtt_payload = {"unit_id": ID, "command": "deny"}
                    client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                    print("Signal emitted!")
                else:
                    print("Acces Granted via code!")
                    state = "Acces Granted via code!"
                    mqtt_payload = {"unit_id": ID, "command": "grant"}
                    client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                    print("Signal emitted!")


              def check_uid():
                  
                #Global imports
                global card_holder_name
                  
                card_ok = False 

                uidDB = UID.query.all()
                print("Got database results!")
                
                # getting length of list 
                length = len(uidDB) 
                
                # Iterating the index 
                # same as 'for i in range(len(list))' 
                for i in range(length): 
                    print("Checking entry: "+str(i))
                    if("<UID " + uid + ">" in str(uidDB[i])):
                        print("Found UID in database!")
                        m = re.search('<NAME (.+?)>', str(uidDB[i]))
                        if m:
                            card_holder_name = m.group(1)
                        if("<DOOR " + ID + ">" in str(uidDB[i])):
                            print("UID allowed to access requested door!")
                            card_ok = True
                            break
                        else:
                            print("UID not allowed to access requested door!")
                if(card_ok == False):
                    print("Did not find UID in database!")
                    return False
                else:
                    return True


              if(auth_type == "cam"):
                uid_ok = check_uid()
                if((face_detection_results[0] == True) & (uid_ok == True)):
                  print("Acces Granted via cam no thermal!")
                  state = "Acces Granted via cam no thermal!"
                  mqtt_payload = {"unit_id": ID, "command": "grant"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if((face_detection_results[0] == False) & (uid_ok == True)):
                  print("Ask code via cam no thermal!")
                  state = "Ask code via cam no thermal!"
                  mqtt_payload = {"unit_id": ID, "command": "ask_code"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if(uid_ok == False):
                  print("Acces Denied via NFC, invalid badge for this door or not in database!")
                  state = "Acces Denied via NFC, invalid badge for this door or not in database!"
                  mqtt_payload = {"unit_id": ID, "command": "deny"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")

              if((auth_type == "cam+thermal") & (thermal_detected == "True")):
                uid_ok = check_uid()
                if((face_detection_results[0] == True) & (uid_ok == True)):
                  print("Acces Granted via cam thermal!")
                  state = "Acces Granted via cam thermal!"
                  mqtt_payload = {"unit_id": ID, "command": "grant"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if((face_detection_results[0] == False) & (thermal_detected == "True") & (uid_ok == True)):
                  print("Ask code via cam thermal!")
                  state = "Ask code via cam thermal!"
                  mqtt_payload = {"unit_id": ID, "command": "ask_code"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if(uid_ok == False):
                  print("Acces Denied via NFC, invalid badge for this door or not in database!")
                  state = "Acces Denied via NFC, invalid badge!"
                  mqtt_payload = {"unit_id": ID, "command": "deny"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")

              if((auth_type == "cam+thermal") & (thermal_detected == "False")):
                  print("Acces Denied via cam thermal, break in attempt?!")
                  state = "Acces Denied via cam thermal, break in attempt?!"
                  mqtt_payload = {"unit_id": ID, "command": "ask_code"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")

      else:
          print("Invalid MQTT message, aborting...")
          state = "Invalid MQTT message, aborting..."
          
      current_time = datetime.now().strftime("%H:%M:%S")
      if((auth_type == "cam") or (auth_type == "cam+thermal")):
          p = Post(body=state + " at " + current_time + " with uid " + uid + ", Card holder: " + card_holder_name, author=User.query.get(1), image=received_image_B64)
      else:
          p = Post(body=state + " at " + current_time + " with uid " + uid + ", Card holder: " + card_holder_name, author=User.query.get(1))
      db.session.add(p)
      db.session.commit()

#Start of the MQTT subscribing
########################################

#MQTT address
broker_address=MQTT_server
print("creating new instance")
client = mqtt.Client("P99") #create new instance
client.on_message=on_message #attach function to callback
client.on_log=on_log #attach logging to log callback

# Auth
client.username_pw_set(username=MQTT_user,password=MQTT_password)

# now we connect
print("connecting to broker")
client.connect(broker_address) #connect to broker

#Subscribe to all the weather topics we need
print("Subscribing to topic",MQTT_topic)
client.subscribe(MQTT_topic)

#Tell the MQTT client to subscribe forever
client.loop_forever()
