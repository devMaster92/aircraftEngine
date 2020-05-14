/**
 * Created by yashu on 10/1/18.
 */

const app = require('express')();
const fs = require('fs');
const httpsOpts = {
    key: fs.readFileSync('./../keys/server.key', 'utf8'),
    cert: fs.readFileSync('./../keys/server.crt', 'utf8')
};
const https = require('https');

// Load the SDK for JavaScript
const AWS = require('aws-sdk');
const awsIoT = require('aws-iot-device-sdk');
// Set the region
AWS.config.update({ region: 'ap-southeast-1' });
// Create an SQS service object
const sqsVibration = new AWS.SQS({ apiVersion: '2012-11-05' });
const sqsLoad = new AWS.SQS({ apiVersion: '2012-11-05' });
const sqsTemp = new AWS.SQS({ apiVersion: '2012-11-05' });
const clientID = "thrustToggler_" + guid();
const shadowOptions = {
    keyPath: "./certs/aircraftEngine.private.key",
    certPath: "./certs/aircraftEngine.cert.pem",
    caPath: "./certs/root-CA.crt",
    clientId: clientID,
    host: "aqog91rucuuv3.iot.ap-southeast-1.amazonaws.com",
    region: "ap-southeast-1",
    protocol: "wss"
};
const thingShadows = awsIoT.thingShadow(shadowOptions);

let clientTokenGet;
let clientTokenUpdate;
let thingState = {"state":{"desired":{"thrustValue":"0","triggerValue":0}}};
let vibrationDataCache = [];
app.use(require('express').static('./UI_code/'));

//app.get('/aircraft-demo', function(req, res){
//    res.sendFile('./UI_code/aircraft.html');
// }

const server = https.createServer(httpsOpts, app).listen(8888);
const io = require('socket.io')(server);
const socketServer = io.of('/aircraft_demo');

console.log("Started server");

const timeOutVal = 10;
let thrustValue = 0;
let systemState = {state: { thrustValue: "0", triggerValue: 0, batteryVoltage: "0", batteryStatus: "NotConnected"}};
let systemStatus = "Offline"
const sensorDetails = {
    vibrationSensor: {
        queueURL: "https://sqs.ap-southeast-1.amazonaws.com/131195301981/digitalTwin_vibrationData_forUI",
        eventName: "vibration_data",
        fetching: false,
        capture: true,
        sqsOb: sqsVibration
    },
    loadSensor: {
        queueURL: "https://sqs.ap-southeast-1.amazonaws.com/131195301981/digitalTwin_loadData_forUI",
        eventName: "load_data",
        fetching: false,
        capture: true,
        sqsOb: sqsLoad
    },
    temperatureSensor: {
        queueURL: "https://sqs.ap-southeast-1.amazonaws.com/131195301981/digitalTwin_temperatureData_forUI",
        eventName: "temperature_data",
        fetching: false,
        capture: true,
        sqsOb: sqsTemp
    },
};
let pendingThrustValues = [0];
let canUpdateThrust = true;
let needToUpdateThrust = false;

socketServer.on('connect', socket => {
    console.log("One client on aircraftDemo");
    socketServer.emit('changeThrustValue', '' + thrustValue);
    socketServer.emit('changeAnomalyTrigger', '' + systemState.state.triggerValue);
    socketServer.emit('changeBatteryStatus', '' + systemState.state.batteryStatus);
    socketServer.emit('changeBatteryVoltage', '' + systemState.state.batteryVoltage);
    socketServer.emit('changeSystemStatus', '' + systemStatus);
    socket.on('changeThrust', newValue => {
        // console.log("changeThrust: " + newValue);
        pendingThrustValues.push(newValue);
        updateThrustValue();
    });
    socket.on('anomalyTrigger', triggerValue => {
        updateTriggerValue(triggerValue);
    });

    // Trigger file save on disconnect event
    /*socket.on('disconnect',function(){
        console.log("Wrting File to Disk ------------------------------")
        writeDataToFile("../data/vibration_data_" + ((new Date()).getTime() / 1000), JSON.stringify(vibrationDataCache))
    });*/
});

thingShadows.on('connect', function() {
    console.log("Connected thing shadows API");
    thingShadows.register('aircraftEngine', { debug: false }, function() {
        clientTokenGet = thingShadows.get("aircraftEngine");
        console.log("Getting state with token: " + clientTokenGet);
    });
});

