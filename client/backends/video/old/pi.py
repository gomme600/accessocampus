#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Camera module.
# Able to use either CSI camera, Lepton FLIR, others ??
# low-level drivers in ../backends/video
#
# [aug.16] added auto-detect of CSI camera
# F.Thiebolt Aug.16
#
# T.Bueno Apr.16
#



# #############################################################################
#
# Import zone
#
import io
import os
import time
import picamera
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
class MotionContainer(object):
    import threading

    _vectors = None
    _lock = threading.Lock()

    def write(self, data):
        self._lock.acquire()

        try:
            motion_data = np.frombuffer(
                data, dtype=[
                    ('x', 'i1'),
                    ('y', 'i1'),
                    ('sad', 'u2'),
                ])

            # TODO: slow and buggy, implement another method, not mandatory
            # width = 720
            # height = 480
            # cols = (width + 15) // 16
            # cols += 1  # there's always an extra column
            # rows = (height + 15) // 16
            #  motion_data = motion_data.reshape(rows, cols)
        except Exception as ex:
            log.debug("failed to compute motion: " + str(ex), exc_info=True)
        else:
            self._vectors = motion_data.copy()

        self._lock.release()

    def value(self):
        if isinstance(self._vectors, np.ndarray):
            return self._vectors.copy()



# #############################################################################
#
# Class
#
class VideoDumper(object):

    def write(self, data):
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

    # attributes
    _camera = None
    _motion = None
    _dumper = None

    def __init__(self):
        log.debug("loading pi camera backend")

        self._motion = MotionContainer()
        self._dumper = VideoDumper()

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
            log.error("pi video unavailable: " + str(ex))
            raise ex

    def capture(self, size=None, format='jpeg'):
        if self._camera:
            io_stream = io.BytesIO()

            try:
                self._camera.capture(io_stream, resize=size, format=format, use_video_port=True)
            except picamera.exc.PiCameraRuntimeError as ex:
                log.error("capture failed, restarting driver: " + str(ex), exc_info=True)
                self.disable()
                self.enable()

            return io_stream
        else:
            log.warning("failed to capture, camera not started")
            return None

    def motion(self):
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

    def enable(self, resolution=None, framerate=None, algorithm=None, *args, **kwargs ):
        try:
            self._camera = None
            time.sleep(1)
            self._camera = picamera.PiCamera()
            time.sleep(1)

            if resolution is not None:
                self._camera.resolution = resolution
            else:
                self._camera.resolution = __class__.DEFAULT_RESOLUTION
            if framerate is not None:
                self._camera.framerate = framerate
            else:
                self._camera.framerate = __class__.DEFAULT_FRAMERATE

            log.info("%s camera resolution=%s, framerate=%d" % (__class__.__name__,str(self._camera.resolution),self._camera.framerate) )
            # select according to selected algorithm (if any)
            if algorithm is None:
                # No algorithm ==> passive camera
                log.debug("[no algorithm] passive camera waiting for orders ...")
                self._camera.start_recording(self._dumper, format='h264', motion_output=self._motion)
            elif str(algorithm).startswith('motion'):
                # Motion* algorithms
                log.debug("[motion] '%s' algorithm selected ..." % str(algorithm))
                self._camera.start_recording('/dev/null', format='h264', profile='baseline', bitrate=1000000, motion_output=self._motion)
            else:
                # fallback case
                log.debug("[unknown algorithm] '%s' ! (thus default to passive camera mode ---i.e waiting for orders)" % str(algorithm))
                self._camera.start_recording(self._dumper, format='h264', motion_output=self._motion)

        except Exception as ex:
            log.debug("exception while enabling pi video: " + str(ex), exc_info=True)

            self.disable()

    def disable(self):
        try:
            self._camera.stop_recording()
            self._camera.close()
            time.sleep(1)
        except Exception as ex:
            log.error("exception while disabling video: " + str(ex), exc_info=True)

        self._camera = None

