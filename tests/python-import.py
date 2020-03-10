#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#import RPi.GPIO as GPIO

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

#Math
import math

#Face recognition
import face_recognition

#Web Server
from datetime import datetime
import re
from werkzeug.security import check_password_hash

print("Python test passed!")
