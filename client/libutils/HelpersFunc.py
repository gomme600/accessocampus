#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Helpers functions library
#   - i2c scanner: returns list of addresses that responded (device type to find)
#   - dynamic import of python modules :)
#
# Thiebolt F.   oct.19  update to remove Adafruit_I2C
# François Avril 2016
#



###############################################################################
#
# Import zone
#
import time

# For SMBus/I2C
from smbus2 import SMBus
from RPi import GPIO

# For SPI
import spidev

# For dynamic import
import os
import sys
import importlib

# For process management
from subprocess import check_output, CalledProcessError
from signal import SIGTERM


# #############################################################################
#
# Functions
#

# Switch Xorg to ON
def setXorgON( ):
    ''' force Xorg to switch ON
        if user interface available (e.g keyboard, mouse), we just wakeup the screen for DPMS duration.
        return True ($?==0), None or False otherwise '''
    try:
        output = check_output("xset s off -dpms".split(), universal_newlines=True )
        if isUserInputAvailable() is True:
            print("user input devices detected ... wakeup xorg for DPMS duration ...")
            output = check_output("xset s on +dpms".split(), universal_newlines=True )
        return True
    except CalledProcessError as ex:
        return None
    except Exception as ex:
        print(ex)
        return None

    return None

# Switch Xorg to OFF
def setXorgOFF():
    ''' force Xorg to switch OFF
        return True ($?==0), None or False otherwise '''
    try:
        output = check_output("xset s on dpms force off".split(), universal_newlines=True )
        return True
    except CalledProcessError as ex:
        return None
    except Exception as ex:
        print(ex)
        return None

def isUserInputAvailable( _keywords = [ 'mouse', 'keyboard', 'touch' ]):
    ''' function to determine if there is a usb mouse, keyboard or touch screen available
        True if an USB input device is present, False or None  otherwise '''
    try:
        #p = subprocess.run('lsusb -v'.split(), stdout=subprocess.PIPE)
        #output = check_output("lsusb -v".split(), universal_newlines=True ).splitlines()
        output = check_output("lsusb -v".split(), universal_newlines=True )
        if any(word in output.lower() for word in _keywords):
            return True
    except CalledProcessError as ex:
        return None
    except Exception as ex:
        print(ex)
        return None

    return None

def getPIDbyName( name, option=None ):
    ''' obtain list of PIDs according to name '''
    try:
        if option is not None:
            res = check_output( [ "pgrep", option, name ], universal_newlines=True ).split()
        else:
            res = check_output( [ "pgrep", name ], universal_newlines=True ).split()
        return list(map(int, res))
    except CalledProcessError as ex:
        return None
    except Exception as ex:
        print(ex)
        return None

def killPIDbyName( name  ):
    ''' kill process matching name.
        Returns number of process killed '''
    _pk=0
    _retry=3
    process2kill=getPIDbyName( name, "-f" )
    while _retry>0 and isinstance(process2kill,list) and len(process2kill)>0:
        _retry-=1
        try:
            for p in process2kill:
                try:
                    os.kill( p, SIGTERM )
                    time.sleep(1)
                    _pk+=1
                except Exception as ex:
                    print(ex)
                    continue
        except Exception as ex:
            pass
        time.sleep(1)
        process2kill=getPIDbyName( name, "-f" )
    return _pk

# Function to scan an i2c bus
def i2cScan(busnum=-1, debug=False):
    ''' Scan i2c bus. Default i2c bus choosen if not provided
    Return None if busnum is an error else empty list if not device detected
    else list of addr that responded to query'''
    # Range of possible I2C addr
    _I2C_ADDR_RANGE = range( 0x3, 0x78)

    # instantiate bus
    try:
        bus = SMBus(busnum if busnum >= 0 else 1)
    except IOError as err:
        if (debug): print("[%s] i2c busnum '%d' does not seem to exist!" % (__name__,busnum))
        return
    devicesList = []
    # parse addr list
    for addr in _I2C_ADDR_RANGE:
        try:
            ret=bus.write_quick(addr)
        except IOError as err:
            continue
        if (debug): print("[0x%X]" % addr, end="")
        devicesList.append(addr)
    return devicesList

# Function to dump an i2c device
def i2c_dump(i2c_addr, busnum=-1, size=128):
    ''' Dump content of an i2c device '''
    # instantiate bus
    try:
        bus = SMBus(busnum if busnum >= 0 else 1)
    except IOError as err:
        if (debug): print("[%s] i2c busnum '%d' does not seem to exist!" % (__name__,busnum))
        return

    # try to detect requested device
    try:
        ret=bus.write_quick(i2c_addr)
    except IOError as ex:
        print("Device 0x%02X not found!" % i2c_addr)
        raise ex

    # Read content of device
    print("=== I2C scan of device 0x%02X ===" % i2c_addr)
    _data = list()
    for mem in range(size):
        return
    # TO BE CONTINED

# Function to dynamically load python modules
def get_modules(basepath, moduleName=None, packages=None, debug=False):
    '''Function to dynamically load a python module.''' 
    if (debug): print("Will start to import modules ...")

    # convert basepath to absolutepath
    absbasepath = os.path.abspath(basepath)

    # check if path exist and not already in sys.path
    if ( not os.path.exists(absbasepath) ):
        if (debug): print("warning, path [%s] does not exists ..." % absbasepath)
    elif ( not absbasepath in sys.path) :
        if (debug): print("adding [%s] to sys.path" % absbasepath)
        sys.path.append(absbasepath)

    filenames = [f for f in os.listdir(absbasepath) if os.path.isfile(os.path.join(absbasepath,f))]
    for fp in filenames:
        if (not fp.endswith('.py')): continue
        modname="%s" % fp[:-len(".py")]
        if (moduleName != None and modname != moduleName): continue
        #module = importlib.import_module(modname,packages)
        try:
            yield importlib.import_module(modname,packages)
            if(debug): print("\tmodule [%s] loaded :)" % modname)
        except :
            print("\n\t## either module [%s] is not relevant ... or maybe a real ERROR inside ..." % modname)
            continue

#   return module



# #############################################################################
#
# MAIN
#

def main():
    '''Call the various utilities functions'''

    # i2c bus scan
    i2cbus=-1;  # default I2C bus
    print("I2C bus scan (default bus): ")
    _i2cList = i2cScan(i2cbus, debug=True)
    if (_i2cList != None):
        print("\n\tI2C bus %s exist ..." % ("default" if i2cbus==-1 else str(i2cbus)))
        print("\tFound %d I2C devices\n" % len(_i2cList))
    else:
        print("\n\tI2C bus %d does not exist\n" %i2cbus)

    # spi bus dump
    # TODO

    # python modules load
    sensors_path="../modules"
    print("Import modules from '%s': " % sensors_path)
#   print(I2C_Helpers.get_modules(sensors_path))
#   print(sys.path)
    for devices in get_modules(sensors_path,debug=True):
        print(devices)


# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

