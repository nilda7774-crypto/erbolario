# Instrucciones: seguridad e interacciones hierba-fármaco

Investiga la seguridad y las interacciones con fármacos de síntesis de cada hierba o suplemento de tu lote y guarda un JSON bilingüe (español/inglés). Es información de seguridad: la exactitud importa más que la cantidad.

## Fuentes (usa WebSearch y WebFetch)
Preferidas, en este orden:
1. MedlinePlus "Herbs and Supplements" (medlineplus.gov/druginfo/natural/…): tienen una sección de interacciones con fármacos y su gravedad.
2. Memorial Sloan Kettering "About Herbs" (mskcc.org … /integrative-medicine/herbs/…): sección "Herb-Drug Interactions".
3. NCCIH "Herbs at a Glance" (nccih.nih.gov), NIH LiverTox (ncbi.nlm.nih.gov/books/NBK547852 y fichas), monografías de la EMA (ema.europa.eu), Drugs.com.
4. Revisiones científicas en PubMed / PMC sobre interacciones hierba-fármaco (p. ej. dan shen + warfarina, gan cao + diuréticos/digoxina).
5. Para hierbas chinas sin ficha en las anteriores: americandragon.com (Cautions), meandqi.com, y revisiones de "Chinese herb drug interactions".

## Reglas
- No inventes nada. Cada interacción debe salir de una fuente que hayas leído, y su URL va en "fuente".
- Si no encuentras interacciones documentadas, deja "interacciones": [], pon "sin_interacciones_documentadas": true y dilo en "resumen". No rellenes con suposiciones.
- Interacciones teóricas (por el mecanismo) solo si una fuente las menciona; márcalas con "evidencia": "teorica".
- Solo fármacos de síntesis o clases de fármacos (warfarina, metformina, ISRS, ciclosporina, digoxina, anticonceptivos, fármacos que usan CYP3A4…), no otras hierbas ni alimentos.
- Gravedad: "alta" (evitar la combinación), "moderada" (precaución y vigilancia), "baja" (poco relevante), "teorica" (posible por mecanismo, sin casos).
- Evidencia: "clinica" (estudios en personas), "casos" (reportes de casos), "in_vitro_animal", "teorica".
- "clase" debe ser EXACTAMENTE uno de: anticoagulantes, antidiabeticos, antihipertensivos, cardiacos, diureticos, antidepresivos, sedantes, inmunosupresores, hormonas, tiroides, cyp450, quimioterapia, analgesicos, litio, absorcion, hepatotoxicos, otros.
  (cyp450 = fármacos metabolizados por CYP3A4/2C9/2D6/P-gp; absorcion = la hierba reduce la absorción de fármacos orales; hepatotoxicos = suma riesgo de daño hepático.)
- Redacta de forma clara para el público general, sin alarmismo, y recuerda que es información orientativa.
- Español neutro y su traducción fiel al inglés en cada campo bilingüe.

## Formato de salida
Archivo JSON UTF-8 (un array) en la ruta que indica tu lote. Guarda el archivo cada ~5 entradas para no perder trabajo. Cada elemento:

```json
{
  "ref": "HRB-038",
  "nombre": {"es": "Astrágalo (huang qi)", "en": "Astragalus (huang qi)"},
  "latin": "Astragalus membranaceus",
  "grupo": "china",
  "resumen": {"es": "1-2 frases sobre su seguridad general.", "en": "…"},
  "contraindicaciones": {"es": ["…"], "en": ["…"]},
  "embarazo_lactancia": {"es": "…", "en": "…"},
  "interacciones": [
    {"farmaco": {"es": "Inmunosupresores (ciclosporina, tacrolimus)", "en": "Immunosuppressants (cyclosporine, tacrolimus)"},
     "clase": "inmunosupresores",
     "efecto": {"es": "Puede contrarrestar su efecto al estimular el sistema inmunitario.", "en": "…"},
     "severidad": "moderada", "evidencia": "teorica", "fuente": "https://…"}
  ],
  "sin_interacciones_documentadas": false,
  "fuentes": ["https://…"]
}
```
- "ref": el ID de la hierba (HRB-xxx) si tu lote es de hierbas chinas; null para hierbas occidentales y suplementos.
- "grupo": "china", "occidental" o "suplemento".

Valida al final con Python (C:\Users\idplroom009usr\AppData\Local\Programs\Python\Python312\python.exe) que el JSON carga, que cada "clase", "severidad" y "evidencia" usa los valores permitidos y que toda interacción tiene "fuente". Responde solo con: cuántas entradas guardaste, cuántas tienen interacciones documentadas, y cualquier duda importante.
