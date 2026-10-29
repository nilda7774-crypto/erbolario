"""Genera el sitio web a partir de data/*.json y de web/src/ (cuerpo.html, app.css, app.js, sw.js).

Salidas:
  web/sitio/           sitio para Render (estático): index.html, 404.html, 500.html, assets/ con nombres versionados,
                       img/, manifest, service worker, robots.txt y sitemap.xml. Sin código JavaScript ni CSS en línea,
                       para poder usar una política de seguridad de contenido (CSP) estricta.
  web/herbolario.html  versión de un solo archivo (para publicarla como artefacto en claude.ai).

Uso:  python build_web.py
Variables opcionales: HERBOLARIO_API_URL (servidor del asistente) y HERBOLARIO_SITIO (dirección pública del sitio).
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

BASE = Path(__file__).parent
SRC = BASE / "web" / "src"
SITIO = BASE / "web" / "sitio"
IMG = BASE / "web" / "img"
URL_SITIO = os.environ.get("HERBOLARIO_SITIO", "https://herbolario-consultor.onrender.com").rstrip("/")
API_URL = os.environ.get("HERBOLARIO_API_URL", "https://herbolario-api.onrender.com").rstrip("/")
FUENTES = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700"
           "&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap")
TITULO = "Herbolario Consultor · Guía de suplementos Nature's Sunshine"
DESCRIPCION = ("Guía gratuita y bilingüe de suplementos Nature's Sunshine: asistente de consulta, catálogo, sistemas del cuerpo, "
               "evidencia científica de plantas medicinales, medicina china y seguridad con medicamentos.")
IMAGENES = ["bosque.webp", "equinacea.webp", "astragalo.webp", "goji.webp", "jengibre.webp", "curcuma.webp",
            "manzanilla.webp", "diente-de-leon.webp", "alfalfa.webp", "menta.webp",
            "icono-180.png", "icono-192.png", "icono-512.png", "og.jpg"]


def leer_json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def cargar_datos():
    def idioma(carpeta):
        return {n: leer_json(carpeta / f"{n}.json") for n in ("productos", "empresa", "tcm")}

    es = idioma(BASE / "data")
    datos = {"es": es}
    en = idioma(BASE / "data" / "en")   # Traducción al inglés; lo que falte se muestra en español.
    if en["productos"]:
        datos["en"] = {k: en[k] or es[k] for k in es}
    for clave in ("seguridad", "sistemas", "evidencia"):   # Bilingües dentro de cada ficha.
        valor = leer_json(BASE / "data" / f"{clave}.json")
        if valor:
            datos[clave] = valor
    datos["creditos"] = leer_json(IMG / "creditos.json") or {}
    return datos


def huella(contenido):
    return hashlib.sha256(contenido).hexdigest()[:10]


def csp(api):
    return "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        f"connect-src 'self'{' ' + api if api else ''}",
        "manifest-src 'self'",
        "worker-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ])


def cabeza(titulo, descripcion, css, extra=""):
    """<head> común. Las rutas empiezan con «/» para que 404.html funcione en cualquier dirección."""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{titulo}</title>
<meta name="description" content="{descripcion}">
<meta name="theme-color" content="#2d6a4c">
<meta name="referrer" content="strict-origin-when-cross-origin">
<link rel="icon" type="image/png" sizes="192x192" href="/img/icono-192.png">
<link rel="apple-touch-icon" href="/img/icono-180.png">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FUENTES}">
<link rel="stylesheet" href="/assets/{css}">
{extra}</head>
"""


def pagina_error(codigo, css, titulo_es, texto_es, titulo_en, texto_en):
    """Página estática de error: sin JavaScript, sin detalles técnicos y con enlace al inicio."""
    return cabeza(f"{titulo_es} · Herbolario Consultor", texto_es, css, '<meta name="robots" content="noindex">\n') + f"""<body>
<header class="barra"><div class="barra-in">
  <a class="marca" href="/"><img src="/img/icono-192.png" alt="" width="36" height="36"><span><b>Herbolario</b> Consultor</span></a>
</div></header>
<main id="principal">
  <section class="vista no-encontrado">
    <p class="codigo">{codigo}</p>
    <h1>{titulo_es}</h1>
    <p>{texto_es}</p>
    <p lang="en" class="note">{titulo_en}. {texto_en}</p>
    <div class="acciones">
      <a class="btn grande" href="/">Volver al inicio · Home</a>
      <a class="btn grande ghost" href="/#/contacto">Contacto · Contact</a>
    </div>
  </section>
</main>
</body>
</html>
"""


