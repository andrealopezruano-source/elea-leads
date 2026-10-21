"""Fase 1 — Descubrimiento de anunciantes en la Biblioteca de Anuncios de Meta.

Navega la Ad Library pública con Chromium (sin token) y analiza a nivel de página
de anunciante: primero busca por palabra clave para encontrar páginas candidatas
y después abre la vista de cada página (view_all_page_id) para medir su actividad.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

from playwright.async_api import async_playwright

log = logging.getLogger("discovery")

LIBRARY = "https://www.facebook.com/ads/library/"
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
# Destinos que no son la tienda del anunciante
NON_SHOP_HOSTS = (
    "facebook.com", "fb.me", "fb.com", "instagram.com", "messenger.com", "wa.me",
    "whatsapp.com", "play.google.com", "apps.apple.com", "linktr.ee", "bit.ly",
    "youtube.com", "tiktok.com", "google.com", "forms.gle", "onelink.me",
)


class RateLimited(Exception):
    pass


def build_queries(niche: dict, offer_terms: list[str], max_variants: int = 10) -> list[str]:
    """Variantes de búsqueda: términos de producto + producto combinado con oferta."""
    product = list(dict.fromkeys(niche["queries"]))
    queries = product[:7]
    offers = list(offer_terms)
    random.shuffle(offers)
    for term, offer in zip(product, offers):
        if len(queries) >= max_variants:
            break
        queries.append(f"{term} {offer}")
    return queries[:max_variants]


def shop_domain(url: str | None, caption: str | None = None) -> str | None:
    for candidate in (url, caption):
        if not candidate:
            continue
        if "://" not in candidate:
            candidate = "https://" + candidate
        host = (urlparse(candidate).hostname or "").lower()
        host = host.removeprefix("www.").removeprefix("m.")
        if not host or "." not in host or "{" in host:
            continue
        if any(host == h or host.endswith("." + h) for h in NON_SHOP_HOSTS):
            continue
        return host
    return None


def _iter_ads(obj):
    if isinstance(obj, dict):
        if "ad_archive_id" in obj and "snapshot" in obj:
            yield obj
        for v in obj.values():
            yield from _iter_ads(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_ads(v)


def normalize_ad(ad: dict) -> dict:
    snap = ad.get("snapshot") or {}
    cards = snap.get("cards") or []
    first_card = cards[0] if cards else {}
    link_url = snap.get("link_url") or first_card.get("link_url")
    body = (snap.get("body") or {}).get("text") or first_card.get("body") or ""
    title = snap.get("title") or first_card.get("title") or ""
    start = ad.get("start_date")
    images = snap.get("images") or []
    return {
        "ad_archive_id": ad.get("ad_archive_id"),
        "page_id": str(ad.get("page_id") or snap.get("page_id") or ""),
        "page_name": snap.get("page_name") or ad.get("page_name"),
        "page_url": snap.get("page_profile_uri"),
        "page_likes": snap.get("page_like_count"),
        "page_categories": snap.get("page_categories") or [],
        "is_active": ad.get("is_active"),
        "start_date": datetime.fromtimestamp(start, timezone.utc).date().isoformat() if start else None,
        "platforms": ad.get("publisher_platform") or [],
        "format": snap.get("display_format"),
        "cta_type": snap.get("cta_type") or first_card.get("cta_type"),
        "cta_text": snap.get("cta_text") or first_card.get("cta_text"),
        "body": body,
        "title": title,
        "link_url": link_url,
        "domain": shop_domain(link_url, snap.get("caption") or first_card.get("caption")),
        "versions": ad.get("collation_count") or 1,
        "n_cards": len(cards),
        "image_url": (images[0].get("original_image_url") if images else first_card.get("original_image_url")),
        "has_video": bool(snap.get("videos")) or any(c.get("video_sd_url") for c in cards),
    }


def parse_library_html(html: str) -> tuple[int | None, list[dict], bool]:
    """Devuelve (total de resultados, anuncios normalizados, captcha requerido)."""
    captcha = '"xfb_ad_library_is_captcha_required":true' in html
    m = re.search(r'"search_results_connection":\{"count":(\d+)', html)
    total = int(m.group(1)) if m else None
    ads: dict[str, dict] = {}
    for script in re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S):
        if '"ad_archive_id"' not in script or not script.lstrip().startswith("{"):
            continue
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue
        for ad in _iter_ads(data):
            n = normalize_ad(ad)
            ads[n["ad_archive_id"]] = n
    return total, list(ads.values()), captcha


class AdLibrary:
    """Sesión de navegador sobre la Ad Library con pausas para no disparar límites."""

    def __init__(self, country="ES", delay=(5.0, 10.0)):
        self.country = country
        self.delay = delay

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        self._ctx = await self._browser.new_context(
            locale="es-ES", user_agent=USER_AGENT, viewport={"width": 1366, "height": 900},
            timezone_id="Europe/Madrid",
        )
        self._page = await self._ctx.new_page()
        return self

    async def __aexit__(self, *exc):
        await self._browser.close()
        await self._pw.stop()

    def _url(self, **params) -> str:
        base = {"active_status": "active", "ad_type": "all", "country": self.country, "media_type": "all"}
        base.update(params)
        return LIBRARY + "?" + "&".join(f"{k}={quote(str(v))}" for k, v in base.items())

    async def _load(self, url: str) -> tuple[int | None, list[dict]]:
        for attempt in range(3):
            await asyncio.sleep(random.uniform(*self.delay))
            resp = await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await self._page.wait_for_timeout(4000)
            html = await self._page.content()
            total, ads, captcha = parse_library_html(html)
            if resp and resp.status == 200 and not captcha and (ads or total == 0):
                return total, ads
            wait = 30 * (attempt + 1)
            log.warning("Ad Library sin datos (status=%s captcha=%s); reintento en %ss", resp and resp.status, captcha, wait)
            await asyncio.sleep(wait)
        raise RateLimited(url)

    async def search_keyword(self, q: str):
        return await self._load(self._url(q=q, search_type="keyword_unordered"))

    async def page_ads(self, page_id: str):
        return await self._load(self._url(view_all_page_id=page_id, search_type="page"))


def summarize_page(page_id: str, total: int | None, ads: list[dict], today=None) -> dict:
    """Métricas y señales a nivel de página a partir de sus anuncios activos."""
    today = today or datetime.now(timezone.utc).date()
    ads = [a for a in ads if a["page_id"] == page_id] or ads
    starts = sorted(a["start_date"] for a in ads if a["start_date"])
    oldest = starts[0] if starts else None
    days_oldest = (today - datetime.fromisoformat(oldest).date()).days if oldest else 0
    days = [(today - datetime.fromisoformat(s).date()).days for s in starts]
    domains = Counter(a["domain"] for a in ads if a["domain"])
    formats = Counter(a["format"] for a in ads if a["format"])
    platforms = sorted({p for a in ads for p in a["platforms"]})
    bodies = [a["body"].strip() for a in ads if a["body"]]
    unique_bodies = len(set(bodies))
    paths = [urlparse(a["link_url"]).path.rstrip("/") for a in ads if a["link_url"] and a["domain"]]
    to_home = sum(1 for p in paths if p in ("", "/es", "/es-es"))
    ctas = Counter(a["cta_type"] for a in ads if a["cta_type"])
    n = len(ads)
    first = ads[0] if ads else {}

    signals_invest = {
        "anuncio_mas_30_dias": days_oldest >= 30,
        "min_3_activos": (total or n) >= 3,
        "varias_versiones": any(a["versions"] > 1 for a in ads),
        "usa_catalogo_dpa": formats.get("DPA", 0) + formats.get("DCO", 0) > 0,
    }
    signals_inhouse = {
        "poca_variedad_copy": n >= 3 and unique_bodies <= max(1, n // 3),
        "todo_a_la_home": bool(paths) and to_home / len(paths) >= 0.7,
        "copies_largos": bool(bodies) and sum(len(b) > 500 for b in bodies) / len(bodies) >= 0.5,
        "sin_testing_visible": n <= 3 and not signals_invest["varias_versiones"],
        "sin_catalogo": not signals_invest["usa_catalogo_dpa"],
    }
    return {
        "page_id": page_id,
        "page_name": first.get("page_name"),
        "page_url": first.get("page_url") or f"https://www.facebook.com/{page_id}",
        "page_likes": first.get("page_likes"),
        "page_categories": first.get("page_categories"),
        "library_url": f"{LIBRARY}?active_status=active&ad_type=all&country=ES&view_all_page_id={page_id}&search_type=page",
        "domain": domains.most_common(1)[0][0] if domains else None,
        "other_domains": [d for d, _ in domains.most_common()[1:4]],
        "active_ads": total if total is not None else n,
        "ads_sampled": n,
        "oldest_active_ad": oldest,
        "days_oldest_active": days_oldest,
        "ads_over_30_days": sum(d >= 30 for d in days),
        "platforms": platforms,
        "formats": dict(formats),
        "ctas": dict(ctas),
        "unique_copies": unique_bodies,
        "pct_to_home": round(to_home / len(paths), 2) if paths else None,
        "signals_invest": signals_invest,
        "signals_inhouse": signals_inhouse,
        "ads": [
            {k: a[k] for k in ("ad_archive_id", "start_date", "format", "platforms", "cta_type", "cta_text",
                               "title", "body", "link_url", "versions", "has_video", "image_url")}
            for a in sorted(ads, key=lambda a: a["start_date"] or "")
        ],
    }


def is_candidate(page: dict, cfg: dict, known_domains: set[str]) -> tuple[bool, str]:
    icp = cfg["icp"]
    lim = cfg["limits"]
    dom = page.get("domain")
    if not dom:
        return False, "sin tienda propia en los anuncios"
    if dom in known_domains:
        return False, "ya en el CRM"
    if any(dom == d or dom.endswith("." + d) for d in icp["exclude_domains"]):
        return False, "dominio excluido"
    name = (page.get("page_name") or "").lower()
    if any(k in name or k in dom for k in icp["exclude_keywords"]):
        return False, "palabra excluida en nombre/dominio"
    if (page.get("page_likes") or 0) > icp.get("max_page_likes", 10**9):
        return False, "marca demasiado grande"
    if page["active_ads"] < lim["min_active_ads"]:
        return False, f"solo {page['active_ads']} anuncios activos"
    if page["days_oldest_active"] < lim["min_days_active_oldest_ad"]:
        return False, f"anuncio más antiguo de {page['days_oldest_active']} días"
    return True, "ok"


async def discover(cfg: dict, niche_keys: list[str], known_domains: set[str], max_pages: int,
                   errors: list | None = None) -> dict:
    """Devuelve {'qualified': [...], 'rejected': [...], 'queries': n}."""
    errors = errors if errors is not None else []
    known = set(known_domains)
    seen_pages: dict[str, dict] = {}
    qualified, rejected = [], []
    n_queries = 0
    async with AdLibrary(cfg["meta"]["country"]) as lib:
        for key in niche_keys:
            niche = cfg["niches"][key]
            for q in build_queries(niche, cfg["offer_terms"], cfg["limits"].get("query_variants", 10)):
                if len(qualified) >= max_pages:
                    break
                n_queries += 1
                try:
                    _, ads = await lib.search_keyword(q)
                except RateLimited as e:
                    errors.append({"fase": "meta", "ref": q, "error": "rate limit / captcha"})
                    log.error("Rate limit en búsqueda %r: %s", q, e)
                    continue
                for a in ads:
                    if a["page_id"] and a["page_id"] not in seen_pages:
                        seen_pages[a["page_id"]] = {"niche": key, "query": q, "sample": a}
                # Prefiltro barato antes de abrir la página
                for pid, info in list(seen_pages.items()):
                    if info.get("done") or len(qualified) >= max_pages:
                        continue
                    info["done"] = True
                    s = info["sample"]
                    if not s["domain"] or s["domain"] in known:
                        continue
                    if (s["page_likes"] or 0) > cfg["icp"].get("max_page_likes", 10**9):
                        rejected.append({"page_id": pid, "page_name": s["page_name"], "domain": s["domain"],
                                         "motivo": "marca demasiado grande", "niche": key})
                        continue
                    try:
                        total, page_ads = await lib.page_ads(pid)
                    except RateLimited:
                        errors.append({"fase": "meta", "ref": pid, "error": "rate limit / captcha"})
                        continue
                    page = summarize_page(pid, total, page_ads)
                    page.update({"niche": key, "found_with_query": info["query"]})
                    ok, why = is_candidate(page, cfg, known)
                    if ok:
                        qualified.append(page)
                        known.add(page["domain"])
                        log.info("✓ %s (%s) %s anuncios, desde %s", page["page_name"], page["domain"],
                                 page["active_ads"], page["oldest_active_ad"])
                    else:
                        rejected.append({"page_id": pid, "page_name": page["page_name"], "domain": page["domain"],
                                         "motivo": why, "niche": key})
            if len(qualified) >= max_pages:
                break
    return {"qualified": qualified, "rejected": rejected, "queries": n_queries}
