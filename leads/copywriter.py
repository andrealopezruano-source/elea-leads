"""Fase 6 — Reglas del email y validación automática antes de crear el borrador.

La redacción la hace la revisión de cada lead a partir de sus hallazgos; este módulo
impide que salga nada que incumpla las reglas de Elea.
"""
from __future__ import annotations

import re

SIGNATURE = "Andrea\nElea Marketing"
OPT_OUT = "Si no te interesa, responde \"no\" y no vuelvo a escribirte."

BANNED = [
    "sinergia", "escalar exponencialmente", "exponencial", "garantizamos", "garantizado", "roas de",
    "inteligencia artificial", " ia ", "automatiza", "automático", "automática", "€/mes", "euros al mes",
    "precio", "tarifa", "te grabo un vídeo", "vídeo de 3 minutos", "bienvenido", "bienvenida", "bienvenid@", "querido", "querida", "estimado", "estimada",
]
# CTA permitidos: llamada corta o dossier de servicios
CTAS = ["¿Te cuadra una llamada de 15 minutos la semana que viene?",
        "¿Quieres que te enviemos nuestro dossier de servicios?"]
# Formas con género dirigidas a quien lee (nosotras sí usamos femenino para nosotras)
GENDERED_READER = [
    r"\binteresad[oa]s?\b", r"\bsegur[oa] de\b", r"\bcansad[oa]\b", r"\bsol[oa] (?:con|en)\b",
    r"\bocupad[oa]\b", r"\bharto\b", r"\bharta\b", r"\bliad[oa]\b", r"\bagobiad[oa]\b",
]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ'’%-]+\b", text))


def validate(subject: str, body: str, kind: str = "inicial") -> list[str]:
    """Devuelve la lista de incumplimientos (vacía = OK)."""
    problems = []
    core = body.split(OPT_OUT)[0].replace(SIGNATURE, "")
    wc = word_count(core)
    lo, hi = (90, 140) if kind == "inicial" else (30, 90)
    if not lo <= wc <= hi:
        problems.append(f"{wc} palabras (debe estar entre {lo} y {hi})")
    sw = len(subject.split())
    if not 2 <= sw <= 5 and kind == "inicial":
        problems.append(f"asunto de {sw} palabras")
    if subject != subject.lower():
        problems.append("asunto con mayúsculas")
    links = re.findall(r"https?://|www\.", body)
    if links and kind == "inicial":
        problems.append("el primer email no lleva enlaces")
    low = f" {body.lower()} "
    for b in BANNED:
        if b in low:
            problems.append(f"palabra prohibida: {b.strip()}")
    for pat in GENDERED_READER:
        m = re.search(pat, low)
        if m:
            problems.append(f"posible género hacia quien lee: «{m.group(0)}»")
    if OPT_OUT not in body and kind != "seg1":
        problems.append("falta la línea de baja")
    if kind == "inicial" and not any(c in body for c in CTAS):
        problems.append("el CTA debe ser la llamada de 15 minutos o el dossier de servicios")
    if "Andrea" not in body:
        problems.append("falta la firma")
    return problems
