"""Optimiza las fotos de web/img y crea la imagen para compartir en redes (Open Graph).

Solo hace falta al cambiar o añadir fotos; el resultado se guarda en web/img y se sube al repositorio.
Requiere Pillow (herramienta de desarrollo, no la usa el sitio):  pip install pillow

Uso:  python scripts/optimizar_imagenes.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMG = Path(__file__).resolve().parent.parent / "web" / "img"
FUENTES = Path("C:/Windows/Fonts")


def webp(nombre, ancho, calidad=74):
    origen = IMG / f"{nombre}.jpg"
    destino = IMG / f"{nombre}.webp"
    with Image.open(origen) as im:
        im = im.convert("RGB")
        if im.width > ancho:
            im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
        im.save(destino, "WEBP", quality=calidad, method=6)
    print(f"{destino.name}: {origen.stat().st_size // 1024} KB -> {destino.stat().st_size // 1024} KB")


def icono(tam):
    ruta = IMG / f"icono-{tam}.png"
    antes = ruta.stat().st_size
    with Image.open(ruta) as im:
        im = im.convert("RGBA").resize((tam, tam), Image.LANCZOS)
        im.quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(ruta, optimize=True)
    print(f"{ruta.name}: {antes // 1024} KB -> {ruta.stat().st_size // 1024} KB")


def fuente(nombre, tam):
    try:
        return ImageFont.truetype(str(FUENTES / nombre), tam)
    except OSError:
        return ImageFont.load_default(tam)


def og():
    """Imagen de 1200 x 630 para WhatsApp, Facebook, X, etc."""
    with Image.open(IMG / "bosque.jpg") as im:
        im = im.convert("RGB")
        escala = max(1200 / im.width, 630 / im.height)
        im = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
        x, y = (im.width - 1200) // 2, (im.height - 630) // 2
        im = im.crop((x, y, x + 1200, y + 630))
    sombra = Image.new("RGBA", im.size)
    d = ImageDraw.Draw(sombra)
    for i in range(630):
        d.line([(0, i), (1200, i)], fill=(12, 22, 16, int(60 + 175 * i / 630)))
    im = Image.alpha_composite(im.convert("RGBA"), sombra)
    with Image.open(IMG / "icono-192.png") as ic:
        im.alpha_composite(ic.convert("RGBA").resize((96, 96)), (72, 300))
    d = ImageDraw.Draw(im)
    d.text((72, 414), "Herbolario Consultor", font=fuente("georgiab.ttf", 70), fill="#ffffff")
    d.text((72, 500), "Guía de suplementos Nature's Sunshine · evidencia, seguridad y asesoría",
           font=fuente("segoeui.ttf", 30), fill="#e3ebe2")
    d.text((72, 548), "Supplement guide · evidence, safety and personal guidance",
           font=fuente("segoeui.ttf", 26), fill="#cfe3d4")
    im.convert("RGB").save(IMG / "og.jpg", "JPEG", quality=82, optimize=True, progressive=True)
    print(f"og.jpg: {(IMG / 'og.jpg').stat().st_size // 1024} KB")


if __name__ == "__main__":
    webp("bosque", 1400, 55)
    for n in ["equinacea", "astragalo", "goji", "jengibre", "curcuma", "manzanilla", "diente-de-leon", "alfalfa", "menta"]:
        webp(n, 800)
    for t in (180, 192, 512):
        icono(t)
    og()
