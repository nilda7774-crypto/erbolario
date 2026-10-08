"""Sistema RAG sobre la base de datos de productos Nature's Sunshine.

1. Recuperación: índice BM25 (Python puro) sobre la tabla `documentos` de naturessunshine.db.
2. Generación: Claude responde usando solo los documentos recuperados y los cita por ID.

Uso:
    python rag.py                          # chat interactivo
    python rag.py "¿Qué me sirve para la digestión?"
    python rag.py --solo-busqueda "estrés"  # solo recuperación, sin API
"""
import argparse
import math
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).parent / "naturessunshine.db"
MODEL = "claude-opus-5-5"
TOP_K = 6

STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes como con contra cual cuales cuando de del
desde donde durante e el ella ellas ellos en entre era es esa esas ese eso esos esta estas este esto
estos fue ha hay la las le les lo los mas me mi mis mucho muy no nos o otra otro para pero poco por
porque que quien se sea ser si sin sobre son su sus tambien te tiene tengo tu un una uno unos y ya yo
cual sirve sirven puedo puede tomar producto productos recomiendas recomienda algun mejor hay tienen
estoy siento sentir quiero necesito ayuda ayudar ayude ayudan hola dame dime cosa bueno buena estar
""".split())
PESO_RAIZ = 0.4  # las coincidencias solo por raíz de 4 letras cuentan menos que las palabras completas


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", texto)
    salida = []
    for t in tokens:
        if t in STOPWORDS or len(t) < 2:
            continue
        # Stemming ligero de plurales: "articulaciones" -> "articulacion", "huesos" -> "hueso"
        if len(t) > 5 and t.endswith("es"):
            t = t[:-2]
        elif len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        salida.append(t)
        # Raíz de 4 letras como término extra para emparejar otras formas: "fundó"/"fundada", "dormir"/"dormido"
        if len(t) >= 4 and not t.isdigit():
            salida.append("~" + t[:4])
    return salida


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tf = [Counter(normalizar(d["titulo"] + " " + d["texto"])) for d in docs]
        # La primera línea de cada documento lleva sus nombres (producto, pinyin, nombre común, latín).
        self.titulos = [set(normalizar(d["texto"].split("\n", 1)[0])) for d in docs]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avgdl = sum(self.len) / len(self.len)
        df = Counter(term for tf in self.tf for term in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def buscar(self, consulta, k=TOP_K):
        terms = normalizar(consulta)
        enfoque = preferencia_de_tipo(terms)
        puntuaciones = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in terms:
                if t not in tf:
                    continue
                f = tf[t]
                peso = PESO_RAIZ if t.startswith("~") else 1.0
                s += peso * self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avgdl))
                if not t.startswith("~") and t in self.titulos[i]:
                    s += BONO_TITULO * self.idf[t]
            if s > 0:
                puntuaciones.append((s * enfoque.get(self.docs[i]["fuente"], 1.0), i))
        puntuaciones.sort(reverse=True)
        # Variedad: como máximo MAX_POR_TIPO documentos del mismo tipo entre los resultados.
        elegidos, por_tipo = [], Counter()
        for s, i in puntuaciones:
            fuente = self.docs[i]["fuente"]
            if por_tipo[fuente] < MAX_POR_TIPO:
                elegidos.append((self.docs[i], s))
                por_tipo[fuente] += 1
            if len(elegidos) == k:
                break
        return elegidos


BONO_TITULO = 1.0   # la palabra aparece en el nombre del documento
MAX_POR_TIPO = 3


def preferencia_de_tipo(terms):
    """Sube un tipo de documento cuando la pregunta lo nombra ("fórmula", "hierba", "china")."""
    t = set(terms)
    enfoque = {}
    if t & {"china", "chino", "chinas", "mtc", "tcm", "yin", "yang"}:
        for f in ("formula_tcm", "hierba_tcm", "modelo_tcm"):
            enfoque[f] = 1.2
    if t & {"formula", "formul", "combinacion"}:
        enfoque["formula_tcm"] = enfoque.get("formula_tcm", 1.0) * 1.6
    if t & {"hierba", "planta", "raiz"}:
        enfoque["hierba_tcm"] = enfoque.get("hierba_tcm", 1.0) * 1.6
    return enfoque


def cargar_documentos():
    if not DB_PATH.exists():
        sys.exit("No existe naturessunshine.db. Ejecuta primero: python build_db.py")
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    docs = [dict(r) for r in con.execute("SELECT id, fuente, titulo, texto FROM documentos")]
    con.close()
    return docs


SYSTEM = """Eres un asistente experto en el catálogo de Nature's Sunshine Products.
Responde en español, de forma clara y breve, usando ÚNICAMENTE la información de los documentos
que se te entregan en <documentos>. Cita cada producto o dato con su ID entre corchetes, por ejemplo [NSP-004].
Si los documentos no contienen la respuesta, dilo claramente en lugar de inventar.
Son suplementos alimenticios: no diagnostiques ni prometas curar enfermedades, menciona las precauciones
relevantes y recomienda consultar a un profesional de la salud cuando haya embarazo, niños, medicamentos
o una condición médica. El modo de uso proviene de la web oficial de EE. UU.; recuerda que la etiqueta
de cada país manda. Los precios son de referencia (tienda de EE. UU., septiembre de 2026) y pueden variar.
Si el documento incluye la ficha oficial, puedes ofrecer el enlace.
Para las fórmulas chinas [TCM-xxx], las hierbas chinas [HRB-xxx] y el modelo energético [MOD-xx]: explica la polaridad
(positiva/yang o negativa/yin), el órgano, el elemento, los síntomas y la fórmula clásica cuando el documento los dé,
y deja claro que se trata del uso tradicional de la medicina china, no de tratamientos médicos probados."""


def construir_contexto(resultados):
    bloques = [f'<documento id="{d["id"]}">\n{d["texto"]}\n</documento>' for d, _ in resultados]
    return "<documentos>\n" + "\n".join(bloques) + "\n</documentos>"


class AsistenteRAG:
    def __init__(self):
        import anthropic  # importado aquí para que --solo-busqueda funcione sin el SDK

        self.anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.docs = cargar_documentos()
        self.indice = BM25(self.docs)
        self.aviso = next((d for d in self.docs if d["id"] == "EMP-05"), None)
        self.historial = []

    def preguntar(self, pregunta):
        resultados = self.indice.buscar(pregunta)
        if self.aviso and all(d["id"] != "EMP-05" for d, _ in resultados):
            resultados.append((self.aviso, 0.0))

        contenido = f"{construir_contexto(resultados)}\n\nPregunta: {pregunta}"
        self.historial.append({"role": "user", "content": contenido})

        respuesta = self.client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            # Si el modelo rechaza la petición, la API la reintenta con un modelo de respaldo.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=self.historial,
        )
        # Se guarda el contenido completo (incluidos bloques de razonamiento) para la siguiente vuelta.
        self.historial.append({"role": "assistant", "content": respuesta.content})

        if respuesta.stop_reason == "refusal":
            texto = "No puedo responder a esa consulta."
        else:
            texto = "".join(b.text for b in respuesta.content if b.type == "text")
        fuentes = [d["id"] for d, _ in resultados]
        return texto, fuentes


def modo_busqueda(consulta):
    indice = BM25(cargar_documentos())
    resultados = indice.buscar(consulta)
    if not resultados:
        print("Sin resultados.")
    for d, s in resultados:
        print(f"{s:6.2f}  [{d['id']}] {d['titulo']}")


def main():
    parser = argparse.ArgumentParser(description="RAG de productos Nature's Sunshine")
    parser.add_argument("pregunta", nargs="*", help="Pregunta (si se omite, abre el chat)")
    parser.add_argument("--solo-busqueda", action="store_true", help="Solo muestra los documentos recuperados")
    args = parser.parse_args()
    pregunta = " ".join(args.pregunta)

    if args.solo_busqueda:
        modo_busqueda(pregunta or input("Búsqueda: "))
        return

    asistente = AsistenteRAG()
    if pregunta:
        texto, fuentes = asistente.preguntar(pregunta)
        print(f"{texto}\n\nFuentes recuperadas: {', '.join(fuentes)}")
        return

    print("Asistente Nature's Sunshine (escribe 'salir' para terminar)\n")
    while True:
        try:
            pregunta = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if pregunta.lower() in {"salir", "exit", "quit"}:
            break
        if not pregunta:
            continue
        try:
            texto, fuentes = asistente.preguntar(pregunta)
        except asistente.anthropic.AuthenticationError:
            sys.exit("Error de autenticación: define la variable ANTHROPIC_API_KEY.")
        except asistente.anthropic.RateLimitError:
            print("Límite de peticiones alcanzado; espera un momento y vuelve a intentarlo.\n")
            continue
        except asistente.anthropic.APIStatusError as e:
            print(f"Error de la API ({e.status_code}): {e.message}\n")
            continue
        except asistente.anthropic.APIConnectionError:
            print("No se pudo conectar con la API. Revisa tu conexión.\n")
            continue
        print(f"\nAsistente: {texto}\n  (fuentes: {', '.join(fuentes)})\n")


if __name__ == "__main__":
    main()
