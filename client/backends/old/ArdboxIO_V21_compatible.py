#!/usr/bin/env python3
# coding: utf-8
#
# ArdboxIO backend
#
# We expose a uniform access to all of the Ardbox IO boards.
#
# Each Ardbox features a variable number of I/O that is stored within its EEPROM.
# Ardbox modules are i2c slaves starting from 0x03 to 0x77
#
# NOTE: I/O start at 0 (i.e not 1)
# TODO: _digital_read_callback interrupt can get unseen! (look code below)
#   we ought to implement a thread that will call callbacks function whenever
#   GPIO5 is high!
#
# [Sep.19] S.Lucas      added tests for all V2 settings in main
# [Sep.19] S.Lucas      add support for CRC8 calculation and address registers and dealing with the config register (functions to update each setting)
# [Sep.19] F.Thiebolt   add support for Reseting Ardbox modules on startup
# [Feb.17] F.Thiebolt   add smbus CRC8 (PacketErrorChecking) TODO: activate it!!
# [Jan.17] F.Thiebolt   added Ardbox's i2cbuslock support
# [Jan.17] F.Thiebolt   added support for digital inputs events
# F.Thiebolt Dec.16
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

import crc8

import time
import threading

import RPi.GPIO as GPIO

# extend Python's library search path
import os
import sys
# Helpers and i2c functions import
_path2add='../libutils'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from HelpersFunc import *
from Adafruit_I2C import Adafruit_I2C
#[i2c] we'll make direct use of smbus
from smbus import SMBus

# sensOCampus
_path2add='../sensocampus'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from settings import ARDBOX_I2C_PEC,ARDBOX_I2C_CRC
from logger import log



# #############################################################################
#
# Global Variables
#



# #############################################################################
#
# Functions
#



# #############################################################################
#
# Class
#
class ArdboxIO(object):

    #
    # CLASS ATTRIBUTES
    # Note: Ardbox modules can use the full range of I2C addr ;)
    ADR_LOW         = 0x03
    ADR_HIGH        = 0x77
    _I2C_ADDRS      = list(range( ADR_LOW, ADR_HIGH+1 ))

    # Ardbox EEPROM addresses
    EEPROM_CHECK            = 0     # 42 is th expected value ;)
    EEPROM_I2CSLAVE_ADDR    = 1
    EEPROM_ARDBOX_TYPE      = 2     # 0x10: Ardbox20
    EEPROM_PRGM_MAJOR       = 3     # Ardbox firmware revision, major number
    EEPROM_PRGM_MINOR       = 4     # Ardbox firwmare revision, minor number
    EEPROM_IO_LIST          = 5     # bits[7..4] number of outputs, bits[3..0]: number of inputs
    EEPROM_ADDR_LAST        = 6

    # Ardbox I2C registers
    ARDBOX_CTRL_REG         = 0     # Control register of Ardbox module (e.g enable/disable CRC, loop value etc)
    ARDBOX_CMD_REG          = 1     # Command register (i.e read_digital, write_analog, getID ...)
    ARDBOX_READ_REG         = 15    # General read register (Nothing is actually contained in register 15 but we HAVE to specify a register number when requesting read so we use 15)
    CONFIG_REG_LAST         = 2     # Size of config register (1 bit) + CRC if enabled

    # Ardbox CMD register bits
    ARDBOX_CMD_READ         = 1 << 7    # bit7: (1, read) (0, write)
    ARDBOX_CMD_WRITE        = 0 << 7
    ARDBOX_CMD_DIGITAL      = 1 << 6    # bit6: (1, digital) (0, analog)
    ARDBOX_CMD_ANALOG       = 0 << 6
    ARDBOX_CMD_ID           = 1 << 5    # bit5: (1: ID related op) (0, regular op)
    ARDBOX_CMD_REGULAR      = 0 << 5
    ARDBOX_CMD_READ_CTRL_REG = 1 << 0         # bit0: (1: Combined with bit5 -> read config/control register) (0: Combined with bit5 -> read ID EEPROM)
    # bit4: if [READ operation]
    # Note: Bulk Read only applies to digital inputs
    ARDBOX_CMD_BR           = 1 << 4    # bit4: (1: Bulk Read ---all digital inputs) (0, Regular Read of input specified in bits[3..0]
    ARDBOX_CMD_RR           = 0 << 4
    # bit4: if [WRITE operation]
    ARDBOX_CMD_DV           = 4     # bit4: digital value to write (0 or 1) of output specified in bits[3..0]
    # bit[3..0]: specifiy input or output
    ARDBOX_CMD_IOBITS       = 0x0F  # bits[3..0]

    # Ardbox CTRL register bits
    ARDBOX_CTRL_ENABLECRC   = 1 << 7    # bit7: (1, enable) (0, disable) Default: disabled
    ARDBOX_CTRL_DISABLECRC  = ~(1 << 7)
    ARDBOX_CTRL_RST         = 1 << 6    # bit6: (1, activate software reset)
    ARDBOX_CTRL_ENLOOP      = 1 << 5    # bit5: (1, specified loop value following)
    ARDBOX_CTRL_DISLOOP     = ~(1 << 5)    # bit5: (0, disable manual loop -> reset to predefined loop)
    # Loop value bits[4..2]
    ARDBOX_CTRL_LOOP_100MS  = ~(0x7 << 2)
    ARDBOX_CTRL_LOOP_250MS  = ~(0x6 << 2)
    ARDBOX_CTRL_LOOP_500MS  = ~(0x5 << 2)
    ARDBOX_CTRL_LOOP_1S     = ~(0x4 << 2)
    ARBOX_CTRL_I2CWDG_EN    = ~(1 << 1)    # bit1: (1, disable i2c watchdog) (0, enabled) Default: enabled
    ARBOX_CTRL_I2CWDG_DIS   = 1 << 1
    # Ardbox CTRL bit0 free to use

    _EEPROM_CHECK_VALUE     = 42    # value to test we're not reading bullshit ;) (CRC next time)
    _SIZEOF_ANALOG_READ     = 2     # nb bytes used to encode an analog value = [ LSB, MSB ] (MAX=4)
    _SIZEOF_DIGITAL_READ    = 1     # nb bytes used to encode a digital value (MAX=4)
    _SIZEOF_DIGITAL_BREAD   = 1     # nb bytes used to encode a digital value = [ LSB, ..., ..., MSB ] (MAX=4)
    _ANALOG_READ_MAX        = 2**10 # 2^10 bits for analog values to read (from Analog to digital converter)
    _ANALOG_WRITE_MAX       = 2**8  # 2^8 bits for analog values to write (to Digital to Analog converter)

    # Ardbox dedicated GPIO pins
    _ARDBOX_GPIO_EVENT      = 5     # GPIO 5 / dedicated to receive digital events from Ardbox (i.e digital input change)
    _ARDBOX_GPIO_RESET      = 6     # GPIO 6 / allow to reset the Ardbox modules through their dedicated RESET pin 



    #
    # attributes
    boards = None       # Ardbox boards = [ (i2cadr, Ardbox_EEPROM), (i2cadr, Ardbox_EEPROM) ... ]

    _inputs = None      # Inputs list = [ 8, 8, ... ]. Note that position in list match those in self.boards
    _nbinputs = 0

    _outputs = None     # Outputs list = [ 8, 8, ... ]. Note that position in list match those in self.boards
    _nboutputs = 0

    i2c         = None
    i2cbus      = None
    i2cbuslock  = threading.Lock()

    _CRC_disable_override = False

    # Lock protected attributes (thread-safe)
    _lock           = None
    _i2c_errors     = 0
    _callbacks      = None      # { <callback_func>:[ 0, 3, ... ], <callback_func2>:[ 1, 8, ... ] , ... }
    _digital_inputs = None      # [ (inputs 1st ardbox), (inputs 2nd ardbox), ... ] note: inputs are an integer
    _spurious_events    = -1    # i.e Ardbox's low-level callback called while not event detected!
    _backend_pin_offset = -1    # current backend pin offset regarding the high-level backend


    #
    # Constructor
    def __init__(self, i2cbus=-1, *args, **kwargs):
        ''' Ardbox backend initialization '''

        # initialization
        self.boards             = list()
        self._inputs            = list()
        self._outputs           = list()
        self._callbacks         = dict()
        self._digital_inputs    = list()

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        self.resetHW()

        # instantiate an i2c bus ...
        self.i2cbus = i2cbus
        try:
            #_selectbus=self.i2cbus if self.i2cbus >= 0 else Adafruit_I2C.getPiI2CBusNumber()
            #log.debug("i2c selected bus '%d'" % _selectbus)
            self.i2c = SMBus(self.i2cbus if self.i2cbus >= 0 else Adafruit_I2C.getPiI2CBusNumber())
            if ARDBOX_I2C_PEC is True:
                # Firmware >= 1.7, activate smbus PEC (packet error checking) CRC8
                self.i2c.pec = True
                log.info ("Ardbox's I2C PEC activated ...");
        except Exception as ex:
            log.error("while creating I2C bus %d " % (self.i2cbus) + str(ex))
            raise ex

        # protected attributes
        self._lock = threading.Lock()
        with self._lock:
            self._i2c_error = 0
            self._spurious_events = -1
            self._backend_pin_offset = -1
        
        # detecting boards
        self.boards = self.detect()
        if self.boards is not None and len(self.boards) != 0:
            log.debug("%d Ardbox board(s) detected" % len(self.boards))
        else:
            log.debug("no Ardbox board found out there :|")
        
        # enable I2C CRC ?
        if ARDBOX_I2C_CRC is True:
            try:
                # Firmware >= 2.0, activate i2c CRC8
                self._enableCRC()
                log.info ("Ardbox's I2C CRC-8 activated ...");
            except Exception as ex:
                log.error("while CRC activation on I2C bus %d " % (self.i2cbus) + str(ex))
                raise ex
        
