#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Usefull Raspberry Pi functions
#
# F.Thiebolt Mar.18 added support for switching ON/OFF video output
# F.Thiebolt Jul.16 initial release
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
import socket
import fcntl
import struct
import subprocess

import time



# #############################################################################
#
# Global Variables
#



# #############################################################################
#
# Functions
#

# Return CPU temperature as a character string
def getCPUtemperature():
    res = os.popen('vcgencmd measure_temp').readline()
    return(res.replace("temp=","").replace("'C\n",""))

# Switch HDMI video output ON
def setHDMIon():
    res = os.popen('vcgencmd display_power 1').readline()
    return(res.replace("display_power=","").replace("\n",""))

# Switch HDMI video output OFF
def setHDMIoff():
    res = os.popen('vcgencmd display_power 0').readline()
    return(res.replace("display_power=","").replace("\n",""))

# Helper func to get mac
def getip(ifname):
    ''' returns IP of an interface '''
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24])
    except OSError:
        return None
    else:
        return ip


# Python decorator
# Return internal MAC addr of Raspberry Pi from OTP_rom
def _getmac(func):
    ''' Retrieve MAC address from OTP ROM of the Raspberry Pi
        Even valid with Pi0!'''
    def _wrapper(*args, **kwargs):
        _macaddr="00:00:00:00:00:00"
        if len(args):
            return func(*args, **kwargs)
        print("call to low-level _getmac")
        try:
            lines = subprocess.check_output(["vcgencmd","otp_dump"], universal_newlines=True)
        except (subprocess.CalledProcessError,FileNotFoundError) as ex:
            return _macaddr
    
        lines = lines.split('\n')
        
        for line in lines:
            if line.startswith("28:"):
                _submac=line.split(':')[1][2:]
                _macaddr="b8:27:eb:" + ':'.join([_submac[i:i+2] for i in range(0,len(_submac),2)])
                break;
        return _macaddr

    return _wrapper


# Return MAC addr of an interface
@_getmac
def getmac(interface=None):
    print("call to high level getmac")
    _ifaceDir = "/sys/class/net/"

    if not interface:
        # select current (active) one
        ifaces = next(os.walk(_ifaceDir))[1]
    else:
        ifaces = [interface, ]

    # Return the MAC address of in-use interface
    for i in ifaces:
        # local interface ?
        if i == "lo":
            continue

        # iface has an IP ?
        try:
            str = open("/sys/class/net/%s/address" % i, "r").readline()
        except:
            str = "00:00:00:00:00:00"

        _ip = getip(i)
        if not _ip:
            continue
        print("iface %s[%s] has IP %s" % (i, str[0:17], _ip));
        return str[0:17]



# #############################################################################
#
# MAIN
#

def main():
    '''Call the various utilities functions'''
    print("---")
    print("RPi's CPU current temerature is " + getCPUtemperature() + "°c" )
    
    print("---")
    print("RPi's MAC addr is " + getmac("eth0") )

    print("---")
    print("RPi's MAC addr is " + getmac() )


# Execution or import
if __name__ == "__main__":

    # Start executing
    main()


# The END - Jim Morrison 1943 - 1971
#sys.exit(0)