def main():
    datos = cargar_datos()
    css = (SRC / "app.css").read_text(encoding="utf-8")
    js = (SRC / "app.js").read_text(encoding="utf-8")
    cuerpo = (SRC / "cuerpo.html").read_text(encoding="utf-8")
    datos_json = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))

    # ---------- Versión de un solo archivo (claude.ai: el publicador añade <!doctype>, <head> y <body>) ----------
    incrustado = datos_json.replace("</", "<\\/")   # un "</script>" dentro de los datos no puede cerrar la etiqueta
    (BASE / "web" / "herbolario.html").write_text(
        f'<title>Herbolario Consultor</title>\n<link rel="stylesheet" href="{FUENTES}">\n<style>\n{css}</style>\n'
        f'{cuerpo}\n<script id="data" type="application/json">{incrustado}</script>\n<script>\n{js}</script>\n',
        encoding="utf-8")

    # ---------- Sitio para Render ----------
    # Se borran los archivos de la compilación anterior (no las carpetas: OneDrive a veces las bloquea).
    for viejo in SITIO.rglob("*") if SITIO.exists() else []:
        if viejo.is_file():
            viejo.unlink()
    (SITIO / "assets").mkdir(parents=True, exist_ok=True)
    (SITIO / "img").mkdir(exist_ok=True)
    for nombre in IMAGENES:
        shutil.copyfile(IMG / nombre, SITIO / "img" / nombre)

    css_sitio = css.replace('url("img/', 'url("../img/').encode("utf-8")
    js_b, datos_b = js.encode("utf-8"), datos_json.encode("utf-8")
    nombres = {
        "css": f"app.{huella(css_sitio)}.css",
        "js": f"app.{huella(js_b)}.js",
        "datos": f"datos.{huella(datos_b)}.json",
    }
    (SITIO / "assets" / nombres["css"]).write_bytes(css_sitio)
    (SITIO / "assets" / nombres["js"]).write_bytes(js_b)
    (SITIO / "assets" / nombres["datos"]).write_bytes(datos_b)

    ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebSite", "name": "Herbolario Consultor", "url": URL_SITIO + "/",
        "inLanguage": ["es", "en"], "description": DESCRIPCION,
        "publisher": {"@type": "Person", "name": "Nilda Esparza", "email": "mailto:nilda7774@gmail.com",
                      "sameAs": ["https://www.instagram.com/nilda7774/"]},
    }, ensure_ascii=False).replace("</", "<\\/")
    # En <meta> no se admiten frame-ancestors ni upgrade-insecure-requests útiles en local: van en los encabezados (render.yaml).
    meta_csp = csp(API_URL).replace("; frame-ancestors 'none'", "").replace("; upgrade-insecure-requests", "")
    extra = f"""<meta http-equiv="Content-Security-Policy" content="{meta_csp}">
<link rel="canonical" href="{URL_SITIO}/">
<link rel="alternate" hreflang="es" href="{URL_SITIO}/">
<link rel="alternate" hreflang="en" href="{URL_SITIO}/">
<meta name="robots" content="index, follow">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Herbolario">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Herbolario Consultor">
<meta property="og:locale" content="es_MX">
<meta property="og:locale:alternate" content="en_US">
<meta property="og:title" content="{TITULO}">
<meta property="og:description" content="{DESCRIPCION}">
<meta property="og:url" content="{URL_SITIO}/">
<meta property="og:image" content="{URL_SITIO}/img/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Herbolario Consultor: guía de suplementos Nature's Sunshine">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITULO}">
<meta name="twitter:description" content="{DESCRIPCION}">
<meta name="twitter:image" content="{URL_SITIO}/img/og.jpg">
<meta name="datos" content="/assets/{nombres["datos"]}">
<meta name="api" content="{API_URL}">
<meta name="sw" content="/sw.js">
<link rel="preload" href="/assets/{nombres["datos"]}" as="fetch" crossorigin>
<script type="application/ld+json">{ld}</script>
<script src="/assets/{nombres["js"]}" defer></script>
"""
    (SITIO / "index.html").write_text(
        cabeza(TITULO, DESCRIPCION, nombres["css"], extra) + "<body>\n" + cuerpo + "</body>\n</html>\n", encoding="utf-8")
    (SITIO / "404.html").write_text(pagina_error(
        404, nombres["css"], "No encontramos esta página", "Puede que el enlace esté mal escrito o que la página ya no exista.",
        "Page not found", "The link may be mistyped or the page may no longer exist."), encoding="utf-8")
    (SITIO / "500.html").write_text(pagina_error(
        500, nombres["css"], "Algo salió mal", "Tuvimos un problema al cargar la página. Inténtalo de nuevo en unos minutos.",
        "Something went wrong", "We had a problem loading the page. Please try again in a few minutes."), encoding="utf-8")

    (SITIO / "manifest.webmanifest").write_text(json.dumps({
        "id": "/", "name": "Herbolario Consultor", "short_name": "Herbolario", "lang": "es",
        "description": "Guía de suplementos Nature's Sunshine: consulta, catálogo, evidencia y seguridad.",
        "start_url": "/", "scope": "/", "display": "standalone", "orientation": "any",
        "background_color": "#f2f4ee", "theme_color": "#2d6a4c", "categories": ["health", "lifestyle", "education"],
        "icons": [{"src": "/img/icono-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/img/icono-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}],
        "shortcuts": [
            {"name": "Haz tu consulta", "url": "/#/consulta", "icons": [{"src": "/img/icono-192.png", "sizes": "192x192"}]},
            {"name": "Catálogo", "url": "/#/catalogo", "icons": [{"src": "/img/icono-192.png", "sizes": "192x192"}]},
            {"name": "Evidencia científica", "url": "/#/evidencia", "icons": [{"src": "/img/icono-192.png", "sizes": "192x192"}]},
        ],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (SITIO / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /500.html\n\nSitemap: {URL_SITIO}/sitemap.xml\n", encoding="utf-8")
    (SITIO / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{URL_SITIO}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>\n</urlset>\n",
        encoding="utf-8")

    # Service worker: guarda la aplicación para usarla sin conexión. Su versión cambia con cada compilación.
    precache = ["/", *(f"/assets/{n}" for n in nombres.values()), *(f"/img/{n}" for n in IMAGENES if n != "og.jpg"),
                "/manifest.webmanifest", "/404.html"]
    version = huella("".join(nombres.values()).encode())
    sw = (SRC / "sw.js").read_text(encoding="utf-8")
    sw = sw.replace("__VERSION__", version).replace("__PRECACHE__", json.dumps(precache))
    (SITIO / "sw.js").write_text(sw, encoding="utf-8")

    n = len(datos["es"]["productos"])
    print(f"Sitio generado en web/sitio ({n} productos, {len(datos.get('evidencia', {}).get('plantas', []))} plantas con evidencia) "
          f"y versión de un solo archivo en web/herbolario.html.")


if __name__ == "__main__":
    main()
