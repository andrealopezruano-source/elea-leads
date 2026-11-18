import os
from pathlib import Path
import asyncio, json, sys
S=os.environ.get("ELEA_WA", str(Path(__file__).resolve().parent.parent / "state" / "whatsapp"))
src=open(str(Path(__file__).resolve().parent/"plan_pdf.py")).read().replace("asyncio.run(main())","")
ns={}; exec(src,ns)
from playwright.async_api import async_playwright
CHK="""()=>[...document.querySelectorAll('.page')].map((p,i)=>{const r=p.getBoundingClientRect();const f=p.querySelector('.foot').getBoundingClientRect();
 let mx=0;[...p.children].forEach(c=>{if(!c.classList.contains('foot')){const b=c.getBoundingClientRect();mx=Math.max(mx,b.bottom)}});
 const imgs=[...p.querySelectorAll('img')].filter(x=>!x.complete||x.naturalWidth==0).length;
 return {page:i+1,over:Math.round(mx-f.top),broken:imgs}})"""
async def main():
    data=json.load(open(sys.argv[1]))
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium",args=["--no-sandbox"])
        pg=await b.new_page(viewport={"width":816,"height":1451})
        for d in data:
            h=ns["build"](d)
            await pg.set_content(h,wait_until="networkidle"); await pg.evaluate("document.fonts.ready")
            res=await pg.evaluate(CHK)
            bad=[r for r in res if r["over"]>-2 or r["broken"]]
            await pg.pdf(path=f"{S}/planes/{d['pdf']}",width="216mm",height="384mm",print_background=True,prefer_css_page_size=True)
            print(d["pdf"],"OK" if not bad else f"REVISAR {bad}",flush=True)
        await b.close()
asyncio.run(main())
