import os
from pathlib import Path
import json,re,sys,unicodedata
S=os.environ.get("ELEA_WA", str(Path(__file__).resolve().parent.parent / "state" / "whatsapp"))
sys.path.insert(0,str(Path(__file__).resolve().parent/'lotes'))
from batch1 import B; from batch2 import B2; from batch3 import B3
A=json.load(open(f"{S}/audit_home.json"))
ALL=B+B2+B3
def slug(s): return re.sub(r'[^A-Za-z0-9]+','_',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode()).strip('_')
plans=[];leads=[]
for i,b in enumerate(ALL):
    sp=A[b["dom"]]["speed"][0]; lcp=sp.get("lcp_ms") or 0; s=f'{lcp/1000:.1f}'.replace('.',','); kb=sp.get("kb",0); req=sp.get("requests",0)
    mb=f'{kb/1024:.1f}'.replace('.',',')
    if lcp>=4000: hoy=["!","Web lenta en el móvil",f"En nuestra prueba, la imagen principal de la portada tardó {s} s en aparecer."]; au=["bad","Mejorar","Carga lenta en el móvil",f"La imagen principal de la portada tardó {s} s en aparecer; Google recomienda menos de 2,5 s. La portada pesa {mb} MB y hace {req} peticiones."]
    elif lcp>=2500: hoy=["!","Carga algo lenta en el móvil",f"En nuestra prueba, la portada tardó {s} s en mostrarse."]; au=["mid","Revisar","Carga algo lenta en el móvil",f"La imagen principal de la portada tardó {s} s en aparecer; Google recomienda menos de 2,5 s."]
    else: hoy=["3","Web rápida en el móvil",f"La portada se mostró en {s} s en nuestra prueba: buena base para anunciarse."]; au=["ok","Bien","Carga rápida en el móvil",f"La imagen principal apareció en {s} s (Google recomienda menos de 2,5 s)."]
    h=[x if x[1]!="SPEEDHOY" else hoy for x in b["hoy"]]
    pdf=f'Plan_digital_{slug(b["nombre"])}.pdf'
    plans.append(dict(id=b["id"],pdf=pdf,nombre=b["nombre"],para=b["para"],sector=b["sector"],mes="noviembre de 2026",fecha="18 de noviembre de 2026",fecha_corta="18/11/2026",
        headline=b["headline"],stats=b["stats"],hoy=h,
        anuncio={"img":f'shots/{b["id"]}_ad.png',"titulo":"","caption":b["anuncio_cap"],"pill":b["pill"]},
        web_shot={"img":f'shots/b2_{b["dom"]}_home.png',"titulo":f'{b["dom"].replace("tienda.","")} · portada',"caption":b["web_cap"]},
        audit_nota="Revisada el 18/11/2026 con un móvil y una conexión 4G simulada.",auditoria=[au]+b["audit"],
        flujo=b["flujo"],hariamos=b["hariamos"],cta=b["cta"],
        fuentes="Datos públicos consultados el 18/11/2026: Biblioteca de anuncios de Meta y vuestra web (prueba en móvil con 4G simulado). Si algo no está al día, decídnoslo y lo corregimos."))
    tu=b["tu"]
    T=lambda a,c: a if tu else c
    msg=(f'{b["msg_hola"]}, soy Andrea, de Elea Marketing. {b["feli"]} Estoy haciendo miniauditorías a {b["sector_msg"]} y {b["marca_msg"]} estaba en la lista.\n\n'
         f'{T("Te","Os")} he preparado un plan de cómo funcionaría y lo que os beneficiaría {b["msg_B"]}. {b["msg_A"]}. {T("Te","Os")} lo adjunto en PDF.\n\n'
         f'Por si {T("quieres","queréis")} ver más de lo que hacemos:\nWeb: eleamarketing.netlify.app\nInstagram: instagram.com/elea.marketing\n\n'
         f'¿Le {T("echas","echáis")} un ojo y me {T("dices","decís")} qué {T("te","os")} parece {b["paso"]}?\n\n'
         f'{T("Si no te encaja, dímelo y no te escribo más.","Si no os encaja, decídmelo y no os escribo más.")}')
    seg=(f'Hola de nuevo, soy Andrea, de Elea Marketing. ¿{T("Pudiste","Pudisteis")} ver el plan que {T("te","os")} mandé? Si {T("te","os")} viene mejor, {T("te","os")} lo cuento en una llamada de 15 minutos esta semana. '
         f'{T("Si no te encaja, dímelo y no te escribo más.","Si no os encaja, decídmelo y no os escribo más.")}')
    fijo=b["tel"].replace(" ","")[0] in "89"
    leads.append(dict(id=b["id"],orden=10+i,nombre=b["nombre"],cluster=b["nicho"],municipio=b["ciudad"],servicio="Meta + Google" + (" + Amazon" if any(t=="Amazon" for t,_ in b["hariamos"]) else ""),
        responsable=b["persona"],telefono=b["tel"],telTipo=b["teltipo"],web=b["dom"],email=b["email"],pdf=pdf,estado="pendiente",
        porQue=f'{b["anuncio_cap"]} Velocidad portada: {s} s, {mb} MB, {req} peticiones.' + (" Tiene borrador de email en Gmail: envía por un solo canal." if b["id"] in ("nunubcn","banbu","naturabarf","candypet","aluminalia","tunocanarias","bakeryzerozero","breccia","ritarow","rovinfood","requetebien","santoamaro","delviento") else ""),
        mensajeInicial=msg,mensajeSeguimiento=seg))
json.dump(plans,open(f"{S}/plans.json","w"),ensure_ascii=False,indent=1)
json.dump(leads,open(f"{S}/leads.json","w"),ensure_ascii=False,indent=1)
for l in leads:
    wc=len(re.findall(r"\b[\wÀ-ÿ'’%-]+\b",l["mensajeInicial"].split("Por si")[0]))
    print(l["id"],l["telefono"],l["pdf"],wc)
