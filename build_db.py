"""Crea la base de datos SQLite de productos Nature's Sunshine a partir de data/*.json.

Uso:  python build_db.py
Genera: naturessunshine.db
"""
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
DB_PATH = BASE / "naturessunshine.db"

SCHEMA = """
DROP TABLE IF EXISTS producto_ingrediente;
DROP TABLE IF EXISTS producto_beneficio;
DROP TABLE IF EXISTS producto_palabra_clave;
DROP TABLE IF EXISTS ingredientes;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS empresa;
DROP TABLE IF EXISTS documentos;
DROP TABLE IF EXISTS tcm_formula_hierba;
DROP TABLE IF EXISTS tcm_presentaciones;
DROP TABLE IF EXISTS tcm_formulas;
DROP TABLE IF EXISTS tcm_hierbas;
DROP TABLE IF EXISTS tcm_modelo;

CREATE TABLE categorias (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT UNIQUE NOT NULL
);

CREATE TABLE productos (
    id            TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    nombre_es     TEXT NOT NULL,
    categoria_id  INTEGER NOT NULL REFERENCES categorias(id),
    tipo          TEXT,
    sku           TEXT,
    precio_usd    REAL,
    presentacion  TEXT,
    modo_de_uso   TEXT,
    descripcion   TEXT,
    precauciones  TEXT,
    url           TEXT
);

CREATE TABLE ingredientes (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT UNIQUE NOT NULL
);

CREATE TABLE producto_ingrediente (
    producto_id     TEXT REFERENCES productos(id),
    ingrediente_id  INTEGER REFERENCES ingredientes(id),
    PRIMARY KEY (producto_id, ingrediente_id)
);

CREATE TABLE producto_beneficio (
    producto_id  TEXT REFERENCES productos(id),
    beneficio    TEXT NOT NULL
);

CREATE TABLE producto_palabra_clave (
    producto_id    TEXT REFERENCES productos(id),
    palabra_clave  TEXT NOT NULL
);

CREATE TABLE empresa (
    id      TEXT PRIMARY KEY,
    titulo  TEXT NOT NULL,
    texto   TEXT NOT NULL
);

-- Medicina tradicional china (data/tcm.json)
CREATE TABLE tcm_formulas (
    id TEXT PRIMARY KEY, nombre TEXT NOT NULL, polaridad TEXT, elemento TEXT,
    organos TEXT, meridianos TEXT, accion_energetica TEXT, formula_clasica_base TEXT,
    patrones_mtc TEXT, sintomas TEXT, condiciones_tradicionales TEXT, no_indicado_para TEXT,
    descripcion_oficial TEXT
);
CREATE TABLE tcm_presentaciones (
    formula_id TEXT REFERENCES tcm_formulas(id), formato TEXT, sku TEXT, precio_usd REAL,
    presentacion TEXT, modo_de_uso TEXT, url TEXT
);
CREATE TABLE tcm_hierbas (
    id TEXT PRIMARY KEY, pinyin TEXT, nombre_es TEXT, latin TEXT, naturaleza TEXT, sabor TEXT,
    meridianos TEXT, acciones TEXT, indicaciones_tradicionales TEXT, uso_historico TEXT, precauciones TEXT
);
CREATE TABLE tcm_formula_hierba (
    formula_id TEXT REFERENCES tcm_formulas(id), hierba_id TEXT REFERENCES tcm_hierbas(id), cantidad TEXT
);
CREATE TABLE tcm_modelo (id TEXT PRIMARY KEY, titulo TEXT NOT NULL, texto TEXT NOT NULL);

-- Tabla desnormalizada: un documento de texto por producto/ficha, lista para el RAG.
CREATE TABLE documentos (
    id      TEXT PRIMARY KEY,
    fuente  TEXT NOT NULL,      -- 'producto' | 'empresa'
    titulo  TEXT NOT NULL,
    texto   TEXT NOT NULL
);
"""


def get_or_create(cur, table, nombre):
    cur.execute(f"INSERT OR IGNORE INTO {table}(nombre) VALUES (?)", (nombre,))
    cur.execute(f"SELECT id FROM {table} WHERE nombre = ?", (nombre,))
    return cur.fetchone()[0]


def producto_a_texto(p):
    lineas = [
        f"Producto: {p['nombre_es']} ({p['nombre']}) [ID {p['id']}]",
        f"Categoría: {p['categoria']}",
        f"Tipo: {p['tipo']}",
    ]
    if p.get("sku"):
        lineas.append(f"Código (stock number): {p['sku']}")
    if p.get("presentacion"):
        lineas.append(f"Presentación: {p['presentacion']}")
    if p.get("precio_usd") is not None:
        lineas.append(f"Precio de referencia en la web de EE. UU.: {p['precio_usd']} USD")
    lineas += [
        f"Descripción: {p['descripcion']}",
        f"Ingredientes: {', '.join(p['ingredientes'])}",
        f"Beneficios: {'; '.join(p['beneficios'])}",
    ]
    if p.get("modo_de_uso"):
        lineas.append(f"Modo de uso: {p['modo_de_uso']}")
    lineas += [
        f"Precauciones: {p['precauciones']}",
        f"Palabras clave: {', '.join(p['palabras_clave'])}",
    ]
    if p.get("url"):
        lineas.append(f"Ficha oficial: {p['url']}")
    return "\n".join(lineas)


