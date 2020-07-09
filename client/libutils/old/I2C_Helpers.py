#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SMBus python documentation:
#   http://wiki.erazor-zone.de/wiki:linux:python:smbus:doc
#
# I2C helpers library
#   - i2c scanner: returns list of addresses that responded (device type to find)
#   - dynamic import of python modules :)
#
# François Avril 2016
#



###############################################################################
#
# Import zone
#
import smbus
from Adafruit_I2C import Adafruit_I2C

# Dynamic import
import os
import sys
import importlib



# #############################################################################
#
# Functions
#



# #############################################################################
#
# Class
#

class I2C_Helpers():

    # Range of possible I2C addr
    _I2C_ADDR_RANGE = range( 0x3, 0x78)

    # various flags
    debug = False

    @staticmethod
    def toggleDebug():
        "Toggle debug flag"
        __class__.debug = not(__class__.debug)
        if (__class__.debug): print("[%s] debug activated\n" % os.path.basename(__file__))

    @staticmethod
    def i2cScan(busnum=-1, debug=False):
        ''' Scan i2c bus. Default i2c bus choosen if not provided
        Return None if busnum is an error else empty list if not device detected
        else list of addr that responded to query'''
        # instantiate bus
        try:
            bus = smbus.SMBus(busnum if busnum >= 0 else Adafruit_I2C.getPiI2CBusNumber())
        except IOError as err:
            if (__class__.debug): print("[%s] i2c busnum '%d' does not seem to exist!" % (__name__,busnum))
            return
        devicesList = []
        # parse addr list
        for addr in __class__._I2C_ADDR_RANGE:
            try:
                ret=bus.write_quick(addr)
            except IOError as err:
                continue
            if (__class__.debug): print("[0x%X]" % addr, end="")
            devicesList.append(addr)

        return devicesList

    @staticmethod
    def get_modules(basepath,moduleName=None,packages=None):
        
        if (__class__.debug): print("Will start to import modules ...")

        # check if path exist and not already in sys.path
        if ( os.path.exists(basepath) and not basepath in sys.path ):
            if (__class__.debug): print("adding [%s] to sys.path" % basepath)
            sys.path.append(basepath)

        filenames = [f for f in os.listdir(basepath) if os.path.isfile(os.path.join(basepath,f))]
        for fp in filenames:
            if (not fp.endswith('.py')): continue
            modname="%s" % fp[:-len(".py")]
            if (moduleName != None and modname != moduleName): continue
            #module = importlib.import_module(modname)
            try:
                yield importlib.import_module(modname)
                if(__class__.debug): print("\tmodule [%s] loaded :)" % modname)
            except :
                if(__class__.debug): print("\t## Failed to load module [%s] :(" % modname)
                continue

#       return module



# #############################################################################
#
# MAIN
#

def main():
    '''Call the various utilities functions'''

    # activate debug
    I2C_Helpers.toggleDebug()

    print("I2C bus scan (default bus): ")
    _i2cList = I2C_Helpers.i2cScan(-1, False)
    if (_i2cList != None):
        print("\n\tFound some devices :)\n")

    sensors_path="../libsensors"
    print("Import libsensors modules from '%s': " % sensors_path)
#   print(I2C_Helpers.get_modules(sensors_path))
#   print(sys.path)
    for devices in I2C_Helpers.get_modules(sensors_path):
        print(devices)


# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

