#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Lepton FLIR neOCampus backend
# To test, launch <neocampus_rpi>/tests/test_leptonFLIR.py
#
# This passive micro-bolometer uses both i2c (control interface) and spi (video data)
#   As a default, camera responds to i2c addr = 0x2a, spi interface could either
#   spidev-0.0 (default) or spidev0.1
#
# https://cdn.sparkfun.com/datasheets/Sensors/Infrared/FLIR_Lepton_Data_Brief.pdf
# http://www.flir.com/uploadedFiles/OEM/Products/LWIR-Cameras/Lepton/FLIR-Lepton-Software-Interface-Description-Document.pdf
#
# WARNING: 16bits operation ONLY on i2c bus and BIG-ENDIAN ONLY (i.e MSB, LSB)
#   while linux on x86 and ARM are little endian ...
#
# TODO: find a way for 16bits addresses ...
#
# F.Thiebolt    oct.19  migrate to smbus2
# F.Thiebolt Feb.17
# [May.16] original from T.Bueno
#



# #############################################################################
#
# Import zone
#
import errno
import os
import signal
import syslog
import sys
import threading

import time

import RPi.GPIO as GPIO
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


# Lepton FLIR specific import
from .pylepton.lepton import Lepton
# and numpy for video processing
import numpy as np
from scipy.misc import imsave



# #############################################################################
#
# Global Variables
#



# #############################################################################
#
# Functions
#
def normalize(matrix):
    sum = np.sum(matrix)
    if sum > 0.:
        return matrix / sum
    else:
        return matrix


