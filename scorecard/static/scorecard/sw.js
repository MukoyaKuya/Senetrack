/* SENETRACK Service Worker - basic offline caching */
const CACHE_NAME = 'senetrack-v1';
const STATIC_ASSETS = [
  '/',
  '/static/scorecard/vendor/tailwind.js',
  '/static/scorecard/vendor/lucide.min.js',
  '/static/scorecard/images/hero-parliament.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => Promise.all(
      names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.mode !== 'navigate' && !event.request.url.match(/\.(js|css|png|jpg|jpeg|gif|ico|woff2?)$/)) {
    return;
  }
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        const clone = res.clone();
        if (res.ok && event.request.method === 'GET') {
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(event.request).then((r) => r || caches.match('/')))
  );
});
