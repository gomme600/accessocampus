#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# sensOCampus configuration module
#
# Thiebolt F.   Oct.17 take parameters 'server' and 'port' from credentials
# T.Bueno       May.16 initial commit
#



# #############################################################################
#
# Import zone
#
import requests
import configparser
from urllib.parse import urljoin
import validictory
import json
import os.path
import time

# sensOCampus' devices related import
import settings as settings
import protocol as protocol
from logger import log
from exceptions import *



# #############################################################################
#
# Class
#
class Configuration(object):

    _initialized = None
    _login = None
    _password = None
    _server = None
    _port = None
    _topics = None
    _modules = None

    def __init__(self):

        self._initialized = False
        log.debug("configuration initialization started")

        # try to load the configuration file
        # (at least to retrieve the password if any)
        self.load()

        while not self._initialized:

            # retrieve CREDENTIALS from HTTP(S) and create config file
            if not self.httpGetCredentials() or not self.load():
                log.debug("failed to retrieve CREDENTIALS ... reset ... sleeping 10s ...")
                self.reset()
                time.sleep(10)
                continue

            # connect to senOCampus and retrieve CONFIG from HTTP(S)
            if self.update() != True:
                log.error("failed to retrieve CONFIG from sensOCampus ... reset CREDENTIALS and restart ...")
                self.reset()
                time.sleep(10)
            else:
                log.info("device's CONFIG successfully loaded, device is initialized :)")

        # success :)

    def load(self):
        ''' Load CREDENTIALS from config file '''
        if self._initialized:
            log.debug("configuration already initialized, stopping")
            return True

        if not self.exists():
            log.info("either config file does not exists or is invalid")
            return False

        config = configparser.ConfigParser()
        rd = config.read(settings.CONFIG_FILE)

        self._login = config['credentials']['login']
        self._password = config['credentials']['password']
        self._server = (config['credentials']).get('server',settings.MQTT_HOST)
        self._port = int((config['credentials']).get('port',settings.MQTT_PORT))
        return True

    def exists(self):
        ''' Check if a valid CONFIG FILE containing CREDENTIALS exists ... '''
        log.debug("checking for existing configuration")

        if not os.path.exists(settings.CONFIG_DIR):
            try:
                os.makedirs(settings.CONFIG_DIR)
                log.debug("created CONFIG_DIR '%s'" % settings.CONFIG_DIR)
            except Exception as ex:
                log.error("unable to create CONFIG_DIR '%s' !?!?" % settings.CONFIG_DIR)
                return False

        if not os.path.isfile(settings.CONFIG_FILE):
            log.debug("config file not present")
            return False

        config = configparser.ConfigParser()
        rd = config.read(settings.CONFIG_FILE)

        if settings.CONFIG_FILE not in rd:
            log.debug("config file " + settings.CONFIG_FILE + " exists, but could not be opened")
            return False

        if 'credentials' not in config:
            log.debug("config file exists, but is missing credentials section")
            return False

        # minimum required in saved credentials are 'login' and 'password'
        if 'login' not in config['credentials']:
            log.debug("config file exists, but is missing login field")
            return False

        if 'password' not in config['credentials']:
            log.debug("config file exists, but is missing password field")
            return False

        log.debug("config file exists and is valid")
        return True

    def reset(self):
        ''' reset all credentials and DELETE configuration file '''
        self._login = None
        self._password = None
        self._server = None
        self._port = None
        self._topics = None
        self._initialized = False

        try:
            os.remove(settings.CONFIG_FILE)
        except Exception as ex:
            log.debug("exception while removing CONFIG_FILE: " + str(ex))

        if not os.path.exists(settings.CONFIG_DIR):
            try:
                os.makedirs(settings.CONFIG_DIR)
                log.debug("created CONFIG_DIR '%s'" % settings.CONFIG_DIR)
            except Exception as ex:
                log.error("unable to create CONFIG_DIR '%s' !?!?" % settings.CONFIG_DIR)

    def httpGetCredentials(self):
        ''' get credentials from sensOCampus and save them to CONFIG_FILE '''
        #self.reset()

        url = urljoin(settings.SENSO_ENDPOINT, "credentials")
        r = requests.get(url, params={'mac': settings.MAC_ADDR})

        if not r.ok:
            log.error("credentials were not delivered by server: status code " + str(r.status_code))
            return False

        conf = None
        try:
            conf = json.loads(r.text)
            validictory.validate(conf, protocol.SENSO_CREDENTIALS_SCHEMA)
        except Exception as ex:
            log.error("while validating credentials from server: " + str(ex))
            return False

        config = configparser.ConfigParser()
        config['credentials'] = {}
        config['credentials']['login'] = conf['login']

        # brand new config ?
        if self._login is None:
            # new config ...
            if "password" not in conf:
                log.error("no password provided while config file does not exists ?!?! ... FAILURE")
                return False
        # or maybe a new login ?
        elif conf['login'] != self._login and "password" not in conf:
            log.error("login changed but no new password provided ... FAILURE")
            return False

        if "password" in conf:
            config['credentials']['password'] = conf['password']
        elif self._password:
            config['credentials']['password'] = self._password
        else:
            log.error("no saved password and none provided :x")
            return False

        if "server" in conf:
            config['credentials']['server'] = conf['server']

        if "port" in conf:
            # configparser only want strings :|
            config['credentials']['port'] = str(conf['port'])

        # save CREDENTIALS in config file
        try:
            with open(settings.CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
        except Exception as ex:
            log.error("while writing conf in CONFIG_FILE: " + str(ex))
            return False

        return True

    def update(self):
        ''' try to retrieve CONFIGURATION from sensOCampus '''
        if not self.login() or not self.password():
            log.error("tried to grab CONFIG without credentials ?!?!")
            return False

        url = urljoin(settings.SENSO_ENDPOINT, "config")
        r = requests.get(url, auth=(self.login(), self.password()))

        if not r.ok:
            log.error("config was not delivered by server: status code " + str(r.status_code))
            return False

        conf = None
        try:
            conf = json.loads(r.text)
            validictory.validate(conf, protocol.SENSO_CONFIG_SCHEMA)
        except Exception as ex:
            log.error("while validating config from server: " + str(ex))
            return False
        else:
            log.debug("cur_conf = " + str(conf))
            self._topics = conf['topics']
            self._modules = conf['zones']
            # we now have both CREDENTIALS and CONFIG ...
            self._initialized = True

        return self._initialized

    def initialized(self):
        return self._initialized

    def login(self):
        return self._login

    def password(self):
        return self._password

    def topics(self):
        return self._topics

    def modules(self):
        return self._modules

    @property
    def server(self):
        return self._server

    @property
    def port(self):
        return self._port


#
# Execution of import
if __name__ == "__main__":

    conf = Configuration()
    print(conf.__dict__)

