document.addEventListener("DOMContentLoaded", function () {

    var ws_uri = "https://localhost:7000";
    socket = io.connect(ws_uri);

    socket.emit("join", {useragent: navigator.userAgent, room_id: 'app_room'})

    socket.on("refresh status", function(data){
        document.getElementById(data.parcel_id).innerText="przekazana";
        document.getElementById(data.parcel_id+"remove-btn").innerHTML="";
    });

    socket.on("change status to inserted", function(data){
        document.getElementById(data.parcel_id).innerText="w paczkomacie";
        document.getElementById(data.parcel_id+"remove-btn").innerHTML="";
    });

    socket.on("change status to picked up from parcel locker", function(data){
        document.getElementById(data.parcel_id).innerText="odebrana z paczkomatu";
    });

    socket.on("refresh", function(){
        location.reload()
    });
});