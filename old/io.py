RELAY_PIN = 21

try:
    import RPi.GPIO as GPIO
except RuntimeError: 
    print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.output(RELAY_PIN, GPIO.HIGH)
