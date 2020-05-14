


import RPi.GPIO as GPIO
import time
import logging
import Adafruit_PCA9685
from logging.handlers import RotatingFileHandler
import random
import pigpio

# PARAMETERS
CONTROL_PIN = 36
BUTTON_PIN = 32
DUTY_CYCLE = 100
ESC = 21 # Pin to connect ESC
MIN_VALUE = 500
MAX_VALUE = 2000

# Global Variables
pi = None
pwm = None
duty_cycle_list = [0,100,100,100,100]
current_duty_cycle = 0
loggingFormat = None
logFilePath = None
logLevel = None

def setup():
	global pi
	""" Initialise the PWM circuit and start """
	global pwm, current_duty_cycle, logger, ESC, pi, MAX_VALUE, MIN_VALUE
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
	# Initialise PWM and set the duty cycle
	# GPIO.setwarnings(False)
	# # Setup PWM
	# GPIO.setmode(GPIO.BOARD)
	# GPIO.setup(CONTROL_PIN, GPIO.OUT)
	
	# pwm = GPIO.PWM(CONTROL_PIN, 50)  # channel=CONTROL_PIN frequency=50Hz
	# pwm.start(0)
	try:
		pwm = Adafruit_PCA9685.PCA9685()
		pwm.set_pwm(0,0,0)
		
		logger.info("Unbalanced Motor Set up")
	except:
		logger.info("Could not set up engine, try doing sudo i2cdetect -y 1 in terminal")


def changeThrust(newVal):
	global pi, ESC, MIN_VALUE, MAX_VALUE
	try:
		logger.info("Setting thrust to: " + str(newVal))
		newVal = (newVal/100)*4050
		#newVal = MIN_VALUE + (MAX_VALUE - MIN_VALUE) * newVal / 100
		#logger.info("Setting thrust to: " + str(int(newVal)))
		pwm.set_pwm(0,0,int(newVal))
		#pi.set_servo_pulsewidth(ESC,newVal)
	except:
		logging.error("Could not set Value")
		cleanAndExit()



def cleanAndExit():
	global pi, ESC
	pwm.stop()
	logger.info("Dis-armed ESC")
	#pi.set_servo_pulsewidth(ESC,0)
	#pi.stop()
	#pi = None

def triggerAnomaly(trig,thrust):
	try:
		# Start the unbalance motor to induce anomaly
		if(trig == 1 and thrust != 0):
			GPIO.output(22,GPIO.HIGH)
		else:
			GPIO.output(22,GPIO.LOW)
		#time.sleep(random.uniform(0.5,1))
		#GPIO.output(11,GPIO.LOW)
		# time.sleep(1)
		# Update trigger shadow

	except:
		logging.error("Could not set Value")
		# Making sure the relay is turned off
		try: 
			GPIO.output(22,GPIO.LOW)
		except Exception as identifier:
			logger.info('Unbalanced motor error: ' + identifier)
			pass
