# Herbolario Consultor

Aplicación web bilingüe (español e inglés) para elegir suplementos de Nature's Sunshine con información clara:
asistente de consulta, catálogo, sistemas del cuerpo, evidencia científica de plantas medicinales, medicina tradicional
china, seguridad con medicamentos y contacto por WhatsApp. Sitio publicado: https://herbolario-consultor.onrender.com

Funciona como sitio estático (gratis en Render) más un servidor pequeño opcional que redacta las respuestas con Gemini.
No hay cuentas de usuario, base de datos de usuarios, cookies ni analítica.

## Estructura

| Archivo | Qué hace |
|---|---|
| `data/productos.json` | 86 productos extraídos de naturessunshine.com (EE. UU.) el 30-09-2026 (en `data/en/` la traducción al inglés) |
| `data/empresa.json` | 5 fichas sobre la empresa |
| `data/tcm.json` | 16 fórmulas chinas, 97 hierbas chinas y 12 fichas del modelo energético. Lo genera `build_tcm.py` |
| `data/seguridad.json` | 147 hierbas y suplementos con 401 interacciones con medicamentos. Lo genera `build_seguridad.py` |
| `data/sistemas.json` | 9 sistemas del cuerpo, bilingües. Texto propio, no copiado de ningún libro |
| `data/evidencia.json` | Herbario clínico: 38 plantas con la evidencia por padecimiento, el extracto estudiado, la dosis, la tradición y la seguridad, bilingüe y enlazado al catálogo |
| `data/raw/` | Lotes originales extraídos de la web (no se usan directamente) |
| `web/src/` | Código fuente de la aplicación: `cuerpo.html` (estructura), `app.css`, `app.js` y `sw.js` (modo sin conexión) |
| `web/img/` | Fotos (WebP), iconos e imagen para redes (`og.jpg`). Se optimizan con `scripts/optimizar_imagenes.py` |
| `build_web.py` | Genera `web/sitio/` (lo que publica Render) y `web/herbolario.html` (versión de un solo archivo para claude.ai) |
| `servidor/app.py` | Servidor del asistente con Gemini (solo biblioteca estándar de Python, sin dependencias) |
| `build_db.py`, `rag.py` | Base SQLite y asistente de línea de comandos con Claude (uso local) |
| `render.yaml` | Configuración de los dos servicios de Render y de los encabezados de seguridad |

## Instalar y ejecutar en tu computadora (Windows)

```bash
winget install Python.Python.3.12
```

```bash
pip install -r requirements.txt
```

Generar el sitio y abrirlo en http://localhost:8765 :

```bash
python build_web.py
```

```bash
python -m http.server 8765 --directory web/sitio
```

Probar también el asistente: copia `.env.example` como `.env` y escribe tu clave de Gemini (el servidor lee `.env`
solo). Arranca el servidor en otra terminal y genera el sitio apuntando a él (en PowerShell):

```bash
python servidor/app.py
```

```powershell
$env:HERBOLARIO_API_URL="http://localhost:8000"; python build_web.py
```

Sin el servidor la página sigue funcionando: el chat muestra las fichas que mejor coinciden.

## Publicar en Render

1. Cambia los datos o `web/src/` y ejecuta `python build_web.py`.
2. Sube los cambios: `git add -A`, `git commit -m "..."`, `git push`. Render publica el sitio en uno o dos minutos.
3. **Asistente con Gemini (una sola vez):** en Render, *New → Blueprint* con este repositorio crea el servicio
   `herbolario-api`. En su panel, en *Environment*, escribe `GEMINI_API_KEY` (la clave nunca va en el código).
   Si el sitio estático se creó a mano y no desde el Blueprint, copia los encabezados de `render.yaml` en
   *Settings → Headers* del sitio.

## Seguridad

- **Secretos:** la única clave (`GEMINI_API_KEY`) vive en variables de entorno de Render o en `.env`, que está en
  `.gitignore`. El navegador nunca la recibe. El historial de git no contiene claves.
- **Validación en el servidor:** tipo de contenido JSON, tamaño máximo de 64 KB, pregunta de hasta 600 caracteres,
  contexto que solo admite fichas del catálogo con IDs conocidos (máximo 12), historial de 6 turnos, sin caracteres
  de control. El navegador también valida (límites `maxlength`, formulario de WhatsApp), pero el servidor no confía en él.
- **XSS:** todo texto dinámico pasa por `esc()` antes de insertarse; las respuestas del asistente se convierten a HTML
  escapando primero. No hay scripts ni estilos en línea, así que la **CSP** (en `render.yaml` y en una etiqueta `<meta>`)
  solo permite código propio.
- **Inyección de instrucciones:** el asistente trata la pregunta y las fichas como datos y solo responde sobre el catálogo.
- **SQL:** el sitio no usa SQL. `build_db.py` y `rag.py` usan consultas parametrizadas.
- **Autenticación:** no hay cuentas ni datos de usuarios que proteger; las favoritas se guardan solo en el navegador.
- **Límite de peticiones:** 6 preguntas por minuto y 60 por día por visitante, y un tope global diario (`TOTAL_POR_DIA`).
  El formulario de WhatsApp se bloquea 5 segundos tras enviarse.
- **Encabezados:** HTTPS y HSTS (Render), CSP, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`,
  `Cross-Origin-Opener-Policy`; el servidor añade también `Cache-Control: no-store`.
- **CORS:** el servidor solo acepta peticiones desde `ALLOWED_ORIGINS` (el sitio publicado).
- **Dependencias:** el sitio no usa paquetes de terceros y el servidor solo la biblioteca estándar. `pip-audit -r requirements.txt`
  no encontró vulnerabilidades conocidas (28-10-2026).

## Errores, registros y respaldo

- Página 404 propia (`404.html` y vista «no encontrado» para direcciones internas) y página 500 sin detalles técnicos.
  El servidor responde `{"error": "interno"}` sin trazas; el detalle queda solo en el registro.
- Estados de carga, de lista vacía y de error en cada pantalla; si los datos no cargan, aparece un botón «Reintentar».
- **Registros:** el servidor registra hora, ruta, código y tamaño de cada petición (nunca el texto de las preguntas).
  Se ven en Render, en *Logs* del servicio `herbolario-api`.
- **Respaldo:** no hay base de datos de usuarios. Todos los datos están en `data/*.json` dentro de git (GitHub es el
  respaldo); `naturessunshine.db` se vuelve a crear con `python build_db.py`.

## Legal

La aplicación incluye aviso de privacidad y términos de uso (`#/privacidad` y `#/terminos`). No usa cookies; el idioma,
el tema y las plantas guardadas se quedan en el navegador. Los precios son de referencia (tienda de EE. UU.) y la
información es educativa: los suplementos no diagnostican, tratan, curan ni previenen enfermedades.

## Actualizar los datos

Orden para regenerar todo: `python build_tcm.py`, `python build_seguridad.py`, `python build_db.py`, `python build_web.py`.
Las instrucciones que siguió la investigación de seguridad están en `data/raw/seguridad_INSTRUCCIONES.md`.
