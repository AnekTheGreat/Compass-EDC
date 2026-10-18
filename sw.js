// CACHE is stamped from app.js APP_VERSION by dev/ota.mjs - a released version always
// brings a cache of its own, and activate drops everything older.
var CACHE = 'measuret-v1.1.0';
var ASSETS = [
  './index.html',
  './app.js',
  './manifest.json',
  './updates.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', function(e){
  e.waitUntil(
    caches.open(CACHE).then(function(cache){
      return Promise.all(ASSETS.map(function(f){
        return cache.add(new Request(f, { cache: 'no-store' })).catch(function(){});
      }));
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(
        keys.filter(function(k){ return k !== CACHE; }).map(function(k){ return caches.delete(k); })
      );
    }).then(function(){ return self.clients.claim(); })
  );
});

// NEWEST FIRST, SAVED AS A BACKUP. The old worker answered every request from the cache
// first, so the first copy a phone ever saw was the last one it would ever see: a new
// release could never reach an app that was already installed. The network now wins
// whenever it answers (GitHub Pages serves index.html with a 10 minute max-age, so page
// loads go through 'no-store' rather than the HTTP cache), and the saved copy is what you
// get only when the network is gone - which is the offline promise that must survive.
self.addEventListener('fetch', function(e){
  var url;
  try { url = new URL(e.request.url); } catch (err) { return; }
  if (!url.protocol.startsWith('http') || url.origin !== self.location.origin) return;

  var isDocument = e.request.mode === 'navigate' || e.request.destination === 'document';
  var netRequest = isDocument
    ? new Request(e.request.url, { cache: 'no-store', credentials: 'same-origin', mode: 'same-origin' })
    : e.request;

  e.respondWith(
    fetch(netRequest).then(function(res){
      if (res && res.ok) {
        var copy = res.clone();
        caches.open(CACHE).then(function(cache){ cache.put(e.request, copy); }).catch(function(){});
      }
      return res;
    }).catch(function(){
      return caches.match(e.request, { ignoreSearch: isDocument }).then(function(cached){
        return cached || Response.error();
      });
    })
  );
});

// Lets the page ask the worker to look for a newer build on demand - used by the
// in-app "Update now" flow - instead of only ever checking on navigation.
self.addEventListener('message', function(e){
  var type = e.data && e.data.type;
  if (type === 'CHECK_FOR_UPDATE' && self.registration && self.registration.update) {
    self.registration.update().catch(function(){});
  }
  if (type === 'SKIP_WAITING') self.skipWaiting();
});