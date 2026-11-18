"""Genera el plan digital en PDF de cada ecommerce con el formato de Captación Córdoba."""
import os
from pathlib import Path
import asyncio, base64, json, sys, html
from pathlib import Path
from playwright.async_api import async_playwright
S=Path(os.environ.get("ELEA_WA", str(Path(__file__).resolve().parent.parent / "state" / "whatsapp")))
def b64(p): return "data:image/png;base64,"+base64.b64encode((S/p if not str(p).startswith("/") else Path(p)).read_bytes()).decode()
LOGO="data:image/png;base64,"+base64.b64encode((Path(__file__).resolve().parent/"assets/elea_logo_mask.png").read_bytes()).decode()
e=html.escape
CSS="""
@page{size:216mm 384mm;margin:0}
:root{--plum:#4F0C28;--coral:#A0386A;--lav:#C9CFF5;--lav2:#E6E8FB;--cream:#FAF3C6;--cream2:#F8F1C8;--muted:#6E4A5B;--line:#DCDFF7;--ok:#2E7D5B;--okbg:#E3F2EA;--warn:#8A5A00}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Poppins,sans-serif;color:var(--plum);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{width:216mm;height:384mm;position:relative;overflow:hidden;page-break-after:always;padding:0 15mm 20mm;display:flex;flex-direction:column}
.logo{width:28mm;height:12.2mm;display:block}
.top{display:flex;justify-content:space-between;align-items:center;padding-top:11mm;font-size:10.5pt;color:var(--muted)}
.foot{position:absolute;left:15mm;right:15mm;bottom:9mm;display:flex;justify-content:space-between;align-items:center;font-size:9.5pt;color:var(--muted)}
.foot .logo{width:16mm;height:7mm}
.hero{margin:0 -15mm;padding:0 15mm 22mm;background:var(--lav);position:relative;overflow:hidden}
.hero:before{content:"";position:absolute;right:-28mm;top:-30mm;width:92mm;height:92mm;border-radius:50%;background:var(--cream)}
.hero:after{content:"";position:absolute;left:-10%;right:-10%;bottom:-14mm;height:28mm;background:#fff;border-radius:50% 50% 0 0}
.hero>*{position:relative;z-index:1}
.eyebrow{font-size:9.5pt;letter-spacing:.28em;font-weight:700;color:var(--coral);text-transform:uppercase}
.hero .eyebrow{margin-top:17mm}
h1{font-size:44pt;font-weight:800;line-height:1.02;letter-spacing:-.02em;margin-top:3mm}
.sector{font-size:14pt;margin-top:4mm;color:var(--plum)}
.lead{font-size:19pt;line-height:1.35;font-weight:500;margin-top:4mm}
.sec{margin-top:9mm}
.sec>.eyebrow{margin-bottom:4mm}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}
.tile{background:var(--cream2);border-radius:5mm;padding:5mm 5mm 6mm}
.tile b{display:block;font-size:24pt;font-weight:800;line-height:1.1}
.tile span{font-size:10.5pt;line-height:1.35;display:block;margin-top:1.5mm}
.legend{font-size:10pt;color:var(--muted);display:flex;align-items:center;gap:2mm;margin-bottom:5mm}
.legend i{width:3mm;height:3mm;border-radius:50%;background:var(--coral);display:inline-block}
.tl{display:flex;flex-direction:column}
.tli{display:grid;grid-template-columns:11mm 1fr;gap:5mm;position:relative;padding-bottom:6mm}
.tli:not(:last-child):before{content:"";position:absolute;left:5.4mm;top:11mm;bottom:0;width:.4mm;background:var(--line)}
.dot{width:11mm;height:11mm;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:11pt;background:var(--lav2);color:var(--plum)}
.dot.bad{background:var(--coral);color:#fff}
.tli h3{font-size:14pt;font-weight:600;line-height:1.2}
.tli p{font-size:11pt;color:var(--muted);margin-top:1mm;line-height:1.4}
h2{font-size:30pt;font-weight:800;line-height:1.05;letter-spacing:-.015em;margin-top:9mm}
.subt{font-size:11pt;color:var(--muted);margin-top:2mm}
.shot{border:.35mm solid var(--line);border-radius:5mm;overflow:hidden;margin-top:5mm;background:#fff}
.shot .bar{background:var(--lav2);display:flex;justify-content:space-between;padding:3mm 5mm;font-size:10pt;font-weight:600}
.shot .bar span:last-child{font-weight:500}
.shot img{display:block;width:100%}
.cap{font-size:11.5pt;margin-top:3mm;line-height:1.45}
.pill{display:inline-block;margin-top:3mm;background:var(--cream);border:.35mm solid var(--plum);border-radius:99mm;padding:1.6mm 4mm;font-size:10pt;font-weight:600}
.two{display:grid;grid-template-columns:1fr 1fr;gap:5mm;align-items:start}
.phone img{height:118mm;object-fit:cover;object-position:top}
.adimg{height:118mm;object-fit:contain;background:#F3F3F7}
.audit{margin-top:4mm;display:flex;flex-direction:column;gap:2.4mm}
.ai{display:grid;grid-template-columns:22mm 1fr;gap:4mm;align-items:start;border:.35mm solid var(--line);border-radius:4mm;padding:2.6mm 4mm}
.tag{font-size:8.5pt;font-weight:700;letter-spacing:.06em;text-transform:uppercase;border-radius:99mm;padding:1.2mm 0;text-align:center}
.tag.bad{background:#F8E3E3;color:#A33A3A}.tag.mid{background:var(--cream);color:var(--warn)}.tag.ok{background:var(--okbg);color:var(--ok)}
.ai h4{font-size:12pt;font-weight:600;line-height:1.25}
.ai p{font-size:10.2pt;color:var(--muted);line-height:1.38;margin-top:.8mm}
.flow{display:grid;grid-template-columns:1fr 1fr 1fr;gap:3mm 5mm;margin-top:3mm}
.fi{display:grid;grid-template-columns:9mm 1fr;gap:2.5mm}
.ic{width:9mm;height:9mm;border-radius:2.6mm;font-size:11pt!important;background:var(--plum);position:relative;color:var(--cream);display:grid;place-items:center;font-weight:800;font-size:13pt}
.fi h4{font-size:11.5pt;font-weight:600;line-height:1.2}
.fi p{font-size:9.4pt;color:var(--muted);line-height:1.35;margin-top:.6mm}
.box{border:.35mm solid var(--line);border-radius:5mm;padding:3.2mm 6mm 3.2mm;margin-top:2.2mm}
.box ul{list-style:none;display:grid;grid-template-columns:1fr 1fr;gap:1.4mm 6mm;margin-top:2mm}
.box li{font-size:10.8pt;padding-left:5mm;position:relative;line-height:1.3}
.box li:before{content:"";position:absolute;left:0;top:1.8mm;width:2.3mm;height:2.3mm;border-radius:50%;background:var(--coral)}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:4mm}
.st{background:var(--lav2);border-radius:4mm;padding:3mm 4mm;display:grid;grid-template-columns:7mm 1fr;column-gap:2mm}
.st b{grid-row:span 2;font-size:16pt;line-height:1;color:var(--coral);font-weight:800;display:block}
.st h4{font-size:10.8pt;font-weight:700;margin-top:0;line-height:1.2}
.st p{font-size:9.4pt;color:var(--muted);margin-top:1mm;line-height:1.35}
.note{font-size:11.5pt;font-weight:500;margin-top:5mm}
.cta{flex-shrink:0;background:var(--plum);color:#fff;border-radius:6mm;padding:5.5mm 9mm 5.5mm;margin-top:4mm;position:relative;overflow:hidden}
.cta:after{content:"";position:absolute;right:-12mm;top:-12mm;width:50mm;height:50mm;border-radius:50%;border:7mm solid rgba(255,255,255,.12)}
.cta h2{color:var(--cream);margin:0;font-size:24pt}
.cta p{font-size:12pt;margin-top:2mm;max-width:120mm;line-height:1.45}
.cta .sig{color:var(--cream);font-weight:700;margin-top:3mm;font-size:12pt}
.brief{background:var(--cream2);border-color:var(--cream2)}
.brief .bt{font-size:12pt;font-weight:600;margin-top:1.5mm;line-height:1.35}
.fl{display:flex;gap:5mm;align-items:center}
.foot a{color:var(--plum);text-decoration:none;font-weight:600}
.links{display:flex;gap:8mm;margin-top:2.5mm;font-size:12pt;font-weight:600}
.links a{color:#FAF3C6;text-decoration:none}
.src{font-size:8.8pt;color:var(--muted);margin-top:4mm;line-height:1.4}
"""
def logo(): return f'<svg class="logo" viewBox="0 0 600 261"><defs><mask id="m{logo.n}" maskUnits="userSpaceOnUse" x="0" y="0" width="600" height="261"><image href="{LOGO}" width="600" height="261"/></mask></defs><rect width="600" height="261" fill="#4F0C28" mask="url(#m{logo.n})"/></svg>'
logo.n=0
def L():
    logo.n+=1; return logo()
