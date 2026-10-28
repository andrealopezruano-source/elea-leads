"""Orquestador diario — parte determinista (Python).

Uso:
  python run_daily.py discover --known state/crm_domains.txt   # Fase 1 (+ deduplicación)
  python run_daily.py research                                   # Fases 3–4 sobre lo descubierto hoy
  python run_daily.py slots --n 12                               # horas de envío de hoy (Madrid)
  python run_daily.py validate --subject "..." --body-file x.txt # reglas del email

La tarea programada (ver DAILY_TASK.md) ejecuta estos pasos y hace con los conectores
lo que requiere criterio o cuentas (Apollo, Gmail, Google Sheets, redacción).
Es idempotente: cada paso guarda su salida en state/AAAA-MM-DD/ y no se repite si ya existe
(usa --force para rehacerlo). Los errores se registran y el proceso sigue con el siguiente lead.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from leads.copywriter import validate
from leads.discovery_meta import discover
from leads.outreach import normalize_domain, send_slots
from leads.web_research import research_site

ROOT = Path(__file__).parent
TODAY = datetime.now(ZoneInfo("Europe/Madrid")).date()
DAY_DIR = ROOT / "state" / TODAY.isoformat()


def setup_logging():
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(ROOT / "logs" / f"{TODAY}.log"), logging.StreamHandler()],
    )


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))


def todays_niches(cfg: dict) -> list[str]:
    """Rota los nichos: cada día laborable empieza por uno distinto."""
    keys = list(cfg["niches"])
    k = TODAY.toordinal() % len(keys)
    return keys[k:] + keys[:k]


def cmd_discover(args, cfg):
    out = DAY_DIR / "discovered.json"
    if out.exists() and not args.force:
        print(f"Ya existe {out}; nada que hacer.")
        return
    known = set()
    if args.known and Path(args.known).exists():
        known = {normalize_domain(l) for l in Path(args.known).read_text().splitlines() if l.strip()}
    errors: list = []
    res = asyncio.run(discover(cfg, todays_niches(cfg), known, cfg["limits"]["pages_per_day"], errors))
    res["errors"] = errors
    write_json(out, res)
    print(f"Descubiertas {len(res['qualified'])} páginas nuevas, {len(res['rejected'])} descartadas, "
          f"{len(errors)} errores. → {out}")


def cmd_research(args, cfg):
    src = DAY_DIR / "discovered.json"
    out = DAY_DIR / "research.json"
    pages = json.loads(src.read_text())["qualified"]
    done = json.loads(out.read_text()) if out.exists() and not args.force else {}
    for p in pages:
        dom = p["domain"]
        if dom in done:
            continue
        urls = [a["link_url"] for a in reversed(p["ads"]) if a.get("link_url")]
        try:
            done[dom] = asyncio.run(research_site(dom, urls, p["page_name"]))
        except Exception as e:  # noqa: BLE001
            logging.exception("research %s", dom)
            done[dom] = {"domain": dom, "errors": [f"fatal: {e}"]}
        write_json(out, done)  # guarda tras cada lead: si algo falla, se retoma
    print(f"Research de {len(done)} webs → {out}")


def cmd_slots(args, cfg):
    for s in send_slots(cfg, args.n, TODAY):
        print(s.isoformat())


def cmd_validate(args, cfg):
    body = Path(args.body_file).read_text()
    problems = validate(args.subject, body, args.kind)
    print(json.dumps({"ok": not problems, "problemas": problems}, ensure_ascii=False))
    sys.exit(1 if problems else 0)


def main():
    setup_logging()
    cfg = load_cfg()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover"); d.add_argument("--known"); d.add_argument("--force", action="store_true")
    r = sub.add_parser("research"); r.add_argument("--force", action="store_true")
    s = sub.add_parser("slots"); s.add_argument("--n", type=int, default=20)
    v = sub.add_parser("validate"); v.add_argument("--subject", required=True); v.add_argument("--body-file", required=True)
    v.add_argument("--kind", default="inicial", choices=["inicial", "seg1", "seg2"])
    args = ap.parse_args()
    {"discover": cmd_discover, "research": cmd_research, "slots": cmd_slots, "validate": cmd_validate}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
