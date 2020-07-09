#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sensOCampus (devices) logger management
#
# F.Thiebolt Jan.17
# T.Bueno 2016
#



# #############################################################################
#
# Import zone
#
import logging
import logging.handlers

# sensOCampus' devices related import
from settings import LOG_LEVEL, SENSO_HOST


#
# Setup logging
logging.raiseExceptions = False
log = logging.getLogger()
log.setLevel(logging.DEBUG)
_log_format = logging.Formatter('[%(asctime)s][%(module)s:%(funcName)s:%(lineno)d][%(levelname)s] %(message)s')
_stream_handler = logging.StreamHandler()
_stream_handler.setLevel(LOG_LEVEL)
_stream_handler.setFormatter(_log_format)
log.addHandler(_stream_handler)



# #############################################################################
#
# Functions
#

#
# Function to initialize python logging
def init_remote_logger(login, password):
    log.debug("setting up remote logger")
    _url='/device/logger'
    _remote_handler = logging.handlers.HTTPHandler(host=SENSO_HOST, url=_url, method='POST',
                                                   secure=True, credentials=(login, password))
    # remote handler ONLY send ERROR to sensOCampus logger
    _remote_handler.setLevel(logging.ERROR)
    log.addHandler(_remote_handler)
    log.info("Started remote logging to host=https://%s%s ... " % (SENSO_HOST,_url) )


#
# Function to change logger's log level
def setLogLevel(logLevel):
    if logLevel == None: return
    log.debug("changing logger level to " + str(logLevel))
    try:
        log.setLevel(logLevel)
        _stream_handler.setLevel(logLevel)
    except ValueError as err:
        self._errMsg("Exception while setting logger to logLevel %s !" % (str(logLevel)) )
        return False
    return True


#
# Function to retrieve current logger's log level
def getLogLevel():
    return logging.getLevelName(log.getEffectiveLevel())


