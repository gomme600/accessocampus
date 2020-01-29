#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   NeOCampus mqtt accessocampus server
   Author : Sebastian Lucas 2019-2020
"""

############
#Imports
import paho.mqtt.client as mqtt #import the mqtt client
import time #Used for the timing
import json #Used for converting to and from json strings
#import re
import math
import scipy #Used for wind average
import numpy as np #Used for converting list to array
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

##########################
##----END  SETTINGS----###
##########################


#Outputs log messages and call-backs in the console
def on_log(mqttc, obj, level, string):
    print(string)

#Code to execute when any MQTT message is received
def on_message(client, userdata, message):


    #Display the received message in the console
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)

    #Check if the message topic is "loop" and decode the weather data
    if(message.topic == MQTT_topic):
      #if(":" in str(message.payload.decode("utf-8"))):
      #        card_id = str(message.payload.decode("utf-8"))
      #        uid,ID = card_id.split(':')
      saved_uid  = open("cards.conf", "r")
    
      #We convert the loop JSON string to a python dictionary
      inData = json.loads(str(message.payload.decode("utf-8")))
      print("We loaded the JSON data!")
      #We load the data from the dictionary using the keys

      if(True):
      #if ( ("door_id" in inData) & ("auth_type" in inData) ("nfc_uid" in inData) ("passcode" in inData) ("image" in inData) ):
              
              print("Format correct!")
              ID = str(inData["door_id"])
              uid = str(inData["nfc_uid"])
              code = str(inData["passcode"])
              print("Loaded parameters!")

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
                         if("#DOOR_ID:" + ID + "#" in line):
                             if("#CARD_UID:" + uid + "#" in line):
                                 if("#PASSCODE:" + code + "#" in line):
                                     card_ok = True

                                     print("Acces Granted!")
                                     mqtt_payload = {"door_id": ID, "command": "granted"}
                                     client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                                     print("Signal emitted!")
                  else:
                      print("Checking next line...")

                  if(card_ok == False):
                                 print("Acces Denied")
                                 mqtt_payload = {"door_id": ID, "command": "denied"}
                                 client.publish(MQTT_auth_topic, json.dumps(mqtt_payload))
                                 print("Signal emitted!")

              saved_uid.close()
      else:
          print("Invalid MQTT message, aborting...")        

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
