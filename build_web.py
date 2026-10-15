"""Genera web/herbolario.html incrustando data/*.json en web/plantilla.html.

Uso:  python build_web.py
"""
import json
from pathlib import Path

BASE = Path(__file__).parent


def main():
    def cargar(carpeta):
        leer = lambda n: json.loads((carpeta / n).read_text(encoding="utf-8")) if (carpeta / n).exists() else None
        return {"productos": leer("productos.json"), "empresa": leer("empresa.json"), "tcm": leer("tcm.json")}

    es = cargar(BASE / "data")
    productos = es["productos"]
    idiomas = {"es": es}
    # Traducción al inglés (data/en/); lo que falte se muestra en español.
    en = cargar(BASE / "data" / "en")
    if en["productos"]:
        idiomas["en"] = {k: en[k] or es[k] for k in es}
    datos = json.dumps(idiomas, ensure_ascii=False)
    # Evita que un "</script>" dentro de los datos cierre la etiqueta antes de tiempo.
    datos = datos.replace("</", "<\\/")
    plantilla = (BASE / "web" / "plantilla.html").read_text(encoding="utf-8")
    creditos_path = BASE / "web" / "img" / "creditos.json"
    creditos = creditos_path.read_text(encoding="utf-8") if creditos_path.exists() else "{}"
    pagina = plantilla.replace("__DATA__", datos).replace("__CREDITOS__", creditos.replace("</", "<\\/"))

    # Versión para claude.ai (el publicador añade <!doctype>, <head> y <body>).
    salida = BASE / "web" / "herbolario.html"
    salida.write_text(pagina, encoding="utf-8")

    # Versión independiente para Render u otro hosting estático.
    sitio = BASE / "web" / "sitio"
    sitio.mkdir(exist_ok=True)
    img = BASE / "web" / "img"
    if img.is_dir():
        destino = sitio / "img"
        destino.mkdir(exist_ok=True)
        for f in img.iterdir():
            if f.is_file():
                (destino / f.name).write_bytes(f.read_bytes())
    (sitio / "index.html").write_text(
        '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="description" content="Herbolario Consultor: catálogo de productos de '
        'Nature\'s Sunshine, fórmulas chinas y hierbas, en español e inglés.">\n'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        '</head>\n<body>\n' + pagina + '\n</body>\n</html>\n',
        encoding="utf-8")
    print(f"Página generada en {salida.relative_to(BASE)} y {(sitio / 'index.html').relative_to(BASE)} "
          f"({len(productos)} productos).")


if __name__ == "__main__":
    main()
