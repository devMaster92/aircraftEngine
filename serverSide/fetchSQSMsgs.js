/**
 * Created by yashu on 10/1/18.
 */

// Load the SDK for JavaScript
const AWS = require('aws-sdk');
// Set the region
AWS.config.update({region: 'us-west-2'});

// Create an SQS service object
const sqs = new AWS.SQS({apiVersion: '2012-11-05'});

const queueURL = "https://sqs.us-west-2.amazonaws.com/027511483135/digitalTwin_vibrationData_forAnomalyDetection";

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
sqs.receiveMessage(params, function(err, data) {
    if (err) {
        console.log("Receive Error", err);
    } else if (data.Messages) {
        const entries = [];
        for (let i=0; i<data.Messages.length; i++) {
            console.log("MessageID: ", JSON.parse(data.Messages[i].Body).MessageId);
            console.log("MessageContent: ", JSON.parse(data.Messages[i].Body).Message);
            entries.push({
                Id: 'deleteMsgID_' + i,
                ReceiptHandle: data.Messages[i].ReceiptHandle
            });
        }
        deleteParams.Entries = entries;
        sqs.deleteMessageBatch(deleteParams, function (err, data) {
            if (err) {
                console.log("Delete Error", err);
            } else {
                console.log("Message Deleted", data);
            }
        });
    }
});