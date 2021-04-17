document.addEventListener("DOMContentLoaded", function () {

    var ws_uri_parcel_locker = "https://localhost:7003";
    var ws_uri_app = "https://localhost:7000";
    socket_parcel_locker = io.connect(ws_uri_parcel_locker);
    socket_app = io.connect(ws_uri_app);

    socket_app.emit("join", {useragent: navigator.userAgent, room_id: 'app_room'})
    socket_parcel_locker.emit("join", {useragent: navigator.userAgent, room_id: 'parcel_locker_room'})

    var insert_form = document.getElementById("insert-form");
    var parcel_id_input = document.getElementById("parcel-id-input");

    insert_form.addEventListener("submit", ()=>{
        socket_parcel_locker.emit("parcel inserted")
        socket_app.emit("parcel inserted", data={parcel_id: parcel_id_input.value})
    })
});