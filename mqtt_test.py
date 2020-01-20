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

#MQTT
import paho.mqtt.client as mqtt #import the mqtt client

######THREADS######
#MQTT Thread



#Outputs log messages and call-backs in the console
def on_log(mqttc, obj, level, string):
    print(string)

#Code to execute when any MQTT message is received
def on_message(client, userdata, message):
        #Display the received message in the console
        print("message received!")
        print("message received " ,str(message.payload.decode("utf-8")))
        print("message topic=",message.topic)

# run method gets called when we start the thread
#def run(self):

print("Thread!")
#Start of the MQTT subscribing
########################################

#MQTT address
broker_address=MQTT_server
print("creating new MQTT instance")
client = mqtt.Client("P1") #create new instance
client.on_message=on_message #attach function to callback
client.on_log=on_log #attach logging to log callback

# Auth
client.username_pw_set(username=MQTT_user,password=MQTT_password)

# now we connect
print("connecting to MQTT broker")
client.connect(broker_address) #connect to broker

#Subscribe to all the weather topics we need
print("Subscribing to topic",MQTT_auth_topic)
client.subscribe(MQTT_auth_topic)

#Tell the MQTT client to subscribe forever
client.loop_forever()
