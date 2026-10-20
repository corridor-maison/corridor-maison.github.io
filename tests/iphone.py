"""iPhone (WebKit, iPhone 13) : l'inscription doit marcher même quand le stockage du téléphone (IndexedDB) ne répond jamais,
comme dans le navigateur intégré de Gmail sur certains iPhone.

1. Stockage normal : le champ du code apparaît, se remplit, et le code mène au code parent.
2. Stockage muet (indexedDB.open ne répond jamais) : ouverture simple → champ du code en moins de 8 s, utilisable ;
   lien d'inscription (#code=…) → écran du code parent en moins de 8 s.

Lancer : python3 tests/iphone.py      (démarre et arrête lui-même un serveur sur le port 8776)
"""
import asyncio, os, functools, http.server, pathlib, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
APP = pathlib.Path(os.environ.get("KONO_APP") or pathlib.Path(__file__).resolve().parent.parent / "app"); BASE = "http://localhost:8776/"; fails = []
MUET = "Object.defineProperty(IDBFactory.prototype, 'open', { value: function () { return {}; }, configurable: true, writable: true });"   # une demande qui ne répond jamais (v0.4.6 : reste sur le logo)
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

async def main():
    srv = http.server.ThreadingHTTPServer(("localhost", 8776), functools.partial(H, directory=str(APP))); threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        async with async_playwright() as p:
            b = await p.webkit.launch(); dev = p.devices["iPhone 13"]
            async def page(muet):
                ctx = await b.new_context(**dev, service_workers="block")
                if muet: await ctx.add_init_script(MUET)
                pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); return ctx, pg, errs
            # 1. stockage normal
            ctx, pg, errs = await page(False)
            await pg.goto(BASE + "#test"); await pg.wait_for_selector("#code", timeout=15000)
            await pg.tap("#code"); await pg.keyboard.type(CODE); await pg.tap("#go")
            ok = await pg.wait_for_selector("#pin", timeout=10000) is not None
            check("iPhone, stockage normal : le code se tape et mène au code parent", ok and not errs, "; ".join(errs)[:200]); await ctx.close()
            # 2a. stockage muet, ouverture simple
            ctx, pg, errs = await page(True); t = time.time()
            await pg.goto(BASE + "#test"); await pg.wait_for_selector("#code", timeout=15000); dt = time.time() - t
            await pg.tap("#code"); await pg.keyboard.type(CODE); val = await pg.input_value("#code")
            check("iPhone, stockage muet : champ du code en moins de 8 s et utilisable", dt < 8 and val.replace("-", "").upper() == CODE.replace("-", "").upper(), f"{dt:.1f} s")
            await pg.tap("#go"); ok = await pg.wait_for_selector("#pin", timeout=10000) is not None
            check("iPhone, stockage muet : le code mène au code parent", ok and not errs, "; ".join(errs)[:200]); await ctx.close()
            # 2b. stockage muet, lien d'inscription
            ctx, pg, errs = await page(True); t = time.time()
            await pg.goto(BASE + "#test&code=" + CODE); await pg.wait_for_selector("#pin", timeout=15000); dt = time.time() - t
            check("iPhone, stockage muet, lien d'inscription : code parent en moins de 8 s", dt < 8 and not errs, f"{dt:.1f} s " + "; ".join(errs)[:200]); await ctx.close()
            await b.close()
    finally:
        srv.shutdown()
    print("IPHONE :", "OK" if not fails else "ÉCHEC : " + " ; ".join(fails)); sys.exit(1 if fails else 0)

if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
