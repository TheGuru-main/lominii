// LOMINII Service Worker – Offline caching, push notifications, and PWA support
const CACHE_NAME = 'lominii-v3-keyboard';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/css/lominii-keyboard.css',
  '/js/lominii-keyboard.js',
  '/js/search.js',
  '/offline_dictionary.json.gz'
];

// ---------- Install ----------
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await Promise.all(STATIC_ASSETS.map(async (url) => {
      try {
        const response = await fetch(url, { cache: 'reload' });
        if (response.ok) await cache.put(url, response);
      } catch (error) {
        console.warn('LOMINII offline asset unavailable:', url);
      }
    }));
    await self.skipWaiting();
  })());
});

// ---------- Activate (clean old caches) ----------
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys
      .filter(key => key.startsWith('lominii-') && key !== CACHE_NAME)
      .map(key => caches.delete(key)));
    await Promise.all(keys
      .filter(key => key.startsWith('lominii-') && key !== CACHE_NAME)
      .map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

// ---------- Fetch (serve from cache, fallback to network) ----------
self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const isDocument = request.mode === 'navigate';

    if (!isDocument) {
      const cached = await cache.match(request);
      if (cached) return cached;
    }

    try {
      const response = await fetch(request);
      if (response && response.ok && response.type === 'basic') {
        cache.put(request, response.clone()).catch(() => {});
      }
      return response;
    } catch (error) {
      const cached = await cache.match(request);
      if (cached) return cached;
      if (isDocument) {
        const fallback = await cache.match('/index.html');
        if (fallback) return fallback;
      }
      return new Response('LOMINII is offline. Reconnect and try again.', {
        status: 503,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }
  })());
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