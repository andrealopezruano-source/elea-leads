# Captación por WhatsApp (formato Captación Córdoba)

Piloto del 18/11/2026: cada marca recibe un **plan digital en PDF** (3 páginas, mismo diseño que los de Córdoba)
y un **mensaje de WhatsApp** que Andrea envía a mano desde el panel
[Captación Ecommerce](https://claude.ai/artifact/KxJXzSTnmXKComTEPTQUw9).

Los ficheros de trabajo van en `state/whatsapp/` (o en la carpeta de `ELEA_WA`).

| Script | Qué hace |
|---|---|
| `phones.py salida.json dom1,dom2` | Busca WhatsApp (`wa.me`), `tel:` y teléfonos en home, contacto y aviso legal. Ignora listados de tiendas/distribuidores. Clasifica móvil / fijo / WhatsApp. |
| `verify_ads.py` | Abre cada anuncio citado por su ID (`?id=`) y lee **Activo / Inactivo** y sus fechas. Obligatorio antes de usar un anuncio como evidencia: la vista de página puede incluir anuncios ya apagados. |
| `audit.py jobs.json salida.json` | Velocidad en móvil (4G simulado, CPU x4: LCP, peso, peticiones) y capturas de la web. |
| `ad_crop.py '[["nombre","ad_id"]]'` | Captura recortada de la ficha del anuncio en la Ad Library. |
| `plan_pdf.py datos.json` | Genera el PDF de cada marca. Formato de datos: `ejemplo_piloto.json`. |

## Reglas del mensaje de WhatsApp
1. «Hola [nombre], soy Andrea, de Elea Marketing. ¡Enhorabuena por [hecho real comprobado]! Estoy haciendo
   miniauditorías a [sector] y [marca] estaba en la lista.»
2. «Os he preparado un plan de cómo funcionaría y lo que os beneficiaría [punto B]. Hoy [punto A: problema
   comprobado]… Os lo adjunto en PDF.»
3. «Por si queréis ver más de lo que hacemos: eleamarketing.netlify.app»
4. «¿Le echáis un ojo y me decís qué os parece dar el paso a [punto B]?»
5. Línea de baja: «Si no os encaja, decídmelo y no os escribo más.»

Sin «con mi hermana Elena», sin cifras prometidas, sin precios. Cada dato del PDF y del mensaje, comprobado el
mismo día (anuncio activo por ID, texto visible en la web, no solo en el código).
