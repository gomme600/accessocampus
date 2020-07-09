#!/usr/bin/env python3
# coding: utf-8
#
# ArdboxIO backend release v2.2
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
# [Oct.19] S.Lucas      switch to smbus2
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
from smbus2 import SMBus, i2c_msg

# extend Python's library search path
import os
import sys
# Helpers and i2c functions import
_path2add='../libutils'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from HelpersFunc import *

# sensOCampus
_path2add='../sensocampus'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from settings import ARDBOX_I2C_PEC, ARDBOX_I2C_CRC, ARDBOX_EXPECT_PRGM_MAJOR, ARDBOX_EXPECT_PRGM_MINOR
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
    ARDBOX_CTRL_REG         = 0     # Settings (i.e control) register of Ardbox module (e.g enable/disable CRC, loop value etc)
    ARDBOX_CMD_REG          = 1     # Command register (i.e read_digital, write_analog, getID ...)

    # Ardbox CMD register bits
    ARDBOX_CMD_READ         = 1 << 7    # bit7: (1, read) (0, write)
    ARDBOX_CMD_WRITE        = 0 << 7
    ARDBOX_CMD_DIGITAL      = 1 << 6    # bit6: (1, digital) (0, analog)
    ARDBOX_CMD_ANALOG       = 0 << 6
    ARDBOX_CMD_ID           = 1 << 5    # bit5: (1: ID related op) (0, regular op)
    ARDBOX_CMD_REGULAR      = 0 << 5
    # bit4: if [READ operation]
    # Note: Bulk Read only applies to digital inputs
    ARDBOX_CMD_BR           = 1 << 4    # bit4: (1: Bulk Read ---all digital inputs) (0, Regular Read of input specified in bits[3..0]
    ARDBOX_CMD_RR           = 0 << 4
    # bit4: if [WRITE operation]
    ARDBOX_CMD_DV           = 4     # bit4: digital value to write (0 or 1) of output specified in bits[3..0]
    # bit[3..0]: specifiy input or output
    ARDBOX_CMD_IOBITS       = 0x0F  # bits[3..0]

    # Ardbox SETTINGS register bits
    ARDBOX_CTRL_CRC         = 1 << 7    # bit7: i2c CRC (1:enable) (0:disable) Default: enabled
    ARDBOX_CTRL_RST         = 1 << 6    # bit6: (1, activate software reset)
    ARDBOX_CTRL_BIT5        = 1 << 5    # bit5: free to use
    ARDBOX_CTRL_I2C_WD_DIS  = 1 << 4    # bit4: i2c watchdog disable (1:disabled) (0:enabled) Default: enabled
    ARDBOX_CTRL_BIT3        = 1 << 3    # bit3: free to use
    ARDBOX_CTRL_LOOP_MASK   = 0x07      # bits 2..0
    ARDBOX_CTRL_LOOP_NOP    = 0x00      # no change to existing loop_delay value
    ARDBOX_CTRL_LOOP_125MS  = 0x01
    ARDBOX_CTRL_LOOP_250MS  = 0x02
    ARDBOX_CTRL_LOOP_500MS  = 0x03
    ARDBOX_CTRL_LOOP_1S     = 0x04

    # Ardbox general settings
    _SIZEOF_CTRL_REG        = 1     # nb bytes used to get/set control register
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

    i2c_crc_enabled = True      # as a default, CRC8 is enabled on all Ardbox20 at startup

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
            # [oct.19] default i2c bus is 1 ;)
            self.i2c = SMBus(self.i2cbus if self.i2cbus >= 0 else 1)
            if ARDBOX_I2C_PEC is True:
                raise Exception("i2c PEC not supported so far !")
                # Firmware >= 1.7, activate smbus PEC (packet error checking) CRC8
                #self.i2c.pec = True
                #log.info("Ardbox's I2C PEC activated ...");
            if ARDBOX_I2C_CRC is not True:
                raise Exception("i2c CRC is mandatory ! ... at least at startup ...")
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

        # Ardbox dedicated event pin
        log.debug("Setup Ardbox's event GPIO %d" % __class__._ARDBOX_GPIO_EVENT)
        GPIO.setup(__class__._ARDBOX_GPIO_EVENT, GPIO.IN)


    def detect(self):
        ''' Automated detection of Ardbox modules '''
        log.debug("Start searching for Ardbox boards ... ")
        _boards = list()

        # because original RPi lack the expected GPIO count
        if( GPIO.RPI_REVISION <= 2 ):
            log.warning("Ardbox does not has support for original RPi ... sorry")
            return None

        # scan i2c bus and try to match against possible i2c addr of modules
        #TODO: scan all i2c buses
        addresses = []
        # scan and intersect ...
        addresses = list(set(__class__._I2C_ADDRS) & set(i2cScan(self.i2cbus)))
        if len(addresses)==0:
            print("no devices addresses available ?!?! ... :|")
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
                    log.debug("i2c device 0x%02X is not an Ardbox board, continuing" % adr);
                    continue;
            except Exception as ex:
                log.debug("Ardbox [0x%X] raised an exception: " % adr + str(ex))
                continue

            # board detected ... but is it the correct FW ?
            _prgm_ok = True
            if( boardEEPROM[__class__.EEPROM_PRGM_MAJOR] < ARDBOX_EXPECT_PRGM_MAJOR ):
                _prgm_ok = False
            elif( boardEEPROM[__class__.EEPROM_PRGM_MAJOR] == ARDBOX_EXPECT_PRGM_MAJOR and
                boardEEPROM[__class__.EEPROM_PRGM_MINOR] < ARDBOX_EXPECT_PRGM_MINOR ):
                _prgm_ok = False
            if( _prgm_ok is not True ):
                log.warning("ARDBOX [0x%02X] firmware '%d.%d' is lower than '%d.%d' expected ... aborting :|" %
                            (adr,boardEEPROM[__class__.EEPROM_PRGM_MAJOR],boardEEPROM[__class__.EEPROM_PRGM_MINOR],
                             ARDBOX_EXPECT_PRGM_MAJOR,ARDBOX_EXPECT_PRGM_MINOR) )
                return None

            # ok, add Ardbox :)
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


    def status(self):
        '''send back maximum number of inputs / outputs'''
        return self._nbinputs, self._nboutputs


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
    # - _setConfigRegister()
    #

    def _getID(self, adr):
        ''' retrieve Ardbox board identity informations (EEPROM) '''
        command = __class__.ARDBOX_CMD_READ | __class__.ARDBOX_CMD_ID

        retry = 3
        while retry!=0:
            try:
                # we read up to EEPROM_ADDR_LAST bytes
                with __class__.i2cbuslock:
                    # compose i2c request
                    _frame = [adr, __class__.ARDBOX_CMD_REG, command]
                    if( self.i2c_crc_enabled is True):
                        # add CRC8 byte
                        _frame.append( int(crc8.crc8(bytes(_frame)).hexdigest(), 16) )
                    # prepare smbus2 transaction
                    _msg2write = i2c_msg.write(_frame[0],_frame[1:])
                    _msg2read = i2c_msg.read(_frame[0],__class__.EEPROM_ADDR_LAST+1)    # EEPROM size + 1 for optional CRC
                    self.i2c.i2c_rdwr( _msg2write, _msg2read )
                    # retrieve data ...
                    data = list(_msg2read)

                    if( self.i2c_crc_enabled is True ):
                        # check CRC is valid
                        if( data[__class__.EEPROM_ADDR_LAST] != int(crc8.crc8(bytes(data[:__class__.EEPROM_ADDR_LAST])).hexdigest(),16) ):
                            raise Exception("CRC failed!")

            except (IOError, Exception) as ex:
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

        log.info("EEPROM ID Ardbox[0x%02X] = %s" % (adr,str(data)));
        return data[:__class__.EEPROM_ADDR_LAST]


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

                # generate list of tuples for those upon an event has been detected = [ (pin, new_value), (pin, new_value) ... ]
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

                # end of iteration ... do we need to restart a whole data acquisition ?
                # ... it depends whether the GPIO event line is still LOW !
                # TODO: if input 5 change just during return from callback call ... no GPIO.FALLING will be seen and you're stuck!
                if GPIO.input(channel) == GPIO.LOW:
                    log.debug("GPIO_event pin still LOW at the end of callback ... new events need to get processed then!")
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
                    # compose i2c request
                    _frame = [adr, __class__.ARDBOX_CMD_REG, command]
                    if( self.i2c_crc_enabled is True):
                        # add CRC8 byte
                        _frame.append( int(crc8.crc8(bytes(_frame)).hexdigest(), 16) )
                    # prepare smbus2 transaction
                    _msg2write = i2c_msg.write(_frame[0],_frame[1:])
                    self.i2c.i2c_rdwr( _msg2write )

            except (IOError, Exception) as ex:
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
                    # compose i2c request
                    _frame = [adr, __class__.ARDBOX_CMD_REG, command]
                    if( self.i2c_crc_enabled is True):
                        # add CRC8 byte
                        _frame.append( int(crc8.crc8(bytes(_frame)).hexdigest(), 16) )
                    # prepare smbus2 transaction
                    _msg2write = i2c_msg.write(_frame[0],_frame[1:])
                    _msg2read = i2c_msg.read(_frame[0],__class__._SIZEOF_DIGITAL_BREAD+1)   # byte(s) to read along with optional CRC
                    self.i2c.i2c_rdwr( _msg2write, _msg2read )
                    # retrieve data ...
                    data = list(_msg2read)

                    if( self.i2c_crc_enabled is True ):
                        # check CRC is valid
                        if( data[__class__._SIZEOF_DIGITAL_BREAD] != int(crc8.crc8(bytes(data[:__class__._SIZEOF_DIGITAL_BREAD])).hexdigest(),16) ):
                            raise Exception("CRC failed!")

                # now process received (and optionnaly validated) data ...
                _data = int()
                if __class__._SIZEOF_DIGITAL_BREAD == 1:
                    _data = data[0]
                elif __class__._SIZEOF_DIGITAL_BREAD == 2:
                    _data = data[0] | (data[1] << 8)
                elif __class__._SIZEOF_DIGITAL_BREAD == 4:
                    _data = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
                else:
                    raise ValueError("Wrong size of digital_bread data :|")

            except ValueError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_bread : " + str(ex));
                    raise
                else:
                    log.warning("Warning: i2c[0x%02X] ValueError while digital_bread ... retrying" % (adr))

            except (IOError, Exception) as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_bread ... "  + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while digital_bread ... retrying" % (adr))

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
                    # compose i2c request
                    _frame = [adr, __class__.ARDBOX_CMD_REG, command]
                    if( self.i2c_crc_enabled is True):
                        # add CRC8 byte
                        _frame.append( int(crc8.crc8(bytes(_frame)).hexdigest(), 16) )
                    # prepare smbus2 transaction
                    _msg2write = i2c_msg.write(_frame[0],_frame[1:])
                    _msg2read = i2c_msg.read(_frame[0],__class__._SIZEOF_DIGITAL_READ+1)   # byte(s) to read along with optional CRC
                    self.i2c.i2c_rdwr( _msg2write, _msg2read )
                    # retrieve data ...
                    data = list(_msg2read)

                    if( self.i2c_crc_enabled is True ):
                        # check CRC is valid
                        if( data[__class__._SIZEOF_DIGITAL_READ] != int(crc8.crc8(bytes(data[:__class__._SIZEOF_DIGITAL_READ])).hexdigest(),16) ):
                            raise Exception("CRC failed!")

                # now process received (and optionnaly validated) data ...
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

            except ValueError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_read[pin=%d] : " % (pin) + str(ex));
                    raise
                else:
                    log.warning("Warning: i2c[0x%02X] ValueError while digital_read[pin=%d] ... retrying" % (adr,pin))

            except (IOError, Exception) as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while digital_read[pin=%d] ... " % (pin) + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while digital_read[pin=%d] ... retrying" % (adr,pin))

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
                    # compose i2c request
                    _frame = [adr, __class__.ARDBOX_CMD_REG, command]
                    if( self.i2c_crc_enabled is True):
                        # add CRC8 byte
                        _frame.append( int(crc8.crc8(bytes(_frame)).hexdigest(), 16) )
                    # prepare smbus2 transaction
                    _msg2write = i2c_msg.write(_frame[0],_frame[1:])
                    _msg2read = i2c_msg.read(_frame[0],__class__._SIZEOF_ANALOG_READ+1)   # byte(s) to read along with optional CRC
                    self.i2c.i2c_rdwr( _msg2write, _msg2read )
                    # retrieve data ...
                    data = list(_msg2read)

                    if( self.i2c_crc_enabled is True ):
                        # check CRC is valid
                        if( data[__class__._SIZEOF_ANALOG_READ] != int(crc8.crc8(bytes(data[:__class__._SIZEOF_ANALOG_READ])).hexdigest(),16) ):
                            raise Exception("CRC failed!")

                # recreate value from MSB, LSB
                _data = int()

                if __class__._SIZEOF_ANALOG_READ == 1:
                    _data = data[0]
                elif __class__._SIZEOF_ANALOG_READ == 2:
                    _data = data[0] | (data[1] << 8)
                elif __class__._SIZEOF_ANALOG_READ == 4:
                    _data = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
                else:
                    raise Exception("Wrong size of analog_read data :|")

                if( _data < 0 or _data >= __class__._ANALOG_READ_MAX):
                    raise ValueError("analog_read=%d is out of range [0..%d]" % (_data,__class__._ANALOG_READ_MAX-1) )

            except ValueError as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while analog_read[pin=%d] : " % (pin) + str(ex));
                    raise
                else:
                    log.warning("Warning: i2c[0x%02X] ValueError while analog_read[pin=%d] ... retrying" % (adr,pin))

            except (IOError, Exception) as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while analog_read[pin=%d] ... " % (pin) + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while analog_read[pin=%d] ... retrying" % (adr,pin))
            else:
                # done :)
                retry=0

        #log.debug("[0x%02X] analog_read(%d) = " % (adr,pin) + str(_data))
        return _data


    def _getConfigRegister(self, adr):
        ''' retrieve Ardbox board config/control register '''
        retry = 3
        while retry!=0:
            try:
                # we'll read the config register (or settings register) byte
                with __class__.i2cbuslock:
                    # compose i2c request
                    _frame = [adr, __class__.ARDBOX_CTRL_REG]
                    if( self.i2c_crc_enabled is True):
                        # add CRC8 byte
                        _frame.append( int(crc8.crc8(bytes(_frame)).hexdigest(), 16) )
                    # prepare smbus2 transaction
                    _msg2write = i2c_msg.write(_frame[0],_frame[1:])
                    _msg2read = i2c_msg.read(_frame[0],__class__._SIZEOF_CTRL_REG+1)   # byte(s) to read along with optional CRC
                    self.i2c.i2c_rdwr( _msg2write, _msg2read )
                    # retrieve data ...
                    data = list(_msg2read)

                    if( self.i2c_crc_enabled is True ):
                        # check CRC is valid
                        if( data[__class__._SIZEOF_CTRL_REG] != int(crc8.crc8(bytes(data[:__class__._SIZEOF_CTRL_REG])).hexdigest(),16) ):
                            raise Exception("CRC failed!")

            except (IOError, Exception) as ex:
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

        log.debug("Config/control register Ardbox[0x%02X] = 0x%02X" % (adr,data[0]));
        return data[0]


    def _setConfigRegister(self, adr, val):
        ''' write Ardbox board config/control register '''
        retry = 3
        while retry!=0:
            try:
                # we'll write the Setting/Control/Config register byte
                with __class__.i2cbuslock:
                    # compose i2c request
                    _frame = [adr, __class__.ARDBOX_CTRL_REG, int(val)]
                    if( self.i2c_crc_enabled is True):
                        # add CRC8 byte
                        _frame.append( int(crc8.crc8(bytes(_frame)).hexdigest(), 16) )
                    # prepare smbus2 transaction
                    _msg2write = i2c_msg.write(_frame[0],_frame[1:])
                    self.i2c.i2c_rdwr( _msg2write )

            except (IOError, Exception) as ex:
                with self._lock:
                    self._i2c_errors += 1
                retry -= 1
                if retry == 0:
                    log.error("Error while writing config register ... " + str(ex));
                    raise
                else:
                    log.debug("Warning: i2c[0x%02X] IOError while writing config register ... retrying" % (adr))
            else:
                # done :)
                retry=0

        log.debug("Config/control register Ardbox[0x%02X] = 0x%02X" % (adr,val));
        return True



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
    # - setLoopDelay()
    # - getLoopDelay()
    # - i2c_WD_enable()
    # - i2c_WD_disable()


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
                # [oct.19] switch to FALLING event
                GPIO.add_event_detect( __class__._ARDBOX_GPIO_EVENT, GPIO.FALLING, callback=self._digital_read_callback )
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


    def resetHW(self):
        ''' Ardbox Hardware reset through dedicated GPIO '''
        log.debug("Reseting Ardbox modules through GPIO %d" % __class__._ARDBOX_GPIO_RESET)

        # [oct.19] check for RPi revision
        # because original RPi lack the expected GPIO count
        if( GPIO.RPI_REVISION <= 2 ):
            log.warning("Ardbox does not has support for original RPi ... sorry")
            return

        # let's reset :)
        GPIO.setup(__class__._ARDBOX_GPIO_RESET, GPIO.OUT, initial=GPIO.LOW)
        time.sleep(1)
        GPIO.setup(__class__._ARDBOX_GPIO_RESET, GPIO.IN)
        time.sleep(20)  # for newer Ardbox (bootloader that takes longer to start)


    def resetSW(self, adr=None):
        ''' Ardbox Software reset through SETTINGS register
            Applies to ALL of the registered Ardbox unless specified '''

        # check arguments
        if( adr is not None and isinstance(adr,int) is not True ):
            log.error("adr to be an integer !")
            return

        # build command byte
        command = __class__.ARDBOX_CTRL_RST | __class__.ARDBOX_CTRL_LOOP_NOP
        if( self.i2c_crc_enabled is True ):
            command |= __class__.ARDBOX_CTRL_CRC

        _success=0
        # Parse all registered ArdBox modules
        for target,_ in self.boards:
            if( adr is None or target==adr ):
                try:
                    # software reset ...
                    _ret = self._setConfigRegister( target, command )
                    if( _ret is True ):
                        _success+=1
                        log.info("[0x%02X] Software reset sent to Ardbox ..." % target)
                except Exception as ex:
                    log.debug("Failed to soft reset Ardbox [0x%02X], continuing" % target)

                # did we found the requested Ardbox module ?
                if( target==adr ): break

        if( _success==0 ):
            log.warning("unable to soft reset even a single Ardbox module ?!?!")
            return False

        log.debug("%d Ardbox have been soft reset" % _success)
        log.debug("Waiting 10 seconds for the Ardbox modules to come back up...")
        time.sleep(10)
        return True  


    def setLoopDelay(self, loop_delay_ms, adr=None):
        ''' Function to disable manual loop on one or all ArdBox boards '''

        # check arguments
        if( isinstance(loop_delay_ms,int) is not True ):
            log.error("loop_delay_ms ought to be an integer !")
            return
        if( adr is not None and isinstance(adr,int) is not True ):
            log.error("adr to be an integer !")
            return

        # compute loopDelayIdx
        loopDelayIdx = __class__.ARDBOX_CTRL_LOOP_NOP

        if( int(loop_delay_ms) < 125 ):
            log.warning("unsupported loop_delay_ms '%s'" % str(loop_delay_ms))
            return
        elif( int(loop_delay_ms) < 250 ):
            loopDelayIdx = __class__.ARDBOX_CTRL_LOOP_125MS
        elif( int(loop_delay_ms) < 500 ):
            loopDelayIdx = __class__.ARDBOX_CTRL_LOOP_250MS
        elif( int(loop_delay_ms) < 1000 ):
            loopDelayIdx = __class__.ARDBOX_CTRL_LOOP_500MS
        elif( int(loop_delay_ms) == 1000 ):
            loopDelayIdx = __class__.ARDBOX_CTRL_LOOP_1S
        else:
            log.warning("unsupported loop_delay_ms '%s'" % str(loop_delay_ms))
            return

        # check for an idx that matches ...
        if( loopDelayIdx == __class__.ARDBOX_CTRL_LOOP_NOP ):
            log.warning("unable to compute a loopDelayIdx for specified loop_delay_ms '%s'" % str(loop_delay_ms))
            return

        # Parse all registered ArdBox modules
        for target,_ in self.boards:
            if( adr is None or target==adr ):
                try:
                    # retrieve current control/settings register value
                    cur_settings = self._getConfigRegister( target )

                    # compute command
                    new_settings = (cur_settings&~__class__.ARDBOX_CTRL_LOOP_MASK) | loopDelayIdx

                    # apply new settings
                    self._setConfigRegister( target, new_settings )

                except (Exception,IOError) as ex:
                    log.error("[0x%02X] unable to set loop_delay :(" % target )

                # did we found the requested Ardbox module ?
                if( target==adr ): break

        # end


    def getLoopDelay(self, adr=None):
        ''' Function to retrieve loop_delay from one or all ArdBox boards
            return a list [ (i2c_adr,loop_delay_ms), ... ] '''
        res=list()
        # Parse all registered ArdBox modules
        for target,_ in self.boards:
            if( adr is None or target==adr ):
                try:
                    loop_delay_idx = self._getConfigRegister( target )&__class__.ARDBOX_CTRL_LOOP_MASK

                    if( loop_delay_idx <= __class__.ARDBOX_CTRL_LOOP_NOP ):
                        log.error("[0x%02X] ArdBox loop delay '0x%02X' is out-of-range ..." % (target,loop_delay_idx))
                    elif( loop_delay_idx == __class__.ARDBOX_CTRL_LOOP_125MS ):
                        res.append((target,"125ms"))
                    elif( loop_delay_idx == __class__.ARDBOX_CTRL_LOOP_250MS ):
                        res.append((target,"250ms"))
                    elif( loop_delay_idx == __class__.ARDBOX_CTRL_LOOP_500MS ):
                        res.append((target,"500ms"))
                    elif( loop_delay_idx == __class__.ARDBOX_CTRL_LOOP_1S ):
                        res.append((target,"1s"))
                    elif( loop_delay_idx > __class__.ARDBOX_CTRL_LOOP_1S ):
                        log.error("[0x%02X] ArdBox loop delay '0x%02X' is out-of-range ..." % (target,loop_delay_idx))
                except Exception as ex:
                    log.error("Failed to soft reset Ardbox [0x%02X], continuing" % adr)

                # did we found the requested Ardbox module ?
                if( target==adr ): break

        # return list of tuples (ardbox_i2c_adr, loop_delay)
        return res 


    def disableCRC(self):
        ''' Function to disable I2C CRC on ALL ArdBox boards '''
        raise Exception("not yet implemented!")
        #self.self.i2c_crc_enabled = False


    def enableCRC(self):
        ''' Function to enable I2C CRC on ALL ArdBox boards '''
        raise Exception("not yet implemented!")
        #self.self.i2c_crc_enabled = True



