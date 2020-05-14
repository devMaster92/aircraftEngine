from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import logging
import time
import json
import argparse
from random import *
from logging.handlers import RotatingFileHandler
import sys
import os

os.system("sudo pigpiod")

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
	import battery

# AWS IoT config
host = "aqog91rucuuv3.iot.ap-southeast-1.amazonaws.com"
rootCAPath = "./certs/root-CA.crt"
certificatePath = "./certs/aircraftEngine.cert.pem"
privateKeyPath = "./certs/aircraftEngine.private.key"
clientId = "basicPubSub"

start = time.time()
anomalyStartTime = time.time()
maxAnomalySec = 10
logFilePath = "./awsLogs.log"
thrustValue = 0
logger = None
batteryStatus = "Connected"
lastBatteryVoltage = 12
lastBatteryStatus = "Connected"
batteryVoltage = 12

myAWSIoTMQTTClient = None
myAWSIoTMQTTShadowClient = None

myAWSIoTMQTTClientVibration = None
myAWSIoTMQTTShadowClientVibration = None

myAWSIoTMQTTClientLoad = None
myAWSIoTMQTTShadowClientLoad = None

myAWSIoTMQTTClientTemp = None
myAWSIoTMQTTShadowClientTemp = None

deviceShadowHandler = None
loggingFormat = '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
shadowObject = {"state":{"desired":{"thrustValue":"0","triggerValue":0,"batteryStatus": "Connected","batteryVoltage": "12"}}}

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
		

def myOnOnlineCallback():
	global startshadowObject
	startshadowObject = {"state":{"desired":{"thrustValue":"0","triggerValue":0,"batteryStatus": "Connected","batteryVoltage": "12"}}}
	end = time.time()
	logger.info("Connection still active at" + str(end - start) +  " seconds")

def myOnOfflineCallback():
	global start
	end = time.time()
	logger.info("Connection went offline in " + str(end - start) +  " seconds")

# Init AWSIoTMQTTClient
def makeAWSConnections():
	global myAWSIoTMQTTClient, myAWSIoTMQTTShadowClient, deviceShadowHandler, myAWSIoTMQTTClientVibration, \
		myAWSIoTMQTTShadowClientVibration, myAWSIoTMQTTClientLoad, myAWSIoTMQTTShadowClientLoad, \
		myAWSIoTMQTTClientTemp, myAWSIoTMQTTShadowClientTemp, myOnOfflineCallback, myOnOnlineCallback, batteryStatus
	
	myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId, useWebsocket=True)
	myAWSIoTMQTTShadowClient.configureEndpoint(host, 443)
	myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath)
	# AWSIoTMQTTShadowClient configuration
	myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
	myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
	myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec
	myAWSIoTMQTTShadowClient.onOffline = myOnOfflineCallback
	myAWSIoTMQTTShadowClient.onOnline = myOnOnlineCallback
	# Connect and subscribe to AWS IoT
	myAWSIoTMQTTShadowClient.connect(60)
	myAWSIoTMQTTClient = myAWSIoTMQTTShadowClient.getMQTTConnection()
	
	
	myAWSIoTMQTTShadowClientVibration = AWSIoTMQTTShadowClient(clientId + "Vibration", useWebsocket=True)
	myAWSIoTMQTTShadowClientVibration.configureEndpoint(host, 443)
	myAWSIoTMQTTShadowClientVibration.configureCredentials(rootCAPath)
	# AWSIoTMQTTShadowClient configuration
	myAWSIoTMQTTShadowClientVibration.configureAutoReconnectBackoffTime(1, 32, 20)
	myAWSIoTMQTTShadowClientVibration.configureConnectDisconnectTimeout(10)  # 10 sec
	myAWSIoTMQTTShadowClientVibration.configureMQTTOperationTimeout(5)  # 5 sec
	# Connect and subscribe to AWS IoT
	myAWSIoTMQTTShadowClientVibration.connect(60)
	myAWSIoTMQTTClientVibration = myAWSIoTMQTTShadowClientVibration.getMQTTConnection()
	
	
	myAWSIoTMQTTShadowClientLoad = AWSIoTMQTTShadowClient(clientId + "Load", useWebsocket=True)
	myAWSIoTMQTTShadowClientLoad.configureEndpoint(host, 443)
	myAWSIoTMQTTShadowClientLoad.configureCredentials(rootCAPath)
	# AWSIoTMQTTShadowClient configuration
	myAWSIoTMQTTShadowClientLoad.configureAutoReconnectBackoffTime(1, 32, 20)
	myAWSIoTMQTTShadowClientLoad.configureConnectDisconnectTimeout(10)  # 10 sec
	myAWSIoTMQTTShadowClientLoad.configureMQTTOperationTimeout(5)  # 5 sec
	# Connect and subscribe to AWS IoT
	myAWSIoTMQTTShadowClientLoad.connect(60)
	myAWSIoTMQTTClientLoad = myAWSIoTMQTTShadowClientLoad.getMQTTConnection()
	
	
	myAWSIoTMQTTShadowClientTemp = AWSIoTMQTTShadowClient(clientId + "Temp", useWebsocket=True)
	myAWSIoTMQTTShadowClientTemp.configureEndpoint(host, 443)
	myAWSIoTMQTTShadowClientTemp.configureCredentials(rootCAPath)
	
	# AWSIoTMQTTShadowClient configuration
	myAWSIoTMQTTShadowClientTemp.configureAutoReconnectBackoffTime(1, 32, 20)
	myAWSIoTMQTTShadowClientTemp.configureConnectDisconnectTimeout(10)  # 10 sec
	myAWSIoTMQTTShadowClientTemp.configureMQTTOperationTimeout(5)  # 5 sec
	# Connect and subscribe to AWS IoT
	myAWSIoTMQTTShadowClientTemp.connect(60)
	myAWSIoTMQTTClientTemp = myAWSIoTMQTTShadowClientTemp.getMQTTConnection()
	
	# Create a deviceShadow with persistent subscription
	deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName("aircraftEngine", True)
	deviceShadowHandler.shadowUpdate(json.dumps(shadowObject), customShadowCallback_Update, 5) # 5 sec
	deviceShadowHandler.shadowRegisterDeltaCallback(customShadowCallback_Delta) # Updates motor thrust


