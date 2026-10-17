# RAG de Nature's Sunshine

Base de datos SQLite con productos de Nature's Sunshine y un asistente RAG (búsqueda BM25 + respuestas de Claude).

## Estructura

| Archivo | Qué hace |
|---|---|
| `data/productos.json` | 86 productos extraídos de naturessunshine.com (EE. UU.) el 30-09-2026: código, precio, presentación, ingredientes, modo de uso, beneficios, precauciones, palabras clave y URL |
| `data/empresa.json` | 5 fichas sobre la empresa: historia, modelo de negocio, calidad, categorías y aviso legal |
| `data/raw/` | Lotes extraídos tal cual de la web y el primer borrador sin verificar (no se usa) |
| `data/tcm.json` | 16 fórmulas chinas (polaridad Positiva/Negativa, elemento, órganos, síntomas, uso tradicional, hierbas), 97 hierbas chinas (naturaleza, sabor, meridianos, acciones, indicaciones) y 12 fichas del modelo energético. Lo genera `build_tcm.py` a partir de `data/raw/tcm_*.json` y `data/raw/hierbas_*.json` |
| `data/sistemas.json` | 8 sistemas del cuerpo (estructural, linfático, nervioso, circulatorio, glandular, urinario, reproductor femenino y masculino), en español e inglés: qué hace, señales, hábitos, cuándo ir al médico y los productos, fórmulas y hierbas relacionados. Texto propio, no copiado de ningún libro. Lo usa `build_web.py` |
| `build_db.py` | Crea `naturessunshine.db` (tablas normalizadas y la tabla `documentos` que usa el RAG) |
| `rag.py` | Recupera los 5 documentos más relevantes y pide a Claude una respuesta con citas `[NSP-xxx]` |
| `build_web.py` + `web/plantilla.html` | Generan `web/herbolario.html`, la versión web (mismo buscador en JavaScript; en claude.ai responde con la cuenta del usuario) |

## Cómo ejecutarlo (Windows)

```bash
winget install Python.Python.3.12
```

```bash
pip install -r requirements.txt
```

```bash
python build_db.py
```

```bash
python rag.py --solo-busqueda "dolor de rodillas"
```

Para usar las respuestas de Claude, primero define `ANTHROPIC_API_KEY`:

```bash
python rag.py "¿Qué productos ayudan con la digestión y qué precauciones tienen?"
```

Para abrir el chat interactivo, ejecuta `python rag.py` sin argumentos.

## Ampliar el catálogo

Añade productos a `data/productos.json` con los mismos campos y vuelve a ejecutar `python build_db.py`.

## Aviso

Los datos vienen de la tienda oficial de EE. UU. y están traducidos al español. Los precios cambian (algunos estaban en oferta
al extraerlos), y las fórmulas, los nombres y las dosis pueden variar en otros países: la etiqueta local es la referencia.

## Publicar en Render

El sitio público está en `web/sitio/index.html`, que genera `python build_web.py`.
En el sitio público el chat muestra las fichas encontradas, pero Claude no escribe la respuesta.
Para tener respuestas de Claude hace falta un servidor con una clave de API de Anthropic.

1. Cambia los datos o la plantilla y ejecuta `python build_web.py`.
2. Sube los cambios a GitHub (`git add -A`, `git commit -m "..."`, `git push`).
3. Render vuelve a publicar el sitio automáticamente. La configuración está en `render.yaml`:
   sitio estático publicado desde `web/sitio`.

## Seguridad e interacciones

`build_seguridad.py` une `data/raw/seguridad_*.json` en `data/seguridad.json`: 147 hierbas y suplementos
(97 hierbas chinas, 47 hierbas occidentales y 3 suplementos), con 401 interacciones con medicamentos.
Cada interacción lleva su gravedad, su nivel de evidencia y la URL de la fuente. Las instrucciones que siguió
la investigación están en `data/raw/seguridad_INSTRUCCIONES.md`.
Orden para regenerar todo: `python build_seguridad.py`, `python build_db.py`, `python build_web.py`.
