# Simple demo of continuous ADC conversion mode for channel 0 of the ADS1x15 ADC.
# Author: Tony DiCola
# License: Public Domain
import time

# Import the ADS1x15 module.
import Adafruit_DHT
from threading import Thread
import logging
from logging.handlers import RotatingFileHandler
import json
import calendar

def cleanAndExit():
	logger.info("Cleaning...")
	# Stop continuous conversion.  After this point you can't get data from get_last_result!
	adc.stop_adc()
	logger.info("Bye!")
	sys.exit()

myAWSIoTMQTTClient = None
thrustValue = 0
triggerValue = 0
message = {}
thread = None
loggingFormat = None
logFilePath = None
logLevel = None

def setup():
	global adc, logger
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

	# Create an ADS1115 ADC (16-bit) instance.
	#adc = Adafruit_ADS1x15.ADS1115()
	
	# Or create an ADS1015 ADC (12-bit) instance.
	#adc = Adafruit_ADS1x15.ADS1015()
	
	# Note you can change the I2C address from its default (0x48), and/or the I2C
	# bus by passing in these optional parameters:
	#adc = Adafruit_ADS1x15.ADS1015(address=0x49, busnum=1)
	
	# Choose a gain of 1 for reading voltages from 0 to 4.09V.
	# Or pick a different gain to change the range of voltages that are read:
	#  - 2/3 = +/-6.144V
	#  -   1 = +/-4.096V
	#  -   2 = +/-2.048V
	#  -   4 = +/-1.024V
	#  -   8 = +/-0.512V
	#  -  16 = +/-0.256V
	# See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
	#GAIN = 1
	
	# Start continuous ADC conversions on channel 0 using the previously set gain
	# value.  Note you can also pass an optional data_rate parameter, see the simpletest.py
	# example and read_adc function for more infromation.
	#adc.start_adc(0, gain=GAIN)
	# Once continuous ADC conversions are started you can call get_last_result() to
	# retrieve the latest result, or stop_adc() to stop conversions.
	
	# Note you can also call start_adc_difference() to take continuous differential
	# readings.  See the read_adc_difference() function in differential.py for more
	# information and parameter description.
	logger.info("Temperature sensor set up done")

def getValue():
	global thrustValue
	try:
		# These three lines are usefull to debug wether to use MSB or LSB in the reading formats
		# for the first parameter of "hx.set_reading_format("LSB", "MSB")".
		# Comment the two lines "val = hx.get_weight(5)" and "print val" and uncomment the three lines to see what it prints.
		#np_arr8_string = hx.get_np_arr8_string()
		#binary_string = hx.get_binary_string()
		#print binary_string + " " + np_arr8_string
		
		humidity, value = Adafruit_DHT.read_retry(11, 4)
		# Prints the weight. Comment if you're debbuging the MSB and LSB issue.
		
		time.sleep(0.004)
		# logger.info("Temp sensor got value: " + str(value))
		temperatureJson = json.dumps({'timestamp' : int(time.time()*1000), 'value' : value, 'thrust' : thrustValue, 'trigger' : triggerValue})
		#return str(value)
		return(temperatureJson)
	except Exception as e:
		logger.error(str(e))
		cleanAndExit()


def sendValueToAWS(topic, data):
	global myAWSIoTMQTTClient
	if myAWSIoTMQTTClient is not None and thrustValue != 0:
		# logger.info("Temp sensor sending value: " + data)
		myAWSIoTMQTTClient.publishAsync(topic, data, 1)


def recursiveFunction():
	while True:
		sendValueToAWS("temperatureSensor", getValue())


def setupAndStartThread():
	global thread
	thread = Thread(target=recursiveFunction)
	thread.daemon = True # Setting true kills the threads when the main code is killed
	thread.start()
