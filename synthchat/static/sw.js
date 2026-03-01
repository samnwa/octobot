const CACHE_NAME = "synthchat-v3";
const PRECACHE = [
  "/synthchat/",
  "/synthchat/static/style.css?v=9",
  "/synthchat/static/app.js?v=9",
  "/synthchat/static/manifest.json",
  "/synthchat/static/icon-192.png",
  "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap",
  "https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (
    e.request.method !== "GET" ||
    url.pathname.startsWith("/synthchat/api/") ||
    url.pathname.startsWith("/synthchat/chat") ||
    url.pathname.startsWith("/synthchat/stop")
  ) {
    return;
  }
  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
