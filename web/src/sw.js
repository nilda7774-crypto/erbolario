/* Service worker del Herbolario Consultor: permite abrir la aplicación sin conexión.
   La versión y la lista de archivos las escribe build_web.py; al publicar una versión nueva se borra la caché anterior. */
const CACHE = "herbolario-__VERSION__";
const PRECACHE = __PRECACHE__;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((claves) => Promise.all(claves.filter((k) => k.startsWith("herbolario-") && k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  // Solo GET del propio sitio; el asistente (otro dominio) y las fuentes van siempre a la red.
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (req.mode === "navigate") {
    // Páginas: primero la red (para tener siempre la última versión); sin conexión, la copia guardada.
    e.respondWith(fetch(req).catch(() => caches.match("/", { ignoreSearch: true })));
    return;
  }
  // Archivos con versión en el nombre, imágenes y manifiesto: primero la caché.
  e.respondWith(caches.match(req).then((guardado) => guardado || fetch(req).then((r) => {
    if (r.ok && (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/img/"))) {
      const copia = r.clone();
      caches.open(CACHE).then((c) => c.put(req, copia));
    }
    return r;
  })));
});
