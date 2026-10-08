"""Une la investigación de medicina china en data/tcm.json.

Entradas (data/raw/):
  tcm_oficial.json   fichas oficiales de naturessunshine.com (productos y paquetes)
  tcm_modelo.json    modelo energético Positivo/Negativo y datos tradicionales por fórmula
  hierbas_*.json     materia médica de cada hierba

Uso:  python build_tcm.py
"""
import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).parent
RAW = BASE / "data" / "raw"

# Productos que no son fórmulas chinas aunque compartan nombre.
EXCLUIR = {"kidney-activator"}  # Kidney Activator occidental (enebro, perejil, gayuba)

# Ingredientes que no son hierbas chinas (Mineral-Chi Tonic).
NO_HIERBAS = {"potassium", "fulvic acid", "natural apple and cherry flavors", "purified water", "trace minerals",
              "white grape juice"}

# Nombres de etiqueta que remiten a otra hierba.
SINONIMOS = {"cardamon": "cardamom", "ligusticum wallichii": "cnidium", "deglycyrrhizinated licorice": "licorice"}


def clave(texto):
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    for a, b in SINONIMOS.items():
        t = t.replace(a, b)
    return t


def nombre_base(nombre):
    n = nombre.replace("®", "")
    n = re.sub(r"\(.*?\)", "", n)
    n = n.split("/")[0]
    n = re.sub(r"\b(TCM Concentrate|TCM Conc|TCM|VegCapsules|VegiCapsules|Liquid|Chinese|Formula)\b", "", n, flags=re.I)
    return re.sub(r"[\s,]+$", "", re.sub(r"\s+", " ", n)).strip(" ,")


# Palabras de parte de planta que se quitan para emparejar ingredientes con hierbas.
PARTES = r"\b(root|roots|tuber|rhizome|bark|stem|fruit|fruits|seed|seeds|flower|flowers|bud|buds|leaf|leaves|tops?|top|" \
         r"whole|plant|peel|twig|hull|of|without|with|sclerotium|shell|bulb|mushroom|fruiting|body|mycelia|extract|" \
         r"mature|green|rind|sap|and|the|asian|chinese|large|tartarian|tree|blue)\b"


def raiz(texto):
    return re.sub(r"\s+", " ", re.sub(PARTES, " ", clave(texto))).strip()


