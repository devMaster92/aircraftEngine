import RPi.GPIO as GPIO
import time
import sys
from hx711 import HX711
from threading import Thread
import logging
from logging.handlers import RotatingFileHandler
import json
import calendar

def cleanAndExit():
    logger.info("Cleaning...")
    GPIO.cleanup()
    logger.info("Bye!")
    sys.exit()

hx = None
myAWSIoTMQTTClient = None
thrustValue = 0
triggerValue = 0
message = {}
thread = None
loggingFormat = None
logFilePath = None
logLevel = None

avgValue = 0
allVals = []

def setup():
    global hx, logger
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
    
    hx = HX711(5, 6)
    
    # I've found out that, for some reason, the order of the bytes is not always the same between versions of python, numpy and the hx711 itself.
    # Still need to figure out why does it change.
    # If you're experiencing super random values, change these values to MSB or LSB until to get more stable values.
    # There is some code below to debug and log the order of the bits and the bytes.
    # The first parameter is the order in which the bytes are used to build the "long" value.
    # The second paramter is the order of the bits inside each byte.
    # According to the HX711 Datasheet, the second parameter is MSB so you shouldn't need to modify it.
    hx.set_reading_format("LSB", "MSB")
    
    # HOW TO CALCULATE THE REFFERENCE UNIT
    # To set the reference unit to 1. Put 1kg on your sensor or anything you have and know exactly how much it weights.
    # In this case, 92 is 1 gram because, with 1 as a reference unit I got numbers near 0 without any weight
    # and I got numbers around 184000 when I added 2kg. So, according to the rule of thirds:
    # If 2000 grams is 184000 then 1000 grams is 184000 / 2000 = 92.
    #hx.set_reference_unit(113)
    hx.set_reference_unit(5091.04)
    hx.reset()
    hx.tare()
    logger.info("Load sensor set up done")

def getValue():
    global allVals, thrustValue
    try:
        GPIO.setmode(GPIO.BCM)
        startTime = time.time()
        # These three lines are usefull to debug wether to use MSB or LSB in the reading formats
        # for the first parameter of "hx.set_reading_format("LSB", "MSB")".
        # Comment the two lines "val = hx.get_weight(5)" and "print val" and uncomment the three lines to see what it prints.
        #np_arr8_string = hx.get_np_arr8_string()
        #binary_string = hx.get_binary_string()
        #print binary_string + " " + np_arr8_string
        
        # Prints the weight. Comment if you're debbuging the MSB and LSB issue.
        while time.time() - startTime < 1:
            val=hx.get_weight(5)
            # print val
    
            hx.power_down()
            hx.power_up()
            time.sleep(0.004)
            allVals.append(val)
        
        valToSend = sum(allVals) / len(allVals)
        # logger.info("Load sensor got value: " + str(sum(allVals) / len(allVals)) + " for " + str(len(allVals)))
        allVals = []
        loadJson = json.dumps({'timestamp' : int(time.time()*1000), 'value' : valToSend, 'thrust' : thrustValue, 'trigger' : triggerValue})
        #return str(valToSend
        return(loadJson)
    except Exception as e:
        logger.error(str(e))
        cleanAndExit()

def sendValueToAWS(topic, data):
    global myAWSIoTMQTTClient
    if myAWSIoTMQTTClient is not None and thrustValue != 0:
        # logger.info("Load sensor sending value: " + data)
        myAWSIoTMQTTClient.publishAsync(topic, data, 1)

def recursiveFunction():
    while True:
        sendValueToAWS("loadSensor", getValue())

def setupAndStartThread():
    global thread
    thread = Thread(target=recursiveFunction)
    thread.daemon = True # Setting true kills the threads when the main code is killed
    thread.start()
