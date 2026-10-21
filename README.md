# Elea Leads — captación diaria de ecommerce que se anuncian en Meta

Sistema de Elea Marketing que cada día laborable:

1. **Descubre** ecommerce españoles con anuncios activos en la Biblioteca de Anuncios de Meta. Lo hace
   a nivel de página de anunciante, eligiendo la página en el desplegable de sugerencias.
2. **Investiga** su web y sus anuncios:
   - tecnología, tracking, CRO y confianza;
   - presencia en Amazon;
   - creatividades, textos y destinos.
3. **Puntúa** cada lead de 0 a 100 y descarta los que no encajan, con el motivo.
4. **Redacta** un email personalizado con observaciones verificables y 3 ideas gratis.
5. Lo deja como **borrador en Gmail** y lo registra todo en el **CRM (Google Sheets)**.
6. Programa y redacta los **seguimientos** (día +3 y +7) en el mismo hilo. Se detienen si hay respuesta.

## Cómo funciona

| Pieza | Qué hace |
|---|---|
| `leads/discovery_meta.py` | Fase 1. Ad Library con navegador, sin token: búsqueda por palabras clave → desplegable → vista de página → métricas y señales |
| `leads/web_research.py` | Fases 3–4. Visita home, fichas, carrito, "sobre nosotros", aviso legal y blog en móvil; mide el LCP; busca la marca en Amazon.es |
| `leads/scoring.py` | Fase 5. Inversión 30 + ICP 25 + oportunidades 25 + contacto 20 |
| `leads/copywriter.py` | Fase 6. Reglas del email y validador automático |
| `leads/outreach.py` | Fases 7–8. Horas de envío, supresión y columnas del CRM |
| `run_daily.py` | Orquestador idempotente: `discover`, `research`, `slots`, `validate` |
| `DAILY_TASK.md` | Guion que sigue la tarea programada cada mañana: conectores de Gmail, Sheets y Apollo, y criterio |
| `config.yaml` | Nichos, límites, horarios, remitente y modo de envío |

La parte mecánica la hace Python. Lo que requiere criterio (descartar dropshipping, elegir hallazgos,
redactar) y las cuentas conectadas (Gmail, Google Sheets, Apollo) lo hace Claude en la tarea programada,
siguiendo `DAILY_TASK.md`.

**CRM:** <https://docs.google.com/spreadsheets/d/17gWx4WwjSL20IjUQnzvfZsPR9USTCE7xZGTAJa_hBi8>
- **Leads:** una fila por dominio, con estado y próxima acción.
- **Supresion:** bajas, respuestas negativas, rebotes y clientes. Nunca se les escribe.
- **Resumen_diario** y **Errores**.

## Instalación (solo si lo ejecutas en tu ordenador)

En la nube no hace falta: la tarea programada lo instala cada vez.

```bash
git clone https://github.com/andrealopezruano-source/elea-leads.git
cd elea-leads
pip install -r requirements.txt
python -m playwright install chromium   # solo en tu ordenador
cp .env.example .env                    # y rellena lo que tengas
```

En `.env` (nunca se sube a GitHub) todo es opcional:
- `PAGESPEED_API_KEY`: puntuación oficial de PageSpeed. Sin ella, se mide el LCP con el navegador.
- `META_ACCESS_TOKEN`: no se usa. El descubrimiento va por navegador.
- `APOLLO_API_KEY`: solo si algún día se usa Apollo fuera del conector.

### Ejecutarlo a mano
```bash
python run_daily.py discover --known state/crm_domains.txt   # Fase 1
python run_daily.py research                                   # Fases 3–4
python run_daily.py validate --subject "asunto" --body-file email.txt
```
Cada paso guarda su resultado en `state/AAAA-MM-DD/`. Si lo repites el mismo día no duplica nada; usa
`--force` para rehacerlo. Los logs quedan en `logs/AAAA-MM-DD.log`.

## Configuración (`config.yaml`)

- **`send_mode`**
  - `draft` (por defecto): solo crea borradores.
  - `send`: envía. Ver abajo.
- **`sender`**: nombre, cuenta y frase de presentación (`intro`) con `{sector}` y `{marca}`.
- **`limits`**:
  - `new_emails_per_day`: ahora 10;
  - `apollo_reveal_credits_per_day`: 0 = no se gasta ningún crédito;
  - `pages_per_day`;
  - `min_active_ads`;
  - `min_days_active_oldest_ad`.
- **`contact.fill_recipient`**: `false` = el borrador se crea sin destinatario y lo añades tú.
- **`schedule`**: días y franja de envío (martes a jueves, de 9:00 a 13:00, hora de Madrid).
- **`scoring`**: umbrales de 70 (email) y 50 (nutrir).
- **`icp`**: tamaño, cargos, dominios y palabras excluidas, y `max_page_likes`.

### Cómo añadir un nicho
Añade un bloque en `niches` con 5–10 búsquedas en español de España:
```yaml
niches:
  cosmetica_solida:
    label: Cosmética sólida
    queries: [champú sólido, desodorante natural, cosmética zero waste, pastilla jabón facial, acondicionador sólido]
```
Los términos de oferta (`offer_terms`: envío gratis, -20 %, nueva colección…) se combinan solos con los
de producto. Los nichos rotan: cada día se empieza por uno distinto.

## Del modo borrador al envío

Hoy funciona así:
1. Cada mañana aparecen en tu Gmail hasta 10 borradores **sin destinatario**.
2. Buscas el email en su web, lo pegas en el borrador y lo envías.
3. Al día siguiente el sistema detecta que lo has enviado y marca el lead como `enviado`.
4. Te prepara los seguimientos de los días +3 y +7 como borradores en el mismo hilo.

Para que envíe solo, cuando hayas validado varios borradores:
1. Pon `contact.fill_recipient: true` y sube `limits.apollo_reveal_credits_per_day`. Requiere créditos
   de Apollo para conseguir emails verificados.
2. Cambia `send_mode: draft` → `send_mode: send`.
3. Guarda los cambios en GitHub. La siguiente ejecución repartirá los envíos de martes a jueves entre las 9:00
   y las 13:00, revisando antes la lista de supresión.

## Tarea programada
Se ejecuta cada día laborable a las 8:30 (hora de Madrid) en una sesión nueva de Claude Code en la nube
con este repositorio y los conectores de Gmail, Google Sheets y Apollo. Puedes verla, pausarla o
lanzarla a mano en claude.ai/code → Scheduled tasks.

## Reglas del email
- Entre 90 y 140 palabras, texto plano, sin enlaces ni adjuntos.
- Asunto de 2–5 palabras en minúsculas.
- De tú y con lenguaje neutro hacia quien lee (nosotras sí en femenino).
- Nada de jerga vacía.
- Estructura:
  1. Presentación breve: mini auditorías del sector.
  2. Observación verificable.
  3. Dolor con empatía.
  4. Tres ideas rápidas.
  5. "Llevamos nosotras mismas Meta, Google y Amazon, sin permanencia".
  6. CTA de bajo compromiso.
  7. Firma y línea de baja.
- Prohibido: inventar datos, prometer resultados, hablar de precios, mencionar IA o automatización.
- Sin observación verificable no hay email: el lead pasa a revisión manual.
- `leads/copywriter.py` bloquea lo que incumpla las reglas.

## Aviso legal
En España, el art. 21 de la LSSI restringe las comunicaciones comerciales por email no solicitadas.
El primer email aporta valor sin vender, lleva línea de baja y respeta la lista de supresión. Aun así,
valida el enfoque con tu asesoría antes de enviar a volumen.
