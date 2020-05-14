var app = require('express')();
var fs = require('fs');
var httpsOpts = {
    key: fs.readFileSync('./keys/server.key', 'utf8'),
    cert: fs.readFileSync('./keys/server.crt', 'utf8')
};
var https = require('https');
var config = require('./config.json');

app.use(require('express').static('./'));
var server = https.createServer(httpsOpts, app).listen(8888);

var io = require('socket.io')(server);
var heat = io.of('/heatmap_data');
var line = io.of('/linechart_data');
var stream = io.of('/streamgraph_data');
io.on('connection', function (socket) {
    console.log('connected');
});
var heatData = [];
var lineData = [];
var streamData = [];
sendHeatData();
sendLineData();
sendStreamData();
heat.on('connection', socket=> {
    socket.on('fetch', function (name) {
        socket.emit('messageFetched',{
            received: name,
            data: heatData
        });
    });
    socket.on('room', function (room) {
        socket.join(room);
        sendHeatDataToRoom(room);
    });
});
line.on('connection', socket=> {
    socket.on('fetch', function (name) {
        socket.emit('messageFetched',{
            received: name,
            data: lineData
        });
    });
    socket.on('room', function (room) {
        socket.join(room);
        sendLineDataToRoom(room);
    });
});
stream.on('connection', socket=> {
    socket.on('fetch', function (name) {
        socket.emit('messageFetched',{
            received: name,
            data: streamData
        });
    });
    socket.on('room', function (room) {
        socket.join(room);
        sendStreamDataToRoom(room);
    });
});
function sendHeatData() {

    heatData.map((elem)=> {
        elem.hour--
    });
    for (var j = 0; j < config.heatData.cat.length; j++) {
        heatData.push({
            "day": config.heatData.cat[j],
            "cpu_usage": config.heatData.valueLimits[0] + Math.random() * (config.heatData.valueLimits[1] - config.heatData.valueLimits[0]),
            "hour": 24
        });
    }
    if (heatData.length >= config.heatData.length * config.heatData.cat.length)
        heatData = heatData.slice(config.heatData.cat.length);

    // heat.emit('message', heatData);
    heat.emit('heatData', heatData);
    setTimeout(sendHeatData, config.timeout);
}

function sendLineData() {
    if (lineData.length >= config.lineData.length)
        lineData = lineData.slice(1);

    lineData.push({
        "time": new Date().getTime(),
        "calls": config.lineData.valueLimits[0] + (Math.random() * (config.lineData.valueLimits[1] - config.lineData.valueLimits[0]))
    });
    // line.emit('message', lineData);
    line.emit('lineData', lineData);
    setTimeout(sendLineData, config.timeout);
}

function sendStreamData() {
    for (var j = 0; j < config.streamData.keys.length; j++)
        streamData.push({
            "key": config.streamData.keys[j],
            "value": config.streamData.valueLimits[0] + Math.random() * (config.streamData.valueLimits[1] - config.streamData.valueLimits[0]),
            "date": new Date().toLocaleString(),
            "time": new Date().getTime()
        });
    if (streamData.length >= config.streamData.length * config.streamData.keys.length)
        streamData = streamData.slice(config.streamData.keys.length);

    // stream.emit('message', streamData);
    stream.emit('streamData', streamData);
    setTimeout(sendStreamData, config.timeout);
}

function sendHeatDataToRoom(room) {

    heat.to(room).emit('heatData', [{
        "day": "day1",
        "cpu_usage": config.heatData.valueLimits[0] + Math.random() * (config.heatData.valueLimits[1] - config.heatData.valueLimits[0]),
        "hour": 24
    }]);
    setTimeout(sendHeatDataToRoom.bind(null, room), config.timeout);
}

function sendLineDataToRoom(room) {
    line.to(room).emit('lineData', [{
        "time": new Date().getTime(),
        "calls": config.lineData.valueLimits[0] + (Math.random() * (config.lineData.valueLimits[1] - config.lineData.valueLimits[0]))
    }]);
    setTimeout(sendLineDataToRoom.bind(null, room), config.timeout);
}

function sendStreamDataToRoom(room) {
    stream.to(room).emit('streamData', [{
        "key": config.streamData.keys[j],
        "value": config.streamData.valueLimits[0] + Math.random() * (config.streamData.valueLimits[1] - config.streamData.valueLimits[0]),
        "date": new Date().toLocaleString(),
        "time": new Date().getTime()
    }]);
    setTimeout(sendStreamDataToRoom.bind(null, room), config.timeout);
}
