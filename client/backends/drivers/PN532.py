#!/usr/bin/env python3
# -*-coding:Utf-8-*
#
# PN532: NFC sensor
#
# S.Lucas    Jui.20  File creation
#


# #############################################################################
#
# Import zone
#

from math import fsum
import time

from smbus2 import SMBus

# extend Python's library search path
import os
import sys

#NFC specific librarys
from py532lib.i2c import *
from py532lib.frame import *
from py532lib.constants import *

# Helpers and i2c functions import
_path2add='../../libutils'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from HelpersFunc import *

# sensOCampus
_path2add='../../sensocampus'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from logger import log


# #############################################################################
#
# Class
#
class PN532(object):

    # CLASS ATTRIBUTE
    ADR_LOW = 0x24
    ADR_HIGH = 0x24
    _I2C_ADDRS = list(range( ADR_LOW, ADR_HIGH+1 ))

    # I2C bus
    i2cbus = -1
    address = None

    def __init__(self, address, i2cbus=-1, *args, **kwargs):
        ''' Sensor instance initialization '''
        self.address = address
        self.i2cbus = i2cbus
        log.info("Initializing '%s' device %#02x" % (self.__class__.__name__,self.address))
        try:
            # [oct.19] default i2c bus is 1 ;)
            self.i2c = SMBus(self.i2cbus if self.i2cbus >= 0 else 1)
        except Exception as ex:
            log.error("while creating I2C bus instance with bus=%d and adr=0x%X " % (self.i2cbus,self.address) + str(ex))
            raise ex

        # now check sensor is really what we expect
        self.validate_sensor()
        #log.info("NFC sensor validated!")
        # set sensor default resolution
        if (ret == -1): raise IOError('device unreachable :(')
        log.info("NFC sensor validated!")

    def validate_sensor(self):
        """ read ChipID or something else to get sure it iw what we expect ... """
        # powerOn device
        for i in range(0,2):
          try:
            log.info("Enable NFC ... Try number : "+str(i))
            self.enable()
          except:
            log.error("Unable to connect to NFC module!")
            continue
          break

        log.info("Connected to NFC module!")

        # poweroff device
        self.disable();
        log.debug("Returning True ...")
        return True;

    def enable(self):
        """ PowerON device """
        # powerOn device
        # TODO: implement it with one-shot feature!
        pn532 = Pn532_i2c()
        pn532.SAMconfigure()

    def disable(self):
        """ PowerOFF device """
        # powerOff device
        # TODO: implement it with one-shot feature!
        pass

    # -------------------------------------------------------------------------
    #
    # neOCampus generic interfaces
    # - detect()
    # - acquire()
    # - unitID()
    #
    # luminosity module method that will get called ...
    def acquire(self):
        ''' temperature module will call this method '''
        return pn532.read_mifare().get_data()

    # identity of sensor (i2c bus and i2c addr combination)
    # [Nov.16] RPis only have a single i2c bus ... so we just send back i2c_addr
    def unitID(self):
        '''send back i2c addr'''
        return self.address

    @staticmethod
    def detect():
        ''' Automated sensors detection
                [ ("PN532", i2c_bus, adr),("PN532", i2c_bus, adr), ... ] '''
        log.debug("Trying to find-out sensors ...")

        sensorsList = []

        # scan i2c bus and try to match against possible i2c addr of sensor
        #TODO: scan all i2c buses
        i2cbus=-1
        addresses = []
        # scan and intersect ...
        log.debug("Scanning i2c bus ...")
        addresses = list(set(PN532._I2C_ADDRS) & set(i2cScan(i2cbus)))
        log.info("Sensors addresses : " + str(addresses))
        if len(addresses)==0:
            print("no device found ... :|")
            return None
        log.info("Found some NFC sensors!")
        # parse addresses list to check that device corresponds
        for adr in addresses:
            #try:
            #    sensor = PN532(adr)
            #    log.info("Sensor : "+str(sensor))
            #except Exception as ex:
            #    log.info("Exception")
            #    pass
            #else:
                # sensor detected ...
                _sensor_params = ( "PN532", i2cbus, adr )
                sensorsList.append(_sensor_params)
                #del sensor
                log.info("Sensor OK")

        # only return usefull parameters
        log.info("Sensors list size : " + str(len(sensorsList)))
        if len(sensorsList) == 0:
            return None
        return sensorsList



#
# Main application case
#
if __name__ == "__main__":

    # launch auto-detection
    sensorsList = PN532.detect()
    if sensorsList is None:
        raise Exception("No PN532 devices found")

    # parse list
    #for (_,_,adr) in sensorsList:
        #sensor = PN532(adr)

        #del sensor


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)



###
### FIN
###
