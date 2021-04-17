document.addEventListener("DOMContentLoaded", function () {

    var ws_uri_courier = "https://localhost:7002";
    var ws_uri_app = "https://localhost:7000";
    socket_courier = io.connect(ws_uri_courier);
    socket_app = io.connect(ws_uri_app);

    socket_courier.emit("join", {useragent: navigator.userAgent, room_id: 'courier_room'})
    socket_app.emit("join", {useragent: navigator.userAgent, room_id: 'app_room'})

    var pickup_form = document.getElementById("pickup-form");
    var parcel_id_input = document.getElementById("parcel-id-input");

    pickup_form.addEventListener("submit", ()=>{
        socket_courier.emit("parcel picked up")
        socket_app.emit("parcel picked up", data={parcel_id: parcel_id_input.value})
    })
});