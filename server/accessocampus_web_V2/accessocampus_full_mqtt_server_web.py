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

#Face names
#known_face_names = [
#    "Barack Obama",
#    "Joe Biden",
#    "test",
#    "test2",
#    "test3",
#    "test4",
#]

known_face_names = []

##########################
##----END  SETTINGS----###
##########################

#Globals
card_holder_name = "UNKNOWN"

#Autodetection of faces in folder
#if(FACES_NUMBER == "AUTO"):
#    FACES_NUMBER = sum([len(files) for r, d, files in os.walk(FACES_FOLDER + "/")])
#    print("Auto detected " + str(FACES_NUMBER) + " images in faces folder")

#Faces
my_face_encoding = []

#for x in range(FACES_NUMBER):
#    picture_of_me = face_recognition.load_image_file(FACES_FOLDER + "/" + str(x)+".jpg")
#    my_face_encoding.append(face_recognition.face_encodings(picture_of_me)[0])
#    print("Loaded face: " + str(x))
#print("Loaded " + str(x+1) + " faces from database")

users = UID.query.all()
face_count = 0
for x in users:
    head, data = x.image.split(',', 1)
    file_ext = head.split(';')[0].split('/')[1]
    plain_data = base64.b64decode(data)
    with open('tmp.' + file_ext, 'wb') as f:
        f.write(plain_data)
    picture_of_me = face_recognition.load_image_file('tmp.'+file_ext)
    my_face_encoding.append(face_recognition.face_encodings(picture_of_me)[0])
    known_face_names.append(x.name)
    face_count = face_count + 1
    print("Loaded face: " + str(face_count))
print("Loaded " + str(face_count) + " faces from database")
FACES_NUMBER = face_count

#Outputs log messages and call-backs in the console
def on_log(mqttc, obj, level, string):
    print(string)