# #############################################################################
#
# Class
#
class LeptonBackend(object):

    # Class attributes
    LEPTON_FLIR_RESOLUTION      = ( 80 , 60 )

    # Lepton FLIR CCI(i.e i2c) registers
    # WARNING: 16 bits ONLY registers
    REGISTER_CONTROL_PWR        = 0x00
    REGISTER_STATUS             = 0x02
    REGISTER_COMMAND            = 0x04
    REGISTER_DATA_IO_LENGTH     = 0x06  # commands may have a variable number of arguments so length is specified here
    _REGISTER_DATA_IO_START     = 0x08
    _REGISTER_DATA_IO_END       = 0x26
    # up to 16 registers for data_io commands; WARNING: an iterable range (i.e not a list)
    REGISTERS_DATA_IO_CMD       = range(_REGISTER_DATA_IO_START, _REGISTER_DATA_IO_END+2, 2)
    # DATA BUFFER0 size=1024 bytes (16 bits access too)
    _BLOCK_DATA_BUFFER0_START   = 0xF800
    _BLOCK_DATA_BUFFER0_END     = 0xFBFE
    DATA_BUFFER0                = range(_BLOCK_DATA_BUFFER0_START, _BLOCK_DATA_BUFFER0_END+2, 2)
    # DATA BUFFER1 size=1024 bytes (16 bits access too)
    _BLOCK_DATA_BUFFER1_START   = 0xFC00
    _BLOCK_DATA_BUFFER1_END     = 0xFFFE
    DATA_BUFFER1                = range(_BLOCK_DATA_BUFFER1_START, _BLOCK_DATA_BUFFER1_END+2, 2)

    # Lepton timing parameters
    LEPTON_POWERON_DELAY        = 1     # 950ms delay after RESET / powerON

    # Lepton status bits (reg. REGISTER_STATUS)
    LEPTON_BOOT_STATUS          = 1 << 2    # bit 2 (0: boot still on way, 1: boot completed)
    LEPTON_BUSY_STATUS          = 1 << 0    # bit 0 (0: interface ready for new command, 1: camera is busy)
    LEPTON_RETURN_CODE          = lambda x: (x >> 8) & 0x0F

    # Lepton command bits (reg. REGISTER_COMMAND)
    LEPTON_CMD_GET              = 0         # bits[1..0] camera orders
    LEPTON_CMD_SET              = 1         # bits[1..0] camera orders
    LEPTON_CMD_RUN              = 2         # bits[1..0] camera orders
    LEPTON_MODULES_CMD          = 0x3f << 2 # bits[7..2] command for a specified module (i.e AGC, SYS, etc)
    LEPTON_MODULE_AGC           = 0x1 << 8  # bits[11..8] camera module ID
    LEPTON_MODULE_SYS           = 0x2 << 8  # bits[11..8] camera module ID
    LEPTON_MODULE_VID           = 0x3 << 8  # bits[11..8] camera module ID
    LEPTON_MODULE_OEM           = 0x8 << 8  # bits[11..8] camera module ID
    LEPTON_MODULE_RAD           = 0xe << 8  # bits[11..8] camera module ID
    LEPTON_CMD_OEM_BIT          = 1 << 14

    # Lepton SYS module commands
    MOD_SYS_CMD_STATUS          = 0x04      # GET --> return 4 words (64bits) system status
    MOD_SYS_CMD_SERIAL          = 0x08      # GET --> return 4 words (64bits) serial number
    MOD_SYS_CMD_UPTIME          = 0x0C      # GET --> return 2 words (32bits) camera uptime ms
    MOD_SYS_CMD_AUX_TEMP        = 0x10      # GET --> return 1 word  (16bits) kelvin temp of AUX (??) [0..16383] scale=100
    MOD_SYS_CMD_FPA_TEMP        = 0x14      # GET --> return 1 word  (16bits) kelvin temp of FPA (??) [0..65535] scale=100
    MOD_SYS_CMD_FFC_STATUS      = 0x44      # GET --> return 2 words (32bits) FFC status


    # Default I2C address of device
    I2C_ADDR    = 0x2a

    # Lepton PowerON/OFF GPIO
    _LEPTON_PWR_GPIO    = 4     # GPIO 4

    # I2C bus definitions and I2C bus instance
    # WARNING: i2c access are 16bits ONLY!
    i2c         = None
    i2cbus      = None
    i2cdebug    = False

    # SPI bus definitions and SPI bus instance
    spi         = None
    spibus      = None
    spics       = None


    # Initialization
    def __init__(self,i2cbus=-1, spi_bus=0, spi_cs=0, *args, **kwargs):
        self.i2cbus = i2cbus
        self.spibus = spi_bus
        self.spics  = spi_cs
        log.debug("Start loading lepton FLIR camera backend ...")

        log.info("Initializing I2C bus ...")
        try:
            self.i2c = SMBus(self.i2cbus if self.i2cbus >= 0 else 1)
        except Exception as ex:
            log.error("while creating I2C bus %d " % (self.i2cbus) + str(ex))
            raise ex

        # Setup GPIO power pin for lepton FLIR
        log.debug("Setup Lepton PWR GPIO %d" % __class__._LEPTON_PWR_GPIO)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(__class__._LEPTON_PWR_GPIO, GPIO.OUT)
        GPIO.output(__class__._LEPTON_PWR_GPIO, GPIO.LOW)

        # now check that this i2c device is really what we expect ...
        self.validate_sensor()

        '''
        # now we may try to capture a frame through SPI ...
        try:
            with Lepton("/dev/spidev" + self.spibus + "." + self.spics) as device:
                frame, frame_id = device.capture()
                if frame_id <= 0:
                    raise Exception("error while initializing lepton")

        except Exception as ex:
            log.error("lepton video unavailable: " + str(ex))
            raise ex
        '''

    def __del__(self):
        GPIO.setup(__class__._LEPTON_PWR_GPIO, GPIO.IN)

    def validate_sensor(self):
        """ read ChipID or something else to get sure it iw what we expect ... """
        # power cycle OFF / ON
        self.power_cycle()

        #[Feb.17] 16bits lengths registers address does not work with smbus :(
        return

        # now wait for busy status before issuing a command
        self.wait_lepton_ready()

        print("lepton camera ready for processing a command")

        # access to LEPTON's SYS module ...       
        #TODO: set macro, list, etc for data length to read
        #self.i2c.write_word_data(__class__.I2C_ADDR, __class__.REGISTER_DATA_IO_LENGTH, 4)  # we want to read AUX TEMP --> 1 value (16 bits)
        _cmd = __class__.LEPTON_CMD_GET | __class__.LEPTON_MODULE_SYS | __class__.MOD_SYS_CMD_SERIAL
        #self.i2c.write_word_data(__class__.I2C_ADDR, __class__.REGISTER_COMMAND, _cmd)

        # wait for lepton camera to process the command
        _cmd_status = self.wait_lepton_ready()
        # check command status return code
        if __class__.LEPTON_RETURN_CODE(_cmd_status)!=0 :
            log.error("\nLEPTON FLIR command '0x%04X' failed error_code = %d" % (_cmd_status, LEPTON_RETURN_CODE(_cmd_status)) )
            raise Exception("LEPTON FLIR command processing failed")

        # and finally retrieve command returned value
        count=10
        for reg in __class__.REGISTERS_DATA_IO_CMD:
            _word = self.i2c.read_i2c_block_data(__class__.I2C_ADDR, reg, 2)
            print("REGISTER_DATA_IO[0x%02X] = %d" % (reg,int(_word)))
            count -= 1
            if count==0: break
            
        _cmd_result = self.i2c.read_i2c_block_data(__class__.I2C_ADDR, __class__.REGISTERS_DATA_IO_CMD[0], 2)   # one word to retrieve

        log.info("LEPTON FLIR aux module temp = %d kelvin" % int(_cmd_result))

    def powerON(self):
        ''' PowerON device '''
        # switch ON transistor
        GPIO.output(__class__._LEPTON_PWR_GPIO, GPIO.HIGH)

        # powerOn device
        # Note: powerON automatically occurs so nothing to do ...
        #self.i2c.write_i2c_block_data(__class__.I2C_ADDR, __class__.REGISTER_CONTROL_PWR, [0, 0])
 
        # delay after powerON
        time.sleep(__class__.LEPTON_POWERON_DELAY)

        # Check device exists at i2c address
        try:
            ret = self.i2c.write_quick(__class__.I2C_ADDR)
        except IOError as ex:
            log.debug("No lepton FLIR found on i2c bus")
            raise ex

        #[Feb.17] 16bits lengths registers address does not work with smbus :(
        return

        # check boot status
        cur_status = self._smb16_read_word(__class__.I2C_ADDR, __class__.REGISTER_STATUS)
        if (cur_status & __class__.LEPTON_BOOT_STATUS) != 1: raise Exception("Lepton FLIR boot failure!")
        log.debug("Successfully powering ON lepton FLIR :)")

    def powerOFF(self):
        ''' PowerOFF device '''
        # switch OFF transistor
        GPIO.output(__class__._LEPTON_PWR_GPIO, GPIO.LOW)

    def power_cycle(self):
        ''' Power cycle the whole camera '''
        log.debug("Powering OFF ... then ON through GPIO %d" % __class__._LEPTON_PWR_GPIO)
        self.powerOFF()
        time.sleep(0.1)
        self.powerON()

    def wait_lepton_ready(self):
        ''' for for BUSY flag getting FALSE '''
        _iter=5
        while ( _iter!=0 ):
            cur_status = self.i2c.read_i2c_block_data(__class__.I2C_ADDR,__class__.REGISTER_STATUS, 2)
            if (cur_status & __class__.LEPTON_BUSY_STATUS) != 0:
                log.debug("Lepton FLIR camera busy ... sleeping a bit before retry ...")
                time.sleep(0.3)
                _iter -= 1
                continue
            return cur_status
        raise Exception("LEPTON FLIR continuously busy ... :|")


    def capture(self, size=None, format='png'):
        with Lepton("/dev/spidev0.0") as device:
            io_stream = io.BytesIO()

            frame, frame_id = device.capture()
            frame = normalize(frame)

            imsave(io_stream, frame, format)

            return io_stream

    def status(self,msg):
        msg['resolution'] = __class__.LEPTON_FLIR_RESOLUTION
        #msg['frame_rate'] = Compute it!


    def enable(self, *args, **kwargs):
        self.power_cycle()

        #[Feb.17] 16bits lengths registers address does not work with smbus :(
        # now wait for busy status before issuing a command
        #self.wait_lepton_ready()
        pass

    def disable(self):
        self.powerOFF()


    # -------------------------------------------------------------------------
    # 16bits I2C access
    # - _smb16_read_word(i2c_addr, reg_addr)

    def _smb16_read_word(self, i2c_addr, reg_addr):
        ''' Specify 16bits addr register to read,
            then read up to count data. '''
        # set the 16bits base address register
        self.i2c.write_byte_data(i2c_addr, reg_addr >> 8,reg_addr & 0xFF)
        _data = list()
        #_data = self.i2c.read_i2c_block_data(i2c_addr,2) [oct.19]
        print(_data)
        return (_data[0] << 8 | _data[1] )


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