#TODO: change GPIO signaling polarity
        # Ardbox dedicated event pin
        log.debug("Setup Ardbox's event GPIO %d" % __class__._ARDBOX_GPIO_EVENT)
        GPIO.setup(__class__._ARDBOX_GPIO_EVENT, GPIO.IN)


    def detect(self):
        ''' Automated detection of Ardbox modules '''
        log.debug("Start searching for Ardbox boards ... ")
        _boards = list()

        # scan i2c bus and try to match against possible i2c addr of modules
        #TODO: scan all i2c buses
        addresses = []
        # scan and intersect ...
        addresses = list(set(__class__._I2C_ADDRS) & set(i2cScan(self.i2cbus)))
        if len(addresses)==0:
            print("no device found ... :|")
            return None
        
        # parse addresses list to check that device corresponds
        for adr in addresses:
            try:
                # we ask for Identity data block
                boardEEPROM = self._getID(adr)
                log.debug("EEPROM info:")
                log.debug(boardEEPROM)
                # ... then check validity
                if boardEEPROM[__class__.EEPROM_CHECK]!=__class__._EEPROM_CHECK_VALUE or \
                    boardEEPROM[__class__.EEPROM_I2CSLAVE_ADDR] != adr:
                    log.info("i2c device 0x%02X is not an Ardbox board, continuing" % adr);
                    continue;
            except Exception as ex:
                log.debug("Ardbox [0x%X] raised an exception: " % adr + str(ex))
                pass
            else:
                # board detected ...
                _boards.append((adr,boardEEPROM))
        
        # only return usefull parameters
        if len(_boards) == 0:
            return None

        # update inputs / outputs lists
        self._inputs = [ (eeprom[__class__.EEPROM_IO_LIST] & 0b00001111 ) for _,eeprom in _boards ]
        self._nbinputs = sum(self._inputs)
        self._outputs = [ (eeprom[__class__.EEPROM_IO_LIST] & 0b11110000 ) >> 4 for _,eeprom in _boards ]
        self._nboutputs = sum(self._outputs)
        return _boards


    # -------------------------------------------------------------------------
    # Low-level Ardbox API:
    # - _getID()
    # - _digital_read()
    # - _digital_read_callback()  Method called upon GPIO event related to Ardbox's digital event
    # - _digital_bread()    Digital Bulk read (i.e all inputs)
    # - _digital_write()
    # - _analog_read()
    #
    # - _getConfigRegister()
    # - _enableCRC()
    # - _disableCRC()
    # - _i2c_WD_enable()
    # - _i2c_WD_disable()
    # - _manual_loop_enable()
    # - _manual_loop_disable()

    ''' For some operations we use &, this is if we want to set a bit from 1 back to 0 but it's important not
    to overwrite the wrong bits. If you look at the defined values when we want 0 we use ~(1 << bit_position) '''

    def _manual_loop_enable(self, loop_value, adr=-1):
        ''' enable manual loop value on designated Ardbox through i2c bus '''

        retry = 3
        while retry!=0:
            try:
                if ( adr == -1 ):
                #Will enable manual loop on all connected ArdBox modules
                  for (adr,reste) in self.boards:

                    #Check if manual loop is enabled, if yes then we have to toggle it off for the ArdBox to update
                    current_config = self._getConfigRegister(adr)
                    if ( current_config & 0b00100000 == 0b00100000 ):
                        self._manual_loop_disable(adr)
                        time.sleep(1)

                    ''' TODO : Fix the loop values, problem with | and & operators as we are dealing with 3 bits
                               at once !!! '''

                    current_config = self._getConfigRegister(adr)
                    if ( loop_value == 0 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) & __class__.ARDBOX_CTRL_LOOP_100MS
                    if ( loop_value == 1 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) & __class__.ARDBOX_CTRL_LOOP_250MS
                    if ( loop_value == 2 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) & __class__.ARDBOX_CTRL_LOOP_500MS
                    if ( loop_value == 3 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) & __class__.ARDBOX_CTRL_LOOP_1S
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 0
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

                #Will enable manual loop on specified Ardbox module    
                else:

                    #Check if manual loop is enabled, if yes then we have to toggle it off for the ArdBox to update
                    current_config = self._getConfigRegister(adr)
                    if ( current_config & 0b00100000 == 0b00100000 ):
                        self._manual_loop_disable(adr)
                        time.sleep(1)

                    current_config = self._getConfigRegister(adr)
                    if ( loop_value == 0 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) | ARDBOX_CTRL_LOOP_100MS
                    if ( loop_value == 1 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) | ARDBOX_CTRL_LOOP_250MS
                    if ( loop_value == 2 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) | ARDBOX_CTRL_LOOP_500MS
                    if ( loop_value == 3 ):
                        command = (current_config | __class__.ARDBOX_CTRL_ENLOOP) | ARDBOX_CTRL_LOOP_1S 
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 0
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1   
                if retry == 0:
                    log.error("Error while enabling manual loop " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while enabling manual loop ... retrying" % (adr))
            else:    
                # done :)
                retry=0

        log.debug("manual loop enabled!")
        return True

    def _manual_loop_disable(self, adr=-1):
        ''' disable manual loop value on designated Ardbox through i2c bus '''

        retry = 3
        while retry!=0:
            try:
                if ( adr == -1 ):
                #Will disable manual loop on all connected ArdBox modules
                  for (adr,reste) in self.boards:
                    current_config = self._getConfigRegister(adr)
                    command = current_config &  __class__.ARDBOX_CTRL_DISLOOP 
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 0
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)
                #Will disable manual loop on specified Ardbox module   
                else:
                    current_config = self._getConfigRegister(adr)
                    command = current_config & __class__.ARDBOX_CTRL_DISLOOP 
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 0
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1   
                if retry == 0:
                    log.error("Error while disabling manual loop " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while disabling manual loop ... retrying" % (adr))
            else:    
                # done :)
                retry=0

        log.debug("manual loop disabled!")
        return True

    def _i2c_WD_enable(self, adr=-1):
        ''' enable i2c watchdog on designated Ardbox through i2c bus '''

        retry = 3
        while retry!=0:
            try:
                if ( adr == -1 ):
                #Will enable i2c watchdog on all connected ArdBox modules
                  for (adr,reste) in self.boards:
                    current_config = self._getConfigRegister(adr)
                    command = current_config & __class__.ARBOX_CTRL_I2CWDG_EN 
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 0
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)
                #Will enable i2c watchdog on specified Ardbox module   
                else:
                    current_config = self._getConfigRegister(adr)
                    command = current_config & __class__.ARBOX_CTRL_I2CWDG_EN 
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 0
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1   
                if retry == 0:
                    log.error("Error while enabling i2c watchdog " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while enabling i2c watchdog ... retrying" % (adr))
            else:    
                # done :)
                retry=0

        log.debug("i2c watchdog enabled!")
        return True

    def _i2c_WD_disable(self, adr=-1):
        ''' disable i2c watchdog on designated Ardbox through i2c bus '''

        retry = 3
        while retry!=0:
            try:
                if ( adr == -1 ):
                #Will disable i2c watchdog on all connected ArdBox modules
                  for (adr,reste) in self.boards:
                    current_config = self._getConfigRegister(adr)
                    command = current_config | __class__.ARBOX_CTRL_I2CWDG_DIS
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 1
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)
                #Will disable i2c watchdog on specified Ardbox module   
                else:
                    current_config = self._getConfigRegister(adr)
                    command = current_config | __class__.ARBOX_CTRL_I2CWDG_DIS
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 0
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1   
                if retry == 0:
                    log.error("Error while disabling i2c watchdog " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while disabling i2c watchdog ... retrying" % (adr))
            else:    
                # done :)
                retry=0

        log.debug("i2c watchdog disabled!")
        return True

    def _disableCRC(self, adr=-1):
        '''  Disable CRC on designated Ardbox through i2c bus '''

        retry = 3
        while retry!=0:
            try:
                if( adr == -1):
                #Will disable CRC8 on all connected ArdBox modules
                  for (adr,reste) in self.boards:
                    current_config = self._getConfigRegister(adr)
                    command = current_config & __class__.ARDBOX_CTRL_DISABLECRC
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 1
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)
                else:
                    current_config = self._getConfigRegister(adr)
                    command = current_config & __class__.ARDBOX_CTRL_DISABLECRC
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 1
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1   
                if retry == 0:
                    log.error("Error while disabeling CRC ... " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while disabeling CRC ... retrying" % (adr))
            else:
                # done :)
                retry=0

        log.debug("CRC8 disabled!")
        return True

    def _enableCRC(self, adr=-1):
        '''  Enable CRC on designated Ardbox through i2c bus '''

        retry = 3
        while retry!=0:
            try:
                if(adr == -1):
                #Will enable CRC8 on all connected ArdBox modules
                  for (adr,reste) in self.boards:
                    current_config = self._getConfigRegister(adr)
                    command = current_config | __class__.ARDBOX_CTRL_ENABLECRC
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 1
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)
                else:
                    current_config = self._getConfigRegister(adr)
                    command = current_config | __class__.ARDBOX_CTRL_ENABLECRC
                    with __class__.i2cbuslock:

                         #We create a list containing all the values needed for the CRC8 calculation
                         CRC_list = [adr, __class__.ARDBOX_CTRL_REG, command]
                         #We create a list containing all the data to send via i2c
                         fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                         #We write our block of data to register 1
                         data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while writing digital value ... " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while writing digital value ... retrying" % (adr))
            else:
                # done :)
                retry=0

        log.debug("CRC8 enabled!")
        return True


    def _getConfigRegister(self, adr):
        ''' retrieve Ardbox board config/control register '''
        command = __class__.ARDBOX_CMD_READ | __class__.ARDBOX_CMD_ID | __class__.ARDBOX_CMD_READ_CTRL_REG

        retry = 3
        while retry!=0:
            try:
                # we read up to EEPROM_ADDR_LAST bytes
                with __class__.i2cbuslock:
                   
                     #We create a list containing all the values needed for the CRC8 calculation
                     CRC_list = [adr, __class__.ARDBOX_CMD_REG, command]
                     #We create a list containing all the data to send via i2c
                     fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                     #We write our block of data to register 1
                     self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CMD_REG, fullDataList)
                     #We read back the requested data from register 15
                     data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, __class__.CONFIG_REG_LAST)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while reading config register ... " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while reading config register ... retrying" % (adr))
            else:
                # done :)
                retry=0

        log.debug("Config/control register Ardbox[0x%02X] = %s" % (adr,str(data)));
        return data[0]

    def _getID(self, adr):
        ''' retrieve Ardbox board identity informations (EEPROM) '''
        command = __class__.ARDBOX_CMD_READ | __class__.ARDBOX_CMD_ID

        retry = 3
        while retry!=0:
            try:
                # we read up to EEPROM_ADDR_LAST bytes
                with __class__.i2cbuslock:
                   
                   
		     #We create a list containing all the values needed for the CRC8 calculation
                     CRC_list = [adr, __class__.ARDBOX_CMD_REG, command]
		     #We create a list containing all the data to send via i2c
                     fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                     #fullDataList = [command]
                     #We write our block of data to register 1
                     self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CMD_REG, fullDataList)
		     #We read back the requested data from register 15
                     data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, (__class__.EEPROM_ADDR_LAST))

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while reading EEPROM IDs ... " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while reading EEPROM IDs ... retrying" % (adr))
            else:
                # done :)
                retry=0

        log.debug("EEPROM ID Ardbox[0x%02X] = %s" % (adr,str(data)));
        return data


    # Ardbox's low-level callback function
    def _digital_read_callback(self, channel):
        ''' func called upon GPIO notification related to a digital input that evolved @ digitl inputs of Ardbox(s) '''
        log.debug(" --> digital event detected --> ardbox's low-level callback running ...")
        # check it is for us
        if channel != __class__._ARDBOX_GPIO_EVENT:
            log.warning("ouch ... callback activated for wrong pin event (%d while %d expected!!)" % (__class__._ARDBOX_GPIO_EVENT,channel))
            return

        with self._lock:

            _iterate=True
            while _iterate is True:
                _iterate = False

                # a callback has been registered?
                if len(self._callbacks)==0:
                    log.error("ardbox's low-level callback activated while no _callbacks handler registered ?!?!")
                    return
                # let's read all value to detect changes
                _cur_digital_inputs = self.digital_bread()
            
                # is this first time
                if len(self._digital_inputs)==0:
                    self._digital_inputs = _cur_digital_inputs
                    return

                # compute list of digital events
                _xor_digital_inputs = list()
                # XOR(_last_bulk_read, _cur_bulk_read)
                _xor_digital_inputs = map(lambda x: x[0] ^ x[1], zip(self._digital_inputs, _cur_digital_inputs))

                self._digital_inputs = _cur_digital_inputs

                # generate list of tuples for thos upon an event has been detceted = [ (pin, new_value), (pin, new_value) ... ]
                _eventsList = list()

                _poffset=0  # pin offset
                for _pevent,_pvalue,_nbinputs in zip(_xor_digital_inputs,_cur_digital_inputs,self._inputs):

                    if _pevent == 0:
                        # no digital input change here ...
                        _poffset += _nbinputs
                        continue

                    # parse bits to create tuples (pin_number, new_value)
                    for _bit_index in range(_pevent.bit_length()):
                        if (_pevent >> _bit_index) & 0x01 == 1:
                            # event deteted
                            _pin = _bit_index + _poffset
                            _pin_value = (_pvalue >> _bit_index) & 0x01
                            _eventsList.append((_pin,_pin_value))

                    # increment pin offset
                    _poffset += _nbinputs
                
                log.debug("Digital events = " + str(_eventsList) )

                if len(_eventsList)==0:
                    if self._spurious_events == __class__._spurious_events:
                        # we eliminate first event that may not be an error
                        self._spurious_events = 0
                    else:
                        log.warning("low-level callback called while no events detected ... spurious interrupt ...")
                        self._spurious_events += 1
                    return

                # ... then filter according to registered callbacks ...
                # .. thus we go through the list of callbacks
                for _func,_inputs2watch in self._callbacks.items():

                    _events4callback = list()
                    # ... we try to match pin events from list of inputs2watch ...
                    for _pin,_pinvalue in _eventsList:
                        if _pin in _inputs2watch:
                            # compute real pin number and value to send [ (104,0), (112,1) ... ]
                            _events4callback.append( (_pin + self._backend_pin_offset, _pinvalue) )

                    # and call registred callbacks according to pin(s) event(s)
                    if len(_events4callback)!=0:
                        try:
                            # notify registered callback
                            _func(_events4callback)
                        except Exception as ex:
                            log.error("error while notifying registered callback: " + str(ex))
                            pass

                # end of iteration ... do we need to restart a whole data acquisition ?
                # ... it depends whether the GPIO event line is still HIGH !
                # TODO: if input 5 change just during return from callback call ... no GPIO.RISING will be seen and you're stuck!
                if GPIO.input(channel) == GPIO.HIGH:
                    log.debug("GPIO_event pin still high at the end of callback ... new events need to get processed then!")
                    _iterate = True



    def _digital_write(self, adr, pin, value):
        ''' Write digital_output to designated Ardbox through i2c bus '''
        command = __class__.ARDBOX_CMD_WRITE | __class__.ARDBOX_CMD_DIGITAL | __class__.ARDBOX_CMD_REGULAR | (__class__.ARDBOX_CMD_IOBITS & pin)
        if value!= 0:
            command |= (1 <<__class__.ARDBOX_CMD_DV)

        retry = 3
        while retry!=0:
            try:
                # we use the register field for the command, and we just send the command (digital value included within command :) )
                with __class__.i2cbuslock:
                    #data = self.i2c.write_byte(adr, command)

		    #We create a list containing all the values needed for the CRC8 calculation
                     CRC_list = [adr, __class__.ARDBOX_CMD_REG, command]
                     #We create a list containing all the data to send via i2c
                     fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                     #We write our block of data to register 1
                     data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CMD_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while writing digital value ... " + str(ex));
                    raise
                else:

                    log.debug("Warning: i2c[0x%02X] IOError while writing digital value ... retrying" % (adr))
            else:
                # done :)
                retry=0

        log.debug("[0x%02X] digital_write(%d) = " % (adr,pin) + str(value))
        return True


    # Digital bulk read
    def _digital_bread(self, adr):
        ''' Read ALL digital inputs from specified ardbox modules through I2C bus '''
        command = __class__.ARDBOX_CMD_READ | __class__.ARDBOX_CMD_DIGITAL | __class__.ARDBOX_CMD_REGULAR | __class__.ARDBOX_CMD_BR

        retry = 3
        while retry!=0:
            try:
                # we use the register field for the command, and we read all inputs as digital
                with __class__.i2cbuslock:
                    #data = self.i2c.read_i2c_block_data(adr, command, __class__._SIZEOF_DIGITAL_BREAD)
		    #We create a list containing all the values needed for the CRC8 calculation
                     CRC_list = [adr, __class__.ARDBOX_CMD_REG, command]
                     #We create a list containing all the data to send via i2c
                     fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                     #We write our block of data to register 1
                     self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CMD_REG, fullDataList)
                     #We read back the requested data from register 15
                     #data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, __class__._SIZEOF_DIGITAL_BREAD)

                     #We check received CRC if enabled
                     if ((ARDBOX_I2C_CRC is True) & (__class__._CRC_disable_override is False)): 

                         #We read back the requested data from register 15 with CRC
                         data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, (__class__._SIZEOF_DIGITAL_BREAD+1))
                         #The received CRC isn't calculated with the address but just with the received data
                         CRC_list = [data[0]]
                         log.debug("received CRC: [CRC=%d]" % (data[__class__._SIZEOF_DIGITAL_BREAD]))
                         log.debug("calculated CRC: [CRC]=%d]" % (int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)))
                         #We use __class__._SIZEOF_DIGITAL_BREAD and not __class__._SIZEOF_DIGITAL_BREAD+1 because data starts at 0
                         if ( data[__class__._SIZEOF_DIGITAL_BREAD] != int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)):
                              
                       
                             raise IOError("Wrong CRC received!")

                     else:
                         #We read back the requested data from register 15 without CRC
                         data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, __class__._SIZEOF_DIGITAL_BREAD)

                _data = int()
                if __class__._SIZEOF_DIGITAL_BREAD == 1:
                    _data = data[0]
                elif __class__._SIZEOF_DIGITAL_BREAD == 2:
                    _data = data[0] | (data[1] << 8)
                elif __class__._SIZEOF_DIGITAL_BREAD == 4:
                    _data = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
                else:
                    raise ValueError("Wrong size of digital_bread data :|")

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_bread ... "  + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while digital_bread ... retrying" % (adr))
            except ValueError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_bread : " + str(ex));
                    raise
                else:
                    log.warning("Warning: i2c[0x%02X] ValueError while digital_bread ... retrying" % (adr))
            else:
                # done :)
                retry=0

        return _data


    def _digital_read(self, adr, pin):
        ''' Read digital_input from designated Ardbox through i2c bus '''
        command = __class__.ARDBOX_CMD_READ | __class__.ARDBOX_CMD_DIGITAL | __class__.ARDBOX_CMD_REGULAR | __class__.ARDBOX_CMD_RR | (__class__.ARDBOX_CMD_IOBITS & pin)

        retry = 3
        while retry!=0:
            try:
                # we use the register field for the command, and we read 1byte
                with __class__.i2cbuslock:
                    #data = self.i2c.read_i2c_block_data(adr, command, __class__._SIZEOF_DIGITAL_READ)
		    #We create a list containing all the values needed for the CRC8 calculation
                     CRC_list = [adr, __class__.ARDBOX_CMD_REG, command]
                     #We create a list containing all the data to send via i2c
                     fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                     #We write our block of data to register 1
                     self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CMD_REG, fullDataList)
                     #We read back the requested data from register 15
                     #data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, __class__._SIZEOF_DIGITAL_READ)

                     #We check received CRC if enabled
                     if ((ARDBOX_I2C_CRC is True) & (__class__._CRC_disable_override is False)):

                         #We read back the requested data from register 15 with CRC
                         data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, (__class__._SIZEOF_DIGITAL_READ+1))
                         #The received CRC isn't calculated using the address but just the received data
                         CRC_list = [data[0]]
                         log.debug("received CRC: [CRC=%d]" % (data[__class__._SIZEOF_DIGITAL_READ]))
                         log.debug("calculated CRC: [CRC]=%d]" % (int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)))
                         #We use __class__._SIZEOF_DIGITAL_READ and not __class__._SIZEOF_DIGITAL_READ+1 because data starts at 0
                         if ( data[__class__._SIZEOF_DIGITAL_READ] != int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)):
                              
                       
                             raise IOError("Wrong CRC received!")

                     else:
                         #We read back the requested data from register 15 without CRC
                         data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, __class__._SIZEOF_DIGITAL_READ)


                _data = int()
                if __class__._SIZEOF_DIGITAL_READ == 1:
                    _data = data[0]
                elif __class__._SIZEOF_DIGITAL_READ == 2:
                    _data = data[0] | (data[1] << 8)
                elif __class__._SIZEOF_DIGITAL_READ == 4:
                    _data = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
                else:
                    raise ValueError("Wrong size of digital_read data :|")
                # test that value is either 0 or 1 (and no other bit(s) set)
                if _data & -2 != 0:
                    raise ValueError("digital_read=%d is not a bool" % (_data) )
            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_read[pin=%d] ... " % (pin) + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while digital_read[pin=%d] ... retrying" % (adr,pin))
            except ValueError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_read[pin=%d] : " % (pin) + str(ex));
                    raise
                else:
                    log.warning("Warning: i2c[0x%02X] ValueError while digital_read[pin=%d] ... retrying" % (adr,pin))
            else:
                # done :)
                retry=0

        return _data


    def _analog_read(self, adr, pin):
        ''' Read analog_input from designated Ardbox through i2c bus '''
        command = __class__.ARDBOX_CMD_READ | __class__.ARDBOX_CMD_ANALOG | __class__.ARDBOX_CMD_REGULAR | (__class__.ARDBOX_CMD_IOBITS & pin)

        retry = 3
        while retry!=0:
            try:
                # we use the register field for the command, and we read 2bytes (MSB, LSB)
                with __class__.i2cbuslock:
                    #data = self.i2c.read_i2c_block_data(adr, command, __class__._SIZEOF_ANALOG_READ)
		    #We create a list containing all the values needed for the CRC8 calculation
                     CRC_list = [adr, __class__.ARDBOX_CMD_REG, command]
                     #We create a list containing all the data to send via i2c
                     fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                     #We write our block of data to register 1
                     self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CMD_REG, fullDataList)
                     #We read back the requested data from register 15
                     #data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, __class__._SIZEOF_ANALOG_READ)

                     #We check received CRC if enabled
                     if ((ARDBOX_I2C_CRC is True) & (__class__._CRC_disable_override is False)):

                         #We read back the requested data from register 15 with CRC
                         data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, (__class__._SIZEOF_ANALOG_READ+1))
                         #The returned CRC isn't calculated with the address but just with the returned data!
                         CRC_list = [data[0], data[1]]
                         log.debug("received CRC: [CRC=%d]" % (data[__class__._SIZEOF_ANALOG_READ]))
                         log.debug("calculated CRC: [CRC]=%d]" % (int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)))
                         #We use __class__._SIZEOF_ANALOG_READ and not __class__._SIZEOF_ANALOG_READ+1 because data starts at 0
                         if ( data[__class__._SIZEOF_ANALOG_READ] != int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)):
                              
                       
                             raise IOError("Wrong CRC received!")

                     else:
                         #We read back the requested data from register 15 without CRC
                         data = self.i2c.read_i2c_block_data(adr, __class__.ARDBOX_READ_REG, __class__._SIZEOF_ANALOG_READ)

                # recreate value from MSB, LSB
                _data = int()
                if __class__._SIZEOF_ANALOG_READ == 1:
                    _data = data[0]
                elif __class__._SIZEOF_ANALOG_READ == 2:
                    _data = data[0] | (data[1] << 8)
                elif __class__._SIZEOF_ANALOG_READ == 4:
                    _data = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
                else:
                    raise ValueError("Wrong size of analog_read data :|")
                if _data < 0 or _data >= __class__._ANALOG_READ_MAX:
                    raise ValueError("analog_read=%d is out of range [0..%d]" % (_data,__class__._ANALOG_READ_MAX-1) )
            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while analog_read[pin=%d] ... " % (pin) + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while analog_read[pin=%d] ... retrying" % (adr,pin))
            except ValueError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while analog_read[pin=%d] : " % (pin) + str(ex));
                    raise
                else:
                    log.warning("Warning: i2c[0x%02X] ValueError while analog_read[pin=%d] ... retrying" % (adr,pin))
            else:
                # done :)
                retry=0

        #log.debug("[0x%02X] analog_read(%d) = " % (adr,pin) + str(_data))
        return _data


    def status(self):
        '''send back maximum number of inputs / outputs'''
        return self._nbinputs, self._nboutputs



    # -------------------------------------------------------------------------
    #
    # neOCampus backends API
    # - digital_read()
    # - digital_bread()         Digital Bulk read (i.e all inputs)
    # - digital_read_callback() Set callback for digital input events
    # - cancel_digital_read_callback()  Cancel previously set callback
    # - digital_write()
    # - analog_read()
    # - analog_write()
    #
    # - resetHW()               Hardware reset through dedicated GPIO pin
    # - resetSW()               Sofwtare reset through I2C command
    # - enableCRC()
    # - disableCRC()
    # - manual_loop_enable()
    # - manual_loop_disable()
    # - i2c_WD_enable()
    # - i2c_WD_disable()

    def i2c_WD_disable(self, adr=-1):
        ''' Function to disable i2c watchdog on one or all ArdBox boards '''
        #Calls the _i2c_WD_disable function
        self._i2c_WD_disable(adr)

    def i2c_WD_enable(self, adr=-1):
        ''' Function to enable i2c watchdog on one or all ArdBox boards '''
        #Calls the _i2c_WD_enable function
        self._i2c_WD_enable(adr)

    def manual_loop_disable(self, adr=-1):
        ''' Function to disable manual loop on one or all ArdBox boards '''
        #Calls the _manual_loop_enable function
        self._manual_loop_disable(adr)

    def manual_loop_enable(self, loop_value, adr=-1):
        ''' Function to enable manual loop on one or all ArdBox boards '''
        #Calls the _manual_loop_enable function
        self._manual_loop_enable(loop_value, adr)

    def disableCRC(self, adr=-1):
        ''' Function to enable CRC on one or all ArdBox boards '''
        #Calls the _disableCRC function
        self._disableCRC(adr)
        ARDBOX_I2C_CRC = False
        __class__._CRC_disable_override = True

    def enableCRC(self, adr=-1):
        ''' Function to enable CRC on one or all ArdBox boards '''
        #Calls the _enableCRC function
        self._enableCRC(adr)
        __class__._CRC_disable_override = False

    def resetHW(self):
        log.debug("Reseting Ardbox modules through GPIO %d" % __class__._ARDBOX_GPIO_RESET)
        GPIO.setup(__class__._ARDBOX_GPIO_RESET, GPIO.OUT, initial=GPIO.LOW)
        time.sleep(1)
        GPIO.setup(__class__._ARDBOX_GPIO_RESET, GPIO.IN)
        time.sleep(10)

    def resetSW(self, adr=-1):

        command = __class__.ARDBOX_CTRL_RST

        if(adr == -1):
            #Will software reset all connected ArdBox modules
                for (adr,reste) in self.boards:
                    retry = 3
                    while retry!=0:
                      try:
                      
                       with __class__.i2cbuslock:

                            #We create a list containing all the values needed for the CRC8 calculation
                            CRC_list = [adr, __class__.ARDBOX_CTRL_REG, __class__.ARDBOX_CTRL_RST]
                            #We create a list containing all the data to send via i2c
                            fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                            #We write our block of data to register 0
                            data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

                      except IOError as ex:
                            with self._lock:
                                self._i2c_errors += 1
                            retry -= 1
                            if retry == 0:
                                log.error("Error while performing software reset ... " + str(ex));
                                raise
                            else:
                                log.debug("Warning: i2c[0x%02X] IOError while resetting ArdBox ... retrying" % (adr))
                      else:
                           # done :)
                           retry=0

                           log.debug("Ardbox reset!")
        else:
          retry = 3
          while retry!=0:
            try:
                # we use the register field for the command, and we just send the command (digital value included within command :) )
                with __class__.i2cbuslock:

                     #We create a list containing all the values needed for the CRC8 calculation
                     CRC_list = [adr, __class__.ARDBOX_CTRL_REG, ARDBOX_CTRL_RST]
                     #We create a list containing all the data to send via i2c
                     fullDataList = [command, int(crc8.crc8(bytes(CRC_list)).hexdigest(), 16)]
                     #We write our block of data to register 0
                     data = self.i2c.write_i2c_block_data(adr, __class__.ARDBOX_CTRL_REG, fullDataList)

            except IOError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while performing software reset ... " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while resetting ArdBox ... retrying" % (adr))
            else:
                # done :)
                retry=0

                log.debug("Ardbox reset!")
        log.debug("Waiting 10 seconds for the Ardbox modules to come back up...")
        time.sleep(10)
        return True  


    def digital_write(self, pin, value):
        ''' Function to write a value to a digital output. First, we need to select
            proper board according to pin number. '''
        # is pin in our range of inputs ?
        if ( pin < 0 ) or ( pin >= self._nboutputs):
            log.error("outputPin %d not in our list [0 .. %d]" % (pin,self._nboutputs) )
            raise Exception("pin not in range of our Ardbox board(s)")
        # let's parse all boards to find proper one according to its inputs range
        for (i,nb) in enumerate(self._outputs):
            if (pin >= nb):
                #log.debug("current board [%d] features %d outputs >= %d output wanted ... next one" % (i, nb, pin))
                pin -= nb
            else:
                self._digital_write(self.boards[i][0],pin,value)
                log.debug("[board 0x%02X] write outputPin %d with value=%d" % (self.boards[i][0],pin,value))
                return True
        # not found :(
        log.error("unknown error while digital_write to an Ardbox board !?")
        raise Exception("unknown error while digital_write to an Ardbox board !?")


    # Digital bulk read --> [ (inputs 1st Ardbox), (inputs 2th Ardbox) ... ]
    def digital_bread(self):
        ''' Read ALL digital inputs from ALL ardbox modules through I2C bus '''
        _data = list()
        for _i2c,_ in self.boards:
            _data.append( self._digital_bread(_i2c) )
        return _data


    # Set callback for specified digital inputs. inputsList = [ 0, 3, ... ]
    # Note that inputsList may either be a list or a single pin number
    def digital_read_callback(self, inputsList, callback, pin_iostart=0):
        ''' Callback for digital inputs '''
        if callable(callback) is not True:
            log.error("provided callback function is not callable ?!?! ... rejecting")
            return
        if isinstance(inputsList,list) is not True:
            _inputsList = [ inputsList ]
        else:
            _inputsList = inputsList
        # check input is in our range
        if max(_inputsList) >= self._nbinputs:
            log.error("inputsList=%s with at least one pin not in our list [0 .. %d]" % (str(_inputsList),self._nbinputs-1) )
            raise Exception("pin(s) not in range of our Ardbox board(s)")

        # ok, now check if this is first time register self._digital_read_callback ?
        _register_ardbox_callback = False
        with self._lock:
            # memorise current backend global pin offset
            if self._backend_pin_offset==-1:
                self._backend_pin_offset = pin_iostart
            if not self._callbacks:
                _register_ardbox_callback = True

            try:
                # add inputs to watch to callback list
                self._callbacks[callback].extend(_inputsList)
            except KeyError as ex:
                # create callback list of inputs
                self._callbacks[callback] = _inputsList

            log.debug("Ardbox _callbacks dict = %s" % str(self._callbacks))

            # start ardbox's _digital_read_callback ?
            if _register_ardbox_callback is not False:
                log.debug("... and set Ardbox's low-level callback upon digital events ...")
                GPIO.add_event_detect( __class__._ARDBOX_GPIO_EVENT, GPIO.RISING, callback=self._digital_read_callback )
                # 1st time bulk read of all inputs
                self._digital_inputs = self.digital_bread()


    # Cancel callback for specified digital inputs. inputsList = [ 0, 3, ... ]
    def cancel_digital_read_callback(self, inputsList):
        ''' Cancel callback that was previously set for digital inputs '''
        if isinstance(inputsList,list) is not True:
            _inputsList = [ inputsList ]
        else:
            _inputsList = inputsList

        # check input is in our range
        if max(_inputsList) >= self._nbinputs:
            log.error("inputsList=%s with at least one pin not in our list [0 .. %d]" % (str(_inputsList),self._nbinputs-1) )
            raise Exception("pin(s) not in range of our Ardbox board(s)")
        
        # find callback to cancel
        with self._lock:
            _callbacksKeys2delete = list()
            for _func,_inputs2watch in self._callbacks.items():
                # compute lists intersection
                _inputs2remove = list(set(_inputs2watch) & set(_inputsList))
                if len(_inputs2remove) == 0:
                    continue
                # ok we'll remove inputs
                for _pin in _inputs2remove:
                    self._callbacks[_func].remove(_pin)
                if len(self._callbacks[_func]) == 0:
                    _callbacksKeys2delete.append(_func)

            # ... and now delete specified _callbacks keys
            if len(_callbacksKeys2delete)!=0:
                # map does not work here ?!?! ... maybe because key is a function ...
                #map(self._callbacks.pop,_callbacksKeys2delete)
                for _key in _callbacksKeys2delete:
                    self._callbacks.pop(_key)

            log.debug("Ardbox _callbacks dict = %s" % str(self._callbacks))

            # if no more inputs to watch ... de-register ardbox's low-level callback
            if not self._callbacks:
                log.debug("... unset Ardbox's low-level callback because of no more inputs to look after ...")
                GPIO.remove_event_detect( __class__._ARDBOX_GPIO_EVENT )
                #GPIO.cleanup()


    # Note: at least one digital_read per digital input to properly set tham as digital inputs in Ardbox boards
    # (Done at Digital module init)
    def digital_read(self, pin):
        ''' Function to read a value from a digital input. First, we need to select
            proper board according to pin number. '''
        # is pin in our range of inputs ?
        if ( pin < 0 ) or ( pin >= self._nbinputs):
            log.error("inputPin %d not in our list [0 .. %d]" % (pin,self._nbinputs-1) )
            raise Exception("pin not in range of our Ardbox board(s)")
        # let's parse all boards to find proper one according to its inputs range
        for (i,nb) in enumerate(self._inputs):
            if (pin >= nb):
                #log.debug("current board [%d] features %d inputs >= %d input wanted ... next one" % (i, nb, pin))
                pin -= nb
            else:
                _value = self._digital_read(self.boards[i][0],pin)
                value = bool(_value)
                log.debug("[board 0x%02X] read inputPin %d (raw value=%d) = %d" % (self.boards[i][0],pin,_value,value))
                return value
        # not found :(
        log.error("unknown error while digital_read from an Ardbox board !?")
        raise Exception("unknown error while digital_read from an Ardbox board !?")
        

    def analog_read(self, pin, min_value, max_value):
        ''' Function to read an analog input from an Ardbox board. '''
        # is pin in our range of inputs ?
        if ( pin < 0 ) or ( pin >= self._nbinputs):
            log.error("inputPin %d not in our list [0 .. %d]" % (pin,self._nbinputs-1) )
            raise Exception("pin not in range of our Ardbox board(s)")
        # let's parse all boards to find proper one according to its inputs range
        for (i,nb) in enumerate(self._inputs):
            if (pin >= nb):
                #log.debug("current board [%d] features %d inputs >= %d input wanted ... next one" % (i, nb, pin))
                pin -= nb
            else:
                _value = self._analog_read(self.boards[i][0],pin)
                fvalue = float( _value * float(max_value - min_value) / (__class__._ANALOG_READ_MAX - 1) ) + min_value
                log.debug("[board 0x%02X] read inputPin %d (raw value=%d) = %.2f" % (self.boards[i][0],pin,_value,fvalue))
                return fvalue
        # not found :(
        log.error("unknown error while analog_read from an Ardbox board !?")
        raise Exception("unknown error while analog_read from an Ardbox board !?")


    def analog_write(self, pin, value, min_value, max_value):
        ''' Function to write a value to an analog output. First, we need to select
            proper board according to pin number. '''
        #TODO
        raise Exception("not yet implemented :|")