thingShadows.on('delta', 
    function(thingName, stateObject) {
       console.log('received delta on '+thingName+': '+ JSON.stringify(stateObject));
       thingState = { "state": { "desired": stateObject.state}};
    
       // Resetting AWS state based on last update time
       //console.log(Math.floor((new Date()).getTime() / 1000))
       //console.log(stateObject.metadata.desired.thrustValue.timestamp)
       //console.log("Updated before :" + (stateObject.metadata.desired.thrustValue.timestamp - Math.floor((new Date()).getTime() / 1000)) + " seconds")
       if (Math.floor((new Date()).getTime() / 1000) - stateObject.metadata.thrustValue.timestamp > 60) {
            console.log("Thrust value reset to 0 due to inactivity")
            thingState.state.desired.thrustValue = 0;  
            thingState.state.desired.triggerValue = 0;
            clientTokenUpdate = thingShadows.update('aircraftEngine', thingState);
            if (clientTokenUpdate === null) {
                console.log('update shadow failed, operation still in progress');
            } else {
                canUpdateThrust = false;
            }
        }
        thrustValue = parseInt(stateObject.state.thrustValue);
        systemState = stateObject
        socketServer.emit('changeThrustValue', '' + thrustValue);
        socketServer.emit('changeAnomalyTrigger', '' + stateObject.state.triggerValue);
        socketServer.emit('changeBatteryStatus', '' + stateObject.state.batteryStatus);
        socketServer.emit('changeBatteryVoltage', '' + stateObject.state.batteryVoltage);
    });

thingShadows.on('status', function(thingName, stat, clientToken, stateObject) {
    console.log('received ' + stat + ' on ' + thingName + ': ' + JSON.stringify(stateObject));
    
    if (stat == "accepted"){
        
        if (clientToken == clientTokenGet) {
            console.log("Got thrust value to be: " + stateObject.state.desired.thrustValue);
            thrustValue = parseInt(stateObject.state.desired.thrustValue);
            socketServer.emit('changeThrustValue', '' + thrustValue);
        } else if (clientToken == clientTokenUpdate) {
            thrustValue = parseInt(stateObject.state.desired.thrustValue);
            socketServer.emit('changeThrustValue', '' + thrustValue);
            // console.log("Done updating thing Shadow to thrust value: " + thrustValue);
        } else {
            console.log("unknown thrust update, check who is updating: " + clientToken);
        }
        canUpdateThrust = true;
        if (needToUpdateThrust) {
            updateThrustValue();
        }
        pendingThrustValues = [];
    }
});

thingShadows.on('timeout', function(thingName, clientToken) {
    console.log('received timeout on ' + thingName + ' with token: ' + clientToken);
});

function guid() {
    function s4() {
        return Math.floor((1 + Math.random()) * 0x10000)
            .toString(16)
            .substring(1);
    }
    return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
        s4() + '-' + s4() + s4() + s4();
}

function getDataAndSendToUI() {
    //if (thrustValue != 0) {
        for (let i = 0; i < Object.keys(sensorDetails).length; i++) {
            if (sensorDetails[Object.keys(sensorDetails)[i]].capture && !sensorDetails[Object.keys(sensorDetails)[i]].fetching) {
                const eventName = sensorDetails[Object.keys(sensorDetails)[i]].eventName;
                const queueURL = sensorDetails[Object.keys(sensorDetails)[i]].queueURL;
                const sqsOb = sensorDetails[Object.keys(sensorDetails)[i]].sqsOb;
                //console.log(sqsOb+ " || " +Object.keys(sensorDetails)[i]+ " || " +eventName+ " || " +queueURL);
                getDataFromSQSQueue(sqsOb, Object.keys(sensorDetails)[i], eventName, queueURL);
            }
        }
    //}
    setTimeout(getDataAndSendToUI, timeOutVal);
    // getDataAndSendToUI();
}

getDataAndSendToUI();

function emitDataToUI(sensorName, eventName, data) {
    sensorDetails[sensorName].fetching = false;
    if (data.length != 0){
        socketServer.emit(eventName, data);
        // Writing vibration readings into vibrationDataCache to be saved at end of session
        /*if (eventName == "vibration_data") {
            vibrationDataCache = vibrationDataCache.concat(data)
        }*/
    }
    storeValuesInObject(sensorName, data);
    // console.log("Sent data on: " + eventName + " data: " + JSON.stringify(data));
}