# #############################################################################
#
# MAIN
#

def main():
    ''' Call the various functions
        Notes:
        - read analog values at first (default are digital inputs)
    '''

    # debug mode
    import logging
    from logger import setLogLevel
    setLogLevel(logging.DEBUG)

    print("\nNote: pins used in this test are related to Ardbox-089e concentrator")
    # Ardbox-089e (1,digital,BP), (2,digital,IR), (3,analog,lux)
    # Ardbox-11d7 (1,analog,lux), (2,digital,IR), (3,digital,BP), (4,analog,temp)

    # instantiate
    print("\nInstantiate ArdboxIO backend ...")
    b = ArdboxIO()
    time.sleep(0.5)

    # get status
    print("\nRetrieve ArdboxIO backend status ...")
    print(b.status())
    time.sleep(0.5)

    # loop_delay
    print("\nLoop_delay: display default value(s)")
    print(b.getLoopDelay())
    time.sleep(0.5)
    print("\nLoop_delay: change to 1s")
    b.setLoopDelay( loop_delay_ms=1000 )
    time.sleep(0.5)
    print("\nLoop_delay: get current value(s)")
    print(b.getLoopDelay())
    time.sleep(0.5)

    # Software reset
    print("\nArdbox software reset ...")
    b.resetSW()
    time.sleep(0.5)

    print("\nLoop_delay: current values")
    print(b.getLoopDelay())
    time.sleep(0.5)

    # analog_read: lux sensor 0 --> 1000 lux
    # Note: remember there's a 2s integration of analog inputs ...
    # hence, this FIRST analog read ought to fail !!
    pin=3
    min_val=0
    max_val=1000
    print("\nanalog_read( pin=%d, min=%d, max=%d ) ..." % (pin,min_val,max_val))
    try:
        # Note: pin starts at 0
        print(b.analog_read( pin-1, min_val, max_val ))
    except ValueError as ex:
        print("\nfirst analog_read usually fails, it's OK :)")
    else:
        print("\nfirst analog_read ought to fail due to the integration time ?!?!")
        raise Exception("undetermined behaviour: first analog_read ought to fail!")
    time.sleep(0.5)

    # Digital bulk read
    print("Digital_bread() = " + str(b.digital_bread()) )
    time.sleep(0.5)

    # digital_read
    pin=2;  # IR sensor
    print("\ndigital_read( pin=%d ) = %d" % (pin,b.digital_read(pin-1)) )
    pin=1;  # button
    print("\ndigital_read( pin=%d ) = %d" % (pin,b.digital_read(pin-1)) )
    time.sleep(0.5)

    # digital_write(1)=1
    pin=1
    print("\ndigital_write( pin=%d ) = 1 ..." % pin )
    # Note: pin starts at 0!
    b.digital_write( pin-1, 1 )
    time.sleep(0.5)
    # digital_write(1)=0
    print("\ndigital_write( pin=%d ) = 0 ..." % pin )
    # Note: pin starts at 0!
    b.digital_write( pin-1, 0 )
    time.sleep(0.5)

    # analog_read: lux sensor 0 --> 1000 lux
    # ... this time analog input has been integrated
    pin=3
    min_val=0
    max_val=1000
    print("\nanalog_read( pin=%d, min=%d, max=%d ) ..." % (pin,min_val,max_val))
    try:
        # Note: pin starts at 0
        print(b.analog_read( pin-1, min_val, max_val ))
    except ValueError as ex:
        print("\naie ... we're > integration_time regarding last analog_read ... it should have worker :|")
        raise Exception("undetermined behaviour: we're not supposed to receive out-of-range values (unless in-between reset)")
    except IOError as ex:
        # that's life ...
        pass
    time.sleep(0.5)


# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