# #############################################################################
#
# MAIN
#

def main():
    '''Call the various functions'''

    # debug mode
    import logging
    from logger import setLogLevel
    setLogLevel(logging.DEBUG)

    print("\nNote: pins used in this test are related to Ardbox_11d7 concentrator")

    # instantiate
    print("\nInstantiate ArdboxIO backend ...")
    b = ArdboxIO()

    # get status
    print("\nRetrieve ArdboxIO backend status ...")
    print(b.status())

    #Test software reset on all connected modules
    print("\nTesting software reset ...")
    b.resetSW()

    #Test enable CRC on all connected modules
    print("\nTesting CRC enable ...")
    b.enableCRC()
    time.sleep(3)

    #Test disable CRC on all connected modules
    print("\nTesting CRC disable ...")
    b.disableCRC()
    time.sleep(3)

    #Testing a digital read without CRC
    print("\nTesting that a digital read works without CRC ...")
    pin=2;  # IR sensor
    print("\ndigital_read( pin=%d ) = %d" % (pin,b.digital_read(pin-1)) )
    time.sleep(3)

    #Reenable CRC on all connected modules
    print("\nReenabling CRC on all connected modules after last test ...")
    b.enableCRC()
    time.sleep(3)

    #Test manual loop enable on all connected modules, setting 3 -> 1s
    print("\nTesting manual loop enable ( 1s ) ...")
    b.manual_loop_enable(3)
    time.sleep(3)
    
    #Test manual loop enable on all connected modules, setting 2 -> 500ms                                  
    print("\nTesting manual loop enable ( 500ms ) ...")                                                    
    b.manual_loop_enable(2)                                                                                
    time.sleep(3)

    #Test manual loop enable on all connected modules, setting 1 -> 250ms                                  
    print("\nTesting manual loop enable ( 250ms ) ...")                                                        
    b.manual_loop_enable(1)                                                     
    time.sleep(3)

    #Test manual loop enable on all connected modules, setting 0 -> 100ms  
    print("\nTesting manual loop enable ( 100ms ) ...")      
    b.manual_loop_enable(0)  
    time.sleep(3)
    
    #Test manual loop disable on all connected modules
    print("\nTesting manual loop disable ...")
    b.manual_loop_disable()
    time.sleep(3)

    #Test i2c watchdog disable on all connected modules
    print("\nTesting i2c watchdog disable ...")
    b.i2c_WD_disable()
    time.sleep(3)

    #Test i2c watchdog enable on all connected modules
    print("\nTesting i2c watchdog enable ...")
    b.i2c_WD_enable()
    time.sleep(3)

    # analog_read: lux sensor 0 --> 1000 lux
    # WARNING: when reading an analog_value, an invalid data is sent back on the first call
    # due to the integration processus
    pin=3
    min_val=0
    max_val=1000
    print("\nanalog_read( pin=%d, min=%d, max=%d ) ..." % (pin,min_val,max_val))
    try:
        # Note: pin starts at 0
        # first call to configure pin as an analog input
        b.analog_read( pin-1, min_val, max_val )
    except Exception as ex:
        pass
    time.sleep(4)
    print(b.analog_read( pin-1, min_val, max_val ))

    time.sleep(0.5)

    # Digital bulk read
    print("Digital_bread() = " + str(b.digital_bread()) )

    time.sleep(0.5)

    #digital_write(1)=1
    pin=1
    print("\ndigital_write( pin=%d ) = 1 ..." % pin )
    #Note: pin starts at 0!
    b.digital_write( pin-1, 1 )
    time.sleep(0.5)
    #digital_write(1)=0
    print("\ndigital_write( pin=%d ) = 0 ..." % pin )
    #Note: pin starts at 0!
    b.digital_write( pin-1, 0 )

    time.sleep(0.5)

    # digital_read
    for i in range(3):
        # Note: pin starts at 0!
        pin=2;  # IR sensor
        print("\ndigital_read( pin=%d ) = %d" % (pin,b.digital_read(pin-1)) )
        pin=3;  # button
        print("\ndigital_read( pin=%d ) = %d" % (pin,b.digital_read(pin-1)) )
        time.sleep(0.5)


# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

