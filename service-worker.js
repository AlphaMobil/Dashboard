/**
 * Alpha-Mobil Händler-Cockpit – Service Worker für die installierbare App.
 * Netzwerk zuerst: Es wird immer die aktuell veröffentlichte Version geladen.
 * Nur ohne Verbindung kommt die zuletzt geladene Version aus dem Cache.
 * Die Daten im Cache sind – wie online – verschlüsselt.
 */
var CACHE_NAME = 'haendler-cockpit-v1';
var SHELL = ['./', './index.html', './d3.min.js', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE_NAME).then(function (c) { return c.addAll(SHELL); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE_NAME; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  e.respondWith(fetch(req, {cache: 'no-store'}).then(function (res) {
    if (res && res.ok) { var copy = res.clone(); caches.open(CACHE_NAME).then(function (c) { c.put(req, copy); }); }
    return res;
  }).catch(function () { return caches.match(req).then(function (r) { return r || caches.match('./index.html'); }); }));
});
