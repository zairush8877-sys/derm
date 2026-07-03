// Service worker для PWA: офлайн-кэш статики (app shell).
const CACHE = "aura-v4";
const ASSETS = [
  "/", "/skin", "/tracker", "/food", "/shop", "/assistant", "/subscription", "/auth",
  "/static/styles.css", "/static/app.js", "/static/tracker.js",
  "/static/food.js", "/static/shop.js", "/static/assistant.js",
  "/static/subscription.js", "/static/auth-helper.js",
  "/static/icon.svg", "/static/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // API-запросы (POST/анализ) — всегда из сети.
  if (request.method !== "GET" || request.url.includes("/api/") || request.url.includes("/v1/")) {
    return;
  }
  // Статика — сначала кэш, затем сеть.
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
