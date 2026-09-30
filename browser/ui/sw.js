// HugOS Browser Minimal Service Worker for PWA Desktop Pinning
const CACHE_NAME = 'hugos-browser-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Pass-through to network for local AI dynamic routing
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