# Custom Shadow callback
def customShadowCallback_Delta(payload, responseStatus, token):
	global thrustValue, shadowObject, anomalyStartTime
	# payload is a JSON string ready to be parsed using json.loads(...)
	# in both Py2.x and Py3.x
	logger.info(responseStatus)
	payloadDict = json.loads(payload)
	logger.info("++++++++DELTA++++++++++")
	logger.info("payload thrustValue: " + str(payloadDict["state"]["thrustValue"]))
	logger.info("local thrustValue: " + str(shadowObject["state"]["desired"]["thrustValue"]))
	logger.info("payload triggerValue: " + str(payloadDict["state"]["triggerValue"]))
	logger.info("local triggerValue: " + str(shadowObject["state"]["desired"]["triggerValue"]))
	logger.info("Battery Status: " + str(shadowObject["state"]["desired"]["batteryStatus"]))
	logger.info("Battery Voltage: " + str(shadowObject["state"]["desired"]["batteryVoltage"]))
	logger.info("version: " + str(payloadDict["version"]))
	logger.info("+++++++++++++++++++++++\n\n")
	currentShadowState = payloadDict["state"]
	thrustValue = int(payloadDict["state"]["thrustValue"])
	triggerValue = int(payloadDict["state"]["triggerValue"])
	if args.env != "dev":
		Load_sensor.thrustValue = thrustValue
		Vibration_3axis.thrustValue = thrustValue
		temperature_sensor.thrustValue = thrustValue
		if batteryStatus == "Connected":
			motorController.changeThrust(float(thrustValue))
		Load_sensor.triggerValue = triggerValue
		Vibration_3axis.triggerValue = triggerValue
		temperature_sensor.triggerValue = triggerValue
		#if triggerValue == 1:			
		logger.info("Anomaly Triggered")
		anomalyStartTime = time.time()
		motorController.triggerAnomaly(triggerValue,thrustValue)
		#Load_sensor.triggerValue = 0
		#Vibration_3axis.triggerValue = 0
		#temperature_sensor.triggerValue = 0
		#currentShadowState["triggerValue"] = 0
		shadowObject["state"]["desired"] = currentShadowState
		#deviceShadowHandler.shadowUpdate(json.dumps(shadowObject), customShadowCallback_Update, 5)

