#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Flow meter module driver for Micronics ultrasonic heat-meter U1000-HM
#
# F.Thiebolt Nov.17
#



# #############################################################################
#
# Import zone
#


# Modbus imports
import serial
import minimalmodbus
from .modbusHelpers import modbusGetAll



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
class MicronicsU1000(object):
    ''' RS-485 modbus drivers for Socomec Countis energy meters '''

    # Class attributes
    # MANDATORY !
    ENERGY_METER_NAME           = "Micronics U1000-HM"

    # Modbus addresses
    # [nov.17] WARNING: see modbus table, you ought to select U1000 registers (not Modbus registers ?!?!)
    MODBUS_PRODUCT_ID           = 0
    PRODUCT_ID                  = 0xAC

    MODBUS_PRODUCT_STATUS       = 1
    PRODUCT_STATUS_OK           = 0
    
    # Modbus addresses
    # Format of tuples is ( modbus_table_index, <type>, unit, *float(conversion_factor) )
    _INDEX2READ = ( \
                    (8, "float", "m3/hr", 1),\
                    (10, "float", "kW", 1), \
                    (12, "float", "kWh", 1), \
                    (14, "float", "hot_degresC", 1), \
                    (16, "float", "cold_degresC", 1), \
                    (18, "float", "diff_degresC", 1), \
                     )

    # Note: does not feature reset capability
    _INDEX2RESET = None

    # Attributes


    # Initialization
    def __init__(self, *args, **kwargs):
        pass


    # detection of energy meter type
    # Note: instrument is already set with target address
    @staticmethod
    def detect( instrument ):

        # First check we're a U1000-HM
        _val = instrument.read_register(__class__.MODBUS_PRODUCT_ID)
        if _val != __class__.PRODUCT_ID:
            return None

        return True


    # -------------------------------------------------------------------------
    # methods to override those of the parent class
    #
    @staticmethod
    def read(instrument):
        # first, check flow-meter is OK
        _val = instrument.read_register(__class__.MODBUS_PRODUCT_STATUS)
        if _val != __class__.PRODUCT_STATUS_OK:
            print("###ERROR U1000-HM status is NOT OK :(, status = %d" % int(_val) )
            raise Exception("U1000HM device is NOT OK :(, status = %d" % int(_val) )
        return modbusGetAll( instrument, __class__._INDEX2READ )


    @staticmethod
    def reset(instrument):
        if __class__._INDEX2RESET is None or len(__class__._INDEX2RESET) == 0:
            return None
        print("In reset function ...")
        for _index in __class__._INDEX2RESET:
            instrument.write_long(int(_index), 0)


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

