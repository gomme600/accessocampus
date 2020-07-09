#!/usr/bin/env python3
# -*-coding:Utf-8-*
#
# TSL2561: I2C luminosity sensor
#   Light sensor featuring a dual sensor technology
#   to approximate light as perceived by a human eye
#
# Based on various versions found over the Internet :)
# especially Seanbehoffer's version.
#
# Thiebolt F.   oct.19  migrated to smbus2
# [Sep.16] luminosity module integration
# [Apr.16] migrated to python3
#
# F.Thiebolt Sep.16
#


# #############################################################################
#
# Import zone
#
import sys
import time

from smbus2 import SMBus

# extend Python's library search path
import os
import sys

# Helpers and i2c functions import
_path2add='../../libutils'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from HelpersFunc import *

# sensOCampus
_path2add='../../sensocampus'
if (os.path.exists(_path2add) and not os.path.abspath(_path2add) in sys.path):
    sys.path.append(os.path.abspath(_path2add))
from logger import log



# #############################################################################
#
# Class
#
class TSL2561(object):

    FULLSPECTRUM              = 0       # channel 0 (Visible light and IR)
    INFRARED                  = 1       # channel 1 (IR only)
    VISIBLE                   = 2       # channel 0 - channel 1 (i.e Visible light only)

    # i2c address options
    ADR_LOW                   = 0x29    # adr pin grounded
    ADR_FLOAT                 = 0x39    # floating adr pin
    ADR_HIGH                  = 0x49    # adr pin Vcc'ed

    # CLASS ATTRIBUTE
    _I2C_ADDRS = [  ADR_LOW, ADR_FLOAT, ADR_HIGH ]

    # Lux calculations differ slightly for CS package
    PACKAGE_CS                = 0
    PACKAGE_T_FN_CL           = 1

    READBIT                   = 0x01
    COMMAND_BIT               = 0x80    # Must be 1
    CLEAR_BIT                 = 0x40    # Clears any pending interrupt (write 1 to clear)
    WORD_BIT                  = 0x20    # 1 = read/write word (rather than byte)
    BLOCK_BIT                 = 0x10    # 1 = using block read/write

    CONTROL_POWERON           = 0x03
    CONTROL_POWEROFF          = 0x00

    LUX_LUXSCALE              = 14      # Scale by 2^14
    LUX_RATIOSCALE            = 9       # Scale ratio by 2^9
    LUX_CHSCALE               = 10      # Scale channel values by 2^10
    LUX_CHSCALE_TINT0         = 0x7517  # 322/11 * 2^    LUX_CHSCALE
    LUX_CHSCALE_TINT1         = 0x0FE7  # 322/81 * 2^    LUX_CHSCALE

    # T, FN, and CL package values
    LUX_K1T                   = 0x0040   # 0.125 * 2^RATIO_SCALE
    LUX_B1T                   = 0x01f2   # 0.0304 * 2^    LUX_SCALE
    LUX_M1T                   = 0x01be   # 0.0272 * 2^    LUX_SCALE
    LUX_K2T                   = 0x0080   # 0.250 * 2^RATIO_SCALE
    LUX_B2T                   = 0x0214   # 0.0325 * 2^    LUX_SCALE
    LUX_M2T                   = 0x02d1   # 0.0440 * 2^    LUX_SCALE
    LUX_K3T                   = 0x00c0   # 0.375 * 2^RATIO_SCALE
    LUX_B3T                   = 0x023f   # 0.0351 * 2^    LUX_SCALE
    LUX_M3T                   = 0x037b   # 0.0544 * 2^    LUX_SCALE
    LUX_K4T                   = 0x0100   # 0.50 * 2^RATIO_SCALE
    LUX_B4T                   = 0x0270   # 0.0381 * 2^    LUX_SCALE
    LUX_M4T                   = 0x03fe   # 0.0624 * 2^    LUX_SCALE
    LUX_K5T                   = 0x0138   # 0.61 * 2^RATIO_SCALE
    LUX_B5T                   = 0x016f   # 0.0224 * 2^    LUX_SCALE
    LUX_M5T                   = 0x01fc   # 0.0310 * 2^    LUX_SCALE
    LUX_K6T                   = 0x019a   # 0.80 * 2^RATIO_SCALE
    LUX_B6T                   = 0x00d2   # 0.0128 * 2^    LUX_SCALE
    LUX_M6T                   = 0x00fb   # 0.0153 * 2^    LUX_SCALE
    LUX_K7T                   = 0x029a   # 1.3 * 2^RATIO_SCALE
    LUX_B7T                   = 0x0018   # 0.00146 * 2^    LUX_SCALE
    LUX_M7T                   = 0x0012   # 0.00112 * 2^    LUX_SCALE
    LUX_K8T                   = 0x029a   # 1.3 * 2^RATIO_SCALE
    LUX_B8T                   = 0x0000   # 0.000 * 2^    LUX_SCALE
    LUX_M8T                   = 0x0000   # 0.000 * 2^    LUX_SCALE

    # CS package values
    LUX_K1C                   = 0x0043   # 0.130 * 2^RATIO_SCALE
    LUX_B1C                   = 0x0204   # 0.0315 * 2^    LUX_SCALE
    LUX_M1C                   = 0x01ad   # 0.0262 * 2^    LUX_SCALE
    LUX_K2C                   = 0x0085   # 0.260 * 2^RATIO_SCALE
    LUX_B2C                   = 0x0228   # 0.0337 * 2^    LUX_SCALE
    LUX_M2C                   = 0x02c1   # 0.0430 * 2^    LUX_SCALE
    LUX_K3C                   = 0x00c8   # 0.390 * 2^RATIO_SCALE
    LUX_B3C                   = 0x0253   # 0.0363 * 2^    LUX_SCALE
    LUX_M3C                   = 0x0363   # 0.0529 * 2^    LUX_SCALE
    LUX_K4C                   = 0x010a   # 0.520 * 2^RATIO_SCALE
    LUX_B4C                   = 0x0282   # 0.0392 * 2^    LUX_SCALE
    LUX_M4C                   = 0x03df   # 0.0605 * 2^    LUX_SCALE
    LUX_K5C                   = 0x014d   # 0.65 * 2^RATIO_SCALE
    LUX_B5C                   = 0x0177   # 0.0229 * 2^    LUX_SCALE
    LUX_M5C                   = 0x01dd   # 0.0291 * 2^    LUX_SCALE
    LUX_K6C                   = 0x019a   # 0.80 * 2^RATIO_SCALE
    LUX_B6C                   = 0x0101   # 0.0157 * 2^    LUX_SCALE
    LUX_M6C                   = 0x0127   # 0.0180 * 2^    LUX_SCALE
    LUX_K7C                   = 0x029a   # 1.3 * 2^RATIO_SCALE
    LUX_B7C                   = 0x0037   # 0.00338 * 2^    LUX_SCALE
    LUX_M7C                   = 0x002b   # 0.00260 * 2^    LUX_SCALE
    LUX_K8C                   = 0x029a   # 1.3 * 2^RATIO_SCALE
    LUX_B8C                   = 0x0000   # 0.000 * 2^    LUX_SCALE
    LUX_M8C                   = 0x0000   # 0.000 * 2^    LUX_SCALE

    REGISTER_CONTROL          = 0x00
    REGISTER_TIMING           = 0x01
    REGISTER_THRESHHOLDL_LOW  = 0x02
    REGISTER_THRESHHOLDL_HIGH = 0x03
    REGISTER_THRESHHOLDH_LOW  = 0x04
    REGISTER_THRESHHOLDH_HIGH = 0x05
    REGISTER_INTERRUPT        = 0x06
    REGISTER_CRC              = 0x08
    REGISTER_ID               = 0x0A
    REGISTER_CHAN0_LOW        = 0x0C
    REGISTER_CHAN0_HIGH       = 0x0D
    REGISTER_CHAN1_LOW        = 0x0E
    REGISTER_CHAN1_HIGH       = 0x0F

    INTEGRATIONTIME_13MS      = 0x00    # 13.7ms
    INTEGRATIONTIME_101MS     = 0x01    # 101ms
    INTEGRATIONTIME_402MS     = 0x02    # 402ms
    
    GAIN_0X                   = 0x00    # 1x gain (low gain)
    GAIN_16X                  = 0x10    # 16x gain
    GAIN_AUTO                 = 0x80    # auto gain

    REGISTER_ID_TSL2561       = 0x10    # ChipID code for TSL2561 (0x50 usually 0b0101xxxx)

    # default addr is floating pin
    address = ADR_FLOAT
    package = PACKAGE_T_FN_CL
    timing = INTEGRATIONTIME_402MS
    gain = GAIN_AUTO

    # either I2C bus number or I2C bus instance
    i2c         = None
    i2cbus      = None
    

    def __init__(self, address, i2cbus=-1, *args, **kwargs):
        ''' Sensor instance initialization '''
        self.address = address
        self.i2cbus = i2cbus
        log.info("Initializing '%s' device %#02x" % (self.__class__.__name__,self.address))
        try:
            # [oct.19] default i2c bus is 1 ;)
            self.i2c = SMBus(self.i2cbus if self.i2cbus >= 0 else 1)
        except Exception as ex:
            log.error("while creating I2C bus instance with bus=%d" % (self.i2cbus) + str(ex))
            raise ex

        # now check sensor is really what we expect
        self.validate_sensor()

        # set device default gain and timing
        ret = self.i2c.write_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_TIMING, (self.gain & ~self.GAIN_AUTO) | self.timing);
        #ret = self.i2c.write8(self.COMMAND_BIT | self.REGISTER_TIMING, (self.gain & ~self.GAIN_AUTO) | self.timing);
        if (ret == -1): raise IOError('device unreachable :(')


    def validate_sensor(self):
        """ read ChipID or something else to get sure it iw what we expect ... """
        # powerOn device
        self.enable()

        # ... now read status
        status = self.i2c.read_byte_data( self.address, self.COMMAND_BIT | self.CLEAR_BIT | self.REGISTER_CONTROL);
        #status = self.i2c.readU8(self.COMMAND_BIT | self.CLEAR_BIT | self.REGISTER_CONTROL);
        log.debug("status = %#02x" % status)
        if (status & 0b00000011) != self.CONTROL_POWERON:
            raise Exception("Sensor status does not match what we expected")
        # read registerID
        regID = self.i2c.read_byte_data( self.address, self.COMMAND_BIT | self.CLEAR_BIT | self.REGISTER_ID);
        #regID = self.i2c.readU8(self.COMMAND_BIT | self.CLEAR_BIT | self.REGISTER_ID);
        log.debug("RegisterID = %#02x" % regID)
        # [sep.16] model ID sends 0x50 instead of 0x10 ??
        if (regID & 0b11110000) != self.REGISTER_ID_TSL2561 and (regID & 0b11110000) == 0x00:
            raise Exception("ChipID does not match what we expected")

        # poweroff device
        self.disable()

        return True

    def setGain(self, gain=1):
        """ Set the gain, 1 --> 1X, 16 --> 16X, 0 --> auto"""
        if (gain==0):
            self.gain |= self.GAIN_AUTO
            return
        else:
            # disable auto gain anyway
            self.gain &= ~self.GAIN_AUTO

        if (gain==1):
            _gain = self.GAIN_0X
        else:
            _gain = self.GAIN_16X

        # do we need to update ?
        if (self.gain != _gain):
            self.gain = _gain
            # write settings to device
            self.i2c.write_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_TIMING, (self.gain & ~self.GAIN_AUTO) | self.timing);
            #self.i2c.write8(self.COMMAND_BIT | self.REGISTER_TIMING, (self.gain & ~self.GAIN_AUTO) | self.timing);
            log.debug("set gain %#02x" % (self.gain & ~self.GAIN_AUTO))

    def setTiming(self, timing=13):
        """ Set integration time in ms """
        if (timing <= 13):
            _timing = self.INTEGRATIONTIME_13MS
        elif (timing <= 101):
            _timing = self.INTEGRATIONTIME_101MS
        else:
            _timing = self.INTEGRATIONTIME_402MS

        # do we need to update ?
        if ( self.timing != _timing):
            self.timing = _timing
           # write settings to device
            self.i2c.write_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_TIMING, (self.gain & ~self.GAIN_AUTO) | self.timing);
            #self.i2c.write8(self.COMMAND_BIT | self.REGISTER_TIMING, (self.gain & ~self.GAIN_AUTO) | self.timing);
            log.debug("set integration time %#02x" % self.timing)

    def enable(self):
        """ PowerON device """
        # powerOn device
        self.i2c.write_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_CONTROL, self.CONTROL_POWERON);
        #self.i2c.write8(self.COMMAND_BIT | self.REGISTER_CONTROL, self.CONTROL_POWERON);

    def disable(self):
        """ PowerOFF device """
        # powerOff device
        self.i2c.write_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_CONTROL, self.CONTROL_POWEROFF);
        #self.i2c.write8(self.COMMAND_BIT | self.REGISTER_CONTROL, self.CONTROL_POWEROFF);

    def wait(self):
        if self.timing == self.INTEGRATIONTIME_13MS:
            _sleep=0.014
        if self.timing == self.INTEGRATIONTIME_101MS:
            _sleep=0.102
        if self.timing == self.INTEGRATIONTIME_402MS:
            _sleep=0.403
        # additional delay due to RPi's timer imprecision
        time.sleep(_sleep+0.02)

    def _getData(self):
        """ get channel0 (Visible + IR ---broadband)
            and channel1 (IR)
               return: broadband IR """
        self.enable()
        self.wait()
        
        # read channel 0 (Visible AND ir)
        # I2C block read for two bytes
        # Look the datasheet of TSL2561 page 18 : Application Information : SoftWare -> Basic Operation 
        _tmp = self.i2c.read_i2c_block_data( self.address, self.COMMAND_BIT | self.WORD_BIT | self.REGISTER_CHAN0_LOW, 2)
        #_tmp = self.i2c.readList( self.COMMAND_BIT | self.WORD_BIT | self.REGISTER_CHAN0_LOW, 2)
        chan0 = _tmp[0] | (_tmp[1]<<8)      

        log.debug("chan0=%#04X (chan0[0]=%#02X, chan0[1]=%#02X)" % (chan0, _tmp[0], _tmp[1]))
        _tmp[0] = self.i2c.read_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_CHAN0_LOW);
        #_tmp[0] = self.i2c.readU8(self.COMMAND_BIT | self.REGISTER_CHAN0_LOW);
        _tmp[1] = self.i2c.read_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_CHAN0_HIGH);
        #_tmp[1] = self.i2c.readU8(self.COMMAND_BIT | self.REGISTER_CHAN0_HIGH);
        log.debug("I2C single byte read --> (chan0[0]=%#02X, chan0[1]=%#02X)" % (_tmp[0], _tmp[1]))

        # read channel 1 (IR only)
        # I2C block read for two bytes
        _tmp = self.i2c.read_i2c_block_data( self.address, self.COMMAND_BIT | self.WORD_BIT | self.REGISTER_CHAN1_LOW, 2)
        #_tmp = self.i2c.readList( self.COMMAND_BIT | self.WORD_BIT | self.REGISTER_CHAN1_LOW, 2)
        chan1 = _tmp[0] | (_tmp[1]<<8)

        log.debug("chan1=%#04X (chan1[0]=%#02X, chan1[1]=%#02X)" % (chan1, _tmp[0], _tmp[1]))
        _tmp[0] = self.i2c.read_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_CHAN1_LOW);
        #_tmp[0] = self.i2c.readU8(self.COMMAND_BIT | self.REGISTER_CHAN1_LOW);
        _tmp[1] = self.i2c.read_byte_data( self.address, self.COMMAND_BIT | self.REGISTER_CHAN1_HIGH);
        #_tmp[1] = self.i2c.readU8(self.COMMAND_BIT | self.REGISTER_CHAN1_HIGH);
        log.debug("I2C single byte read --> (chan0[0]=%#02X, chan0[1]=%#02X)" % (_tmp[0], _tmp[1]))

        # switch off sensor 
        self.disable()  
        return chan0, chan1;

    def getLuminosity(self):
        """ compute best luminosity value if auto gain selected.
            Then send back channel0, channel1
            chan0 --> visible + IR
            chan1 --> IR only """
        
        chan0, chan1 = self._getData()

        # Do we need to change the gain ?
        # auto gain computation
        if ( (chan0 & 0xF000) == 0 and (chan1 & 0xF000) == 0 and (self.gain & ~self.GAIN_AUTO)==self.GAIN_0X):
            # set gain to 16 and get values
            
            log.debug("Set Gain to 16")
            
            self.setGain(16)
            return self._getData()

        if ( ((chan0 & 0xF000)==0xF000 or (chan1 & 0xF000)==0xF000) and ((self.gain & ~self.GAIN_AUTO))==self.GAIN_16X):
            # set gain to 1 and get values
            
            log.debug("Set Gain to 0")
            
            self.setGain(1)
            return self._getData()

        # To avoid to a "NotType Return"
        return chan0, chan1;
           
    def calculateLux(self, ch0, ch1):
        """ Compute Lux value according to ADC0 & ADC1 """
        # Inspired by the datasheet of TSL2561 algorithm "Application SoftWare : Simplified Lux Calculation"        

        # default is no scaling ... integration time = 402ms        
        # Set the Scale depending of the Integration Time
        chScale = (1 << self.LUX_CHSCALE);
        if self.timing == self.INTEGRATIONTIME_13MS:
            chScale = self.LUX_CHSCALE_TINT0
            log.debug("Lux Scale calcule : CHSCALE_TINT0")
        if self.timing == self.INTEGRATIONTIME_101MS:
            chScale = self.LUX_CHSCALE_TINT1
            log.debug("Lux Scale calcule : CHSCALE_TINT1")
         
        log.debug("Lux Scale after = %d" % chScale)
        
        # Scaling only if gain is x1
        if self.gain == 0:
            chScale = chScale << 4

        # scale the channel values
        channel0 = (ch0 * chScale) >> self.LUX_CHSCALE
        channel1 = (ch1 * chScale) >> self.LUX_CHSCALE

        # find the ratio of the channel values (Channel1/Channel0)
        ratio_tmp = 0
        if channel0 != 0:
            ratio_tmp = (channel1 << (self.LUX_RATIOSCALE+1)) // channel0

        # round the ratio value
        ratio = (ratio_tmp + 1) >> 1
        
        if self.package == self.PACKAGE_T_FN_CL:
            if (ratio >= 0) and (ratio <= self.LUX_K1T):  
                b = self.LUX_B1T
                m = self.LUX_M1T
            elif ratio <= self.LUX_K2T:
                b = self.LUX_B2T
                m = self.LUX_M2T
            elif ratio <= self.LUX_K3T:
                b = self.LUX_B3T
                m = self.LUX_M3T
            elif ratio <= self.LUX_K4T:
                b = self.LUX_B4T
                m = self.LUX_M4T
            elif ratio <= self.LUX_K5T:
                b = self.LUX_B5T
                m = self.LUX_M5T
            elif ratio <= self.LUX_K6T:
                b = self.LUX_B6T
                m = self.LUX_M6T
            elif ratio <= self.LUX_K7T:
                b = self.LUX_B7T
                m = self.LUX_M7T
            elif ratio > self.LUX_K8T:
                b = self.LUX_B8T
                m = self.LUX_M8T
        else:    
            # PACKAGE_CS otherwise
            if (ratio >= 0) and (ratio <= self.LUX_K1C):  
                b = self.LUX_B1C
                m = self.LUX_M1C
            elif ratio <= self.LUX_K2C:
                b = self.LUX_B2C
                m = self.LUX_M2C
            elif ratio <= self.LUX_K3C:
                b = self.LUX_B3C
                m = self.LUX_M3C
            elif ratio <= self.LUX_K4C:
                b = self.LUX_B4C
                m = self.LUX_M4C
            elif ratio <= self.LUX_K5C:
                b = self.LUX_B5C
                m = self.LUX_M5C
            elif ratio <= self.LUX_K6C:
                b = self.LUX_B6C
                m = self.LUX_M6C
            elif ratio <= self.LUX_K7C:
                b = self.LUX_B7C
                m = self.LUX_M7C
            elif ratio > self.LUX_K8C:
                b = self.LUX_B8C
                m = self.LUX_M8C

        temp = ((channel0 * b) - (channel1 * m))
        # do not allow negative lux value
        if temp < 0:
            temp = 0
        # round lsb (2^(LUX_SCALE-1))
        temp += (1 << (self.LUX_LUXSCALE-1))

        # strip off fractional portion
        lux = temp >> self.LUX_LUXSCALE

        # Signal I2C had no errors
        log.debug("Scale de : %d et gain : %#02X"  % (chScale, self.gain))
        
        return lux


    # -------------------------------------------------------------------------
    #
    # neOCampus generic interfaces
    # - detect()
    # - acquire()
    # - unitID()
    #
    # luminosity module method that will get called ...
    def acquire(self):
        ''' luminosity module will call this method '''
        ch0, ch1 = self.getLuminosity()
        return self.calculateLux(ch0, ch1)


    # identity of sensor (i2c bus and i2c addr combination)
    # [Nov.16] RPis only have a single i2c bus ... so we just send back i2c_addr
    def unitID(self):
        '''send back i2c addr'''
        return self.address


    @staticmethod
    def detect():
        ''' Automated sensors detection
                [ ("TSL2561", i2c_bus, adr),("TSL2561", i2c_bus, adr), ... ] '''
        log.debug("Trying to find-out sensors ...")

        sensorsList = []

        # scan i2c bus and try to match against possible i2c addr of sensor
        #TODO: scan all i2c buses
        i2cbus=-1
        addresses = []
        # scan and intersect ...
        addresses = list(set(TSL2561._I2C_ADDRS) & set(i2cScan(i2cbus)))
        if len(addresses)==0:
            print("no device found ... :|")
            return None

        # parse addresses list to check that device corresponds
        for adr in addresses:
            try:
                sensor = TSL2561(adr)
            except Exception as ex:
                pass
            else:
                # sensor detected ...
                _sensor_params = ( "TSL2561", i2cbus, adr )
                sensorsList.append(_sensor_params)
                del sensor

        # only return usefull parameters
        if len(sensorsList) == 0:
            return None
        return sensorsList



#
# Main application case
#
if __name__ == "__main__":

    # launch auto-detection
    sensorsList = TSL2561.detect()
    if sensorsList is None:
        raise Exception("No TSL2561 devices found")
    
    # parse list
    for (_,_,adr) in sensorsList:
        sensor = TSL2561(adr)

        # set auto gain (default) and get values
        sensor.setGain(0)

        print(time.strftime("%A %d %B %Y %H:%M:%S"))
        print("[0x%.02x] Luminosity = %d \n" % (sensor.unitID(),sensor.acquire()))
        del sensor

