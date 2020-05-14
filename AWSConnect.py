
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import logging
import time
import json
import argparse
from random import *
from logging.handlers import RotatingFileHandler
import sys


parser = argparse.ArgumentParser()
parser.add_argument("-e", "--environment", action="store", default="dev", dest="env", help="Environment to run this script: dev/prod")
parser.add_argument("-l", "--logLevel", action="store", default="info", dest="logLevel", help="Log level to capture")
args = parser.parse_args()

if args.env != "dev":
	sys.path.append("./sensorCodes")
	import Load_sensor
	import Vibration_3axis
	import temperature_sensor
	import motorController

host = "aqog91rucuuv3.iot.ap-southeast-1.amazonaws.com"
rootCAPath = "./certs/root-CA.crt"
certificatePath = "./certs/aircraftEngine.cert.pem"
privateKeyPath = "./certs/aircraftEngine.private.key"
clientId = "basicPubSub"

logFilePath = "./awsLogs.log"
thrustValue = 0
logger = None
myAWSIoTMQTTClient = None
myAWSIoTMQTTShadowClient = None
deviceShadowHandler = None
loggingFormat = '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
shadowObject = '{"state":{"desired":{"thrustValue":"0"}}}'

# Configure logging
def initialiseLogging():
	global logger, loggingFormat, logFilePath
	logger = logging.getLogger("AWSIoTPythonSDK.core")
	if args.logLevel == "debug":
		logger.setLevel(logging.DEBUG)
	elif args.logLevel == "info":
		logger.setLevel(logging.INFO)
	elif args.logLevel == "error":
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
	
	if args.env != "dev":
		Load_sensor.loggingFormat = loggingFormat
		Vibration_3axis.loggingFormat = loggingFormat
		temperature_sensor.loggingFormat = loggingFormat
		motorController.loggingFormat = loggingFormat
		Load_sensor.logFilePath = logFilePath
		Vibration_3axis.logFilePath = logFilePath
		temperature_sensor.logFilePath = logFilePath
		motorController.logFilePath = logFilePath
		Load_sensor.logLevel = args.logLevel
		Vibration_3axis.logLevel = args.logLevel
		temperature_sensor.logLevel = args.logLevel
		motorController.logLevel = args.logLevel
		
		motorController.setup()


# Init AWSIoTMQTTClient
def makeAWSConnections():
	global myAWSIoTMQTTClient, myAWSIoTMQTTShadowClient, deviceShadowHandler
	
	myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId, useWebsocket=True)
	myAWSIoTMQTTShadowClient.configureEndpoint(host, 443)
	myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath)

	# AWSIoTMQTTShadowClient configuration
	myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
	myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
	myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec
	
	# Connect and subscribe to AWS IoT
	myAWSIoTMQTTShadowClient.connect()
	
	myAWSIoTMQTTClient = myAWSIoTMQTTShadowClient.getMQTTConnection()
	
	# Create a deviceShadow with persistent subscription
	deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName("aircraftEngine", True)
	deviceShadowHandler.shadowUpdate(shadowObject, customShadowCallback_Update, 5)
	deviceShadowHandler.shadowRegisterDeltaCallback(customShadowCallback_Delta)



# Custom Shadow callback
def customShadowCallback_Delta(payload, responseStatus, token):
	global thrustValue
	# payload is a JSON string ready to be parsed using json.loads(...)
	# in both Py2.x and Py3.x
	logger.info(responseStatus)
	payloadDict = json.loads(payload)
	logger.info("++++++++DELTA++++++++++")
	logger.info("thrustValue: " + str(payloadDict["state"]["thrustValue"]))
	logger.info("version: " + str(payloadDict["version"]))
	logger.info("+++++++++++++++++++++++\n\n")
	thrustValue = int(payloadDict["state"]["thrustValue"])
	if args.env != "dev":
		Load_sensor.thrustValue = thrustValue
		Vibration_3axis.thrustValue = thrustValue
		temperature_sensor.thrustValue = thrustValue
		motorController.changeThrust(float(thrustValue))

#Subscribe To a topic
def subscribeToAWSTopic(topic, subAckCB, msgCB):
	myAWSIoTMQTTClient.subscribeAsync(topic, 1, ackCallback=subAckCB, messageCallback=msgCB)


# Custom Shadow callback
def customShadowCallback_Update(payload, responseStatus, token):
	if responseStatus == "timeout":
		logger.info("Update request " + token + " time out!")
	if responseStatus == "accepted":
		payloadDict = json.loads(payload)
		logger.info("~~~~~~~~~~~~~~~~~~~~~~~")
		logger.info("Update request with token: " + token + " accepted!")
		logger.info("property: " + str(payloadDict["state"]["desired"]["thrustValue"]))
		logger.info("~~~~~~~~~~~~~~~~~~~~~~~\n\n")
	if responseStatus == "rejected":
		logger.info("Update request " + token + " rejected!")


# Suback callback
def subAckCallback(mid, data):
	logger.info("Received SUB-ACK")

initialiseLogging()
logger.info("Making AWS Connections")
makeAWSConnections()
time.sleep(2)

if args.env != "dev":
	Load_sensor.setup()
	Vibration_3axis.setup()
	temperature_sensor.setup()

	Load_sensor.myAWSIoTMQTTClient = myAWSIoTMQTTClient
	Vibration_3axis.myAWSIoTMQTTClient = myAWSIoTMQTTClient
	temperature_sensor.myAWSIoTMQTTClient = myAWSIoTMQTTClient
	
	Load_sensor.setupAndStartThread()
	Vibration_3axis.setupAndStartThread()
	temperature_sensor.setupAndStartThread()

loopCount = 0
while True:
	try:
		loopCount += 1
		if args.env != "dev":
			if loopCount%10 == 0:
				logger.info("Running main thread in PROD")
			else:
				logger.debug("Running main thread in PROD")
		else:
			if loopCount%10 == 0:
				logger.info("Running main thread in dev")
			else:
				logger.debug("Running main thread in dev")
			message = {}
			message["seqNum"] = loopCount
			messageJson = json.dumps(message)
			topicToSend = ["temperatureSensor", "vibrationSensor", "loadSensor"]
			if thrustValue != 0:
				top = topicToSend[randint(0, 2)]
				myAWSIoTMQTTClient.publishAsync(top, messageJson, 1)
				logger.info('Published topic %s: %s' % (top, messageJson))
		time.sleep(2)
	except:
		logger.info("Exiting..!")
		Load_sensor.cleanAndExit()
		Vibration_3axis.cleanAndExit()
		temperature_sensor.cleanAndExit()
