window.addEventListener('load', () => {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .register('../service-worker.js')
      .then(function () { console.log("Service Worker Registered"); })
      .catch(function(e){
        console.log("Cannot register service worker. Error: -> ",e);
      });
  }
});