#Code to execute when any MQTT message is received
def on_message(client, userdata, message):

    def check_uid():
                uidDB = UID.query.all()
                print("Got database results!")
                uid_short = str(uid).replace("75110484","")
                count = 0
                for n in uidDB:
                    count = count+1
                    uid_data = n.uid.replace(",","")
                    uid_data = uid_data.replace(" ","")
                    print("Checking entry: "+ str(count))
                    print("Received UID: "+str(int(uid)))
                    print("Received short UID: "+str(int(uid_short)))
                    print("Database UID: "+str(n.uid))
                    print("Database formatted UID: "+str(uid_data))
                    print(str(int(uid_short)) in str(int(uid_data)))
                    if((str(int(uid_short)) in str(int(uid_data))) and (str(ID) in str(n.door))):
                        print("UID in database at position "+str(count)+" and door id is OK!")
                        return count
                    if(int(uid_short) in int(uid_data)):
                        print("UID in database at position "+str(count)+", but door id is different!")
                print("UID not in database !")
                return False

    #Global imports
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
      if ( ("unit_id" in inData) & ("seq_id" in inData) & ("auth_type" in inData) & ("nfc_uid" in inData) & ("passcode" in inData) & ("image" in inData) ):
              
              print("Format correct!")
              ID = str(inData["unit_id"])
              seq_id = str(inData["seq_id"])
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
                  print("Received face encoded!")
                  # Now we can see the two face encodings are of the same person with `compare_faces`!
                  for y in range(FACES_NUMBER):
                      print("checking face: " + str(y))
                      face_detection_results = face_recognition.compare_faces([my_face_encoding[y]], unknown_face_encoding)
                      if face_detection_results[0] == True:
                          print("We got a match on face: " + str(y))
                          break

                  if True in face_detection_results:
                      first_match_index = face_detection_results.index(True)
                      name = known_face_names[first_match_index]
                      print(name)
                  else:
                      first_match_index = -1

                  if face_detection_results[0] == True:
                      print("Person in database!")
                  else:
                      print("Person not in database!")

              if(auth_type == "code"):

                code_ok = False
                uid_test = check_uid()
                print("uid test results: "+str(int(uid_test)))
                if(uid_test != False):
                        

                        uidDB = UID.query.all()
                        print("Got database results!")
                
                        if(check_password_hash(uidDB[uid_test-1].code, code) ==  True):
                            print("Code OK!")
                            print("Welcome, " + uidDB[uid_test-1].name)
                            code_ok = True
                        else:
                            print("Invalid code!")
                else:
                    print("UID not allowed to access requested door!")
                            
                if(code_ok == False):
                    print("Acces Denied via code!")
                    state = "Acces Denied via code!"
                    mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "deny"}
                    client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                    print("Signal emitted!")
                else:
                    print("Acces Granted via code!")
                    state = "Acces Granted via code!"
                    mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "grant"}
                    client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                    print("Signal emitted!")

              if(auth_type == "cam"):
                uid_ok = False
                uid_test = check_uid()
                print("uid test results: "+str(int(uid_test)))
                print("First match index: "+str(int(first_match_index)+1))
                if(uid_test != False):
                    uid_ok = True

                if((face_detection_results[0] == True) & (uid_ok == True) & (int(uid_test) == int(first_match_index)+1)):
                  print("Acces Granted via cam no thermal!")
                  state = "Acces Granted via cam no thermal!"
                  mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "grant"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if((face_detection_results[0] == False) & (uid_ok == True)):
                  print("Ask code via cam no thermal!")
                  state = "Ask code via cam no thermal!"
                  mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "ask_code"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if(uid_ok == False):
                  print("Acces Denied via NFC, invalid badge for this door or not in database!")
                  state = "Acces Denied via NFC, invalid badge for this door or not in database!"
                  mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "deny"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")

              if((auth_type == "cam+thermal") & (thermal_detected == "True")):
                uid_ok = False
                uid_test = check_uid()
                print("uid test results: "+str(int(uid_test)))
                print("First match index: "+str(int(first_match_index)+1))
                if(uid_test != False):
                    if(int(uid_test) == int(first_match_index)+1):
                        uid_ok = True

                if((face_detection_results[0] == True) & (uid_ok == True)):
                  print("Acces Granted via cam thermal!")
                  state = "Acces Granted via cam thermal!"
                  mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "grant"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if((face_detection_results[0] == False) & (thermal_detected == "True") & (uid_ok == True)):
                  print("Ask code via cam thermal!")
                  state = "Ask code via cam thermal!"
                  mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "ask_code"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                if(uid_ok == False):
                  print("Acces Denied via NFC, invalid badge for this door or not in database!")
                  state = "Acces Denied via NFC, invalid badge!"
                  mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "deny"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")

              if((auth_type == "cam+thermal") & (thermal_detected == "False")):
                  print("Acces Denied via cam thermal, break in attempt?!")
                  state = "Acces Denied via cam thermal, break in attempt?!"
                  mqtt_payload = {"unit_id": ID, "seq_id": seq_id, "command": "ask_code"}
                  client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                  print("Signal emitted!")
                  
              #Logging
              current_time = datetime.now().strftime("%H:%M:%S")
              if((auth_type == "cam") or (auth_type == "cam+thermal")):
                  p = Post(body=state + " at " + current_time + " with uid " + uid + ", Card holder: " + card_holder_name, author=User.query.get(1), image=received_image_B64)
              else:
                  p = Post(body=state + " at " + current_time + " with uid " + uid + ", Card holder: " + card_holder_name, author=User.query.get(1))
              db.session.add(p)
              db.session.commit()

      else:
          if(("mqtt_status" in inData) & ("nfc_status" in inData) & ("camera_status" in inData) & ("thermal_status" in inData)):
              print("Received status message!")
              #Logging
              current_time = datetime.now().strftime("%H:%M:%S")
              p = Post(body="Received status at " + current_time + " | MQTT Status: " + str(inData["mqtt_status"]) + " | NFC Status: " + str(inData["nfc_status"]) + " | Camera Status: " + str(inData["camera_status"]) + " | Thermal Camera Status: " + str(inData["thermal_status"]), author=User.query.get(1))
              db.session.add(p)
              db.session.commit()
          else:
              print("Invalid MQTT message, aborting...")
              #Logging
              current_time = datetime.now().strftime("%H:%M:%S")
              p = Post(body="Received invalid MQTT message at " + current_time, author=User.query.get(1))
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
