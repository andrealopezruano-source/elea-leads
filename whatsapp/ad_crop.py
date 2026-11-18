import asyncio, sys, json
import os
from pathlib import Path
sys.path.insert(0,"/home/user/elea-leads")
from leads.discovery_meta import AdLibrary
S=os.environ.get("ELEA_WA", str(Path(__file__).resolve().parent.parent / "state" / "whatsapp"))
JOBS=json.loads(sys.argv[1])
async def main():
    async with AdLibrary("ES",delay=(1,2)) as lib:
        p=lib._page
        await p.set_viewport_size({"width":1366,"height":1400})
        for name,aid in JOBS:
            await p.goto(f"https://www.facebook.com/ads/library/?id={aid}",wait_until="domcontentloaded",timeout=60000); await p.wait_for_timeout(8000)
            dlg=p.locator('[role="dialog"]').last
            try:
                await dlg.screenshot(path=f"{S}/shots/{name}_ad.png"); print(name,"ok",await dlg.bounding_box(),flush=True)
            except Exception as e: print(name,"FAIL",e,flush=True)
asyncio.run(main())
