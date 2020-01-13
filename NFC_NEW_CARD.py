"""
This example shows connecting to the PN532 with I2C (requires clock
stretching support), SPI, or UART. SPI is best, it uses the most pins but
is the most reliable and universally supported.
After initialization, try waving various 13.56MHz RFID cards over it!
"""
import serial
import board
import busio
from digitalio import DigitalInOut
#
# NOTE: pick the import that matches the interface being used
#
from adafruit_pn532.i2c import PN532_I2C
#from adafruit_pn532.spi import PN532_SPI
#from adafruit_pn532.uart import PN532_UART
 
# I2C connection:
i2c = busio.I2C(board.SCL, board.SDA)
 
# Non-hardware
#pn532 = PN532_I2C(i2c, debug=False)
 
# With I2C, we recommend connecting RSTPD_N (reset) to a digital pin for manual
# harware reset
reset_pin = DigitalInOut(board.D6)
# On Raspberry Pi, you must also connect a pin to P32 "H_Request" for hardware
# wakeup! this means we don't need to do the I2C clock-stretch thing
req_pin = DigitalInOut(board.D12)
pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
 
# SPI connection:
#spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
#cs_pin = DigitalInOut(board.D5)
#pn532 = PN532_SPI(spi, cs_pin, debug=False)
 
# UART connection
#uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=100)
#uart = serial.Serial("/dev/ttyS0", baudrate=115200, timeout=10)
#pn532 = PN532_UART(uart, debug=False)
 
ic, ver, rev, support = pn532.get_firmware_version()
print('Found PN532 with firmware version: {0}.{1}'.format(ver, rev))
 
# Configure PN532 to communicate with MiFare cards
pn532.SAM_configuration()
 
print('Waiting for RFID/NFC card...')
while True:
    # Check if a card is available to read
    uid = pn532.read_passive_target(timeout=0.5)
    print('.', end="")
    # Try again if no card is available.
    if uid is None:
        continue
    print('Found card with UID:', [hex(i) for i in uid])
    card = list(uid)
    card_id = ""
    for block in card:  
        card_id += str(block)
    print("Card ID: ")
    print(card_id)

    answer = None
    while answer not in ("a", "r"):
        answer = input("add or remove card ? a/r: ")
        if answer == "a":
            add_card = True
            card_to_add = "---new card---" +  card_id + "---"
        elif answer == "r":
            add_card = False
            card_to_remove = "---new card---" +  card_id + "---"
            
        else:
    	    print("Please enter a or r.")

    if(add_card == True):
        fh = open("cards.conf", "a") 
        fh.write(card_to_add) 
        fh.close
    else:
        with open("cards.conf", "r") as f:
            lines = f.readlines()
        f.close()
        with open("cards.conf", "w") as f:
            for line in lines:
                if line.strip("\n") != card_to_remove:
                    f.write(line)
        f.close()
