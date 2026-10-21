"""Fase 5 — Scoring 0–100: inversión (30) + ICP (25) + oportunidades (25) + contacto (20).

Las señales objetivas salen de las fases 1–3. Los juicios que requieren criterio
(¿es generalista/dropshipping?, ¿es marca de grupo?, hallazgos concretos) llegan en
`judgement`, que rellena la revisión de cada lead antes de puntuar.
"""
from __future__ import annotations


def score_lead(page: dict, web: dict, contact: dict, judgement: dict, cfg: dict) -> dict:
    reasons: list[str] = []

    # Inversión aparente (30)
    inv = 0
    if page["days_oldest_active"] >= 90:
        inv += 10; reasons.append(f"anuncio activo desde hace {page['days_oldest_active']} días")
    elif page["days_oldest_active"] >= 30:
        inv += 6
    n = page["active_ads"]
    inv += 10 if n >= 15 else 7 if n >= 6 else 4 if n >= 3 else 0
    if page["signals_invest"]["varias_versiones"]:
        inv += 5
    if page["signals_invest"]["usa_catalogo_dpa"]:
        inv += 5; reasons.append("usa anuncios de catálogo")
    inv = min(inv, 30)

    # Encaje ICP (25)
    icp = 0
    tech = set(web.get("home", {}).get("tech", []))
    if tech & {"shopify", "woocommerce", "prestashop", "magento", "wix"}:
        icp += 5
    if judgement.get("espana", True):
        icp += 5
    emp = contact.get("employees")
    lo, hi = cfg["icp"]["employees"]
    if emp is None or lo <= emp <= hi:
        icp += 5
    else:
        reasons.append(f"{emp} empleados (fuera de rango)")
    inhouse = sum(page["signals_inhouse"].values()) + int(bool(judgement.get("senal_inhouse")))
    icp += min(10, inhouse * 3)
    if judgement.get("generalista_o_dropshipping"):
        icp = 0; reasons.append("tienda generalista / dropshipping")
    if judgement.get("marca_de_grupo") or judgement.get("agencia_detectada"):
        icp = 0; reasons.append("marca de grupo o con agencia")
    icp = min(icp, 25)

    # Oportunidades claras (25): solo hallazgos con evidencia verificable
    findings = [f for f in judgement.get("hallazgos", []) if f.get("evidencia")]
    opp = min(25, 6 * len(findings) + (5 if judgement.get("oportunidad_amazon") else 0))

    # Calidad del contacto (20)
    con = 0
    if contact.get("name"):
        con += 8 if contact.get("is_founder") else 5
    status = contact.get("email_status")
    if status == "verified":
        con += 12
    elif status == "generic":
        con += 4; reasons.append("solo email genérico")
    elif status is None and contact.get("name"):
        con += 8  # pendiente de revelar: se recalcula tras Apollo
    con = min(con, 20)

    total = inv + icp + opp + con
    th = cfg["scoring"]
    tier = "email" if total >= th["email_threshold"] else "nutrir" if total >= th["nurture_threshold"] else "descartado"
    if tier != "descartado" and judgement.get("generalista_o_dropshipping"):
        tier = "descartado"
    return {
        "score": total,
        "tier": tier,
        "breakdown": {"inversion": inv, "icp": icp, "oportunidades": opp, "contacto": con},
        "motivo": f"inv {inv}/30, icp {icp}/25, opor {opp}/25, contacto {con}/20 — " + "; ".join(reasons),
    }
