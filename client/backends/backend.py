#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Backend class - IO management system
#
# This class will hold all a list of all of the actuators reachable in a seemless way
#
# -----------------------------------------------------------------------------
# |   neOCampus IO mapping                                                    |
# -----------------------------------------------------------------------------
# | PiFaceIO       |   0  --> 99                                              |
# -----------------------------------------------------------------------------
# | ArboxIO        | 100  --> 999                                             |
# -----------------------------------------------------------------------------
# | neoIO          | 1000 --> 1999                                            |
# -----------------------------------------------------------------------------
#
# [Jan.17] F.Thiebolt: add callback support for digital inputs
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

# extend Python's library search path
import os
import sys
# import RPi / helpers tools
_path2add='../libutils'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from HelpersFunc import *
#from rpi_utils import *

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
class backend(object):

    # class attributes
    _BACKENDSDIR = '';  # path to backends directory (auto detected)

    # attributes
    backendsList = None;   # list of instantiated backends

    # Backend IO mapping
    IO_MAPPING = { 'pifaceio':0, 'ardboxio':100, 'neoio':1000 }


    # --- init ----------------------------------------------------------------
    def __init__(self,auto=False):
        # Hack to find backend directory
        import backend as __backend
        #print(sys.modules.keys())
        __class__._BACKENDSDIR = os.path.dirname(__backend.__file__)
        del __backend
        log.debug("Backends dir = '%s'" % __class__._BACKENDSDIR)

        self.backendsList = list()

        # automatic loading of backends
        if auto:
            log.info("Automatic load of available backends ...");
            #TODO: automatically find the backends modules from directory!
            for _backend in [ "PifaceIO", "ArdboxIO", "neoIO"]:
                self.addBackend(_backend)

    def status(self):
        '''return tuples of inputs / outputs: e.g with a Piface and 2xArdboxIO
            inputs=[ (0,8), (100,16) ], outputs=[ (0,8), (100,16) ]'''
        inputs= []; nb_inputs=0;
        outputs= []; nb_outputs=0;
        
        for b in self.backendsList:
            i,o = b.status()
            nb_inputs,nb_outputs = nb_inputs+i,nb_outputs+o
            b_start=__class__.IO_MAPPING[b.__class__.__name__.lower()]
            inputs.append((b_start,i))
            outputs.append((b_start,o))
        log.debug("Backend features\n\t[%d inputs] = %s\n\t[%d outputs] = %s" % (nb_inputs,str(inputs),nb_outputs,str(outputs)))
        return inputs,outputs

    def _isBackendLoaded(self,backendName):
        '''to check if a backend is already loaded'''
        if (len(self.backendsList)==0): return False
        # let's parse all of the backends
        for b in self.backendsList:
            #if (self.debug): print(b.__class__.__name__)
            if (b.__class__.__name__ == backendName):
                return True
        # not found, ok!
        return False

    def _loadBackend(self,backendName):
        ''' Load specified backend (string) and return instantiated object if
            its detect method returns True '''
        if (backendName == 'backend'):
            log.error("non sense loading backend.py as a backend!");
            return None
        # is backend already loaded
        if (self._isBackendLoaded(backendName) != False):
            log.debug("Backend [%s] already loaded ... :|" % backendName)
            return None
        # start to load backend ...
        b = None
        for b  in get_modules(__class__._BACKENDSDIR,backendName):
            log.debug("current content of backend = " + str(b))
            if (backendName == None): return None
        if ( b == None ):
            log.debug("no module '%s' found :(" % backendName)
            return None
        # TODO:module is now imported, do i need to unload it ?
        # static detect() ?
        #if callable(getattr(b,backendName).detect):
        #    if getattr(b,backendName).detect() is None:
        #        log.debug("Backend [%s].detect() returned None ... so removeing backend" % backendName)
        #        del
        # instantiate latest component
        _instance = None
        _instance = getattr(b,backendName)()
        if _instance is not None:
            return _instance
        del _instance
        return None

    def addBackend(self,backendName):
        ''' add a specified backend (txt) to our backend list :) '''
        b = None
        b = self._loadBackend(backendName)
        if b is not None :
            self.backendsList.append( b )
            log.debug("successfully added module '%s'" % backendName)
        return b


    #
    # === neOCampus I/O methods ===============================================
    #
    # TODO: digital/analog read OUGHT to get bufferized (no access each time)

    def digital_write(self, pin, value):
        ''' Fonction to write a value in a digital output. First, we need to select
            proper backend according to pin number. '''
        # lets' parse all backends to find proper one according to its output range
        for i,b in enumerate(self.backendsList):
            _inputs, _outputs = b.status()
            _b_iostart = __class__.IO_MAPPING[b.__class__.__name__.lower()]
            if _b_iostart <= pin < (_b_iostart+_outputs):
                log.debug("using backend %d (%s) to write outputPin %d" % (i,b.__class__.__name__,pin))
                return b.digital_write(pin-_b_iostart, value)
            log.debug("[backend %d] goes [%d .. %d] don't fit for %d output wanted ... next one" % (i, _b_iostart, _b_iostart+_outputs, pin))
        # not found :(
        return False


    # Set callback for specified digital inputs. inputsList = [ 103, 105, 115 ]
    def digital_read_callback(self, inputsList, callback):
        ''' Callback for digital inputs '''
        # parse all inputs from list
        for pin in inputsList:

            # lets' parse all backends to find proper one according to its output range
            _found = False
            for i,b in enumerate(self.backendsList):
                _inputs, _outputs = b.status()
                _b_iostart = __class__.IO_MAPPING[b.__class__.__name__.lower()]
                if _b_iostart <= pin < (_b_iostart+_inputs):
                    log.debug("using backend %d (%s) for digital_read_callback of inputPin %d" % (i,b.__class__.__name__,pin))
                    b.digital_read_callback(pin-_b_iostart, callback, pin_iostart=_b_iostart)
                    _found = True
                    break
                log.debug("[backend %d] goes [%d .. %d] don't fit for %d input wanted ... next one" % (i, _b_iostart, _b_iostart+_inputs, pin))
            if _found is not True:
                # not found :(
                log.error("unable to find proper backend for inputPin = %d ?!?! ... continuing" % pin)


    # Cancel callback for specified digital inputs. inputsList = [ 103, 105, 115 ]
    def cancel_digital_read_callback(self, inputsList):
        ''' Cancel callback that was previously set for digital inputs '''
        # parse all inputs from list
        for pin in inputsList:

            # lets' parse all backends to find proper one according to its output range
            _found = False
            for i,b in enumerate(self.backendsList):
                _inputs, _outputs = b.status()
                _b_iostart = __class__.IO_MAPPING[b.__class__.__name__.lower()]
                if _b_iostart <= pin < (_b_iostart+_inputs):
                    log.debug("using backend %d (%s) for cancel_digital_read_callback of inputPin %d" % (i,b.__class__.__name__,pin))
                    b.cancel_digital_read_callback(pin-_b_iostart)
                    _found = True
                    break
                log.debug("[backend %d] goes [%d .. %d] don't fit for %d input wanted ... next one" % (i, _b_iostart, _b_iostart+_inputs, pin))
            if _found is not True:
                # not found :(
                log.error("unable to find proper backend for inputPin = %d ... continuing" % pin)


    # send back a list of digital event according to the inputs specified in the list
    # will send back a list of pin that changed along with their value : [ (pin, value), (pin, value) ... ]
    def digital_read_events(self, inputsList):
        ''' will send back a list of pin that changed along with their value : [ (pin, value), (pin, value) ... ] '''
        raise Exception("Not yet implementd")


    def digital_read(self, pin):
        ''' Method to read a digital value. First, we need to select
            proper backend according to pin number. '''
        # lets' parse all backends to find proper one according to its output range
        for i,b in enumerate(self.backendsList):
            _inputs, _outputs = b.status()
            _b_iostart = __class__.IO_MAPPING[b.__class__.__name__.lower()]
            if _b_iostart <= pin < (_b_iostart+_inputs):
                log.debug("using backend %d (%s) to read inputPin %d" % (i,b.__class__.__name__,pin))
                return b.digital_read(pin-_b_iostart)
            log.debug("[backend %d] goes [%d .. %d] don't fit for %d input wanted ... next one" % (i, _b_iostart, _b_iostart+_inputs, pin))
        # not found :(
        return False


    def analog_read(self, pin, min_value, max_value):
        ''' Method to read an analog value. First, we need to select
            proper backend according to pin number. '''
        # lets' parse all backends to find proper one according to its output range
        for i,b in enumerate(self.backendsList):
            _inputs, _outputs = b.status()
            _b_iostart = __class__.IO_MAPPING[b.__class__.__name__.lower()]
            if _b_iostart <= pin < (_b_iostart+_inputs):
                log.debug("using backend %d (%s) to read inputPin %d" % (i,b.__class__.__name__,pin))
                return b.analog_read(pin-_b_iostart,min_value,max_value)
            log.debug("[backend %d] goes [%d .. %d] don't fit for %d input wanted ... next one" % (i, _b_iostart, _b_iostart+_inputs, pin))
        # not found :(
        return False


    def analog_write(self, pin, value, min_value, max_value):
        ''' Function to write an analog value to an output. First, we need to select
            proper backend according to pin number. '''
        #TODO
        raise Exception("not yet implemented :|")


# #############################################################################
#
# MAIN
#

def main():
    '''Test backend functionnalities'''
    #print("[%s] functions tests ..." % (__name__));
    log.debug("Starting tests ...");

    # instantiate a backend
    _bAutoLoad=True
    b = backend(auto=_bAutoLoad)

    if not _bAutoLoad:
        # load a well-known backend
        backend2load="PifaceIO"
        print("Trying to load '%s' backend ..." % backend2load);
        b.addBackend(backend2load)

        # trying to load it anew (ought to fail)
        print("[2nd] Trying to load '%s' backend ..." % backend2load);
        b.addBackend(backend2load)

    # ask instantiated backend's status
    b.status()


# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

