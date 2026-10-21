"""Fase 3 — Research de la web de la tienda.

Visita home, 1–2 fichas de producto (las de los anuncios), carrito, "sobre nosotros"
y aviso legal con Chromium en modo móvil. Devuelve hechos verificables (no opiniones):
tecnologías, tracking, confianza, CRO, velocidad y textos para identificar a la persona
fundadora. La interpretación y redacción de hallazgos se hace después.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from playwright.async_api import async_playwright

from .discovery_meta import CHROMIUM

log = logging.getLogger("web")

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")

TECH_PATTERNS = {
    "shopify": r"cdn\.shopify\.com|Shopify\.theme",
    "woocommerce": r"woocommerce|wp-content/plugins/woocommerce",
    "wordpress": r"wp-content|wp-includes",
    "prestashop": r"prestashop|var prestashop",
    "magento": r"Magento|mage/cookies",
    "wix": r"static\.wixstatic\.com",
    "meta_pixel": r"connect\.facebook\.net/[^\"']*fbevents\.js|fbq\(['\"]init",
    "ga4": r"gtag/js\?id=G-|['\"]G-[A-Z0-9]{6,}['\"]",
    "google_ads_tag": r"AW-\d{6,}",
    "gtm": r"googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]{4,}",
    "tiktok_pixel": r"analytics\.tiktok\.com",
    "klaviyo": r"klaviyo\.com",
    "mailchimp": r"chimpstatic\.com|list-manage\.com",
    "judge_me": r"judge\.me|judgeme",
    "loox": r"loox\.io",
    "yotpo": r"yotpo\.com",
    "trustpilot": r"trustpilot\.com",
    "google_reviews_widget": r"elfsight|trustindex",
    "okendo": r"okendo\.io",
    "hotjar": r"hotjar\.com",
    "clarity": r"clarity\.ms",
}
PAYMENTS = ["bizum", "paypal", "klarna", "apple pay", "google pay", "contrareembolso",
            "contra reembolso", "aplazame", "sequra", "scalapay", "visa", "mastercard"]
ABOUT_HINTS = ["sobre-nosotros", "sobre nosotros", "quienes-somos", "quiénes somos", "nuestra historia",
               "about", "conocenos", "conócenos", "nosotros"]
LEGAL_HINTS = ["aviso-legal", "aviso legal", "legal-notice", "informacion-legal", "terminos", "condiciones"]
RETURNS_HINTS = ["devolucion", "devoluciones", "refund", "cambios"]
LCP_JS = """
() => new Promise(resolve => {
  let lcp = 0;
  try {
    new PerformanceObserver(list => { for (const e of list.getEntries()) lcp = e.startTime; })
      .observe({type: 'largest-contentful-paint', buffered: true});
  } catch (e) {}
  setTimeout(() => resolve(lcp), 1500);
})
"""


def pagespeed(url: str) -> dict | None:
    """Puntuación móvil y LCP de PageSpeed Insights (requiere PAGESPEED_API_KEY para uso diario)."""
    params = {"url": url, "strategy": "mobile", "category": "performance"}
    if os.getenv("PAGESPEED_API_KEY"):
        params["key"] = os.environ["PAGESPEED_API_KEY"]
    try:
        r = requests.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed", params=params, timeout=90)
        if r.status_code != 200:
            return None
        lh = r.json()["lighthouseResult"]
        return {
            "source": "pagespeed",
            "mobile_score": round(lh["categories"]["performance"]["score"] * 100),
            "lcp_s": round(lh["audits"]["largest-contentful-paint"]["numericValue"] / 1000, 1),
        }
    except Exception as e:  # noqa: BLE001
        log.warning("PageSpeed falló para %s: %s", url, e)
        return None


def amazon_presence(brand: str) -> dict:
    """Busca la marca en amazon.es. Devuelve nº de resultados con la marca en el título."""
    try:
        r = requests.get("https://www.amazon.es/s", params={"k": brand}, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/141.0 Safari/537.36", "Accept-Language": "es-ES,es;q=0.9"})
        if r.status_code != 200 or "captcha" in r.text.lower()[:5000]:
            return {"checked": False}
        titles = re.findall(r'<h2[^>]*aria-label="([^"]+)"', r.text) or re.findall(
            r'<span class="a-size-base-plus a-color-base a-text-normal">([^<]+)</span>', r.text)
        b = brand.lower()
        hits = [t for t in titles if b in t.lower()]
        return {"checked": True, "results_with_brand": len(hits), "examples": hits[:3]}
    except Exception:  # noqa: BLE001
        return {"checked": False}


def _find_links(links: list[dict], hints: list[str], domain: str) -> list[str]:
    out = []
    for l in links:
        href, text = l["href"], (l["text"] or "").lower()
        if domain not in (urlparse(href).hostname or ""):
            continue
        if any(h in href.lower() or h in text for h in hints):
            out.append(href.split("#")[0])
    return list(dict.fromkeys(out))


async def _visit(page, url: str) -> dict:
    resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    try:
        await page.wait_for_load_state("load", timeout=15000)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(3500)  # deja aparecer pop-ups y barras
    html = await page.content()
    text = await page.inner_text("body")
    links = await page.eval_on_selector_all(
        "a[href]", "els => els.map(e => ({href: e.href, text: e.innerText.trim().slice(0, 80)}))")
    lcp = await page.evaluate(LCP_JS)
    return {"url": page.url, "status": resp.status if resp else None, "html": html, "text": text,
            "links": links, "lcp_ms": round(lcp) if lcp else None}


def _above_fold_text(text: str, n=400) -> str:
    return re.sub(r"\s+", " ", text)[:n]


def _facts_from_html(html: str, text: str) -> dict:
    low = text.lower()
    years = [int(y) for y in re.findall(r"(?:©|copyright|&copy;)\s*(?:\d{4}\s*[-–]\s*)?(20\d{2})", html, re.I)]
    free_ship = re.findall(r"[^.\n]{0,60}env[ií]o[s]? gratis[^.\n]{0,60}", text, re.I)
    return {
        "tech": sorted(k for k, p in TECH_PATTERNS.items() if re.search(p, html, re.I)),
        "copyright_year": max(years) if years else None,
        "free_shipping_text": [re.sub(r"\s+", " ", s).strip() for s in free_ship[:3]],
        "payments": [p for p in PAYMENTS if p in low],
        "mentions_reviews": bool(re.search(r"rese[ñn]as|opiniones|valoraciones|reviews|★", text, re.I)),
        "email_popup": bool(re.search(r"suscr[ií]bete|newsletter|% de descuento en tu primera|primera compra", low)),
        "phone": bool(re.search(r"(?:\+34\s?)?[6789]\d{2}\s?\d{3}\s?\d{3}", text)),
        "whatsapp": "wa.me" in html or "whatsapp" in low,
        "sold_out_mentions": len(re.findall(r"agotado|sold out|sin stock", low)),
        "old_campaigns": sorted(set(m.lower() for m in re.findall(
            r"black friday|cyber monday|rebajas de (?:enero|verano)|san valent[ií]n|navidad 20\d{2}", low))),
    }


async def research_site(domain: str, product_urls: list[str], brand: str | None = None) -> dict:
    home_url = f"https://{domain}/"
    out: dict = {"domain": domain, "checked_at": date.today().isoformat(), "pages": {}, "errors": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        ctx = await browser.new_context(user_agent=MOBILE_UA, viewport={"width": 390, "height": 844},
                                        is_mobile=True, has_touch=True, locale="es-ES")
        page = await ctx.new_page()
        try:
            home = await _visit(page, home_url)
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"home: {e}")
            await browser.close()
            return out
        out["final_url"] = home["url"]
        out["home"] = {**_facts_from_html(home["html"], home["text"]), "above_fold": _above_fold_text(home["text"]),
                       "lcp_ms_playwright": home["lcp_ms"], "status": home["status"]}
        links = home["links"]

        # Fichas de producto: las de los anuncios primero
        pdps = [u for u in product_urls if "/products/" in u or "/producto" in u or "/product" in u][:2]
        if not pdps:
            pdps = [l["href"] for l in links if re.search(r"/products?/|/producto/", l["href"])][:1]
        for u in pdps:
            try:
                pdp = await _visit(page, u.split("?")[0])
                f = _facts_from_html(pdp["html"], pdp["text"])
                t = pdp["text"].lower()
                out["pages"].setdefault("pdp", []).append({
                    "url": pdp["url"], "status": pdp["status"],
                    "images": len(re.findall(r"<img[^>]+(?:product|media)", pdp["html"], re.I)),
                    "has_faq": bool(re.search(r"preguntas frecuentes|faq", t)),
                    "has_reviews": f["mentions_reviews"] or any(x in f["tech"] for x in ("judge_me", "loox", "yotpo", "okendo")),
                    "has_upsell": bool(re.search(r"tambi[eé]n te puede|completa tu|combina con|frecuentemente comprados|te recomendamos", t)),
                    "sold_out": f["sold_out_mentions"] > 0,
                    "excerpt": _above_fold_text(pdp["text"], 600),
                })
            except Exception as e:  # noqa: BLE001
                out["errors"].append(f"pdp {u}: {e}")

        # Carrito (sin comprar): la ruta depende de la plataforma
        tech = out["home"]["tech"]
        cart_paths = (["/checkout/cart/"] if "magento" in tech else
                      ["/carrito/", "/cart/"] if "woocommerce" in tech else
                      ["/carrito", "/index.php?controller=cart"] if "prestashop" in tech else ["/cart"])
        for path in cart_paths:
            try:
                cart = await _visit(page, urljoin(home["url"], path))
            except Exception as e:  # noqa: BLE001
                out["errors"].append(f"cart: {e}")
                continue
            out["pages"]["cart"] = {"url": cart["url"], "status": cart["status"],
                                    "excerpt": _above_fold_text(cart["text"], 300)}
            if cart["status"] == 200:
                break

        # Sobre nosotros y aviso legal (para la persona fundadora y la razón social)
        for key, hints in (("about", ABOUT_HINTS), ("legal", LEGAL_HINTS), ("returns", RETURNS_HINTS)):
            found = _find_links(links, hints, domain.split(":")[0])
            out[f"has_{key}_page"] = bool(found)
            if key == "returns" or not found:
                continue
            try:
                pg = await _visit(page, found[0])
                txt = re.sub(r"\s+", " ", pg["text"])
                out["pages"][key] = {"url": pg["url"], "text": txt[:3000] if key == "about" else txt[:2000]}
            except Exception as e:  # noqa: BLE001
                out["errors"].append(f"{key}: {e}")

        # Blog: fecha del último post si existe
        blog = _find_links(links, ["/blog", "/blogs/"], domain)
        out["has_blog"] = bool(blog)
        if blog:
            try:
                pg = await _visit(page, blog[0])
                dates = re.findall(r"(\d{1,2} (?:de )?(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]* (?:de )?20\d{2})",
                                   pg["text"], re.I)
                out["blog_latest_dates"] = dates[:3]
            except Exception as e:  # noqa: BLE001
                out["errors"].append(f"blog: {e}")

        out["social_links"] = sorted({l["href"].split("?")[0] for l in links
                                      if re.search(r"instagram\.com/|tiktok\.com/@|linkedin\.com/", l["href"])})[:6]
        out["links_to_amazon"] = any("amazon." in l["href"] for l in links)
        await browser.close()

    out["pagespeed"] = await asyncio.to_thread(pagespeed, out.get("final_url", home_url))
    if brand:
        out["amazon"] = await asyncio.to_thread(amazon_presence, brand)
    return out
