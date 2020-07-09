#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# RS-485 Modbus backend for neOCampus 'energy' module
#
# This backend is able to communicate with various energy meters like:
#   - countis E03
#   - ultrasonic flow meter Micronics U1000-HM
#   - SDM 120 (future)
#
# F.Thiebolt    sep.19  force speed after modbus instrument instanciation as it overrides link speed
# F.Thiebolt    jun.17  initial release
#



# #############################################################################
#
# Import zone
#
import errno
#import io
import os
import signal
import syslog
import sys
import threading

import time


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
from settings import MODBUS_DEBUG_LINK
from logger import log,getLogLevel


# Modbus imports
import serial
import minimalmodbus

# Modbus specific nodes imports

# check content of ./drivers/__init__.py variable 'ALL'
from .drivers import *
from .drivers.countis import Countis
#from .drivers.CountisE03 import CountisE03
#from .drivers.diris import Diris
from .drivers.micronicsU1000 import MicronicsU1000




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
class ModbusBackend(object):
    ''' RS-485 modbus backend '''

    # Class attributes
    DEFAULT_SERIAL_LINK     = "/dev/null"
    DEFAULT_SERIAL_SPEED    = 9600
    DEFAULT_SERIAL_BITS     = serial.EIGHTBITS
    DEFAULT_SERIAL_PARITY   = serial.PARITY_NONE
    DEFAULT_SERIAL_STOP     = serial.STOPBITS_ONE
    DEFAULT_SERIAL_TIMEOUT  = 0.8   # seconds

    DEFAULT_MODBUS_CLOSE_PORT_EACH_CALL = True	# minimalmodbus close port after each call


    # attributes
    _addons     = None      # sensOCampus kwargs parameters
    _link       = None      # device name (e.g /dev/ttyUSB1)
    _link_speed = 0
    instrument  = None      # modbus instrument
    serial_lock = None      # serial link locking: to protect against read and reset at the same time from different threads
    kwnodes     = None      # dictionnary of nodes addr with associated type (e.g kwnodes['68'] = "<object COUNTISE03>")


    # Initialization
    def __init__(self, link=None, link_speed=0, *args, **kwargs):

        log.debug("Start loading Modbus backend ...")
        self._addons        = None
        self.instrument     = None
        self.serial_lock    = None
        self.kwnodes        = None

        if kwargs is not None:
            self._addons = kwargs

        if link is None:
            # auto-detection of RS-485 adapters (future)
            # TODO!
            raise Exception("RS-485 link auto-detection not yet implemented :|")
        else:
            self._link = link
            try:
                self._link_speed = int(link_speed) if int(link_speed)!=0 else __class__.DEFAULT_SERIAL_SPEED
            except ValueError as ex:
                log.error("link_speed '%s' is not an integer ... aborting" % (str(link_speed)) )
                raise ex

        # check link to test presence of adapter
        # now check that this i2c device is really what we expect ...
        self.validate_link( self._link, self._link_speed )


    def validate_link(self, link, link_speed ):
        """ verify link is valid ... """
        try:
            _link = serial.Serial( port=link, baudrate=link_speed,
                                        bytesize=__class__.DEFAULT_SERIAL_BITS,
                                        parity=__class__.DEFAULT_SERIAL_PARITY,
                                        stopbits=__class__.DEFAULT_SERIAL_STOP,
                                        timeout=__class__.DEFAULT_SERIAL_TIMEOUT,
                                        exclusive=True )
            if _link.is_open is False:
                _link.open()
            _link.close()
        except Exception as ex:
            log.error("while opening serial port '%s' with baudrate=%d " % (link,link_speed) + str(ex))
            raise ex
        log.debug("link '%s' @ '%d'bauds is validated as a serial port :)" % (link,link_speed) )


    def status(self,msg):
        ''' Modbus backend status '''
        msg['link']         = self._link
        msg['link_speed']   = self._link_speed
        msg['nodes']        = [(k,v.ENERGY_METER_NAME) for k,v in self.kwnodes.items()]


    def enable(self, link=None, link_speed=0, link_timeout=float(0), *args, **kwargs):
        ''' activate modbus serial link '''
        # either a link has been automatically detected (or not) or a new one
        # is set here
        if link is not None:
            self._link = link
            try:
                self._link_speed = int(link_speed) if int(link_speed)!=0 else __class__.DEFAULT_SERIAL_SPEED
            except ValueError as ex:
                log.error("link_speed '%s' is not an integer ... aborting" % (str(link_speed)) )
                raise ex

            self.validate_link( self._link, self._link_speed )
            # at this point link is validated

        # set defaults to minimalModbus
        minimalmodbus.BAUDRATE  = self._link_speed
        minimalmodbus.PARITY    = serial.PARITY_NONE
        minimalmodbus.STOPBITS  = 1
        try:
            minimalmodbus.TIMEOUT = float(link_timeout) if float(link_timeout)!=float(0) else __class__.DEFAULT_SERIAL_TIMEOUT
        except ValueError as ex:
            log.error("link_timeout '%s' is not a float ... aborting" % (str(link_timeout)) )
            raise ex
        minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = __class__.DEFAULT_MODBUS_CLOSE_PORT_EACH_CALL

        # instantiate Instrument
        # Note: we set modbus node addr to 0
        self.instrument = minimalmodbus.Instrument( self._link, 0 )

        # [sep.19] upon instanciation of instrument, it overrides almost all parameters !
        self.instrument.serial.baudrate = self._link_speed

        try:
            self.instrument.serial.timeout = float(link_timeout) if float(link_timeout)!=float(0) else __class__.DEFAULT_SERIAL_TIMEOUT
        except ValueError as ex:
            log.error("link_timeout '%s' is not a float ... aborting" % (str(link_timeout)) )
            raise ex

        #TODO: find another way instead of a direct access to serial from minimalModbus
        self.instrument.serial.exclusive = True  # no one else can open our serial port. TODO: check it is useful

        # debug mode ?
        if getLogLevel().lower() == "debug" and MODBUS_DEBUG_LINK is True:
            log.debug("... and activating DEBUG level @ Modbus instrument ... ")
            self.instrument.debug = True

        log.debug(self.instrument)

        # initialise lock (to avoid simultaneaous access API from different threads)
        self.serial_lock = threading.Lock()

        # create directory of accessed nodes with type detected
        self.kwnodes = dict()


    def disable(self):
        ''' disable modbus instrument and close serial link '''
        # acquire lock
        self.serial_lock.acquire()

        # destroy instrument
        self.instrument.serial.close()  # really ??
        del(self.instrument)
        self.instrument = None

        # release lock
        self.serial_lock.release()
        self.serial_lock = None

        # destroy nodes dictionnary
        self.kwnodes.clear()
        self.kwnodes = None



    # -------------------------------------------------------------------------
    #
    # Low-level API
    #
    def _read(self, addr):
        # set instrument modbus address
        self._set_instrument_addr(addr)

        # check for already detected counter type at specified modbus addr
        if addr not in self.kwnodes:
            # trying to guess type of energy meter  
            self.kwnodes[addr] = self._detect()

        return self.kwnodes[addr].read(self.instrument)


    def _reset(self, addr):
        # set instrument modbus address
        self._set_instrument_addr(addr)

        # check for already detected counter type at specified modbus addr
        if addr not in self.kwnodes:
            # trying to guess type of energy meter  
            self.kwnodes[addr] = self._detect()

        return self.kwnodes[addr].reset(self.instrument)


    # Set modbus node addr in instrument for subsequent access
    def _set_instrument_addr(self, addr):
        ''' Set modbus node addr in instrument for subsequent access '''
        # set address node within instrument
        self.instrument.address = int(addr)


    def _detect(self):
        ''' detecting type of energy meter and register class within kwnodes '''
        log.info("Trying to guess type of Energy Meter whose address is '%d' ..." % self.instrument.address )

        try:
            # is Countis type ?
            if Countis.detect(self.instrument) is not None:
                # okay, it is a countis type but which one exactly ?
                if countisE03.CountisE03.detect(self.instrument) is True:
                    log.debug("CountisE03 energy meter detected at modbus addr [%d]" % self.instrument.address)
                    return countisE03.CountisE03()
                # add additional Countis type energy meters to detect
        except:
            time.sleep(0.2)
            pass

        try:
            # is Micronics ultrasonic Flow-Meter ?
            if MicronicsU1000.detect(self.instrument) is not None:
                # Found Micronics U1000-HM
                log.debug("Micronics U1000HM ultrasonic flow-meter detected at modbus addr [%d]" % self.instrument.address)
                return MicronicsU1000()
        except:
            time.sleep(0.2)
            pass

        # add additional types of energy meters to detect here

        # not detected :(
        log.warning("Modbus energy meter type whose addr is '%d' is UNKNOWN!" % self.instrument.address)
        raise Exception("Modbus energy meter type whose addr is '%d' is UNKNOWN!" % self.instrument.address)



    # -------------------------------------------------------------------------
    #
    # neOCampus modbus backend API
    # - read()                  Read values from power-meter
    # - reset()                 Reset power-meter energy counters
    
    # Read energy values from a modbus node
    def read( self, addr ):
        ''' reading values from a specified modbus node addr '''
        # access to the serial bus
        with self.serial_lock:
            return self._read(addr)

    # Reset energy values of a modbus node
    def reset( self, addr ):
        ''' Reset energy values of a modbus node '''
        # access to the serial bus
        with self.serial_lock:
            return self._reset(addr)



# #############################################################################
#
# MAIN
#

def main():
    '''Test backend functionnalities'''

    # test settings that match the rpi3-ardbox-11d7
    link = "/dev/ttyUSB0"
    link_speed = 9600

    #print("[%s] functions tests ..." % (__name__));
    log.debug("Starting tests with %s @ %dbauds ..." % (link,link_speed) );

    # instantiate a backend
    b = ModbusBackend(link,link_speed)

    # TO BE CONTINUED
    # add node to read energy values from

    # ask instantiated backend's status
    b.status()


# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

