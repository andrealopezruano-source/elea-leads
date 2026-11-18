import os
from pathlib import Path
import asyncio, sys, json
sys.path.insert(0,"/home/user/elea-leads")
from leads.discovery_meta import AdLibrary, RateLimited
S=os.environ.get("ELEA_WA", str(Path(__file__).resolve().parent.parent / "state" / "whatsapp"))
pages=json.load(open(f"{S}/b2/pages.json")); out_f=f"{S}/b2/page_scan.json"
try: out=json.load(open(out_f))
except Exception: out={}
async def main():
    async with AdLibrary("ES",delay=(4,8)) as lib:
        for dom,pid in pages:
            if dom in out: continue
            try:
                total,ads=await lib.page_ads(pid); out[dom]={"page_id":pid,"total":total,"ads":ads}
                print(dom,total,len(ads),flush=True)
            except RateLimited:
                print(dom,"RATE LIMIT",flush=True); await asyncio.sleep(300)
            except Exception as e: print(dom,"ERR",e,flush=True)
            json.dump(out,open(out_f,"w"),ensure_ascii=False)
asyncio.run(main())
