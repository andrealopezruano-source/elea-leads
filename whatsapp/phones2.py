import os
from pathlib import Path
import asyncio, json, re, sys
from playwright.async_api import async_playwright
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
PATHS=["","/contacto","/contact","/pages/contacto","/pages/contact","/pages/contactanos","/policies/legal-notice","/pages/aviso-legal","/aviso-legal","/aviso-legal/","/pages/legal","/policies/terms-of-service","/pages/quienes-somos","/pages/sobre-nosotros"]
PH=re.compile(r'(?<![\d])(?:\+?34[\s.\-]?)?([6789]\d{2}[\s.\-]?\d{2,3}[\s.\-]?\d{2,3}[\s.\-]?\d{0,3})(?![\d])')
WA=re.compile(r'(?:wa\.me/|phone=|whatsapp[^"\']{0,40}?)(\+?34)?[\s%20]*(\d[\d\s%20]{8,14})',re.I)
def norm(s):
    d=re.sub(r'\D','',s)
    if d.startswith('34') and len(d)==11: d=d[2:]
    return d if len(d)==9 and d[0] in '6789' else None
async def one(b,dom,sem):
    async with sem:
        ctx=await b.new_context(user_agent=UA,locale="es-ES")
        p=await ctx.new_page(); res={"wa":set(),"txt":{}}
        for path in PATHS:
            try:
                r=await p.goto(f"https://{dom}{path}",wait_until="domcontentloaded",timeout=30000)
                if not r or r.status>=400: continue
                await p.wait_for_timeout(1500)
                html=await p.content(); txt=await p.evaluate("document.body.innerText")
                for m in WA.finditer(html.replace("%20"," ")):
                    n=norm(m.group(2))
                    if n: res["wa"].add(n)
                nums=[(norm(m.group(0)),txt[max(0,m.start()-50):m.end()+5].replace("\n"," ")) for m in PH.finditer(txt)]
                nums=[x for x in nums if x[0]]
                if len({n for n,_ in nums})<=5:
                    for n,c in nums: res["txt"].setdefault(n,(path or "/",c))
            except Exception: pass
        await ctx.close()
        print(json.dumps({"domain":dom,"wa":sorted(res["wa"]),"txt":res["txt"]},ensure_ascii=False),flush=True)
async def main():
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium",args=["--no-sandbox"])
        sem=asyncio.Semaphore(5)
        await asyncio.gather(*(one(b,d,sem) for d in sys.argv[1].split(",")))
        await b.close()
asyncio.run(main())