function getDataFromSQSQueue(sqsOb, sensorName, eventName, queueURL) {
    sensorDetails[sensorName].fetching = true;
    if (queueURL.trim().length != 0) {
        const params = {
            AttributeNames: [
                "All"
            ],
            MaxNumberOfMessages: 10,
            MessageAttributeNames: [
                "All"
            ],
            QueueUrl: queueURL,
            VisibilityTimeout: 300,
            WaitTimeSeconds: 20
        };
        const deleteParams = {
            Entries: [],
            QueueUrl: queueURL
        };
        // console.log("receiving from Queue: " + queueURL);
        sqsOb.receiveMessage(params, function(err, data) {
            if (err) {
                console.log("Receive Error", err);
            } else if (data.Messages) {
                const msgsObject = [];
                const entries = [];
                for (let i = 0; i < data.Messages.length; i++) {
                    entries.push({
                        Id: 'deleteMsgID_' + i,
                        ReceiptHandle: data.Messages[i].ReceiptHandle
                    });
                    //console.log("SQS message " + JSON.parse(data.Messages[i].Body).Message);
                    /*msgsObject.push({
                        timestamp: (new Date(JSON.parse(data.Messages[i].Body).Timestamp)).valueOf(),
                        value: JSON.parse(data.Messages[i].Body).Message
                    }); */
                    
                    let receivedJSON = JSON.parse(JSON.parse(data.Messages[i].Body).Message);
                    console.log("Received JSON: " + JSON.stringify(receivedJSON));
                    if ('timestamp' in receivedJSON){
                        receivedJSON.timestamp = (new Date(receivedJSON.timestamp)).valueOf();
                    }
                    msgsObject.push(receivedJSON);
                    // console.log(((new Date()).valueOf() - (new Date(parseInt(data.Messages[i].Attributes.SentTimestamp)))) / 1000);
                }
                //console.log(sensorName + " " + eventName + " " + JSON.stringify(msgsObject));
                emitDataToUI(sensorName, eventName, msgsObject);
                deleteParams.Entries = entries;
                sqsOb.deleteMessageBatch(deleteParams, function(err, data) {
                    if (err) {
                        console.log("Delete Error", err);
                    } else {
                        // console.log("Message Deleted");
                    }
                });
            } else {
                console.log("No data found " + data);
                emitDataToUI(sensorName, eventName, []);
            }
        });
    } else {
        console.log("URL not found");
        emitDataToUI(sensorName, eventName, []);
    }
}

function updateThrustValue() {
    // console.log("In update thrust: " + canUpdateThrust);
    if (canUpdateThrust == true) {
        needToUpdateThrust = false;
        //const newState = { "state": { "desired": { "thrustValue": pendingThrustValues[pendingThrustValues.length - 1] } } 
        //clientTokenUpdate = thingShadows.update('aircraftEngine', newState);
        //console.log(pendingThrustValues.length);
        //console.log(pendingThrustValues[pendingThrustValues.length - 1]);
        //console.log(JSON.stringify(thingState));
        console.log("Updating thrust from " + thingState.state.desired.thrustValue + " to " + pendingThrustValues[pendingThrustValues.length - 1])
        thingState.state.desired.thrustValue = {};
        thingState.state.desired.thrustValue = pendingThrustValues[pendingThrustValues.length - 1]
        console.log("Throttle: " + thingState)
        clientTokenUpdate = thingShadows.update('aircraftEngine', thingState);
        if (clientTokenUpdate === null) {
            console.log('update shadow failed, operation still in progress');
        } else {
            canUpdateThrust = false;
        }
    } else {
        console.log("Cannot update right now.");
        needToUpdateThrust = true;
    }
}

function updateTriggerValue(val) {
    console.log("Updating trigger from " + thingState.state.desired.triggerValue + " to " + val)
    thingState.state.desired.triggerValue = {};
    thingState.state.desired.triggerValue = val;
    console.log("Trigger: " + thingState);
    clientTokenUpdate = thingShadows.update('aircraftEngine', thingState);
    if (clientTokenUpdate === null) {
        console.log('trigger update shadow failed, operation still in progress');
    } else {
        console.log('trigger update shadow successful');
    }
}

//TODO: Remove this after testing
const allSensorData = {};

function storeValuesInObject(sensorName, data) {
    if (!allSensorData.hasOwnProperty(sensorName)) {
        allSensorData[sensorName] = {};
        allSensorData[sensorName].collecting = true;
        allSensorData[sensorName].values = [];
    }
    if (allSensorData[sensorName].collecting === true) {
        allSensorData[sensorName].values = allSensorData[sensorName].values.concat(data);
        //console.log("Sensor: " + sensorName + " data: " + JSON.stringify(data));
        //console.log("Sensor: " + sensorName + " data: " + allSensorData[sensorName].values.length);
        if (allSensorData[sensorName].values.length >= 100) {
            allSensorData[sensorName].collecting = false;
            writeDataToFile(sensorName, JSON.stringify(allSensorData[sensorName].values));
        }
    }
}

function writeDataToFile(fileName, data) {
    fs.writeFile(fileName + '.json', data, (err) => {
        // throws an error, you could also catch it here
        if (err) throw err;

        // success case, the file was saved
        console.log('File saved ' + fileName + ' !');
    });
}

// Lifecycle event
const AWSLifeCycle = require('aws-sdk');
const AWSIoTData = require('aws-iot-device-sdk');
var AWSConfiguration = require('./aws-configuration.js');
var streamClientId = 'aircraftEngine_' + (Math.floor((Math.random() * 100000) + 1));
var subscribedToLifeCycleEvents = false;

