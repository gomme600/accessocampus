#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# PiCamera backend ...
#   ... used as low-level driver by Camera module
#
# [feb.17] motion detection re-written with PiMotionAnalysis
# [aug.16] added auto-detect of CSI camera
#
# F.Thiebolt Feb.17
# F.Thiebolt Aug.16
# T.Bueno Apr.16
#



# #############################################################################
#
# Import zone
#
import io
import os
import time
import threading
import picamera
from picamera.array import PiMotionAnalysis
import numpy as np


# extend Python's library search path
import os
import sys
# sensOCampus
_path2add='../../sensocampus'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from logger import log



# #############################################################################
#
# Class
#
class MotionContainer(PiMotionAnalysis):

    # Class attributes
    MOTION_VECTORS      = 10    # nb 16x16 (pixels) macro-blocks that exhibi motion
    MOTION_MAGNITUDE    = 60    # vectors strenght threshold

    MFRAMES_QUEUE_SIZE  = 10    # max number of 'motion frames'

    # Attributes
    _mframes        = None  # previously recorded 'motion frames'
    _mframes_processing     = None  # list of processing time took for last mframes

    _motion_event   = None  # event used to signal motion detected for upward processing
    last_detected   = None  # last time motion has been detected    


    def __init__(self, camera, size=None, *args, **kwargs):
        super().__init__(camera, size)

        # compute motion vectors count and magnitude if not specified
        #TODO!
        
        self.last_detected = None
        self._motion_event = kwargs.get('event',None)

        # Motion parameters
        _mparams = kwargs.get('algorithm_params',None)
        if _mparams is not None and isinstance(_mparams,list):
            try:
                self.MOTION_VECTORS     = int(_mparams[0])
                self.MOTION_MAGNITUDE   = int(_mparams[1])
            except Exception as ex:
                log.warning("Exception setting motion_parameters: " + str(ex) )
                self.MOTION_VECTORS     = __class__.MOTION_VECTORS
                self.MOTION_MAGNITUDE   = __class__.MOTION_MAGNITUDE


        # last motion frames 
        self._mframes               = [None] * __class__.MFRAMES_QUEUE_SIZE
        self._mframes_processing    = [None] * __class__.MFRAMES_QUEUE_SIZE

        log.debug("[Motion] VECTORS=%d MAGNITUDE=%d" % (self.MOTION_VECTORS,self.MOTION_MAGNITUDE) )


    def analyse(self, a):
        _start = time.time()     # monitor execution time ...

        # Memorize last motion frames
        # incurs some processing penalties ...
        #self._mframes[1:]   = self._mframes[:-1]
        #self._mframes[0]    = a

        a = np.sqrt(
            np.square(a['x'].astype(np.float)) +
            np.square(a['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
        '''
        a = np.sqrt(
            np.square(a['x'].astype(np.uint16)) +
            np.square(a['y'].astype(np.uint16))
            ).clip(0, 255).astype(np.uint8)
        '''
        # If there're more than XX vectors with a magnitude greater than YY,
        # then set the last detected timestamp to now. Note: this is a really
        # crude method - I'm sure someone can do better with a bit of effort!
        # Things to try: filtering on SAD numbers, checking consecutive frames
        # for consistent motion in the same vectors, checking adjacent macro
        # blocks for similar motion vectors (to determine shape/size of moving
        # object). Then there's exposure, AWB, night/day cycles and such like
        # to compensate for
        vector_count = (a > self.MOTION_MAGNITUDE).sum()
        if vector_count > self.MOTION_VECTORS:
            self.detected = time.time()
            # signal motion detected
            self._motion_event.set()

        _end = time.time()     # monitor execution time ...

        self._mframes_processing[1:] = self._mframes_processing[:-1]
        self._mframes_processing[0] = (_end-_start)*(float)(1000)
        # display log messages only when motion is detected
        if vector_count > self.MOTION_VECTORS:
            log.debug("[motion detecetd] motion_vectors computation took %0.4fms" % self._mframes_processing[0] )



# #############################################################################
#
# Class
#
class VideoDumper(object):

    def write(self, data):
        log.warning("Not yet implemented :|")
        pass



# #############################################################################
#
# Class
#
class PiBackend(object):

    #
    # CLASS ATTRIBUTES
    DEFAULT_RESOLUTION  = (640,480)
    DEFAULT_FRAMERATE   = 10

    OVERLAY_FOREGROUND  = 'white'   # from picamera.Colors
    OVERLAY_BACKGROUND  = 'orange'  # from picamera.Colors

    # attributes
    _camera = None
    _motion = None
    _dumper = None

    def __init__(self):
        log.debug("loading pi camera backend")

        #self._motion = MotionContainer()
        #self._dumper = VideoDumper()

        try:
            # waiting for ressources to be free before access
            time.sleep(1)

            test = picamera.PiCamera()
            test.close()
            test = None

            log.info("pi camera initialized and terminated correctly, driver ready")

            # waiting for ressources to be free before returning
            time.sleep(1)

        except Exception as ex:
            log.info("pi video unavailable: " + str(ex))
            raise ex


    def capture(self, size=None, format='jpeg', count=1, interval=1):
        ''' method used to capture a frame or multiple frames with interval
            seconds between '''

        # Jpeg use hardware encoder so best is to use this format
        if self._camera is not None:
            io_stream = io.BytesIO()

            try:
                self._camera.capture(io_stream, resize=size, format=format, use_video_port=True)
            except picamera.exc.PiCameraRuntimeError as ex:
                log.error("capture failed, restarting driver: " + str(ex), exc_info=True)
                #self.disable()
                #self.enable()
                raise ex

            io_stream.seek(0)   # rewind to the beginning so we can read it
            # DEBUG
            #with open('/tmp/output.bin', 'wb') as another_open_file:
            #    another_open_file.write(io_stream.getbuffer())
            # DEBUG

            return io_stream
        else:
            log.warning("camera not started, unable to capture !")
            return None


    def motion(self):
        log.warning("not yet implemented")
        return None

    '''
        data = self._motion.value()
        if data is None:
            return False

        data = np.sqrt(
            np.square(data['x'].astype(np.float)) +
            np.square(data['y'].astype(np.float))
        ).clip(0, 255).astype(np.uint8)

        # If there're more than 5 vectors with a magnitude greater
        # than 1, then say we've detected motion
        if (data > 1).sum() > 5:
            return True

        return False

    def ready(self):
        return isinstance(self._camera, picamera.PiCamera)
    '''

    def status(self,msg):
        msg['resolution'] = str(self._camera.resolution)
        msg['frame_rate'] = str(self._camera.framerate)


    def enable(self, resolution=None, framerate=None, algorithm=None, *args, **kwargs ):
        try:
            self._camera = None
            time.sleep(1)
            self._camera = picamera.PiCamera()
            time.sleep(2)   # for AWG and others parameters to get set properly ...

            if resolution is not None:
                self._camera.resolution = resolution
            else:
                self._camera.resolution = __class__.DEFAULT_RESOLUTION
            if framerate is not None:
                self._camera.framerate = framerate
            else:
                self._camera.framerate = __class__.DEFAULT_FRAMERATE

            # Overlays
            self._camera.annotate_foreground    = picamera.Color( kwargs.get('foreground_overlay', __class__.OVERLAY_FOREGROUND) )
            self._camera.annotate_background    = picamera.Color( kwargs.get('background_overlay', __class__.OVERLAY_BACKGROUND) )
            #TODO: add thread timer to add time to overlay
            self._camera.annotate_text          = kwargs.get('text_overlay', None)

            # Register Video & Motion containers
            self._dumper    = os.devnull    # default Video dumper
            self._motion    = None

            #DO WE NEED TO self._camera.wait_recording(1) from time to time ?

            log.info("%s camera resolution=%s, framerate=%d" % (__class__.__name__,str(self._camera.resolution),self._camera.framerate) )
            # select according to selected algorithm (if any)
            if algorithm is None:
                # No algorithm ==> passive camera
                log.debug("[no algorithm] passive camera waiting for orders ...")
                self._camera.start_recording(self._dumper, format='h264', motion_output=self._motion)
            elif str(algorithm).startswith('motion'):
                # Motion* algorithms
                log.debug("[motion] '%s' algorithm selected ..." % str(algorithm))
                self._motion    = MotionContainer(self._camera,**kwargs)
                self._camera.start_recording(self._dumper, format='h264', profile='baseline', bitrate=1000000, motion_output=self._motion)
            else:
                # fallback case
                log.debug("[unknown algorithm] '%s' ! (thus default to passive camera mode ---i.e waiting for orders)" % str(algorithm))
                self._camera.start_recording(self._dumper, format='h264', motion_output=self._motion)

        except Exception as ex:
            log.debug("exception while enabling pi video: " + str(ex), exc_info=True)
            # stop'n disable camera ...
            self.disable()

    def disable(self):
        try:
            self._camera.stop_recording()
            self._camera.close()
            time.sleep(1)
        except Exception as ex:
            log.error("exception while disabling video: " + str(ex), exc_info=True)

        self._camera = None
        self._motion = None
        self._dumper = None

