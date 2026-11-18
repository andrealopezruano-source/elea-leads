"""Busca teléfonos y WhatsApp en la web de cada dominio: home, contacto, aviso legal y pie."""
import os
from pathlib import Path
import asyncio, json, re, sys
from urllib.parse import urljoin, urlparse, unquote
from playwright.async_api import async_playwright
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
HINTS=["contact","contacto","aviso-legal","aviso_legal","legal-notice","legal","condiciones","quienes-somos","sobre-nosotros","nosotros","about","donde-estamos"]
PH=re.compile(r'(?<![\d/])(?:\+?34[\s.\-]?)?([6789]\d{2}[\s.\-]?\d{2,3}[\s.\-]?\d{2,3}[\s.\-]?\d{0,3})(?![\d/])')
def norm(s):
    d=re.sub(r'\D','',s)
    if d.startswith('0034'): d=d[4:]
    if d.startswith('34') and len(d)==11: d=d[2:]
    return d if len(d)==9 and d[0] in '6789' else None
def tipo(n): return "móvil" if n[0] in "67" else ("fijo" if n[0] in "89" else "?")
async def visit(ctx,url):
    p=await ctx.new_page()
    try:
        r=await p.goto(url,wait_until="domcontentloaded",timeout=40000); await p.wait_for_timeout(2000)
        links=await p.eval_on_selector_all("a[href]","els=>els.map(e=>[e.href,(e.innerText||'').trim().slice(0,60)])")
        text=await p.evaluate("document.body?document.body.innerText:''")
        return {"url":p.url,"status":r.status if r else None,"links":links,"text":text}
    except Exception as e: return {"url":url,"error":str(e)[:120],"links":[],"text":""}
    finally: await p.close()
async def one(b,dom,sem):
    async with sem:
        ctx=await b.new_context(user_agent=UA,locale="es-ES",viewport={"width":390,"height":844})
        out={"domain":dom,"wa":{},"tel_links":{},"text_phones":{},"pages":[]}
        home=await visit(ctx,"https://"+dom)
        pages=[home]; base=home["url"]
        cand=[]
        for h,t in home["links"]:
            u=urlparse(h)
            if u.netloc.replace("www.","")==urlparse(base).netloc.replace("www.","") and any(k in (u.path+t).lower() for k in HINTS) and h not in cand:
                cand.append(h.split("#")[0])
        for u in cand[:5]: pages.append(await visit(ctx,u))
        for pg in pages:
            out["pages"].append(pg["url"])
            nums={norm(m.group(0)) for m in PH.finditer(pg["text"])}-{None}
            if len(nums)>5 or any(k in pg["url"].lower() for k in ("tiendas","store-locator","puntos-de-venta","distribuidores","donde-comprar")):
                out.setdefault("skipped",[]).append(pg["url"]); continue
            for h,t in pg["links"]:
                hl=h.lower()
                if "wa.me/" in hl or "whatsapp.com/send" in hl or "api.whatsapp.com" in hl or "whatsapp://" in hl:
                    m=re.search(r'(?:wa\.me/|phone=)(\+?\d+)',unquote(h)); n=norm(m.group(1)) if m else None
                    out["wa"][n or h[:80]]=pg["url"]
                if hl.startswith("tel:"):
                    n=norm(unquote(h[4:]))
                    if n: out["tel_links"][n]=pg["url"]
            for m in PH.finditer(pg["text"]):
                ctxt=pg["text"][max(0,m.start()-40):m.start()].lower()
                if any(k in ctxt for k in ("cif","nif","tomo","folio","hoja","b-","b6","referencia","ref.")): continue
                n=norm(m.group(0))
                if n: out["text_phones"].setdefault(n,(pg["url"],pg["text"][max(0,m.start()-50):m.end()+10].replace("\n"," ")))
        await ctx.close()
        # mejor número: WhatsApp > móvil en tel/texto > fijo
        allp=list(out["wa"].keys())+list(out["tel_links"].keys())+list(out["text_phones"].keys())
        allp=[p for p in allp if p and p.isdigit()]
        best=None; src=""
        for n in out["wa"]:
            if n and n.isdigit(): best,src=n,"WhatsApp (enlace en la web)"; break
        if not best:
            for n in allp:
                if tipo(n)=="móvil": best,src=n,"móvil publicado en la web"; break
        if not best and allp: best,src=allp[0],"fijo publicado en la web"
        out["best"]=best; out["best_tipo"]=("WhatsApp" if src.startswith("WhatsApp") else tipo(best)) if best else None; out["best_src"]=src
        print(json.dumps({k:out[k] for k in ("domain","best","best_tipo","best_src","wa","tel_links")},ensure_ascii=False),flush=True)
        return out
async def main():
    doms=sys.argv[2].split(","); res={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/opt/pw-browsers/chromium",args=["--no-sandbox"])
        sem=asyncio.Semaphore(6)
        for r in await asyncio.gather(*(one(b,d,sem) for d in doms)): res[r["domain"]]=r
        await b.close()
    json.dump(res,open(sys.argv[1],"w"),ensure_ascii=False,indent=1)
asyncio.run(main())
