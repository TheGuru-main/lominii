// LOMINII Service Worker – Offline caching, push notifications, and PWA support
const CACHE_NAME = 'lominii-v2';
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

// ---------- Push Notifications (now with type‑aware handling) ----------
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};

  // Default values
  let title = 'LOMINII';
  let body = '';
  let icon = '/icons/icon-192.png';
  let badge = '/icons/badge-72.png';
  let targetUrl = '/';
  const type = data.type || '';

  switch (type) {
    case 'news':
      title = '📰 LOMINII News';
      icon = '/icons/news-icon-192.png';   // you can create a dedicated news icon
      badge = '/icons/news-badge-72.png';
      body = data.body || 'Breaking news from LOMINII';
      targetUrl = data.url || '/?tab=news';
      break;
    case 'game_invite':
      title = '🎮 LOMINII Play';
      body = data.body || 'You have been invited to a game!';
      targetUrl = data.url || '/?tab=games';
      break;
    case 'message':
      title = '💬 New message';
      body = data.body || 'You received a new message';
      targetUrl = data.url || '/?tab=social';
      break;
    default:
      // generic notification
      body = data.body || '';
      targetUrl = data.url || '/';
  }

  const options = {
    body,
    icon,
    badge,
    data: { url: targetUrl, type }
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// ---------- Notification click (open the app) ----------
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
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

// ---------- (Optional) Subscription change handling ----------
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil(
    // You can later implement logic to send the new subscription to your backend
    Promise.resolve()
  );
});