/* Hors ligne : l'application, les images et les leçons sont gardées sur la tablette.
   Les leçons, les phrases et le moteur sont d'abord demandés au réseau (pour recevoir la semaine suivante et les mises à jour),
   puis pris dans le cache s'il n'y a pas de connexion. */
const CACHE = 'kono-0.4.7';
const CORE = ['./', 'index.html', 'styles.css', 'app.js', 'manifest.webmanifest',
  'fonts/andika-400.woff2', 'fonts/andika-700.woff2', 'fonts/nunito-800.woff2',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-192.png', 'icons/icon-maskable-512.png', 'parcours.json', 'ecole.json', 'lessons/index.json', 'phrases.json', 'audio/manifest.json',
  'progression/ce1.json', 'progression/gs.json',
  'img/ananas.svg', 'img/ballon.svg', 'img/baobab.svg', 'img/bateau.svg', 'img/bol.svg', 'img/calebasse.svg', 'img/chat.svg', 'img/domino.svg', 'img/jeton.svg', 'img/lapin.svg', 'img/mangue.svg', 'img/panier.svg', 'img/poisson.svg', 'img/sac.svg', 'img/soleil.svg', 'img/velo.svg',
  'img/ananas.webp', 'img/ballon.webp', 'img/baobab.webp', 'img/bateau.webp', 'img/bol.webp', 'img/calebasse.webp', 'img/chat.webp', 'img/lapin.webp', 'img/mangue.webp', 'img/panier.webp', 'img/poisson.webp', 'img/sac.webp', 'img/soleil.webp', 'img/velo.webp',
  'img/scenes/marche.webp', 'img/scenes/vent.webp', 'img/scenes/pecheur.webp', 'img/scenes/merci.webp',
  'img/escales/bamako.webp', 'img/escales/segou.webp', 'img/escales/mopti.webp', 'img/escales/tombouctou.webp', 'img/escales/gao.webp'];

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
/* Les voix (audio/gen, audio/rec) ont pour nom l'empreinte de leur phrase : un fichier ne change jamais. Elles vivent dans un cache
   à part, gardé d'une version à l'autre : une mise à jour de l'application ne retélécharge pas les 60 Mo de voix. */
const AUDIO_CACHE = 'kono-audio';
const isAudio = u => /\/audio\/(gen|rec)\//.test(u);
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const ac = await caches.open(AUDIO_CACHE);
    for (const k of await caches.keys()) {
      if (k === CACHE || k === AUDIO_CACHE) continue;
      const oc = await caches.open(k);   /* les voix d'une ancienne version passent dans le cache des voix au lieu d'être retéléchargées */
      for (const r of await oc.keys()) if (isAudio(r.url)) { const res = await oc.match(r); if (res) await ac.put(r, res); }
      await caches.delete(k);
    }
    await self.clients.claim();
  })());
});
/* Les voix manquantes se téléchargent en arrière-plan, quatre à la fois : le démarrage et les séances gardent la priorité.
   Les voix qui ne sont plus dans le manifeste sont retirées. */
let prefetching = null;
function prefetchAudio(m) { return prefetching || (prefetching = prefetchRun(m).finally(() => { prefetching = null; })); }
async function prefetchRun(m) {
  const c = await caches.open(AUDIO_CACHE), rel = u => new URL(u, location.href).pathname.replace(/^.*\/audio\//, 'audio/');
  const want = Object.values(m.files || {}).map(f => 'audio/' + f), have = new Set((await c.keys()).map(r => rel(r.url)));
  const todo = want.filter(u => !have.has(u)); let i = 0;
  const worker = async () => { while (i < todo.length) { const u = todo[i++]; try { await c.add(u); } catch (err) {} } };
  await Promise.all([worker(), worker(), worker(), worker()]);
  const keep = new Set(want); for (const r of await c.keys()) if (!keep.has(rel(r.url))) await c.delete(r);
}
/* La page le demande à chaque démarrage (message « voix ») : dès la première ouverture, alors qu'elle n'est pas encore contrôlée,
   les voix du manifeste gardé à l'installation se téléchargent en arrière-plan. */
self.addEventListener('message', e => {
  if (e.data !== 'voix') return;
  e.waitUntil(caches.match('audio/manifest.json', { ignoreSearch: true }).then(r => r && r.json()).then(m => m && prefetchAudio(m)).catch(() => {}));
});
const FRESH = p => p.includes('/lessons/') || p.endsWith('parcours.json') || p.endsWith('ecole.json') || p.includes('/progression/') || p.endsWith('manifest.json') || p.endsWith('phrases.json') || p.endsWith('app.js') || p.endsWith('styles.css');
/* Délai maximal du réseau pour les fichiers frais : au-delà, la copie gardée sert tout de suite (le réseau finit de mettre le cache à jour,
   la nouvelle version sera vue à l'ouverture suivante). Un réseau lent ne bloque jamais le démarrage. */
const NET_WAIT = 5000;
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;   /* Google (connexion, Drive) n'est jamais mis en cache */
  const url = new URL(req.url);
  if (FRESH(url.pathname) || req.mode === 'navigate') {
    /* Revalider auprès du serveur (cache: no-cache) : une publication est vue à la première ouverture en ligne, sans rien vider. */
    const net = fetch(req, { cache: 'no-cache' }).then(res => {
      if (res.ok) {
        const copy = res.clone(); e.waitUntil(caches.open(CACHE).then(c => c.put(req, copy)));
        if (url.pathname.endsWith('audio/manifest.json')) e.waitUntil(res.clone().json().then(prefetchAudio).catch(() => {}));
      }
      return res;
    });
    const late = new Promise(r => setTimeout(r, NET_WAIT, null));
    e.respondWith(Promise.race([net.catch(() => null), late]).then(res => res || caches.match(req, { ignoreSearch: true }).then(hit => hit || net.catch(() => caches.match('index.html')))));
    return;
  }
  e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => { if (res.ok) { const copy = res.clone(); e.waitUntil(caches.open(isAudio(req.url) ? AUDIO_CACHE : CACHE).then(c => c.put(req, copy))); } return res; })));
});
