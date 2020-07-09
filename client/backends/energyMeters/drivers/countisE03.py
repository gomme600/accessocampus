#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Countis-E03 energy module driver
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
from .modbusHelpers import modbusGetAll

# Countis specific imports
from .countis import Countis



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
class CountisE03(Countis):
    ''' RS-485 modbus drivers for Socomec Countis energy meters '''

    # Class attributes
    # MANDATORY !
    ENERGY_METER_NAME           = "COUNTIS E03"

    # Modbus addresses
    # Format of tuples is ( modbus_table_index, <type>, unit, *float(conversion_factor) )
    _INDEX2READ = ( \
                    (36868, "long", "Wh", 1),\
                    (50946, "long", "Ea+", 10), \
                    (50520, "long", "V", 0.01), \
                    (50528, "long", "A", 0.001), \
                    (50536, "slong", "W", 10), \
                    (50538, "slong", "VAR", 10 ), \
                    (50540, "long", "VA", 10), \
                    (50542, "slong", "cosPhi", 0.001) \
                     )

    # Note: countisE03 does not feature reset capability
    _INDEX2RESET = None

    # Attributes


    # Initialization
    def __init__(self, *args, **kwargs):
        super().__init__()
        pass


    # detection of energy meter type
    # Note: instrument is already set with target address
    @staticmethod
    def detect( instrument ):
        # check detection @ parent level
        _res = Countis.detect( instrument )

        if _res is None:
            # wrong class of energy meters
            return None

        # Let's check if it matches our current type
        if __class__.ENERGY_METER_NAME.lower() in _res.lower():
            return True

        # ok, we're a countis but not a countisE03
        return None


    # -------------------------------------------------------------------------
    # methods to override those of the parent class
    #
    @staticmethod
    def read(instrument):
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

