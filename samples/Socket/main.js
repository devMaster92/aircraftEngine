/**
 * Created by gopi on 19/1/17.
 */
var heat = io('/heatmap_data');
heat.on('message', function (msg) {
    try {
        $("#heatmap").html(JSON.stringify(msg));
    }
    catch (e) {
        $("#heatmap").html(msg);
    }
});
heat.on('heatData',msg=>{
    $('#heatData').html(JSON.stringify(msg));
});
var line = io('/linechart_data');

line.on('message', function (msg) {
    try {
        $("#linechart").html(JSON.stringify(msg));
    }
    catch (e) {
        $("#linechart").html(msg);
    }
});
line.on('lineData',msg=>{
    $('#lineData').html(JSON.stringify(msg));
});
var stream = io('/streamgraph_data');
stream.on('message', function (msg) {
    try {
        $("#streamgraph").html(JSON.stringify(msg));
    }
    catch (e) {
        $("#streamgraph").html(msg);
    }
});
stream.on('streamData',msg=>{
    $('#streamData').html(JSON.stringify(msg));
});


function fetchHeatData() {
    heat.emit('fetch', 1, function (d) {
        console.log(d);
    });
}
function fetchStreamData() {
    stream.emit('fetch', 1, function (d) {
        console.log(d);
    });
}
function fetchLineData() {
    line.emit('fetch', 1, function (d) {
        console.log(d);
    });
}
