"""Auditoría móvil + capturas: velocidad con 4G simulado, comprobaciones de CRO y capturas de evidencia."""
import os
from pathlib import Path
import asyncio, json, sys, re
from playwright.async_api import async_playwright
S=os.environ.get("ELEA_WA", str(Path(__file__).resolve().parent.parent / "state" / "whatsapp"))
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
JOBS=json.load(open(sys.argv[1]))
LCP_JS="""new Promise(r=>{let v=0;new PerformanceObserver(l=>{for(const e of l.getEntries())v=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});setTimeout(()=>r(v),1500)})"""
async def measure(b,url):
    ctx=await b.new_context(user_agent=UA,locale="es-ES",viewport={"width":390,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True)
    p=await ctx.new_page(); cdp=await ctx.new_cdp_session(p)
    await cdp.send("Network.enable")
    await cdp.send("Network.emulateNetworkConditions",{"offline":False,"latency":150,"downloadThroughput":1.6*1024*1024/8,"uploadThroughput":750*1024/8})
    await cdp.send("Emulation.setCPUThrottlingRate",{"rate":4})
    tot={"bytes":0,"req":0}
    p.on("response",lambda r: tot.__setitem__("req",tot["req"]+1))
    def onload(e):
        tot["bytes"]+=e.get("encodedDataLength",0)
    cdp.on("Network.loadingFinished",onload)
    out={"url":url}
    try:
        r=await p.goto(url,wait_until="load",timeout=90000)
        out["status"]=r.status if r else None
        out["lcp_ms"]=round(await p.evaluate(LCP_JS))
        await p.wait_for_timeout(3000)
        out["kb"]=round(tot["bytes"]/1024); out["requests"]=tot["req"]
    except Exception as e: out["error"]=str(e)[:150]
    await ctx.close(); return out
async def shoot(b,url,name,mobile=True,full=False,clip=None,wait=4000,scroll=0):
    if mobile: ctx=await b.new_context(user_agent=UA,locale="es-ES",viewport={"width":390,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True)
    else: ctx=await b.new_context(locale="es-ES",viewport={"width":1280,"height":900},device_scale_factor=1.5)
    p=await ctx.new_page(); info={"url":url,"file":name}
    try:
        r=await p.goto(url,wait_until="domcontentloaded",timeout=60000); await p.wait_for_timeout(wait)
        info["final"]=p.url; info["status"]=r.status if r else None
        if scroll: await p.mouse.wheel(0,scroll); await p.wait_for_timeout(1200)
        await p.screenshot(path=f"{S}/shots/{name}",full_page=full,clip=clip)
        txt=await p.evaluate("document.body.innerText"); info["text"]=" ".join(txt.split())[:3000]
        info["checks"]=await p.evaluate("""()=>{const h=document.documentElement.innerHTML.toLowerCase();const t=document.body.innerText.toLowerCase();
          return {whatsapp_btn:/wa\\.me|api\\.whatsapp|whatsapp/.test(h),bizum:/bizum/.test(h),paypal:/paypal/.test(h),klarna_aplazame:/klarna|aplazame|sequra|scalapay/.test(h),
          reviews:/reseñ|opinion|valoraci|judge\\.me|trustpilot|estrellas|reviews/.test(t),
          addtocart:!!document.querySelector('button[name=add], form[action*="/cart/add"] button, .single_add_to_cart_button, #add-to-cart, [data-button-action=add-to-cart]'),
          h1:(document.querySelector('h1')||{}).innerText||''}}""")
    except Exception as e: info["error"]=str(e)[:150]
    await ctx.close(); return info
async def main():
    res={}
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium",args=["--no-sandbox"])
        for dom,j in JOBS.items():
            r={"speed":[]}
            for u in j.get("speed",[]): r["speed"].append(await measure(b,u))
            r["shots"]=[]
            for s in j.get("shots",[]): r["shots"].append(await shoot(b,**s))
            res[dom]=r; print(dom,json.dumps(r["speed"]),[ (x["file"],x.get("status"),x.get("error")) for x in r["shots"]],flush=True)
        await b.close()
    json.dump(res,open(sys.argv[2],"w"),ensure_ascii=False,indent=1)
asyncio.run(main())
