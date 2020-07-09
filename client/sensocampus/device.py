#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sensOCampus' device management library
#
# [Aug.16] added support to device status reporting
#
# F.Thiebolt
# T.Bueno
#



# #############################################################################
#
# Import zone
#
import time
import threading
from enum import Enum
import json

# sensOCampus' devices related import
import settings as settings
from logger import log



# #############################################################################
#
# Class
#
class Status(Enum):
    init = 0
    run = 1
    reboot = 2
    restart = 3
    reset = 4
    update = 5

    error = 6

    upgrade = 7
    reinstall = 8



# #############################################################################
#
# Class
#
class Device(object):

    TIMER_STATUS_REPORT = (30*60)   # toutes les 30mn

    _configuration  = None
    _connection     = None
    _shutdown_event = None

    _status         = None      # current status of device
    _status_lock    = None      # lock to send status report
    _status_timer   = None      # timer to periodically send status reports 
    _status_backend = None      # function to retrieve backend's status
    _status_modules = None      # function to retrieve modules' status


    def __init__(self, conf, conn, shutdown_event=None ):

        self._configuration = conf
        
        self._connection = conn
        
        self._shutdown_event = shutdown_event
        if not self._shutdown_event:
            raise ValueError("shutdown event not set")

        self._connection.on_command = self.handle_command   # called upon msg received
        self._connection.on_working = self.handle_working   # called upon successfully subscribed to a topic
        self._connection.connect()
        self._status = Status.init
        self._status_lock = threading.Lock()

        # launch timer for sending status report
        self._status_timer = threading.Timer(__class__.TIMER_STATUS_REPORT, self.status)
        self._status_timer.start()
        #self._do_every(__class__.TIMER_STATUS_REPORT, self.status)


    def _do_every(self, interval, worker_func, iterations = 0):
        '''launch status report peridiocally'''
        if ( iterations != 1):
            self._status_timer = threading.Timer (
                            interval,
                            self._do_every, [interval, worker_func, 0 if iterations == 0 else iterations-1] );
            self._status_timer.start()
        # launch worker function
        worker_func();


    def shutdown(self):
        log.info("Shutting down device ...")
        self._shutdown_event.set()
        time.sleep(10)
        self._status_timer.cancel()
        time.sleep(2)

        #TODO: add useful things here at shutdown


    def reset(self):
        log.info("application reset")
        self._status = Status.reset
        self.status()
        time.sleep(2)

        self._configuration.reset()
        self.restart()


    def restart(self):
        log.info("application restart")
        self._status = Status.restart
        self.status()
        time.sleep(2)

        #TODO: launch sensOCampus as a service
        '''
        [nov.17] find a proper way for python application to restart itself (e.g supervisord ?)
        import os
        import sys
        import psutil

        try:
            p = psutil.Process(os.getpid())
            for handler in p.get_open_files() + p.connections():
                os.close(handler.fd)
        except Exception as ex:
            pass

        python = sys.executable
        os.execl(python, python, *sys.argv)
        '''
        self.reboot()


    def reboot(self):
        log.info("device reboot")
        self._status = Status.reboot
        self.status()
        time.sleep(2)

        self.shutdown()

        import os
        os.system('sudo reboot')


    def update(self):
        log.info("configuration update")
        self._status = Status.update
        self.status()
        time.sleep(2)

        self._configuration.update()


    def upgrade(self):
        log.info("application upgrade")
        self._status = Status.upgrade
        self.status()
        time.sleep(2)

        '''
        # [nov.17] find a proper way for the application to upgrade itself
        self.reinstall()
        '''
        import os
        #os.system('sudo upgrade')
        #TODO: set proper path automatically
        os.system("/root/neocampus_rpi/git-pull.sh")
        time.sleep(2)

        self.restart()


    def reinstall(self):
        log.info("reinstall whole Raspberry Pi!")
        self._status = Status.reinstall
        self.status()
        time.sleep(2)

        self.shutdown()

        import os
        os.system('sudo reinstall')
        

    @property
    def status_backend(self):
        return self._status_backend

    @status_backend.setter
    def status_backend(self,value):
        self._status_backend = value

    @property
    def status_modules(self):
        return self._status_modules

    @status_modules.setter
    def status_modules(self,value):
        self._status_modules = value


    def status(self):
        if( not self._configuration.initialized() or not self._connection.connected() ):
            return
        
        log.info("status report")

        # acquire lock
        with self._status_lock:

            # reset timer
            self._status_timer.cancel()

            report = dict()
            report['unitID'] = settings.MAC_ADDR
            report['status'] = str(self._status)

            # backend status function ?
            if callable(self._status_backend):
                report['backend'] = self._status_backend()
            elif(self._status_backend is not None):
                report['backend'] = str(self._status_backend)

            # modules status function ?
            if callable(self._status_modules):
                report['modules'] = self._status_modules()
            elif(self._status_modules is not None):
                report['modules'] = str(self._status_modules)

            self._connection.send(json.dumps(report))

            # start timer anew ... if not in shutdown mode
            if( not self._shutdown_event.is_set() ):
                self._status_timer = threading.Timer(__class__.TIMER_STATUS_REPORT, self.status)
                self._status_timer.start()


    def handle_command(self, com):
        if 'dest' not in com:
            log.error("received a command without 'dest' field ?!?!")
            return
        if ( com['dest'].lower() != settings.MAC_ADDR.lower() ) and ( com['dest'].lower() != 'all' ):
            log.debug("received a command but not for me")
            return

        if 'order' not in com:
            log.error("received a command without 'order' field ?!?!")
            return
            
        if str(com['order']).lower() == 'reset':
            self.reset()

        if str(com['order']).lower() == 'restart':
            self.restart()

        if str(com['order']).lower() == 'reboot':
            self.reboot()

        if str(com['order']).lower() == 'update':
            self.update()

        if str(com['order']).lower() == 'upgrade':
            self.status()

        if str(com['order']).lower() == 'reinstall':
            self.status()

        if str(com['order']).lower() == 'status':
            self.status()

    def handle_working(self):
        self._status = Status.run
        self.status()