#Subscribe To a topic
def subscribeToAWSTopic(topic, subAckCB, msgCB):
	myAWSIoTMQTTClient.subscribeAsync(topic, 1, ackCallback=subAckCB, messageCallback=msgCB)

shadowObject
# Custom Shadow callback
def customShadowCallback_Update(payload, responseStatus, token):
	Load_sensor.triggerValue = 0
	Vibration_3axis.triggerValue = 0
	temperature_sensor.triggerValue = 0
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

	Load_sensor.myAWSIoTMQTTClient = myAWSIoTMQTTClientLoad
	Vibration_3axis.myAWSIoTMQTTClient = myAWSIoTMQTTClientVibration
	temperature_sensor.myAWSIoTMQTTClient = myAWSIoTMQTTClientTemp
	
	Load_sensor.setupAndStartThread() # Sends Load sensor readings to AWS
	Vibration_3axis.setupAndStartThread() # Sends vibration readings to AWS
	temperature_sensor.setupAndStartThread() # Sends temperature readings to AWS

# Redundant code that runs infinitely to keep threads from stopping
loopCount = 0
while True:
	try:
		batteryVoltage = 12
		logger.info("Detected voltage: " + str(batteryVoltage))
		if batteryVoltage > 5:
			batteryStatus = "Connected"
			
			if abs(batteryVoltage - lastBatteryVoltage) > 0.5 or lastBatteryStatus == "NotConnected":
				logger.info("Published Battery Voltage: " + str(batteryVoltage))
				shadowObject["state"]["desired"]["batteryStatus"] = batteryStatus
				shadowObject["state"]["desired"]["batteryVoltage"] = str(batteryVoltage)
				deviceShadowHandler.shadowUpdate(json.dumps(shadowObject), customShadowCallback_Update, 5) # 5 sec			
		else:
			batteryStatus = "NotConnected"
			if lastBatteryStatus == "Connected":
				motorController.cleanAndExit()

			if lastBatteryStatus == "Connected" or shadowObject["state"]["desired"]["thrustValue"] != "0" or shadowObject["state"]["desired"]["triggerValue"] != 0:
				logger.info("Published Battery status: " + batteryStatus)
				shadowObject["state"]["desired"]["thrustValue"] = "0"
				shadowObject["state"]["desired"]["triggerValue"] = 0
				shadowObject["state"]["desired"]["batteryVoltage"] = "0"
				shadowObject["state"]["desired"]["batteryStatus"] = batteryStatus
				deviceShadowHandler.shadowUpdate(json.dumps(shadowObject), customShadowCallback_Update, 5) # 5 sec
		
		lastBatteryStatus = batteryStatus
		lastBatteryVoltage =  batteryVoltage
		anomalyElapsedTime = time.time() - anomalyStartTime
		#logger.info("Global thrust value: " + str(thrustValue))
		#logger.info("anomalyElapsedTime is " + str(anomalyElapsedTime))
		#logger.info("Trigger state is " + str(shadowObject["state"]["desired"]["triggerValue"]))
		if (anomalyElapsedTime > maxAnomalySec) and int(shadowObject["state"]["desired"]["triggerValue"]) == 1:
			shadowObject["state"]["desired"]["triggerValue"] = 0
			deviceShadowHandler.shadowUpdate(json.dumps(shadowObject), customShadowCallback_Update, 5) # 5 sec
			motorController.triggerAnomaly(0,1)
			logger.info("Anomaly stopped after " + str(anomalyElapsedTime) + " due to safety reasons")
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
		time.sleep(1)
	except Exception as e:
		end = time.time()
		logger.info("Exiting in " + str(end - start) +  " seconds with error " + str(e))
		Load_sensor.cleanAndExit()
		Vibration_3axis.cleanAndExit()
		temperature_sensor.cleanAndExit()

