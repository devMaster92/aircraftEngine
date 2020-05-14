/**
 * Created by gopi on 19/1/17.
 */
const socket = io('/aircraft_demo');
let thrustVal = 0;
socket.on('connect', function (ob) {
    console.log("Connected to server");
});
socket.on('message', function (msg) {
    console.log("On message: " + msg);
});
socket.on('vibration_data', msg=>{
    $('#vibration_data').html(JSON.stringify(msg));
});
socket.on('load_data', msg=>{
    $('#load_data').html(JSON.stringify(msg));
});
socket.on('temperature_data', msg=>{
    $('#temperature_data').html(JSON.stringify(msg));
});
socket.on('changeThrustValue', msg=>{
    $('#changeThrustValue').html(msg);
});

function changeThrust() {
    console.log("Triggered changeThrust");
    thrustVal = document.getElementById('thrust').value;
    // if (thrustVal == 0) {
    //     thrustVal = 1;
    // } else {
    //     thrustVal = 0;
    // }
    socket.emit('changeThrust', '' + thrustVal, function (d) {
        $('#changeThrustValue').html("valueChanged");
    });
}
