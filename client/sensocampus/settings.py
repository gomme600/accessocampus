#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sensOCampus settings file
#
# T.Bueno
#



# #############################################################################
#
# Import zone
#
from appdirs import *
import uuid
import os
import logging


# extend Python's library search path
import os
import sys
# import RPi tools
_path2add='../libutils'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from rpi_utils import getmac



# #############################################################################
#
# sensOCampus settings
#

# General
APP_NAME = "sensocampus"
APP_AUTHOR = "neocampus"

# Directories
CONFIG_DIR = user_config_dir(APP_NAME, APP_AUTHOR)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")

# Data
MAC_ADDR = getmac()

# Server
SENSO_HOST = "sensocampus.univ-tlse3.fr"
#SENSO_ENDPOINT = "http://sensocampus.univ-tlse3.fr/device/"
SENSO_ENDPOINT = "https://sensocampus.univ-tlse3.fr/device/"

MQTT_HOST = "neocampus.univ-tlse3.fr"
MQTT_PORT = 1883
MQTT_KEEP_ALIVE = 60    # set accordingly to the mosquitto server setup
# initial MQTT reconnect delay will be a random(MQTT_RECONNECT_DELAY,MQTT_RECONNECT_DELAY**2)
MQTT_RECONNECT_DELAY = 7

# Log (default value)
LOG_LEVEL = logging.INFO
#LOG_LEVEL = logging.DEBUG

# I2C packet error checking (PEC)
# Requires Firmware >= 2.0 on Ardbox modules
ARDBOX_I2C_PEC = False

# neOCampus I2C custom CRC
# Enable / disable neOCampus custom CRC-8 on all i2c sequences
ARDBOX_I2C_CRC = True
# minimum Ardbox Firmwares revision
ARDBOX_EXPECT_PRGM_MAJOR = 2
ARDBOX_EXPECT_PRGM_MINOR = 2

# Modbus RS-485 debug link (only efficient if debug mode activated)
# If set to True, all modbus exchange will appear (tons of messages)
MODBUS_DEBUG_LINK = False