def main():
    productos = json.loads((BASE / "data" / "productos.json").read_text(encoding="utf-8"))
    empresa = json.loads((BASE / "data" / "empresa.json").read_text(encoding="utf-8"))

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    for p in productos:
        cat_id = get_or_create(cur, "categorias", p["categoria"])
        cur.execute(
            "INSERT INTO productos VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (p["id"], p["nombre"], p["nombre_es"], cat_id, p["tipo"], p.get("sku"), p.get("precio_usd"),
             p.get("presentacion"), p.get("modo_de_uso"), p["descripcion"], p["precauciones"], p.get("url")),
        )
        for ing in p["ingredientes"]:
            ing_id = get_or_create(cur, "ingredientes", ing)
            cur.execute("INSERT OR IGNORE INTO producto_ingrediente VALUES (?,?)", (p["id"], ing_id))
        cur.executemany("INSERT INTO producto_beneficio VALUES (?,?)", [(p["id"], b) for b in p["beneficios"]])
        cur.executemany("INSERT INTO producto_palabra_clave VALUES (?,?)", [(p["id"], k) for k in p["palabras_clave"]])
        cur.execute(
            "INSERT INTO documentos VALUES (?,?,?,?)",
            (p["id"], "producto", p["nombre_es"], producto_a_texto(p)),
        )

    for e in empresa:
        cur.execute("INSERT INTO empresa VALUES (?,?,?)", (e["id"], e["titulo"], e["texto"]))
        cur.execute(
            "INSERT INTO documentos VALUES (?,?,?,?)",
            (e["id"], "empresa", e["titulo"], f"{e['titulo']} [ID {e['id']}]\n{e['texto']}"),
        )

    tcm_path = BASE / "data" / "tcm.json"
    if tcm_path.exists():
        cargar_tcm(cur, json.loads(tcm_path.read_text(encoding="utf-8")))

    con.commit()
    n_prod = cur.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    n_cat = cur.execute("SELECT COUNT(*) FROM categorias").fetchone()[0]
    n_form = cur.execute("SELECT COUNT(*) FROM tcm_formulas").fetchone()[0]
    n_hierb = cur.execute("SELECT COUNT(*) FROM tcm_hierbas").fetchone()[0]
    n_doc = cur.execute("SELECT COUNT(*) FROM documentos").fetchone()[0]
    con.close()
    print(f"Base de datos creada en {DB_PATH.name}: {n_prod} productos, {n_cat} categorías, "
          f"{n_form} fórmulas chinas, {n_hierb} hierbas chinas, {n_doc} documentos para RAG.")


# ---------------------------------------------------------------- Medicina tradicional china

def lista(valor):
    return ", ".join(valor) if valor else "—"


def formula_a_texto(f, hierbas_por_id):
    lineas = [
        f"Fórmula china de Nature's Sunshine: {f['nombre']} [ID {f['id']}]",
        f"Polaridad en el sistema chino de Nature's Sunshine: {f.get('polaridad') or 'no indicada'}",
    ]
    if f.get("nombres_anteriores"):
        lineas.append(f"Nombres anteriores: {lista(f['nombres_anteriores'])}")
    if f.get("elemento"):
        lineas.append(f"Elemento: {f['elemento']}")
    lineas += [
        f"Órganos que trata: {lista(f.get('organos'))}",
        f"Meridianos: {lista(f.get('meridianos'))}",
        f"Acción energética: {f.get('accion_energetica') or '—'}",
    ]
    if f.get("formula_clasica_base"):
        lineas.append(f"Fórmula clásica en la que se basa: {f['formula_clasica_base']}")
    lineas += [
        f"Patrones de medicina china: {lista(f.get('patrones_mtc'))}",
        f"Síntomas específicos: {lista(f.get('sintomas'))}",
        f"Condiciones de salud en las que se ha usado tradicionalmente: {lista(f.get('condiciones_tradicionales'))}",
    ]
    if f.get("descripcion_oficial"):
        lineas.append(f"Descripción oficial: {f['descripcion_oficial']}")
    if f.get("hierbas"):
        partes = []
        for h in f["hierbas"]:
            hb = hierbas_por_id.get(h["hierba_id"], {})
            nombre = " / ".join(x for x in (hb.get("pinyin"), hb.get("nombre_es"), hb.get("latin")) if x)
            partes.append(f"{nombre} [{h['hierba_id']}]" + (f" {h['cantidad']}" if h.get("cantidad") else ""))
        lineas.append(f"Hierbas: {'; '.join(partes)}")
    for pr in f.get("presentaciones", []):
        datos = [pr.get("formato"), pr.get("presentacion"), f"código {pr['sku']}" if pr.get("sku") else None,
                 f"{pr['precio_usd']} USD" if pr.get("precio_usd") is not None else None]
        lineas.append(f"Presentación: {', '.join(d for d in datos if d)}"
                      + (f". Modo de uso: {pr['modo_de_uso']}" if pr.get("modo_de_uso") else "")
                      + (f". Ficha oficial: {pr['url']}" if pr.get("url") else ""))
    lineas.append(f"No indicada para / precauciones: {f.get('no_indicado_para') or f.get('precauciones') or 'consultar la etiqueta y a un profesional'}")
    return "\n".join(lineas)


