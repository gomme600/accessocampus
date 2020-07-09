#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Energy module driver for Socomec Countis Energy meters.
#
# F.Thiebolt Jun.17
#



# #############################################################################
#
# Import zone
#

# Modbus imports
import serial
import minimalmodbus



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
class Countis(object):
    ''' RS-485 modbus drivers for Socomec Countis energy meters '''

    # Class attributes
    # Modbus addresses
    MODBUS_COMPANY_NAME         = 50042
    COMPANY_NAME                = "SOCOMEC"

    MODBUS_PRODUCT_NAME         = 50050
    PRODUCT_NAME                = "COUNTIS"

    MODBUS_PRODUCT_NAME_EXT     = 50058   # "COUNTIS E03" or ...

    

    # Attributes
    #cur_modelname               = None

    # Initialization
    def __init__(self, *args, **kwargs):
        pass


    # detection of energy meter type
    @staticmethod
    def detect( instrument ):
        # check company name
        _val = instrument.read_string(__class__.MODBUS_COMPANY_NAME,8).lower()
        if __class__.COMPANY_NAME.lower() not in _val:
            return None

        # check product name
        _val = instrument.read_string(__class__.MODBUS_PRODUCT_NAME,8).lower()
        if __class__.PRODUCT_NAME.lower() not in _val:
            return None

        # ok, right company name and right product type ... next is to check realy product ID
        return instrument.read_string(__class__.MODBUS_PRODUCT_NAME_EXT,8).lower()


    # -------------------------------------------------------------------------
    # virtual methods to implement by inheritant
    #
    @staticmethod
    def read(instrument):
        pass

    @staticmethod
    def reset(instrument):
        pass



# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

