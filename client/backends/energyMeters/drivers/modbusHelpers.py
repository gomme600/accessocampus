#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Modbus Helpers functions:
#   - acquire all parameters from specified list featuring tuples with:
#       (modbus_index_addr, <format>, units, *float(conversion_factor) )
#
#
# F.Thiebolt    apr.20  round to 3 decimals if conv_factor < 1 (to avoid
#                       value likes cosPhi = 0.9560000001)
# F.Thiebolt    Jun.17  initial release
#


# #############################################################################
#
# Import zone
#

import time

# Modbus imports
import minimalmodbus



# #############################################################################
#
# Global Variables
#



# #############################################################################
#
# Functions
#

def modbusGetAll( instrument, tinput, float_precision=2 ):
    ''' This function reads all tuples sent as arguments and return two lists:
        [ values ], [ units ]
        ... hence for each value in [values] list, there exists a corresponding unit in [units].
        Example: [ 42, 1206, 0.98 ] [ "Wh", "W", "cosPhi" ] means 42Wh, 1206W, powerFactor=0.98
        tinput parameter is the tale to read with unit and conv_factor
    '''

    _values = list()
    _units = list()

    # let's parse inputs
    for _index, _format, _unit, _convFactor in tinput:

        _max_retries=2
        _retry=0
        while _retry <= _max_retries:
            try:
                # select proper operation according to specified 'format'

                # signed OP ?
                _signed = True if _format.lower().startswith("s") else False

                # long ?
                if _format.lower().endswith("long"):
                    _val = float(instrument.read_long(_index,signed=_signed)) * float(_convFactor)
                    # [apr.20] round if conv_factor < 1.0
                    if( float(_convFactor) < 1.0 ):
                        _values.append(round(_val,float_precision))
                    else:
                        _values.append(_val)
                    _units.append(_unit)
                    break

                # float (2 words IEE754) ?
                if _format.lower().endswith("float"):
                    _val = float(instrument.read_float(_index)) * float(_convFactor)
                    _values.append(round(_val,float_precision))
                    _units.append(_unit)
                    break

                # unknown format
                log.error("unknwown format '%s' ?!?! ... continuing" % _format)

            # almost all exceptions including IOError, ValueError
            except Exception as ex:
                _retry = _retry + 1
                if _retry <= _max_retries:
                    print("#WARNING: exception raised, retrying to read (%d, %s, %s, %.3f) : " % (_index,_format,_unit,float(_convFactor)) + str(ex) )
                    time.sleep(0.1*_retry)
                    continue    # while loop
                else:
                    print("###ERROR: an Exception occured while reading (%d, %s, %s, %.3f) : " % (_index,_format,_unit,float(_convFactor)) + str(ex) )
                    raise Exception(ex);

    return _values,_units