def hierba_a_texto(h, formulas_por_id):
    nombres = " / ".join(x for x in (h.get("pinyin"), h.get("nombre_es"), h.get("latin")) if x)
    en = [f"{formulas_por_id[i]['nombre']} [{i}]" for i in h.get("formulas", []) if i in formulas_por_id]
    lineas = [
        f"Hierba china: {nombres} [ID {h['id']}]",
        f"Naturaleza (temperatura): {h.get('naturaleza') or '—'}",
        f"Sabor: {lista(h.get('sabor'))}",
        f"Meridianos / órganos: {lista(h.get('meridianos'))}",
        f"Acciones en medicina china: {lista(h.get('acciones'))}",
        f"Condiciones que trata por sí sola (uso tradicional): {lista(h.get('indicaciones_tradicionales'))}",
    ]
    if h.get("uso_historico"):
        lineas.append(f"Uso histórico (dato general, no verificado en las fuentes citadas): {h['uso_historico']}")
    lineas += [
        f"Precauciones: {h.get('precauciones') or '—'}",
        f"Presente en las fórmulas: {', '.join(en) if en else '—'}",
    ]
    return "\n".join(lineas)


def cargar_tcm(cur, tcm):
    j = lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
    hierbas_por_id = {h["id"]: h for h in tcm["hierbas"]}
    formulas_por_id = {f["id"]: f for f in tcm["formulas"]}

    for m in tcm["modelo"]:
        cur.execute("INSERT INTO tcm_modelo VALUES (?,?,?)", (m["id"], m["titulo"], m["texto"]))
        cur.execute("INSERT INTO documentos VALUES (?,?,?,?)",
                    (m["id"], "modelo_tcm", m["titulo"], f"Modelo energético chino: {m['titulo']} [ID {m['id']}]\n{m['texto']}"))

    for f in tcm["formulas"]:
        cur.execute("INSERT INTO tcm_formulas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            f["id"], f["nombre"], f.get("polaridad"), f.get("elemento"), j(f.get("organos")), j(f.get("meridianos")),
            f.get("accion_energetica"), f.get("formula_clasica_base"), j(f.get("patrones_mtc")), j(f.get("sintomas")),
            j(f.get("condiciones_tradicionales")), f.get("no_indicado_para"), f.get("descripcion_oficial")))
        for pr in f.get("presentaciones", []):
            cur.execute("INSERT INTO tcm_presentaciones VALUES (?,?,?,?,?,?,?)", (
                f["id"], pr.get("formato"), pr.get("sku"), pr.get("precio_usd"), pr.get("presentacion"),
                pr.get("modo_de_uso"), pr.get("url")))
        for h in f.get("hierbas", []):
            cur.execute("INSERT INTO tcm_formula_hierba VALUES (?,?,?)", (f["id"], h["hierba_id"], h.get("cantidad")))
        cur.execute("INSERT INTO documentos VALUES (?,?,?,?)",
                    (f["id"], "formula_tcm", f["nombre"], formula_a_texto(f, hierbas_por_id)))

    for h in tcm["hierbas"]:
        cur.execute("INSERT INTO tcm_hierbas VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            h["id"], h.get("pinyin"), h.get("nombre_es"), h.get("latin"), h.get("naturaleza"), j(h.get("sabor")),
            j(h.get("meridianos")), j(h.get("acciones")), j(h.get("indicaciones_tradicionales")),
            h.get("uso_historico"), h.get("precauciones")))
        titulo = " · ".join(x for x in (h.get("pinyin"), h.get("nombre_es")) if x) or h["id"]
        cur.execute("INSERT INTO documentos VALUES (?,?,?,?)",
                    (h["id"], "hierba_tcm", titulo, hierba_a_texto(h, formulas_por_id)))


if __name__ == "__main__":
    main()
