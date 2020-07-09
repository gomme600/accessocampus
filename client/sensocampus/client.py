#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sensOCampus (devices) client library
#
# This client implement the devices behaviour in the sensOCampus framework.
# Devices are responsible to load modules and to initialize backend global
#   variable.
#
# F.Thiebolt Nov.19 add shutdown_event to 'device' module
# F.Thiebolt Sep.16
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
import threading
import json
import logging

# CLI options
from optparse import OptionParser

# extend Python's library search path
import os
import sys
# import RPi tools
_path2add='../libutils'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from rpi_utils import *
from HelpersFunc import get_modules

# import backend
_path2add='../backends'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from backend import *

# import modules
_path2add='../modules'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
#from modules import *


# sensOCampus' devices related import
from configuration import Configuration
from logger import log, init_remote_logger, setLogLevel, getLogLevel
from connection import Connection
from device import Device
import settings as settings





# #############################################################################
#
# Global Variables
#
# Note: all of these variables are not real 'global variables' as they are sent
# as arguments to all of the modules
#
_shutdownEvent  = None          # signall across all threads to send stop event
_backend        = None          # IO_backend list (piface(s), Ardbox(s) ...)
_modules        = None          # Modules list (camera, lighting, shutter ...)


# #############################################################################
#
# Functions
#

#
# Function ctrlc_handler
def ctrlc_handler(signum, frame):
    global _shutdownEvent
    print("\n<CTRL + C> action detected ... ", end=" ");
    assert _shutdownEvent!=None
    _shutdownEvent.set()



