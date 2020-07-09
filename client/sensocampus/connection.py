#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sensOCampus (devices) MQTT connection management
#
# [nov.19] F.Thiebolt   added on_log messages
# [sep.17] F.Thiebolt
#   add support for MQTT disconnect / reconnect
# [may.16] T.Bueno
#



# #############################################################################
#
# Import zone
#
import json
import time
import validictory
import paho.mqtt.client as mqtt_client
from random import randint

# sensOCampus' devices related import
import settings as settings
import protocol as protocol
from logger import log


# #############################################################################
#
# Class
#
class Connection(object):

    _config = None
    _client = None
    _connected = False
    _topics = None

    on_command = None
    on_working = None

    def __init__(self, conf):

        self._client = mqtt_client.Client()
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe
        self._client.on_log = self._on_log
        self._client.username_pw_set(conf.login(), conf.password())
        self._config = conf
        self._connected = False

    def connect(self):
        # Start connection (blocking call)
        self._client.connect(self._config.server, self._config.port, settings.MQTT_KEEP_ALIVE)

        # Launch client loop
        self._client.loop_start()

    def send(self, msg):
        topic = self._config.topics()[0] + "/device"
        self._client.publish(topic, msg)

    def connected(self):
        return self._connected

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("connected to broker")
            self._connected = True

            # Subscribe to command topic
            self._topics = list(map(lambda t: "/".join([t, "device/command"]), self._config.topics()))
            sub_topics = list(map(lambda t: (t, 0), self._topics))
            log.debug("subscribing to " + str(self._topics))
            self._client.subscribe(sub_topics)

        if rc == 1:
            log.error("connection denied: protocol version mismatch")
        if rc == 2:
            log.error("connection denied: invalid client ID")
        if rc == 3:
            log.error("connection denied: server unavailable")
        if rc == 4:
            log.error("connection denied: invalid credentials")
        if rc == 5:
            log.error("connection denied: not authorized")

    def _on_disconnect(self, client, userdata, rc):
        log.debug("disconnected from MQTT broker with result code: " + str(rc))
        self._connected = False
        if rc == 0: return

        # unexpected disconnect ... we'll retry till death ...
        _time2sleep = randint( settings.MQTT_RECONNECT_DELAY, settings.MQTT_RECONNECT_DELAY**2 )
        while rc != 0:
            log.info("Unexpected disconnection ... sleeping %d seconds before retrying" % _time2sleep)
            time.sleep(_time2sleep)
            log.info("... trying to reconnect ...")
            try:
                rc = self._client.reconnect()
            except Exception as ex:
                log.info("caught exception while mqtt reconnect: " + str(ex) )
                rc = -1
            if rc==0: break
            _time2sleep = _time2sleep*2 if (_time2sleep*2) < 300 else 300   # max. 5mn between two retrials

        # successfully reconnected
        log.info("ok, reconnect was a success ... waiting for on_connect callback ...")


    def _on_message(self, client, userdata, msg):
        log.debug("message received on topic " + msg.topic)

        if msg.topic not in self._topics:
            # this client is not concerned by this message, returning
            return

        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            validictory.validate(payload, protocol.MQTT_COMMAND_SCHEMA)
        except Exception as ex:
            log.error("exception handling json payload: " + str(ex))
            return
        else:
            if callable(self.on_command):
                self.on_command(payload)

    def _on_publish(self, client, userdata, mid):
        log.debug("mid: " + str(mid) + " published!")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        log.debug("Subscribed: " + str(mid) + " " + str(granted_qos))

        if callable(self.on_working):
            self.on_working()

    # [nov.19] Francois
    def _on_log(self, client, userdata, level, buf):
        ''' print exception that may occur in callbacks '''
        # only printing ERR and WARN
        if( level == mqtt_client.MQTT_LOG_ERR or 
            level == mqtt_client.MQTT_LOG_WARNING ):
            print("[on_log][%s] %s" % (str(level),str(buf)))

