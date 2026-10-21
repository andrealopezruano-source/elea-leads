"""Fase 7–8 — Calendario de envíos, supresión y filas del CRM.

El envío en sí (borrador o envío real) y la lectura de hilos se hacen con el conector
de Gmail desde la tarea diaria; aquí vive la lógica determinista que la gobierna.
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CRM_COLUMNS = [
    "fecha", "empresa", "dominio", "page_id", "url_pagina_fb", "nicho", "n_anuncios_activos",
    "anuncio_mas_antiguo", "plataformas", "formatos", "tecnologias", "empleados", "persona_contacto",
    "cargo", "email", "email_estado", "linkedin", "score", "motivo_score", "hallazgos_web",
    "hallazgos_anuncios", "asunto", "cuerpo_enviado", "estado", "proxima_accion", "fecha_proxima_accion",
    "fecha_envio", "gmail_thread_id", "gmail_message_id", "gmail_draft_id", "notas",
]
ESTADOS = ["nuevo", "borrador", "enviado", "seg1", "seg2", "respondió", "reunión", "descartado", "baja", "nutrir",
           "revision_manual"]
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def normalize_domain(d: str) -> str:
    d = (d or "").lower().strip()
    for p in ("https://", "http://", "www."):
        d = d.removeprefix(p)
    return d.split("/")[0]


def is_suppressed(email: str, domain: str, suppression: list[str]) -> bool:
    keys = {normalize_domain(s) if "@" not in s else s.lower().strip() for s in suppression if s}
    return email.lower() in keys or normalize_domain(domain) in keys


def next_send_day(cfg: dict, start: date) -> date:
    days = {DAY_KEYS.index(d) for d in cfg["schedule"]["send_days"]}
    d = start
    while d.weekday() not in days:
        d += timedelta(days=1)
    return d


def send_slots(cfg: dict, n: int, day: date, seed: int | None = None) -> list[datetime]:
    """n horas aleatorias (separadas al menos 6 min) dentro de la ventana de envío, hora de Madrid."""
    tz = ZoneInfo(cfg["schedule"]["timezone"])
    h0, h1 = (time.fromisoformat(t) for t in cfg["schedule"]["send_window"])
    start = datetime.combine(day, h0, tz)
    span = int((datetime.combine(day, h1, tz) - start).total_seconds() // 60)
    rng = random.Random(seed)
    picks: list[int] = []
    while len(picks) < min(n, span // 6):
        m = rng.randrange(span)
        if all(abs(m - p) >= 6 for p in picks):
            picks.append(m)
    return [start + timedelta(minutes=m) for m in sorted(picks)]


def followup_date(cfg: dict, sent: date, step: int) -> date:
    """Fecha del seguimiento `step` (0 → +3 días, 1 → +7 días), movida al siguiente día de envío."""
    return next_send_day(cfg, sent + timedelta(days=cfg["followups"][step]["day"]))


def crm_row(lead: dict) -> list:
    return [lead.get(c, "") if lead.get(c) is not None else "" for c in CRM_COLUMNS]
