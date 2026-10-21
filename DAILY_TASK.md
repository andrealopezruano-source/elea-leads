# Ejecución diaria — guion para la tarea programada

Se ejecuta cada día laborable a las 8:30 (hora de Madrid) en una sesión nueva con este repositorio.
Sigue los pasos en orden. Si un paso falla para un lead, anótalo en la pestaña **Errores** del CRM
y sigue con el siguiente. Nunca te inventes datos.

CRM: Google Sheets `17gWx4WwjSL20IjUQnzvfZsPR9USTCE7xZGTAJa_hBi8` (pestañas Leads, Supresion,
Resumen_diario, Errores). Configuración: `config.yaml`.

## 0. Preparación
1. `pip install -r requirements.txt`
2. Lee `config.yaml` (sobre todo `send_mode`, límites y remitente).
3. Lee del CRM la columna `dominio` de **Leads** y toda **Supresion**. Escribe los dominios en
   `state/crm_domains.txt` (uno por línea), incluidos los de Supresion.

## 1. Respuestas y seguimientos (antes de buscar leads nuevos)
Para cada fila de Leads con estado `enviado`, `seg1` o `seg2`:
1. Lee el hilo con `get_thread(gmail_thread_id)`.
2. Si hay un mensaje de la otra persona:
   - Respuesta positiva o con pregunta → estado `respondió`; próxima acción "contestar (Andrea)".
   - "no", baja o negativa → estado `baja` y añade el email a **Supresion** (motivo baja/negativa).
   - Rebote (mailer-daemon, "Delivery Status Notification") → estado `descartado` y a **Supresion** (rebote).
   - En todos los casos, la secuencia se detiene.
3. Si no hay respuesta y `fecha_proxima_accion` es hoy o anterior y hoy es día de envío:
   - `enviado` → escribe el seguimiento 1 (+3 días): 30–90 palabras, **un insight nuevo** que no saliera
     en el primer email, sacado de los hallazgos guardados. Pasa a `seg1`.
   - `seg1` → seguimiento 2 (+7 días): cierre amable, sin presión, con la línea de baja. Pasa a `seg2`.
   - Valídalo con `python run_daily.py validate --kind seg1|seg2 ...`.
   - Responde **en el mismo hilo** (`reply` si `send_mode: send`; `create_draft` con `replyToMessageId`
     si `send_mode: draft`).
   - Comprueba antes la lista de supresión.
4. Si `seg2` lleva 7 días sin respuesta → estado `descartado` (motivo "sin respuesta").

## 2. Descubrimiento (Fase 1)
`python run_daily.py discover --known state/crm_domains.txt`

## 3. Research (Fases 3–4)
`python run_daily.py research`

## 4. Revisión de cada lead (criterio)
Para cada página de `state/<hoy>/discovered.json` con su research:
1. **Descarta** (y regístralo en Leads con estado `descartado` y el motivo) si es:
   - tienda generalista o dropshipping de baja calidad (catálogo sin hilo común, pago contrareembolso
     como argumento principal, página de Facebook muy reciente con decenas de anuncios de respuesta directa);
   - marca de un grupo corporativo, marketplace o agencia;
   - fuera de España.
2. **Mira de verdad** 2–4 creatividades: descarga `image_url` y míralas. Anota:
   - hooks y ángulos;
   - UGC, prueba social y oferta;
   - textos cortados, `{{product.name}}` visibles y ofertas caducadas.
3. Escribe los **hallazgos** como lista `{tipo, hallazgo, evidencia}`. La evidencia tiene que ser verificable:
   ID del anuncio, fecha, URL o texto literal. Si no puedes comprobar algo, no lo pongas.
4. **Persona decisora**: búscala en "sobre nosotros" o "equipo", en el aviso legal y en LinkedIn (búsqueda web).
   Prioriza fundador/a o CEO.
5. Puntúa con `leads/scoring.py` (pasa el juicio en `judgement`). Guarda el desglose en `motivo_score`.
   - ≥ 70: candidato a email.
   - 50–69: estado `nutrir`.
   - < 50: `descartado`.

## 5. Contacto (Fase 2) — solo leads ≥ 70
- Límite diario: `limits.apollo_reveal_credits_per_day`.
- Usa `apollo_people_match` con nombre + dominio (1 crédito). Usa solo emails con `email_status: verified`.
- Si no hay email verificado → estado `revision_manual`, sin email. Excepción: un genérico (info@, hola@)
  si es la única opción; márcalo `email_estado: generic`.
- Recalcula el score con el estado real del email.
- Anota los créditos gastados en el resumen.

## 6. Email inicial (Fase 6)
Reglas completas en `README.md` → "Reglas del email". Resumen:
- 90–140 palabras, texto plano, sin enlaces, de tú, lenguaje neutro hacia quien lee.
- Asunto de 2–5 palabras en minúsculas.
- Estructura:
  1. Observación verificable.
  2. Dolor con empatía.
  3. 2–3 mejoras concretas y aplicables.
  4. Diferenciación en una línea.
  5. CTA de bajo compromiso.
  6. Firma "Andrea / Elea Marketing" y línea de baja.
- Prohibido: inventar datos, prometer resultados, hablar de precio, mencionar IA o automatización.
- Si no hay una observación verificable → `revision_manual`.
- Valida con `python run_daily.py validate --subject "..." --body-file ...`. Si falla, reescribe.

## 7. Envío (Fase 7)
- Solo martes, miércoles o jueves; máximo `limits.new_emails_per_day` nuevos.
- Revisa la supresión justo antes de cada envío.
- `send_mode: draft` → `create_draft`. Guarda `gmail_draft_id`; estado `borrador`.
- `send_mode: send` → reparte los envíos en las horas de `python run_daily.py slots --n N`. Usa
  `send_message` en cada hora (la sesión puede esperar entre envíos). Guarda `gmail_thread_id` y
  `gmail_message_id`; estado `enviado`; `fecha_proxima_accion` = +3 días (siguiente día de envío).
- Etiqueta los hilos en Gmail con `Elea/Leads`.

## 8. CRM y resumen
1. Escribe o actualiza cada lead en **Leads**, una fila por dominio. Si el dominio ya existe, actualiza
   esa fila en vez de añadir otra.
2. Añade una fila a **Resumen_diario**:
   - páginas descubiertas y nuevas;
   - cualificadas, nutrir y descartadas;
   - borradores o enviados y seguimientos;
   - respuestas;
   - créditos de Apollo.
3. Termina con un resumen corto en el chat: cifras del día, errores (rate limit de Meta, token
   caducado, etc.) y leads que necesitan revisión manual.
