# Ejecución diaria — guion para la tarea programada

Se ejecuta cada día laborable a las 8:30 (hora de Madrid) en una sesión nueva con este repositorio.
Sigue los pasos en orden. Si un paso falla para un lead, anótalo en la pestaña **Errores** del CRM
y sigue con el siguiente. Nunca te inventes datos: todo hallazgo lleva su evidencia (ID de anuncio,
fecha, URL o texto literal) y se comprueba antes de usarlo.

- CRM: Google Sheets `17gWx4WwjSL20IjUQnzvfZsPR9USTCE7xZGTAJa_hBi8` (pestañas Leads, Supresion,
  Resumen_diario, Errores).
- Configuración: `config.yaml`.
- Remitente: la cuenta de Gmail conectada (`sender.email`).

## 0. Preparación
1. `pip install -r requirements.txt`
2. Lee `config.yaml`.
3. Lee del CRM la columna `dominio` de **Leads** y toda **Supresion**. Escribe esos dominios en
   `state/crm_domains.txt`, uno por línea.

## 1. Seguimiento de lo que ya está en marcha
Antes de buscar leads nuevos, recorre los estados `borrador`, `enviado`, `seg1` y `seg2`.

**Borrador**
- Si ya no aparece en `list_drafts` y el hilo (`gmail_thread_id`) tiene un mensaje enviado por
  nosotras, es que Andrea lo envió a mano. Haz esto:
  - estado → `enviado`;
  - `fecha_envio` = fecha de ese mensaje;
  - guarda en `email` el destinatario y en `gmail_message_id` el id del mensaje;
  - `fecha_proxima_accion` = +3 días, movida al siguiente día de envío.
- Si sigue en borrador más de 7 días, próxima acción "revisar borrador pendiente".

**Enviado, seg1 o seg2.** Lee el hilo con `get_thread`.
- Si hay respuesta de la otra persona:
  - positiva o con pregunta → `respondió`, próxima acción "contestar (Andrea)";
  - "no", baja o negativa → `baja` y añádela a **Supresion**;
  - rebote → `descartado` y añádela a **Supresion**.
  
  En cualquiera de estos casos la secuencia se detiene.
- Si no hay respuesta, `fecha_proxima_accion` ya ha llegado y hoy es día de envío:
  - `enviado` → seguimiento 1: 30–90 palabras con **un insight nuevo** sacado de los hallazgos guardados;
  - `seg1` → seguimiento 2: cierre amable con la línea de baja.
  
  Valídalo con `python run_daily.py validate --kind seg1|seg2 ...` y crea el borrador **en el mismo hilo**
  (`create_draft` con `replyToMessageId`). Pasa el estado a `seg1` o `seg2`.
- Si un `seg2` lleva 7 días sin respuesta → `descartado` (motivo "sin respuesta").

## 2. Descubrimiento (Fase 1)
`python run_daily.py discover --known state/crm_domains.txt`

Por cada anunciante encontrado por palabra clave, el script repite el flujo de la interfaz:
España → Todos los anuncios → escribe el nombre → **elige la página del anunciante en el desplegable**
→ analiza todos sus anuncios activos. Guarda también otras páginas con el mismo nombre (`similar_pages`)
por si la marca se anuncia desde más de una.

## 3. Research (Fases 3–4)
`python run_daily.py research`

## 4. Revisión de cada lead (criterio)
1. Descarta y registra el motivo si es:
   - generalista o dropshipping;
   - de un grupo, un marketplace o una agencia;
   - demasiado grande (aporta la evidencia);
   - de fuera de España.
2. Abre su vista de página en la Ad Library (`library_url`) y repasa **todos** sus anuncios activos.
   Descarga y mira 2–4 creatividades. Anota:
   - textos repetidos, títulos cortados y ofertas caducadas;
   - a dónde lleva cada anuncio;
   - cuánto llevan activos.
3. Escribe los **hallazgos** con su evidencia.
4. Busca a la persona fundadora o CEO en "sobre nosotros", "equipo", el aviso legal o LinkedIn.
5. Puntúa con `leads/scoring.py`:
   - ≥ 70 → email;
   - 50–69 → `nutrir`;
   - < 50 → `descartado`.

## 5. Contacto (Fase 2)
`limits.apollo_reveal_credits_per_day: 0` → **no se gastan créditos de Apollo**. El borrador se crea
sin destinatario y Andrea añade el email que encuentre en la web.
- Si ves en la web un email genérico (info@, hola@), anótalo en `email_estado` como pista.
- Si algún día se sube ese límite, usa `apollo_people_match` (nombre + dominio) y solo emails `verified`.

## 6. Email inicial (Fase 6)
Reglas completas en `README.md` → "Reglas del email". Resumen:
- 90–140 palabras, texto plano, sin enlaces, de tú, lenguaje neutro hacia quien lee.
- Asunto de 2–5 palabras en minúsculas.
- Estructura:
  1. **Presentación breve y natural** (`sender.intro`): "Soy Andrea, de Elea Marketing. Con mi hermana
     Elena estamos haciendo mini auditorías a {sector} y {marca} estaba en la lista, así que te cuento
     lo que hemos visto."
  2. Observación verificable.
  3. Dolor con empatía.
  4. "Tres ideas rápidas" concretas y aplicables.
  5. "Llevamos nosotras mismas Meta, Google y Amazon, sin permanencia."
  6. CTA de bajo compromiso.
  7. Firma y línea de baja.
- Prohibido: inventar datos, prometer resultados, hablar de precio, mencionar IA o automatización.
- Si no hay una observación verificable → estado `revision_manual`.
- Valida con `python run_daily.py validate`. Si falla, reescribe.

## 7. Borradores (Fase 7)
- Como máximo `limits.new_emails_per_day` borradores nuevos al día (10).
- Revisa antes la supresión.
- `send_mode: draft` → `create_draft` **sin destinatario** si `contact.fill_recipient: false`.
  - Guarda `gmail_draft_id`, `gmail_thread_id` y `gmail_message_id`.
  - Estado `borrador`; próxima acción "Andrea: añadir el email del destinatario en el borrador y enviarlo".
- `send_mode: send` solo funciona con destinatario (requiere `fill_recipient: true`). Reparte los envíos
  en las horas de `python run_daily.py slots --n N`, de martes a jueves.

## 8. CRM y resumen
1. Una fila por dominio en **Leads**: si el dominio ya existe, actualiza esa fila en vez de añadir otra.
2. Añade una fila a **Resumen_diario**:
   - páginas descubiertas y nuevas;
   - cualificadas, nutrir y descartadas;
   - borradores y seguimientos;
   - respuestas;
   - créditos de Apollo.
3. Termina con un resumen corto: cifras del día, errores (rate limit de Meta, cambios en la interfaz,
   etc.) y la lista de borradores que esperan a que Andrea añada el destinatario.
