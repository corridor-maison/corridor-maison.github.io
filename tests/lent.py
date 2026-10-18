"""Réseau lent et première ouverture.

1. Première ouverture (page pas encore contrôlée) : les voix du manifeste se téléchargent quand même, en arrière-plan,
   dans le cache des voix (message « voix » de la page au service worker).
2. Réseau lent : le serveur répond en 12 s pour le moteur et les styles ; l'application installée doit démarrer en moins de 9 s
   avec sa copie gardée (délai maximal du service worker), au lieu de rester sur l'écran d'attente.

Lancer : python3 tests/lent.py      (démarre et arrête lui-même un serveur sur le port 8775)
"""
import asyncio, functools, http.server, json, pathlib, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
APP = pathlib.Path(__file__).resolve().parent.parent / "app"; PIN = "1234"; LENT = {"on": False}; fails = []
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if LENT["on"] and self.path.split("?")[0].endswith(("app.js", "styles.css")): time.sleep(12)
        return super().do_GET()
async def main():
    srv = http.server.ThreadingHTTPServer(("localhost", 8775), functools.partial(H, directory=str(APP))); threading.Thread(target=srv.serve_forever, daemon=True).start()
    nman = len(json.loads((APP / "audio" / "manifest.json").read_text(encoding="utf-8")).get("files", {}))
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 1280, "height": 800}); pg = await ctx.new_page()
            await pg.goto("http://localhost:8775/#test"); await pg.wait_for_selector("#code"); await pg.fill("#code", CODE); await pg.click("#go")
            await pg.wait_for_selector("#pin"); await pg.fill("#pin", PIN); await pg.click("#go"); await pg.wait_for_selector("#p-name")
            await pg.fill("#p-name", "Awa"); await pg.fill("#p-dob", "2021-02-10"); await pg.click("[data-p='gs']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            n = 0
            for _ in range(240):
                n = await pg.evaluate("caches.open('kono-audio').then(c => c.keys()).then(k => k.length)")
                if n >= nman: break
                await pg.wait_for_timeout(500)
            check(f"première ouverture : les {nman} voix se téléchargent en arrière-plan dans le cache des voix", n == nman, f"{n}/{nman}")
            LENT["on"] = True; t = time.time()
            await pg.reload(); await pg.wait_for_selector(".kids", timeout=30000); dt = time.time() - t
            check("réseau lent (moteur et styles en 12 s) : l'application démarre en moins de 9 s avec sa copie gardée", dt < 9, f"{dt:.1f} s")
            await b.close()
    finally:
        srv.shutdown()
    print("RÉSEAU LENT :", "OK" if not fails else "ÉCHEC : " + " ; ".join(fails)); sys.exit(1 if fails else 0)
if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