###############################################################################
#
# Main application case
#
def main():

    # Global variables
    global _shutdownEvent

    # create threading.event
    _shutdownEvent = threading.Event()

    # Trap CTRL+C (kill -2)
    signal.signal(signal.SIGINT, ctrlc_handler)

    # Parse CLI arguments
    parser = OptionParser()
    parser.add_option("-d", "--debug",
                        action="store_true", dest="debug", default=False,
                        help="Debug mode")
    parser.add_option("-s", "--sim",
                        action="store_true", dest="simulator", default=False,
                        help="Simulator mode")
    (options, args) = parser.parse_args()

    #
    # logging 
    if options.debug==True:
        print("\n[DBG] DEBUG mode activated ... ")
        setLogLevel(logging.DEBUG)
        time.sleep(1)
    else:
        print("\n[LOG] level set to %d" % int(settings.LOG_LEVEL) )
        setLogLevel(settings.LOG_LEVEL)


    #
    # Retrieve credentials (HTTP)
    #   + set remote logger
    #
    # sensOCampus app will give us our MQTT credntials along with json file about
    #   modules to load and backends to initialize.
    log.info("\n[1] Start to retrieve credentials ...");

    # loading configuration (dictionnary)
    # --> get credentials
    # --> get json file (devices/modules zones setup)
    #       dictionnary with 2 keys --> zones, modules
    conf = Configuration()

    if not conf.initialized():
        log.error("configuration failed to initialize, exiting ...")
        sys.exit(1)

    # remote logging initialization (http POST to sensOCampus web app)
    init_remote_logger(conf.login(), conf.password())


    #
    # MQTT connection for device
    #
    # We'll now connect to the MQTT broker to :
    #   - publish in <MQTT_TOPIC>/device
    #   - subscribe to  <MQTT_TOPIC>/device/command
    log.info("\n[2] Start device MQTT connexion ...");

    # MQTT connection initialization
    conn = Connection(conf)

    # 'device' initialization
    dev = Device(conf, conn, _shutdownEvent)

    log.info("\tclient initialized")

    while not conn.connected():
        time.sleep(1)


    #
    # Device's configuration file parsing
    #   launch modules & load backends as specified in json file
    log.info("\n[3] Start IO-backend initialization (piface & Ardbox setup) ...")

    # IO_backend initialization
    _backenAutoLoad=True
    log.debug("Initialise backend (auto=%s) ..." % ("False" if _backenAutoLoad==False else "True"))

    # simulator mode ?
    if ( not options.simulator ):
        _backend = backend(auto=_backenAutoLoad)
        # specify backend to load if no auto
        if not _backenAutoLoad:
            log.debug("\t[backend][Manual] asking to load PifaceIO backend ...");
            _backend.addBackend("PifaceIO");
            log.debug("\t[backend][Manual] asking to load ArdboxIO backend ...");
            _backend.addBackend("ArdboxIO");
        # print IO_Backend's status
        _backend.status()
    else:
        print("[SIM] simulator mode activated from CLI ...")


    #
    # Device's configuration file parsing
    #   launch modules & load backends as specified in json file
    log.info("\n[4] Start reading device JSON config file ...")

    if len(conf.topics()) > 0:
        def_topic = conf.topics()[0]
    else:
        log.error("not default topic provided !")
        def_topic = ""

    # configuration for all modules (eg. lighting, shutter ...)
    modules_conf = dict()
    modules_conf['host'] = conf.server
    modules_conf['port'] = conf.port
    modules_conf['login'] = conf.login()
    modules_conf['password'] = conf.password()
    modules_conf['topic'] = def_topic


    # import all needed modules here
    # from lighting import Lighting
    # from camera import Camera
    # from shutter import Shutter

    # register modules and their arguments here
    # add unitID incrementer if set manually (json from sensOCampus.neocampus.univ-tlse3.fr prefered)
    # Module's description format overview is:
    # ( <module_name>, [<unitID>, <mqtt_conf>], { <dictionnary for additional arguments> } )
    modules = [
        # (Shutter, [1, modules_conf], {'shutterType':"wireless", 'io_backend': _backend, 'upOutput': 0, 'downOutput': 1}),
        # (Lighting, [1, modules_conf], {'io_backend': _backend, 'output': 0}),
        # (Camera, [1, modules_conf], {'backend': 'pi'}),
        # (Camera, [2, modules_conf], {'backend': 'lepton'}),
        # (Luminosity, [1, modules_conf], {'autodetect': <True|False>, 'io_backend': _backend, 'inputs': (<lux sensors inputs@io_backend) })
    ]

    #
    # Parse json config received by sensOCampus
    #   build elements to insert in modules list.
    # each 'zone' == dictionnary of 'modules' and 'topic'
    for zone in conf.modules():
        zone_conf = modules_conf.copy()
        zone_conf['topic'] = zone['topic']

        for mod in zone['modules']:

            modname2load = mod['module']

            inst_cls = None
            try:
                _dbg = True if getLogLevel().lower() == "debug" else False

                python_mods = list( get_modules("../modules", \
                                    moduleName=modname2load.lower(), \
                                    debug=_dbg) )
                if len(python_mods) == 0:
                    raise Exception("no match for " + modname2load)

                inst_cls = getattr(python_mods[0], modname2load, None)
                if inst_cls is None:
                    raise Exception("unable to instantiate loaded module '%s' ?!?!" % modname2load)

            except Exception as ex:
                log.error("could not get referenced module: " + str(ex))
            else:
                # code executed only if no exception raised
                params = dict()
                for arg in mod['params']:
                    params[arg['param']] = arg['value']

                # add module with extracted parameters
                module_constr = (inst_cls, [mod['unit'], zone_conf], params)

                log.debug("initialized module constructor from remote config: " + str(module_constr))
                modules.append(module_constr)

    #
    # Auto-detection of 'sensors type' modules to load (e.g camera, temperature, luxmeter) ...
    #   ONLY if they are NOT already registered in modules list sent from sensOCampus
    log.info("Starting auto-load of sensors type modules ...");
    #TODO: find a better way to guess 'sensor type' module from modules directory
    #_sensorsModules=[ "Camera", "Temperature", "Luminosity", "Humidity", "CO2" ]
    _sensorsModules=[]
    _sensorsModules2load=[ mod for mod in _sensorsModules if mod.lower() not in [_mod.__name__.lower() for(_mod,_,_) in modules]]

    for mod in _sensorsModules2load:
        # load module and launch auto-detection of sensors
        log.debug("trying to auto-load module '%s' ..." % mod)
        _modLoaded = None
        _modLoaded = list(get_modules("../modules", moduleName=mod.lower(),debug=True))
        if len(_modLoaded) == 0:
            log.debug("unable to load neOCampus module [%s]" % (mod.lower()) )
            continue

        # call static method of imported sensor module
        if not callable(getattr(_modLoaded[0],mod).detect):
            log.warning("module %s does not have a 'detect()' method ?!?!" % mod)
            continue
        _res = None
        _res = getattr(_modLoaded[0],mod).detect()
        if _res is None: continue;  # nothing has been detected

        # we now have a list of dictionnaries holding parameters for each of the current module instances
        # _res = [ { }, { }, ... ]
        # _res = [ { 'detectedSensors' : [ ("TSL2561", -1, 0x78), ("TSL2561", -1, 0x79), ... ] }, {  }, ... ]
        # Note: for auto-detected sensors, there's only one dictionnary in _res with 'detectedSensors' field which
        # is a list of all sensors of the same kind.
        autoIDprefix="auto"
        autoID=0
        autoIDsuffix="".join(settings.MAC_ADDR.split(':')[-2:]).upper()
        for arg in _res:
            # add module with extracted parameters
            #TODO: if two zones exists (i.e with different topics), we'll thus select the latest one!
            #TODO: is this what we want ?
            # automatically detected modules get unitID = autoxx_<2digits end of MAC addr>
            inst_cls = getattr(_modLoaded[0],mod, None)
            _autoID=autoIDprefix="auto"+(str(autoID) if autoID!=0 else "")+"_"+autoIDsuffix
            module_constr = (inst_cls, [_autoID, modules_conf], arg)
            log.debug("initialized module constructor from auto-detection: " + str(module_constr))
            modules.append(module_constr)


    # Debug
    print(modules)
    sys.exit(0)


    #
    # report device's status
    # register backend & modules status functions to device's status report function
    log.info("Registering backend and modules status ...")
    dev.status_backend = _backend.status
    #TODO: no modules.status since it is a list of modules!
    #dev.status_modules = _modules.status
    log.info("Sending first device's status report")
    dev.status()


    #
    # set shutdownEvent event to all module's threads
    for (_, _, kwargs) in modules:
        kwargs['shutdown_event'] = _shutdownEvent
        kwargs['io_backend'] = _backend

    # initiate module's instances
    threads = list()
    for (base, args, kwargs) in modules:
        try:
            threads.append(base(*args, **kwargs))
        except Exception as ex:
            log.error("failed to initialize a module: " + str(ex))

    # launch all modules
    for t in threads:
        t.start()

    # waiting for shutdown event ...
    while not _shutdownEvent.is_set():

        for i in range(len(threads)):

            # restart threads in case of failure
            if not threads[i].isAlive():
                log.error("module " + str(threads[i]) + " exited, restarting ... ")

                cls, args, kwargs = modules[i]
                try:
                    threads[i] = cls(*args, **kwargs)
                    threads[i].start()
                except Exception as ex:
                    log.error("couldn't restart thread: " + str(ex))

        _shutdownEvent.wait(2)

    # shutdown initiated ...
    log.info("process terminating ... join on ALL threads ...")
    for t in threads:
        t.join()
    # shutdown 'device'
    log.info("device terminating ...")
    dev.shutdown()


#
# Execution or import
if __name__ == "__main__":

    # Start executing
    main()

# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

