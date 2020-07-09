## Backends python packages ##
______________________________

This repository contains several python modules that implement neOCampus' backends like (non exhaustive):

- **PifaceIO** up to 8 x spi board that each features 8 digital inputs & 8 digital outputs,
- **ArdboxIO** Ardbox20 equipment connected through I2C bus to the RPi (see `tests/ardbox_stress.py`),
- **modbus** [TODO] to handle comms with a PLC (like our Wago one)
- **neoIO** [TODO] rather experimental where inputs / outputs are virtual ones that go through the MQTT broker ... maybe later ;)
- ...

'backend.py' implements the io_backend that maps all inputs and outputs from piface, ardbox etc in a uniform mapping:  

```
-----------------------------------------------------------------------------  
|   neOCampus IO mapping                                                    |  
-----------------------------------------------------------------------------  
| PiFaceIO       |   0 --> 99    | max. 8 Piface --> thus 64 I/O            |  
-----------------------------------------------------------------------------  
| ArboxIO        | 100 --> xxx   | max. 4 Arbox* --> thus 40 I/O            |  
-----------------------------------------------------------------------------  
```  

*Arbox: technically speaking, we can have up to 127 Ardbox per I2C bus, but since we want to ba able to reprogram each of them
through their serial link, we set only 4 Arbox each one being connected through a USB port to the RPi (USB hub to extend).


### Drivers python sub-package (i.e low-level backends) ###

These sub-packages handle low-level drivers mostly intended to i2c & spi chips among them:

- **TCN75A** very cheap i2c temperatre sensor with +/- 1°absolute precision
- **TSL2561** i2c dual sensors luminosity chip that compute lux values
- **MCP9808** [TODO] high precision temperature sensor (+/- 0.25°c absolute)
- ...

