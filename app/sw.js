const VERSION = "jadis-v2";
const FONT_CSS = "https://fonts.googleapis.com/css2?family=Alfa+Slab+One&family=Bricolage+Grotesque:wght@400;500;600;700;800&family=Cormorant+Garamond:wght@700&family=Fraunces:opsz,wght@9..144,700;9..144,900&family=Grenze+Gotisch:wght@700;800&family=Libre+Baskerville:wght@700&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,500;1,7..72,400&family=Marcellus&display=swap";
const SHELL = [
  "./", "index.html", "manifest.webmanifest", "data/articles.json",
  "icons/icon.svg", "icons/icon-192.png", "icons/icon-512.png", "icons/maskable-512.png", "icons/apple-touch-icon.png",
];
const FONT_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com"];

// Les polices sont mises en cache à l'installation pour que le rendu soit identique hors connexion.
// Si elles échouent, l'installation continue : le texte s'affiche avec les polices de secours.
async function precacheFonts(cache) {
  try {
    const css = await fetch(FONT_CSS);
    if (!css.ok) return;
    await cache.put(FONT_CSS, css.clone());
    const urls = [...(await css.text()).matchAll(/url\((https:[^)]+)\)/g)].map((m) => m[1]);
    await Promise.all(urls.map((u) => cache.add(u).catch(() => {})));
  } catch {}
}

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(VERSION);
    await cache.addAll(SHELL);
    await precacheFonts(cache);
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSION) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isFont = FONT_HOSTS.includes(url.hostname);
  if (url.origin !== location.origin && !isFont) return;

  // Cache d'abord, rafraîchi en arrière-plan : lecture instantanée et possible sans réseau.
  e.respondWith((async () => {
    const cache = await caches.open(VERSION);
    const hit = await cache.match(req, { ignoreSearch: !isFont });
    const refresh = fetch(req).then((res) => {
      if (res && (res.ok || res.type === "opaque")) cache.put(req, res.clone());
      return res;
    }).catch(() => null);
    if (hit) { e.waitUntil(refresh); return hit; }
    const res = await refresh;
    if (res) return res;
    if (req.mode === "navigate") return (await cache.match("index.html")) || Response.error();
    return Response.error();
  })());
});
