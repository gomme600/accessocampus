#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PifaceIO backend
#
# We expose a uniform access to all of the PiFace digital IO boards.
# Each Piface features 8 inputs and 8 outputs --> thus 8 IO.
# Maximum is 8 piface digital boards thus max. 64 inputs + 64 outputs
#   PiFacedigital IO board hardware addr ought to start to 0. Subsequent
#   hardware addr ought to continue in sequence (i.e no hole in hardware
#   addr)
#
# https://piface.github.io/pifacedigitalio/reference.html
#
# TODO: static detect()
#
# F.Thiebolt Nov.16
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

import time

# Piface (default included in Raspbian)
# https://piface.github.io/pifacedigitalio/reference.html
import pifacedigitalio as piface

# extend Python's library search path
import os
import sys
# sensOCampus
_path2add='../sensocampus'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
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
class PifaceIO(object):

    # class attributes
    MAX_PIFACE_BOARDS   = 8         # maximum number of Piface digital IO boards per RPi
    PIFACEIO_OUTPUTS    = 8
    PIFACEIO_INPUTS     = 8

    # attributes
    pifaceInstances = None; # instantiated PifacesIO boards

    # extra

    # --- init ----------------------------------------------------------------
    def __init__(self):
        ''' Initialize up to MAX_PIFACE_BOARDS boards. Stops on first instanciation error. '''

        self.pifaceInstances = list()

        # detect multiple boards
        for badr in range(__class__.MAX_PIFACE_BOARDS):
            # trying to detect the board(s)
            try:
                self._instance = piface.PiFaceDigital(hardware_addr=badr, bus=0, chip_select=0, init_board=True)
                # piface.deinit() to stop all interrupts
                log.debug("PiFaceIO board [%d] successfully initialized :)" % (badr))
                #print(self._instance.__dict__)
                self.pifaceInstances.append(self._instance)
            except Exception as ex:
                log.debug("PiFaceIO board [%d] does not exist" % (badr) );
                break;
        if len(self.pifaceInstances) != 0:
            log.debug("%d Piface digital IO boards have been instanciated" % len(self.pifaceInstances))
        else:
            log.debug("no Piface digital IO board found out there :|");

    def status(self):
        '''send back maximum number of inputs / outputs'''
        inputs = len(self.pifaceInstances) * __class__.PIFACEIO_INPUTS;
        outputs = len(self.pifaceInstances) * __class__.PIFACEIO_OUTPUTS;
        return inputs, outputs


    # TODO: static detect()


    #
    # === I/O methods =========================================================
    #

    def digital_write(self, pin, value):
        ''' Function to write a value in a digital output. First, we need to select
            proper board according to pin number. '''
        # is output in range of our piface boards ?
        if ( pin < 0 ) or ( pin >= len(self.pifaceInstances)*__class__.PIFACEIO_OUTPUTS):
            log.error("outputPin %d not in our list [0 .. %d]" % (pin,len(self.pifaceInstances)*__class__.PIFACEIO_OUTPUTS) )
            raise Exception("pin not in range of our Piface board(s)")
        # let's parse all boards to find proper one according to its output range
        for (i,b) in enumerate(self.pifaceInstances):
            curBoardMaxInput, curBoardMaxOutputs = __class__.PIFACEIO_INPUTS, __class__.PIFACEIO_OUTPUTS
            if (pin >= curBoardMaxOutputs):
                log.debug("current board [%d] features %d outputs > %d output wanted ... next one" % (i, curBoardMaxOutputs, pin))
                pin -= curBoardMaxOutputs
            else:
                log.debug("[board %d] write outputPin %d (value=%d)" % (i,pin,value))
                b.output_pins[pin].value = value
                return True
        # not found :(
        log.error("unknown error while digital_write to a Piface board !?")
        raise Exception("unknown error while digital_write to a Piface board !?")


    # Set callback for specified digital inputs. inputsList = [ 0, 3, ... ]
    def digital_read_callback(self, inputsList, callback):
        ''' Callback for digital inputs '''
        #TODO
        raise Exception("not yet implemented :|")


    # Cancel callback for specified digital inputs. inputsList = [ 0, 3, ... ]
    def cancel_digital_read_callback(self, inputsList):
        ''' Cancel callback that was previously set for digital inputs '''
        #TODO
        raise Exception("not yet implemented :|")


    def digital_read(self, pin):
        ''' Function to read a digital value from an input. First, we need to select
            proper board according to pin number. '''
        #TODO
        raise Exception("not yet implemented :|")


    def analog_read(self, pin, min_value, max_value):
        ''' Function to read an analog value from an input. First, we need to select
            proper board according to pin number. '''
        #TODO
        raise Exception("not yet implemented :|")


    def analog_write(self, pin, value, min_value, max_value):
        ''' Function to write an analog value to an output. First, we need to select
            proper board according to pin number. '''
        #TODO
        raise Exception("not yet implemented :|")



# #############################################################################
#
# MAIN
#

def main():
    '''Call the various functions'''

    # instantiate
    b = PifaceIO()

    # get status
    b.status()

# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

