/* Tickwise PWA service worker.
 *
 * Caches the app shell so the UI loads instantly and works offline.
 * API responses are network-first — the user wants live data when
 * online, but we still want the empty shell to render when offline so
 * they can see "no connection" instead of a browser error page.
 */

const CACHE_VERSION = "tickwise-mobile-v1";
const SHELL = [
  "./",
  "index.html",
  "app.js",
  "styles.css",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // API requests: network-first.
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(event.request).catch(() => new Response("offline", { status: 503 })));
    return;
  }
  // Same-origin assets: cache-first, falling back to network.
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(event.request).then((hit) => hit || fetch(event.request)),
    );
  }
});

// Web push handler — payload format is open; we render text only.
self.addEventListener("push", (event) => {
  let body = "Pomodoro update";
  if (event.data) {
    try {
      const data = event.data.json();
      body = data.body || body;
    } catch (_) {
      body = event.data.text();
    }
  }
  event.waitUntil(self.registration.showNotification("Tickwise", { body }));
});
