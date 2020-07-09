#!/usr/bin/env python3
# -*-coding:Utf-8-*
#
# TCN75A: I2C temperature sensor
#
# [Nov.16] neOCampus integration
# [Apr.16] migrated to python3
#
# TODO: implement low-power one-shoot mode!!!
#
# F.Thiebolt    oct.19  migration to smbus2
# Thiebolt.F    Nov.16  initial release
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
class TCN75A(object):

    #
    # TCN75A registers
    REG_TA          = 0x00  # 2 bytes signed
    REG_CONFIG      = 0x01
    REG_THYST       = 0x02  # 2 bytes signed
    REG_TSET        = 0x03  # 2 bytes signed

    # Temperature resolution
    RES_BIT         = 0x60  # bit 6,5
    RES_05          = 0x00  # resolution 0.5° (9 bits) ---default PowerUP
    RES_025         = 0x20  # resolution 0.25° (10 bits)
    RES_0125        = 0x40  # resolution 0.125° (11 bits)
    RES_00625       = 0x60  # resolution 0.0625° (12 bits)

    # Intergration time vs resolution
    INTEGRATION_TIME_05     = 30    # ms
    INTEGRATION_TIME_025    = 60    # ms
    INTEGRATION_TIME_0125   = 120   # ms
    INTEGRATION_TIME_00625  = 240   # ms
    INTEGRATION_TIME_CTE    = 20    # additionnal ms delay to all timings

    # Configuration register
    SHUTDOWN_BIT        = 0b00000001
    COMP_INT_BIT        = 0b00000010
    ALERT_POLARITY_BIT  = 0b00000100
    FAULT_QUEUE_BIT     = 0b00011000
    RES_BIT             = 0b01100000
    ONE_SHOT_BIT        = 0b10000000

    CONTROL_POWERON     = 0x00
    CONTROL_POWEROFF    = 0x01

    # CLASS ATTRIBUTE
    ADR_LOW = 0x48
    ADR_HIGH = 0x4F
    _I2C_ADDRS = list(range( ADR_LOW, ADR_HIGH+1 ))

    # I2C bus
    i2cbus = -1
    address = None

    # default resolution to be set && associated integration time
    resolution = RES_0125
    timing = INTEGRATION_TIME_0125

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

        # set sensor default resolution
        ret = self._setResolution(self.resolution); # this will also clear all bits
        if (ret == -1): raise IOError('device unreachable :(')


    def validate_sensor(self):
        """ read ChipID or something else to get sure it iw what we expect ... """
        # powerOn device
        self.enable()

        # ... now read status
        status = self.i2c.read_byte_data( self.address, self.REG_CONFIG);
        #log.debug("status = %#02x" % status)
        if (status & self.SHUTDOWN_BIT) != self.CONTROL_POWERON:
            raise Exception("Sensor status does not match what we expected")

        # read lower 4 bits of ambient temperature (ought to be 0000)
        # ... may be considered as a kind of RegID
        # read TA register both bytes
        # I2C block read for two bytes
        _raw = self.i2c.read_i2c_block_data( self.address, self.REG_TA, 2)
        regID = _raw[1];    # lower byte
        if (regID & 0b00001111) != 0x00:
            raise Exception("Chip is not the device we were expecting")

        # poweroff device
        self.disable();

        return True;

    def enable(self):
        """ PowerON device """
        # powerOn device
        # TODO: implement it with one-shot feature!
        pass

    def disable(self):
        """ PowerOFF device """
        # powerOff device
        # TODO: implement it with one-shot feature!
        pass

    def _setResolution(self,resolution):
        """ [low-level] set sensor resolution """
        return self.i2c.write_byte_data( self.address, self.REG_CONFIG, resolution );

    def setResolution(self,resolution):
        """ set sensor resolution """
        # catch the asked resolution and associates timing
        _timing = 0
        if resolution==self.RES_05:
            _timing = self.INTEGRATION_TIME_05
        elif resolution==self.RES_025:
            _timing = self.INTEGRATION_TIME_025
        elif resolution==self.RES_0125:
            _timing = self.INTEGRATION_TIME_0125
        elif resolution==self.RES_00625:
            _timing = self.INTEGRATION_TIME_00625
        else:
            log.error("unknow resolution %#02x" % resolution)
            return False

        if self.resolution == resolution:
            return

        # catch new resolution and associates timing
        self.resolution = resolution
        self.timing = _timing

        # read status
        status = self.i2c.read_byte_data( self.address, self.REG_CONFIG );
        #log.debug("current_status = %#02x" % status)
        _status = ( status & ~self.RES_BIT ) | self.resolution
        # set new resolution
        self._setResolution(_status);

    def wait(self):
        _sleep=float(0)
        if self.timing == int(self.INTEGRATION_TIME_05):
            _sleep=float(self.INTEGRATION_TIME_05)/1000
        elif self.timing == int(self.INTEGRATION_TIME_025):
            _sleep=float(self.INTEGRATION_TIME_025)/1000
        elif self.timing == int(self.INTEGRATION_TIME_0125):
            _sleep=float(self.INTEGRATION_TIME_0125)/1000
        elif self.timing == int(self.INTEGRATION_TIME_00625):
            _sleep=float(self.INTEGRATION_TIME_00625)/1000
        assert _sleep != float(0)
        # additional delay due to RPi's timer imprecision
        _sleep = _sleep + float(self.INTEGRATION_TIME_CTE)/1000
        log.debug("sleep for %0.3f" % _sleep)
        time.sleep(_sleep)

    def getTemperature(self):
        """ get temperature """
        self.enable()
        self.wait()
        
        # read TA register both bytes
        # I2C block read for two bytes
        _raw = self.i2c.read_i2c_block_data( self.address, self.REG_TA, 2 )

        # main part of temperature
        upper = float(_raw[0])

        # lower part of temperature is resolution dependant
        lower=float(0)
        if self.resolution==self.RES_05:
            lower = float((_raw[1]>>7)*0.5)
        elif self.resolution==self.RES_025:
            lower = float((_raw[1]>>6)*0.25)
        elif self.resolution==self.RES_0125:
            lower = float((_raw[1]>>5)*0.125)
        elif self.resolution==self.RES_00625:
            lower = float((_raw[1]>>4)*0.0625)

        #log.debug("I2C raw[0] = %#02X, raw[1] = %#02X)" % (_raw[0], _raw[1]))
        log.info("Temperature = %0.4f" % (upper + lower))

        # switch off sensor 
        self.disable()  
        return upper+lower;


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
        return self.getTemperature()

    # identity of sensor (i2c bus and i2c addr combination)
    # [Nov.16] RPis only have a single i2c bus ... so we just send back i2c_addr
    def unitID(self):
        '''send back i2c addr'''
        return self.address

    @staticmethod
    def detect():
        ''' Automated sensors detection
                [ ("TCN75A", i2c_bus, adr),("TCN75A", i2c_bus, adr), ... ] '''
        log.debug("Trying to find-out sensors ...")

        sensorsList = []

        # scan i2c bus and try to match against possible i2c addr of sensor
        #TODO: scan all i2c buses
        i2cbus=-1
        addresses = []
        # scan and intersect ...
        addresses = list(set(TCN75A._I2C_ADDRS) & set(i2cScan(i2cbus)))
        if len(addresses)==0:
            print("no device found ... :|")
            return None

        # parse addresses list to check that device corresponds
        for adr in addresses:
            try:
                sensor = TCN75A(adr)
            except Exception as ex:
                pass
            else:
                # sensor detected ...
                _sensor_params = ( "TCN75A", i2cbus, adr )
                sensorsList.append(_sensor_params)
                del sensor

        # only return usefull parameters
        if len(sensorsList) == 0:
            return None
        return sensorsList



#
# Main application case
#
if __name__ == "__main__":

    # launch auto-detection
    sensorsList = TCN75A.detect()
    if sensorsList is None:
        raise Exception("No TCN75A devices found")

    # parse list
    for (_,_,adr) in sensorsList:
        sensor = TCN75A(adr)

        # Set resolution
        print("[0x%.02x] Set resolution to 0.0625" % adr)
        sensor.setResolution(sensor.RES_00625);
        print("[0x%.02x] Temperature = %0.4f \n" % (adr,sensor.getTemperature()))

        # Set resolution
        print("[0x%.02x] Set resolution to 0.5" % adr)
        sensor.setResolution(sensor.RES_05);
        print("[0x%.02x] Temperature = %0.4f \n" % (adr,sensor.getTemperature()))

        del sensor


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)



###
### FIN
###

