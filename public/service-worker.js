// LOMINII Service Worker – Offline caching, push notifications, and PWA support
const CACHE_NAME = 'lominii-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/style.css',
  '/script.js',
  '/manifest.json',
  '/offline_dictionary.json.gz',  // English
  // Additional language dictionaries will be added as they become available
];

// ---------- Install ----------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
});

// ---------- Activate (clean old caches) ----------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
});

// ---------- Fetch (serve from cache, fallback to network) ----------
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests and API calls
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return cachedResponse || fetch(event.request).then((networkResponse) => {
        // Optionally cache new files for next time
        return networkResponse;
      });
    })
  );
});

// ---------- Push Notifications (premium news alerts, game invites) ----------
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'LOMINII';
  const options = {
    body: data.body || '',
    icon: '/icons/icon-192.png',
    badge: '/icons/badge-72.png',
    data: data.url || '/'
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

// ---------- Notification click (open the app) ----------
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data;
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});