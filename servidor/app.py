"""Servidor del asistente del Herbolario Consultor (para Render, plan gratuito).

Recibe la pregunta y las fichas que encontró el buscador de la página, y pide la respuesta a Gemini.
Solo usa la biblioteca estándar de Python: no hay dependencias que instalar.

Variables de entorno (se configuran en Render):
  GEMINI_API_KEY   clave de la API de Gemini (obligatoria; nunca se escribe en el código)
  GEMINI_MODEL     modelo a usar (por defecto: gemini-2.5-flash)
  ALLOWED_ORIGINS  orígenes permitidos separados por comas (por defecto: el sitio de Render y localhost)
  PORT             puerto (lo pone Render)

Rutas:
  GET  /api/salud      responde {"ok": true}; la página lo llama al cargar para despertar el servicio
  POST /api/preguntar  {"idioma": "es"|"en", "pregunta": str, "contexto": str, "historial": [{"rol": "user"|"model", "texto": str}]}
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELO = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
ORIGENES = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://herbolario-consultor.onrender.com,http://localhost:8765").split(",") if o.strip()]

# Límites para que nadie agote la cuota gratuita.
MAX_PREGUNTA = 600
MAX_CONTEXTO = 24000
MAX_TURNO = 4000
MAX_TURNOS = 6
POR_MINUTO = 6
POR_DIA = 60

REGLAS = {
    "es": """Eres un asistente experto en el catálogo de Nature's Sunshine Products.
Responde en español, de forma clara y breve, usando ÚNICAMENTE la información de los documentos que se te entregan en <documentos>.
Cita cada producto o dato con su ID entre corchetes, por ejemplo [NSP-004].
Si los documentos no contienen la respuesta, dilo claramente en lugar de inventar.
Solo respondes sobre el catálogo, las fórmulas chinas, las hierbas y su seguridad; si te preguntan otra cosa, dilo amablemente.
Son suplementos alimenticios: no diagnostiques ni prometas curar enfermedades, menciona las precauciones relevantes y recomienda consultar a un profesional de la salud cuando haya embarazo, niños, medicamentos o una condición médica.
El modo de uso proviene de la web oficial de EE. UU.; recuerda que la etiqueta de cada país manda. Los precios son de referencia (tienda de EE. UU., septiembre de 2026) y pueden variar.
Para las fórmulas chinas [TCM-xxx], las hierbas chinas [HRB-xxx] y el modelo energético [MOD-xx]: explica la polaridad (positiva/yang o negativa/yin), el órgano, el elemento, los síntomas y la fórmula clásica cuando el documento los dé, y deja claro que se trata del uso tradicional de la medicina china, no de tratamientos médicos probados.
Para la seguridad y las interacciones con medicamentos [SEG-xxx]: indica la gravedad y el nivel de evidencia, nunca digas que una combinación es segura solo porque no hay datos, recomienda siempre consultar al médico o farmacéutico y nunca sugieras suspender o cambiar un medicamento.
Usa párrafos cortos y listas con guiones. No uses tablas ni encabezados.""",
    "en": """You are an expert assistant for the Nature's Sunshine Products catalog.
