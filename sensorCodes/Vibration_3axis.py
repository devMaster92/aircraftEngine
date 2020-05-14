# Simple demo of of the ADXL345 accelerometer library.  Will print the X, Y, Z
# axis acceleration values every half second.
# Author: Tony DiCola
# License: Public Domain
import time
import json
from threading import Thread
import logging
from logging.handlers import RotatingFileHandler
import sys
import calendar

# Import the ADXL345 module.
import Adafruit_ADXL345

accel = None
myAWSIoTMQTTClient = None
thrustValue = 0
triggerValue = 0
message = {}
thread = None
loggingFormat = None
logFilePath = None
logLevel = None
_x,_y,_z = 0,0,0
lastThrustValue = 0

def cleanAndExit():
    logger.info("Cleaning...")
    # Stop continuous conversion.  After this point you can't get data from get_last_result!
    logger.info("Bye!")
    sys.exit()

def setup():
    global accel, logger
    logger = logging.getLogger(__name__)
    if logLevel == "debug":
        logger.setLevel(logging.DEBUG)
    elif logLevel == "info":
        logger.setLevel(logging.INFO)
    elif logLevel == "error":
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)
    streamHandler = logging.StreamHandler()
    rollingFileHandler = RotatingFileHandler(logFilePath, maxBytes=10000, backupCount=4)
    formatter = logging.Formatter(loggingFormat)
    streamHandler.setFormatter(formatter)
    rollingFileHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.addHandler(rollingFileHandler)
    
    # Create an ADXL345 instance.
    accel = Adafruit_ADXL345.ADXL345()
    
    # Alternatively you can specify the device address and I2C bus with parameters:
    #accel = Adafruit_ADXL345.ADXL345(address=0x54, busnum=2)
    
    # You can optionally change the range to one of:
    #  - ADXL345_RANGE_2_G   = +/-2G (default)
    #  - ADXL345_RANGE_4_G   = +/-4G
    #  - ADXL345_RANGE_8_G   = +/-8G
    #  - ADXL345_RANGE_16_G  = +/-16G
    # For example to set to +/- 16G:
    accel.set_range(Adafruit_ADXL345.ADXL345_RANGE_16_G)
    
    # Or change the data rate to one of:
    #  - ADXL345_DATARATE_0_10_HZ = 0.1 hz
    #  - ADXL345_DATARATE_0_20_HZ = 0.2 hz
    #  - ADXL345_DATARATE_0_39_HZ = 0.39 hz
    #  - ADXL345_DATARATE_0_78_HZ = 0.78 hz
    #  - ADXL345_DATARATE_1_56_HZ = 1.56 hz
    #  - ADXL345_DATARATE_3_13_HZ = 3.13 hz
    #  - ADXL345_DATARATE_6_25HZ  = 6.25 hz
    #  - ADXL345_DATARATE_12_5_HZ = 12.5 hz
    #  - ADXL345_DATARATE_25_HZ   = 25 hz
    #  - ADXL345_DATARATE_50_HZ   = 50 hz
    #  - ADXL345_DATARATE_100_HZ  = 100 hz (default)
    #  - ADXL345_DATARATE_200_HZ  = 200 hz
    #  - ADXL345_DATARATE_400_HZ  = 400 hz
    #  - ADXL345_DATARATE_800_HZ  = 800 hz
    #  - ADXL345_DATARATE_1600_HZ = 1600 hz
    #  - ADXL345_DATARATE_3200_HZ = 3200 hz
    # For example to set to 6.25 hz:
    accel.set_data_rate(Adafruit_ADXL345.ADXL345_DATARATE_3200_HZ)
    
    getRawData()
    logger.info("Vibration sensor set up done")

# Baseline setup
def getRawData():
    global _x, _y, _z
    # collect smaples for a baseline
    logger.info("Collecting samples for baseline...")
    for i in range(int(2 / 0.05)):
        x, y, z = accel.read()
        _x, _y, _z = _x + x, _y + y, _z + z
        time.sleep(0.05)
    # compute the baseline
    _x, _y, _z = round(_x/(i+1.)), round(_y/(i+1.)), round(_z/(i+1.))
    logger.info("Initialization complete")

def getValue():
    global _x, _y, _z, thrustValue
    try:
        # Read the X, Y, Z axis positional values and print them.
        x, y, z = accel.read()
        # logger.debug('X={0}, Y={1}, Z={2}'.format(x, y, z))
        # Wait half a second and repeat.
        x = x - _x # Displacement in x-direction
        y = y - _y # Displacement in y-direction
        z = z - _z # Displacement in z-direction
        intensity = ((x ** 2 + y ** 2 + z ** 2) / 3) ** 0.5
        time.sleep(0.04)
        # message['x'] = x
        # message['y'] = y
        # message['z'] = z
        # logger.info("Vibration sensor got value: " + json.dumps(message))
        
        # Passsing data as JSON string to 
        #logger.info('Started JSON creation')
        #logger.info('timestamp ' + str(calendar.timegm(time.gmtime())))
        #logger.info('thrust' + str(thrustValue))
        vibrationJson = json.dumps({'timestamp' : int(time.time()*1000), 'value' : intensity, 'thrust' : thrustValue, 'trigger' : triggerValue})
        #logger.info(type(vibrationJson)
        
        #return str(intensity)
        return(vibrationJson)
    except Exception as e:
        logger.error(str(e))
        logger.info("Cleaning vibration...")
        logger.info("Bye!")
        sys.exit()

def sendValueToAWS(topic, data):
    global myAWSIoTMQTTClient
    if myAWSIoTMQTTClient is not None and thrustValue != 0:
        # logger.info("Vibration sensor sending value: " + data)
        myAWSIoTMQTTClient.publishAsync(topic, data, 1)

def recursiveFunction():
    global lastThrustValue, thrustValue
    while True:
        sendValueToAWS("vibrationSensor", getValue())
        # Setting AWS thrust to 0
        #logger.info("Last Thrust value: " +str(lastThrustValue) + " and current thrust value: " + str(thrustValue))
        
        if thrustValue == 0 and (lastThrustValue - thrustValue) > 0:
            logger.info("Dummy JSON with sent for thrust value 0")
            vibrationJson = json.dumps({'timestamp' : int(time.time()*1000), 'value' : 0, 'thrust' : 0, 'trigger' : 0})
            logger.info("Sent JSON: " + vibrationJson)
            myAWSIoTMQTTClient.publishAsync("vibrationSensor", vibrationJson, 1)

        lastThrustValue = thrustValue

def setupAndStartThread():
    global thread
    thread = Thread(target=recursiveFunction)
    thread.daemon = True # Setting true kills the threads when the main code is killed
    thread.start()