def main():
    oficial = json.loads((RAW / "tcm_oficial.json").read_text(encoding="utf-8"))
    modelo = json.loads((RAW / "tcm_modelo.json").read_text(encoding="utf-8"))
    hierbas_raw = []
    for f in sorted(RAW.glob("hierbas_*.json")):
        hierbas_raw += json.loads(f.read_text(encoding="utf-8"))

    # ---- Hierbas: un registro por pinyin, con todos los alias de etiqueta
    hierbas, por_pinyin, alias, alias_completo = [], {}, {}, {}
    for h in hierbas_raw:
        k = clave(h.get("pinyin")) or clave(h["nombre_etiqueta"])
        if k not in por_pinyin:
            reg = {kk: h.get(kk) for kk in ("pinyin", "chino", "latin", "nombre_es", "nombre_en", "parte", "naturaleza",
                                             "sabor", "meridianos", "categoria_mtc", "acciones", "indicaciones_tradicionales",
                                             "uso_historico", "precauciones", "nota", "fuentes")}
            reg["etiquetas"] = []
            por_pinyin[k] = reg
            hierbas.append(reg)
        reg = por_pinyin[k]
        reg["etiquetas"].append(h["nombre_etiqueta"])
        for parte in re.split(r"[;/()]| also | o ", h["nombre_etiqueta"]):
            if raiz(parte):
                alias.setdefault(raiz(parte), reg)
                alias_completo.setdefault(clave(parte), reg)
        for extra in (h.get("pinyin"), h.get("nombre_en")):
            if extra and raiz(extra):
                alias.setdefault(raiz(extra), reg)
    hierbas.sort(key=lambda r: clave(r["pinyin"]))
    for i, h in enumerate(hierbas, 1):
        h["id"] = f"HRB-{i:03d}"
        h["formulas"] = []

    def buscar_hierba(ing):
        # Primero el nombre completo con la parte de la planta ("lycium root bark" ≠ "lycium fruit").
        completo = clave(f"{ing.get('nombre_comun') or ''} {ing.get('parte') or ''}")
        if completo in alias_completo:
            return alias_completo[completo]
        candidatos = [ing.get("pinyin") and ing["pinyin"].split("(")[0], f"{ing.get('nombre_comun') or ''} {ing.get('parte') or ''}",
                      ing.get("nombre_comun")]
        for c in candidatos:
            r = raiz(c or "")
            if not r:
                continue
            if r in alias:
                return alias[r]
            for a, reg in alias.items():
                if a and (a.startswith(r) or r.startswith(a)):
                    return reg
        return None

    # ---- Fórmulas: agrupar las presentaciones oficiales por nombre base
    datos_modelo = {clave(nombre_base(f["nombre"])): f for f in modelo["formulas"]}
    formulas, por_nombre, sin_emparejar = [], {}, set()
    for p in oficial["productos"]:
        if p["slug"] in EXCLUIR:
            continue
        nb = nombre_base(p["nombre"])
        if clave(nb) not in por_nombre:
            m = datos_modelo.get(clave(nb), {})
            pol = m.get("polaridad")
            if not pol and p.get("paquete"):
                pol = "positiva" if p["paquete"].startswith("positivo") else "negativa"
            f = {
                "nombre": nb, "nombres_anteriores": m.get("nombres_anteriores") or [], "polaridad": pol,
                "elemento": m.get("elemento"), "organos": m.get("organos") or p.get("organos_mencionados") or [],
                "meridianos": m.get("meridianos") or [], "accion_energetica": m.get("accion_energetica") or p.get("energetica_oficial"),
                "formula_clasica_base": m.get("formula_clasica_base"), "patrones_mtc": m.get("patrones_mtc") or [],
                "sintomas": m.get("sintomas") or [], "condiciones_tradicionales": m.get("condiciones_tradicionales") or [],
                "no_indicado_para": m.get("no_indicado_para"), "descripcion_oficial": p.get("descripcion_oficial"),
                "energetica_oficial": p.get("energetica_oficial"), "beneficios_oficiales": p.get("beneficios") or [],
                "precauciones": p.get("precauciones"), "presentaciones": [], "hierbas": [],
                "fuentes": sorted(set((m.get("fuentes") or []) + [p["url"]])),
            }
            por_nombre[clave(nb)] = f
            formulas.append(f)
        f = por_nombre[clave(nb)]
        f["presentaciones"].append({k: p.get(k) for k in ("formato", "sku", "precio_usd", "presentacion", "modo_de_uso", "url")})
        if p["url"] not in f["fuentes"]:
            f["fuentes"].append(p["url"])
        if not f.get("energetica_oficial") and p.get("energetica_oficial"):
            f["energetica_oficial"] = p["energetica_oficial"]
        for ing in p["ingredientes"]:
            if clave(ing.get("nombre_comun")) in NO_HIERBAS:
                continue
            reg = buscar_hierba(ing)
            if reg is None:
                sin_emparejar.add(f"{nb}: {ing.get('nombre_comun')} {ing.get('parte') or ''}".strip())
                continue
            if all(x["hierba_id"] != reg["id"] for x in f["hierbas"]):
                f["hierbas"].append({"hierba_id": reg["id"], "cantidad": ing.get("cantidad")})

    formulas.sort(key=lambda f: ({"positiva": 0, "negativa": 1}.get(f["polaridad"], 2), f["nombre"]))
    for i, f in enumerate(formulas, 1):
        f["id"] = f"TCM-{i:03d}"
        for x in f["hierbas"]:
            next(h for h in hierbas if h["id"] == x["hierba_id"])["formulas"].append(f["id"])
    # Datos tradicionales del modelo para fórmulas que no están a la venta en la tienda de EE. UU.
    vendidas = set(por_nombre)
    paquetes_modelo = []
    for clave_m, m in datos_modelo.items():
        if clave_m in vendidas:
            continue
        if "pack" in clave_m:
            paquetes_modelo.append(m)
        else:
            print(f"Aviso: la fórmula '{m['nombre']}' del modelo no tiene ficha oficial; se omite.")

    # ---- Documentos del modelo
    mo = modelo["modelo"]
    secciones = [("Resumen del sistema chino de Nature's Sunshine", mo.get("resumen")),
                 ("Fórmulas positivas (Yang)", mo.get("positivo")),
                 ("Fórmulas negativas (Yin)", mo.get("negativo")),
                 ("Los Cinco Elementos y los órganos", mo.get("cinco_elementos")),
                 ("Cómo elegir entre la fórmula positiva y la negativa", mo.get("como_elegir")),
                 ("Historia del sistema", mo.get("historia"))]
    docs_modelo = [{"titulo": t, "texto": x} for t, x in secciones if x]
    for pm in paquetes_modelo:
        partes = [pm.get("accion_energetica"),
                  "Patrones: " + ", ".join(pm["patrones_mtc"]) if pm.get("patrones_mtc") else None,
                  "Síntomas: " + ", ".join(pm["sintomas"]) if pm.get("sintomas") else None,
                  "Uso tradicional: " + ", ".join(pm["condiciones_tradicionales"]) if pm.get("condiciones_tradicionales") else None,
                  "No indicado para: " + pm["no_indicado_para"] if pm.get("no_indicado_para") else None]
        cual = "positivo (+)" if pm.get("polaridad") == "positiva" else "negativo (−)"
        docs_modelo.append({"titulo": f"Energética del paquete {cual}", "texto": "\n".join(p for p in partes if p)})
    for pq in oficial["paquetes"]:
        docs_modelo.append({"titulo": pq["nombre"], "texto": (
            f"{pq['descripcion_oficial']}\nTipo: {pq['tipo']}. Fórmulas incluidas: {', '.join(pq['formulas_incluidas'])}."
            + (f" Código {pq['sku']}." if pq.get("sku") else "")
            + (f" Precio de referencia: {pq['precio_usd']} USD." if pq.get("precio_usd") is not None else "")
            + f" Ficha oficial: {pq['url']}")})
    for i, d in enumerate(docs_modelo, 1):
        d["id"] = f"MOD-{i:02d}"

    salida = {"modelo": docs_modelo, "formulas": formulas, "hierbas": hierbas, "fuentes_modelo": mo.get("fuentes", [])}
    (BASE / "data" / "tcm.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"tcm.json: {len(docs_modelo)} documentos de modelo, {len(formulas)} fórmulas, {len(hierbas)} hierbas.")
    sin_formula = [h["pinyin"] for h in hierbas if not h["formulas"]]
    if sin_formula:
        print("Hierbas sin fórmula:", ", ".join(sin_formula))
    if sin_emparejar:
        print("Ingredientes sin emparejar:\n  " + "\n  ".join(sorted(sin_emparejar)))


if __name__ == "__main__":
    main()