Answer in English, clearly and briefly, using ONLY the information in the documents provided inside <documentos>.
Cite every product or fact with its ID in square brackets, for example [NSP-004].
If the documents do not contain the answer, say so clearly instead of making something up.
You only answer about the catalog, the Chinese formulas, the herbs and their safety; if asked about something else, say so politely.
These are dietary supplements: do not diagnose or promise to cure diseases, mention the relevant cautions, and recommend consulting a health professional for pregnancy, children, medications or a medical condition.
Suggested use comes from the official US website; remind the reader that the label in their country takes precedence. Prices are for reference (US store, September 2026) and may vary.
For Chinese formulas [TCM-xxx], Chinese herbs [HRB-xxx] and the energetic model [MOD-xx]: explain the polarity (positive/yang or negative/yin), the organ, the element, the symptoms and the classical formula when the document provides them, and make clear this is traditional Chinese medicine use, not proven medical treatment.
For safety and drug interactions [SEG-xxx]: state the severity and level of evidence, never call a combination safe just because there is no data, always recommend checking with a doctor or pharmacist, and never suggest stopping or changing a medication.
Use short paragraphs and bulleted lists with hyphens. Do not use tables or headings.""",
}

_registro = defaultdict(deque)
_candado = threading.Lock()


def permitido(ip):
    """Límite por visitante: POR_MINUTO preguntas por minuto y POR_DIA por día."""
    ahora = time.time()
    with _candado:
        q = _registro[ip]
        while q and ahora - q[0] > 86400:
            q.popleft()
        if len(q) >= POR_DIA or sum(1 for t in q if ahora - t < 60) >= POR_MINUTO:
            return False
        q.append(ahora)
        return True


def preguntar_a_gemini(idioma, pregunta, contexto, historial):
    contenidos = []
    for t in historial[-MAX_TURNOS:]:
        rol = "model" if t.get("rol") == "model" else "user"
        texto = str(t.get("texto", ""))[:MAX_TURNO]
        if texto:
            contenidos.append({"role": rol, "parts": [{"text": texto}]})
    etiqueta = "Pregunta" if idioma == "es" else "Question"
    contenidos.append({"role": "user", "parts": [{"text": f"{contexto}\n\n{etiqueta}: {pregunta}"}]})
    cuerpo = {
        "systemInstruction": {"parts": [{"text": REGLAS[idioma]}]},
        "contents": contenidos,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent",
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = json.load(r)
    if datos.get("promptFeedback", {}).get("blockReason"):
        return None, "bloqueada"
    cands = datos.get("candidates") or []
    if not cands:
        return None, "vacia"
    partes = (cands[0].get("content") or {}).get("parts") or []
    texto = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip()
    if not texto:
        return None, "vacia"
    return texto, cands[0].get("finishReason")


class Manejador(BaseHTTPRequestHandler):
    def _cors(self):
        origen = self.headers.get("Origin", "")
        if origen in ORIGENES:
            self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, codigo, obj):
        cuerpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/salud"):
            return self._json(200, {"ok": True, "listo": bool(API_KEY)})
        self._json(404, {"error": "no_encontrado"})

    def do_POST(self):
        if not self.path.startswith("/api/preguntar"):
            return self._json(404, {"error": "no_encontrado"})
        if self.headers.get("Origin", "") not in ORIGENES:
            return self._json(403, {"error": "origen"})
        if not API_KEY:
            return self._json(503, {"error": "sin_clave"})
        ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
        if not permitido(ip):
            return self._json(429, {"error": "limite"})
        try:
            largo = min(int(self.headers.get("Content-Length", "0")), 200_000)
            datos = json.loads(self.rfile.read(largo) or b"{}")
            idioma = "en" if datos.get("idioma") == "en" else "es"
            pregunta = str(datos.get("pregunta", "")).strip()[:MAX_PREGUNTA]
            contexto = str(datos.get("contexto", ""))[:MAX_CONTEXTO]
            historial = datos.get("historial") if isinstance(datos.get("historial"), list) else []
        except (ValueError, TypeError):
            return self._json(400, {"error": "peticion"})
        if not pregunta:
            return self._json(400, {"error": "peticion"})
        try:
            texto, motivo = preguntar_a_gemini(idioma, pregunta, contexto, historial)
        except urllib.error.HTTPError as e:
            codigo = "cuota" if e.code == 429 else "proveedor"
            print(f"Gemini HTTP {e.code}: {e.read()[:300]!r}")
            return self._json(502, {"error": codigo})
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"Gemini sin conexión: {e}")
            return self._json(502, {"error": "proveedor"})
        if texto is None:
            return self._json(200, {"error": "bloqueada" if motivo == "bloqueada" else "vacia"})
        self._json(200, {"texto": texto, "cortada": motivo == "MAX_TOKENS"})

    def log_message(self, formato, *args):
        print(f"{self.address_string()} {formato % args}")


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", "8000"))
    print(f"Asistente en el puerto {puerto} · modelo {MODELO} · clave {'configurada' if API_KEY else 'FALTA'}")
    ThreadingHTTPServer(("0.0.0.0", puerto), Manejador).serve_forever()
