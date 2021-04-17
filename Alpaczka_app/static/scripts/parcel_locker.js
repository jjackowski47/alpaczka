document.addEventListener("DOMContentLoaded", function () {

  parcelsPickUpForm = document.getElementById("parcels-pickup-form");
  parcelsPickUpTable = document.getElementById("pickup-table");
  if (parcelsPickUpTable)
    parcelsPickUpTableRows = parcelsPickUpTable.tBodies[0].rows;
  checkboxes = document.querySelectorAll("input[type=checkbox]");

  var ws_uri_courier = "https://localhost:7002";
  var ws_uri = "https://localhost:7003";
  var ws_uri_app = "https://localhost:7000";
  socket = io.connect(ws_uri);
  socket_app = io.connect(ws_uri_app);
  socket_courier = io.connect(ws_uri_courier);

  socket.emit("join", {useragent: navigator.userAgent, room_id: 'parcel_locker_room'})
  socket_courier.emit("join", {useragent: navigator.userAgent, room_id: 'courier_room'})
  socket_app.emit("join", {useragent: navigator.userAgent, room_id: 'app_room'})

  socket.on("refresh parcel locker parcels list", function(){
    location.reload()
  });

  window.addEventListener("load", (event) => {
    for (let i = 0; i < localStorage.length; i++) {
      console.log(localStorage.key(i));
      let cb = document.getElementById(localStorage.key(i));
      if (cb) cb.checked = true;
    }

    Array.prototype.map.call(checkboxes, (cb) =>
      cb.addEventListener("change", handleCheckboxChange)
    );
  });

  function handleCheckboxChange(e) {
    if (e.target.checked) {
      localStorage.setItem(
        e.target.parentElement.parentElement.children[1].innerText,
        "checked"
      );
    } else {
      localStorage.removeItem(
        e.target.parentElement.parentElement.children[1].innerText
      );
    }
  }

  if (parcelsPickUpForm) {
    parcelsPickUpForm.addEventListener("submit", function (event) {
      event.preventDefault();
      socket_courier.emit("parcels picked up from parcel locker")
      socket_app.emit("parcels picked up from parcel locker")
      for (let i = 0; i < localStorage.length; i++) {
        console.log(localStorage.key(i));
        changeParcelStatus(localStorage.key(i), "courier1", "aaa");
      }
      localStorage.clear();
      for (let checkbox of checkboxes) {
        checkboxes.checked = false;
      }
    });
  }

  function changeParcelStatus(parcel_id, courier_id, parcel_locker_id) {
    let changeStatusURL = "https://localhost:7003/changeStatus";
    let urlParams = new URLSearchParams(window.location.search);
    let data = {
      parcel_id: parcel_id,
      courier_id: urlParams.get("courier_id"),
      parcel_locker_id: urlParams.get("parcel_locker"),
    };
    let params = {
      method: "POST",
      body: JSON.stringify(data),
      headers: {
        "Content-Type": "application/json",
      },
      redirect: "follow",
    };

    fetch(changeStatusURL, params)
      .then(() => {
        window.location.reload();
      })
      .catch((err) => {
        console.log("Caught error: " + err);
      });
  }
});