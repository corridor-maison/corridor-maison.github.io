/* Hors ligne : l'application, les images et les leçons sont gardées sur la tablette.
   Les leçons, les phrases et le moteur sont d'abord demandés au réseau (pour recevoir la semaine suivante et les mises à jour),
   puis pris dans le cache s'il n'y a pas de connexion. */
const CACHE = 'kono-0.3.8';
const CORE = ['./', 'index.html', 'styles.css', 'app.js', 'manifest.webmanifest',
  'fonts/andika-400.woff2', 'fonts/andika-700.woff2', 'fonts/nunito-800.woff2',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-192.png', 'icons/icon-maskable-512.png', 'parcours.json', 'ecole.json', 'lessons/index.json', 'phrases.json', 'audio/manifest.json',
  'progression/ce1.json', 'progression/gs.json',
  'img/ananas.svg', 'img/ballon.svg', 'img/baobab.svg', 'img/bateau.svg', 'img/bol.svg', 'img/calebasse.svg', 'img/chat.svg', 'img/domino.svg', 'img/jeton.svg', 'img/lapin.svg', 'img/mangue.svg', 'img/panier.svg', 'img/poisson.svg', 'img/sac.svg', 'img/soleil.svg', 'img/velo.svg'];

/* À la toute première ouverture, la page n'est pas encore contrôlée par ce service worker : ses propres requêtes
   ne passent pas par le cache. On garde donc dès l'installation toutes les séances listées dans l'index ;
   sinon, une tablette ouverte une seule fois avec internet afficherait « Leçons introuvables » hors ligne. */
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(async c => {
    await c.addAll(CORE);
    const idx = await (await fetch('lessons/index.json', { cache: 'no-cache' })).json();
    await c.addAll((idx.lessons || []).map(l => `lessons/${l.id}.json`));
  }).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
const FRESH = p => p.includes('/lessons/') || p.endsWith('parcours.json') || p.endsWith('ecole.json') || p.includes('/progression/') || p.endsWith('manifest.json') || p.endsWith('phrases.json') || p.endsWith('app.js') || p.endsWith('styles.css');
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  const url = new URL(req.url);
  if (FRESH(url.pathname) || req.mode === 'navigate') {
    /* Toujours revalider auprès du serveur (cache: no-cache) : une publication est vue à la première ouverture en ligne, sans rien vider. */
    e.respondWith(fetch(req, { cache: 'no-cache' }).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy));
      /* Le manifeste audio arrive : on télécharge d'avance toutes les voix, pour qu'elles marchent hors ligne. */
      if (url.pathname.endsWith('audio/manifest.json')) res.clone().json().then(m => caches.open(CACHE).then(c => Promise.all(Object.values(m.files || {}).map(f => c.match('audio/' + f).then(hit => hit || c.add('audio/' + f).catch(() => {})))))).catch(() => {});
      return res; })
      .catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || caches.match('index.html'))));
    return;
  }
  e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res; })));
});
