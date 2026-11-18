"""Abre cada anuncio por su ID en la Ad Library y lee si está Activo o Inactivo y sus fechas."""
import os
from pathlib import Path
import asyncio, sys, json, re
sys.path.insert(0,"/home/user/elea-leads")
from leads.discovery_meta import AdLibrary
S=os.environ.get("ELEA_WA", str(Path(__file__).resolve().parent.parent / "state" / "whatsapp"))
jobs=json.load(open(f"{S}/verify_jobs.json"))
out_f=f"{S}/verify_out.json"
try: out=json.load(open(out_f))
except Exception: out={}
async def main():
    async with AdLibrary("ES",delay=(2,4)) as lib:
        p=lib._page
        try: await lib.page_ads("1545946108820068")
        except Exception: pass
        for dom,j in jobs.items():
            for aid in j["ids"]:
                if aid in out: continue
                for attempt in range(3):
                    try:
                        await asyncio.sleep(2.5)
                        r=await p.goto(f"https://www.facebook.com/ads/library/?id={aid}",wait_until="domcontentloaded",timeout=60000)
                        await p.wait_for_timeout(8000)
                        t=" ".join((await p.evaluate("document.body.innerText")).split())
                        m=re.search(r'(Activo|Inactivo)[^I]{0,60}Identificador de la biblioteca:\s*'+aid+r'\s+(.{0,80}?)\s+Plataformas',t)
                        if m:
                            out[aid]={"dom":dom,"estado":m.group(1),"fechas":m.group(2)}; break
                        if r and r.status==403: await asyncio.sleep(30*(attempt+1)); continue
                        out[aid]={"dom":dom,"estado":"?","fechas":t[:160]}; break
                    except Exception as e:
                        out[aid]={"dom":dom,"estado":"ERR","fechas":str(e)[:100]}
                print(dom,aid,out[aid]["estado"],out[aid]["fechas"][:70],flush=True)
                json.dump(out,open(out_f,"w"),ensure_ascii=False,indent=1)
asyncio.run(main())