IG_URL="https://www.instagram.com/elea.marketing/"
WEB_URL="https://eleamarketing.netlify.app/"
def ig(c="currentColor",sz="4.2mm"): return f'<svg viewBox="0 0 24 24" style="width:{sz};height:{sz};vertical-align:-0.8mm" fill="none" stroke="{c}" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1.1" fill="{c}" stroke="none"/></svg>'
def page_foot(n,tot): return f'<div class="foot">{L()}<span class="fl"><a href="{IG_URL}">{ig()} elea.marketing</a><a href="{WEB_URL}">Nuestra web →</a><span>{n}/{tot}</span></span></div>'
def build(d):
    T=3; nm=e(d["nombre"])
    tiles="".join(f'<div class="tile"><b>{e(a)}</b><span>{e(b)}</span></div>' for a,b in d["stats"])
    tl="".join(f'<div class="tli"><div class="dot {"bad" if k=="!" else ""}">{e(k)}</div><div><h3>{e(t)}</h3><p>{e(p)}</p></div></div>' for k,t,p in d["hoy"])
    p1=f'''<section class="page"><div class="hero"><div class="top">{L()}<span>Plan digital · {e(d["mes"])}</span></div>
<div class="eyebrow">Preparado para {e(d["para"])}</div><h1>{nm}</h1><div class="sector">{e(d["sector"])}</div></div>
<div class="lead">{e(d["headline"])}</div>
<div class="sec"><div class="eyebrow">Lo que ya tenéis</div><div class="tiles">{tiles}</div></div>
<div class="sec"><div class="eyebrow">Cómo está hoy</div><div class="legend"><i></i>En color, donde se escapan ventas.</div><div class="tl">{tl}</div></div>
{page_foot(1,T)}</section>'''
    a=d["anuncio"]; w=d["web_shot"]
    au="".join(f'<div class="ai"><div class="tag {c}">{e(lbl)}</div><div><h4>{e(t)}</h4><p>{e(p)}</p></div></div>' for c,lbl,t,p in d["auditoria"])
    p2=f'''<section class="page"><div class="top">{L()}<span>Plan para {nm}</span></div>
<h2>{e(d.get("h2_p2","Así se ven hoy vuestros anuncios y vuestra web"))}</h2><div class="subt">{e(d.get("sub_p2","Capturas reales, tomadas el "+d["fecha"]+"."))}</div>
<div class="two" style="margin-top:1mm"><div><div class="shot"><div class="bar"><span>{e(a.get("titulo") or "Biblioteca de anuncios de Meta")}</span><span>{e(d["fecha_corta"])}</span></div><img class="adimg" src="{b64(a["img"])}"></div><div class="cap">{e(a["caption"])}</div>{f'<div class="pill">{e(a["pill"])}</div>' if a.get("pill") else ""}</div>
<div class="phone"><div class="shot"><div class="bar"><span>{e(w["titulo"])}</span><span>{e(w.get("tag","móvil"))}</span></div><img src="{b64(w["img"])}" style="{"object-fit:contain;background:#F3F3F7" if w.get("fit")=="contain" else ("object-position:"+w["pos"] if w.get("pos") else "")}"></div><div class="cap">{e(w["caption"])}</div></div></div>
<h2 style="font-size:24pt;margin-top:8mm">{e(d.get("h2_audit","Vuestra web, revisada en el móvil"))}</h2><div class="subt">{e(d["audit_nota"])}</div><div class="audit">{au}</div>
{page_foot(2,T)}</section>'''
    fl="".join(f'<div class="fi"><div class="ic">{i+1}</div><div><h4>{e(t)}</h4><p>{e(p)}</p></div></div>' for i,(t,p) in enumerate(d["flujo"]))
    bx="".join(f'<div class="box"><div class="eyebrow">{e(t)}</div><ul>{"".join(f"<li>{e(x)}</li>" for x in items)}</ul></div>' for t,items in d["hariamos"])
    bl=d.get("briefing") or ["Qué vídeos grabar, producto a producto","Guiones con el gancho de los primeros 3 segundos","Lista de tomas: plano, luz y formato (Reels y Stories)","Ideas basadas en lo que ya funciona en vuestro sector"]
    brief=f'<div class="box brief"><div class="eyebrow">Briefing creativo · incluido</div><div class="bt">Os decimos qué grabar para anunciaros con calidad, sin depender de una productora.</div><ul>{"".join(f"<li>{e(x)}</li>" for x in bl)}</ul></div>'
    p3=f'''<section class="page"><div class="top">{L()}<span>Plan para {nm}</span></div>
<h2 style="font-size:22pt">{e(d.get("h2_flujo","Así funcionaría "+d["nombre"]+" vendiendo más online"))}</h2><div class="flow">{fl}</div>
<h2 style="font-size:22pt;margin-top:5mm">Lo que haríamos</h2><div class="subt">{e(d.get("sub_hariamos","Dos especialistas: Paid Media (Google y Meta) y Amazon. Solo lo que tiene sentido para "+d["nombre"]+"."))}</div>{bx}{brief}
<div class="sec" style="margin-top:4mm"><div class="eyebrow">Cómo lo hacemos</div><div class="steps">
<div class="st"><b>1</b><h4>{e(d.get("paso1","Nos contáis vuestro producto"))}</h4><p>Una llamada de 20 minutos o unos audios.</p></div>
<div class="st"><b>2</b><h4>Os damos el briefing creativo</h4><p>Qué vídeos grabar, con guiones y tomas.</p></div>
<div class="st"><b>3</b><h4>Lo montamos y arranca</h4><p>{e(d.get("paso3","Y cada mes os contamos qué vende y qué no."))}</p></div></div></div>
<div class="cta"><h2>¿Lo vemos?</h2><p>{e(d["cta"])}</p><div class="sig">Andrea · Elea Marketing</div><div class="links"><a href="{IG_URL}">{ig("#FAF3C6","5mm")} @elea.marketing</a><a href="{WEB_URL}">Nuestra web →</a></div></div>
<div class="src">{e(d["fuentes"])}</div>
{page_foot(3,T)}</section>'''
    return f'<!doctype html><html lang="es"><head><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap"><style>{CSS}</style></head><body>{p1}{p2}{p3}</body></html>'
async def main():
    data=json.load(open(sys.argv[1]))
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium",args=["--no-sandbox"])
        pg=await b.new_page()
        for d in data:
            h=build(d); (S/"planes"/(d["pdf"][:-4]+".html")).write_text(h)
            await pg.set_content(h,wait_until="networkidle"); await pg.evaluate("document.fonts.ready")
            await pg.pdf(path=str(S/"planes"/d["pdf"]),width="216mm",height="384mm",print_background=True,prefer_css_page_size=True)
            print("ok",d["pdf"],flush=True)
        await b.close()
asyncio.run(main())
