const CACHE_NAME = "AlPaczka_cache";
const OFFLINE_URL = "offline";
const ERROR_URL = "pwa_error";

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    let cache = await caches.open(CACHE_NAME);
    await cache.add(new Request(OFFLINE_URL, { cache: "reload" }));
    await cache.add(new Request(ERROR_URL, { cache: "reload" }));
  })());
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith((async () => {
    try {
      let responseFromNetwork = await fetch(event.request);
      return responseFromNetwork;

    } catch (error) {
      console.log("Caught error during fetch", error);
      let cache = await caches.open(CACHE_NAME);
      let cachedResponse;

      if (event.request.mode === "navigate") {
        cachedResponse = await cache.match(OFFLINE_URL);
      } else {
        cachedResponse = await cache.match(ERROR_URL);
      }
      return cachedResponse;
    }
  })());
});