// Service worker Запоминайки: нужен, чтобы показывать системные уведомления
// (на Android они работают только через service worker) и открывать
// страницу по нажатию на уведомление.

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const page = all.find((c) => c.url.includes('zapominajka'));
    if (page) return page.focus();
    return self.clients.openWindow('zapominajka.html');
  })());
});
