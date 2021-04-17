document.addEventListener("DOMContentLoaded", function () {

    var ws_uri = "https://localhost:7002";
    socket = io.connect(ws_uri);

    socket.emit("join", {useragent: navigator.userAgent, room_id: 'courier_room'})

    socket.on("refresh", function(){
        location.reload()
    });
});