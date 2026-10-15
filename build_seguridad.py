"""Une la investigación de seguridad e interacciones hierba-fármaco en data/seguridad.json.

Entradas: data/raw/seguridad_*.json (un array bilingüe por lote).
Uso:  python build_seguridad.py
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
CLASES = {"anticoagulantes", "antidiabeticos", "antihipertensivos", "cardiacos", "diureticos", "antidepresivos", "sedantes",
          "inmunosupresores", "hormonas", "tiroides", "cyp450", "quimioterapia", "analgesicos", "litio", "absorcion",
          "hepatotoxicos", "otros"}
SEVERIDADES = {"alta", "moderada", "baja", "teorica"}
EVIDENCIAS = {"clinica", "casos", "in_vitro_animal", "teorica"}
ORDEN_GRUPO = {"occidental": 0, "suplemento": 1, "china": 2}


def main():
    fichas, avisos = [], []
    for f in sorted((BASE / "data" / "raw").glob("seguridad_*.json")):
        for g in json.loads(f.read_text(encoding="utf-8")):
            for i in g.get("interacciones", []):
                if i.get("clase") not in CLASES:
                    avisos.append(f"{g['nombre']['es']}: clase '{i.get('clase')}' → otros"); i["clase"] = "otros"
                if i.get("severidad") not in SEVERIDADES:
                    avisos.append(f"{g['nombre']['es']}: severidad '{i.get('severidad')}' → teorica"); i["severidad"] = "teorica"
                if i.get("evidencia") not in EVIDENCIAS:
                    avisos.append(f"{g['nombre']['es']}: evidencia '{i.get('evidencia')}' → teorica"); i["evidencia"] = "teorica"
            g["sin_interacciones_documentadas"] = not g.get("interacciones")
            fichas.append(g)
    fichas.sort(key=lambda g: (ORDEN_GRUPO.get(g.get("grupo"), 9), g.get("ref") or "", g["nombre"]["es"].lower()))
    for n, g in enumerate(fichas, 1):
        g["id"] = f"SEG-{n:03d}"
    (BASE / "data" / "seguridad.json").write_text(json.dumps(fichas, ensure_ascii=False, indent=1), encoding="utf-8")
    con = sum(1 for g in fichas if g["interacciones"])
    total = sum(len(g["interacciones"]) for g in fichas)
    print(f"seguridad.json: {len(fichas)} fichas, {con} con interacciones, {total} interacciones en total.")
    for a in avisos:
        print("  aviso:", a)


if __name__ == "__main__":
    main()