// Remember the clients we learn about in here.
var clients = {"basicPubSub":false, "basicPubSubVibration":false, "basicPubSubLoad":false, "basicPubSubTemp":false};

// Set the region where your identity pool exists (us-east-1, eu-west-1)
AWSLifeCycle.config.region = 'ap-southeast-1';

// Configure the credentials provider to use your identity pool
AWSLifeCycle.config.credentials = new AWSLifeCycle.CognitoIdentityCredentials({
    IdentityPoolId: 'ap-southeast-1:973c5054-5d9a-441e-9bbd-844ac1791d95'
});

var accessKeyId;
var secretAccessKey;
var sessionToken;

// Make the call to obtain credentials
AWSLifeCycle.config.credentials.get(function(){
    // Credentials will be available when this function is called.
    accessKeyId = AWSLifeCycle.config.credentials.accessKeyId;
    secretAccessKey = AWSLifeCycle.config.credentials.secretAccessKey;
    sessionToken = AWSLifeCycle.config.credentials.sessionToken;
    console.log(accessKeyId);

});

const mqttClient = AWSIoTData.device({
    //
    // Set the AWS region we will operate in.
    //
    region: AWSLifeCycle.config.region,
    //
    // Set the AWS IoT Host Endpoint
    // //
    host:AWSConfiguration.host,
    //
    // Use the clientId created earlier.
    //
    clientId: streamClientId,
    //
    // Connect via secure WebSocket
    //
    protocol: 'wss',
    //
    // Set the maximum reconnect time to 8 seconds; this is a browser application
    // so we don't want to leave the user waiting too long for reconnection after
    // re-connecting to the network/re-opening their laptop/etc...
    //
    maximumReconnectTimeMs: 8000,
    //
    // Enable console debugging information (optional)
    //
    debug: false,
    //
    // IMPORTANT: the AWS access key ID, secret key, and sesion token must be 
    // initialized with empty strings.
    //
    accessKeyId: accessKeyId,
    secretKey: secretAccessKey,
    sessionToken: sessionToken
 });


 //
// Connect handler; update div visibility and fetch latest shadow documents.
// Subscribe to lifecycle events on the first connect event.
//
mqttClientConnectHandler = function() {
    console.log('connect');
    //document.getElementById("connecting-div").style.visibility = 'hidden';
    //document.getElementById("clients-div").style.visibility = 'visible';
 
    //
    // We only subscribe to lifecycle events once.
    //
    if (!subscribedToLifeCycleEvents) {
       mqttClient.subscribe('$aws/events/#');
       subscribedToLifeCycleEvents = true;
    }
 };
 
 //
 // Reconnect handler; update div visibility.
 //
 mqttClientReconnectHandler = function() {
    console.log('reconnect');
    //document.getElementById("connecting-div").style.visibility = 'visible';
    //document.getElementById("clients-div").style.visibility = 'hidden';
 };
 
 //
 // Utility function to determine if a value has been defined.
 //
 isUndefined = function(value) {
    return typeof value === 'undefined' || typeof value === null;
 };
 
 //
 // Message handler for lifecycle events; create/destroy divs as clients
 // connect/disconnect.
 //
 mqttClientMessageHandler = function(topic, payload) {
    var topicTokens = topic.split('/');
 
    console.log('message: ' + topic + ':' + payload.toString());
 
    if ((topicTokens[0] === '$aws') &&
       (topicTokens[1] === 'events') &&
       (topicTokens[2] === 'presence') &&
       (topicTokens.length === 5)) {
       //
       // This is a presence event, topicTokens[3] contains the event
       // and topicTokens[4] contains the client name.
       //
       var clientIdString = topicTokens[4];
       console.log("AWS Connection detected: " + clientIdString);
       var divName = clientIdString.replace(/-|\s/g, '');
       if (!isUndefined(clients[divName])) {

          if (topicTokens[3] === 'disconnected') {
            console.log("Existing Connection broken: " + divName);
            clients[divName] = false;
          } else if ((topicTokens[3] === 'connected') && (clientIdString !== streamClientId)) {
            console.log("New Connected made: " + divName);
            clients[divName] = true;
          } else {

          }
        } else{

        }
      }
      else {
       console.log('unrecognized topic :' + topic);
    }
    console.log('clients list: ' + JSON.stringify(clients))
    if ((Object.values(clients)).every(item => item === true)){
        systemStatus = "Online"
        
    } else {
        systemStatus = "Offline"
    }
    socketServer.emit('changeSystemStatus', '' + systemStatus);
};

//
// Install connect/reconnect event handlers.
//
mqttClient.on('connect', mqttClientConnectHandler);
mqttClient.on('reconnect', mqttClientReconnectHandler);
mqttClient.on('message', mqttClientMessageHandler);
socketServer.emit('changeSystemStatus', '' + "Offline");