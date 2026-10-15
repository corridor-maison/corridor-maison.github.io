"""Mise à jour sans vider le cache : une tablette qui a une version ANCIENNE en cache hors ligne doit, à sa première ouverture
avec internet, afficher la nouvelle version en bas de l'accueil, puis la garder hors ligne ; l'ancien cache doit disparaître.

Déroulé : une copie de app/ est servie avec VERSION 0.0.1 et CACHE kono-0.0.1 (l'« ancienne » version) ; le navigateur l'ouvre,
installe le service worker, vérifie qu'elle marche sans réseau. Puis la vraie app/ remplace la copie sur le même serveur
(même adresse : c'est une publication). Le navigateur rouvre l'application, en ligne, sans rien vider : la vraie VERSION doit
s'afficher dès cette ouverture, le seul cache restant doit être le sien, et l'application doit encore marcher sans réseau.

Lancer : python3 tests/maj.py      (démarre et arrête lui-même un serveur sur le port 8773)
"""
import asyncio, os, pathlib, re, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent; APP = ROOT / "app"
PIN = "1234"; fails = []
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)

async def main():
    real = re.search(r"const VERSION = '([^']+)'", (APP / "app.js").read_text(encoding="utf-8")).group(1)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="corridor-maj-")); served = tmp / "app"
    shutil.copytree(APP, served)
    js = served / "app.js"; js.write_text(js.read_text(encoding="utf-8").replace(f"const VERSION = '{real}'", "const VERSION = '0.0.1'"), encoding="utf-8", newline="\n")
    sw = served / "sw.js"; sw.write_text(sw.read_text(encoding="utf-8").replace(f"kono-{real}", "kono-0.0.1"), encoding="utf-8", newline="\n")
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8773", "--directory", str(served)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 1280, "height": 800}); pg = await ctx.new_page()
            await pg.goto("http://localhost:8773/#test"); await pg.wait_for_selector("#code")
            await pg.fill("#code", CODE); await pg.click("#go"); await pg.wait_for_selector("#pin"); await pg.fill("#pin", PIN); await pg.click("#go"); await pg.wait_for_selector("#p-name")
            await pg.fill("#p-name", "Awa"); await pg.fill("#p-dob", "2021-02-10"); await pg.click("[data-p='gs']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            await pg.evaluate("navigator.serviceWorker.ready"); await pg.wait_for_timeout(2500)
            v0 = (await pg.inner_text(".home-foot .small")).strip(); k0 = await pg.evaluate("caches.keys()")
            check("ancienne version installée : v0.0.1 affichée, cache kono-0.0.1", v0 == "v0.0.1" and k0 == ["kono-0.0.1"], f"{v0} {k0}")
            # hors ligne avec l'ancienne version
            await ctx.set_offline(True); await pg.reload(); await pg.wait_for_selector(".kids", timeout=15000)
            check("ancienne version : marche sans réseau", (await pg.inner_text(".home-foot .small")).strip() == "v0.0.1")
            await ctx.set_offline(False)
            # publication : la vraie app/ remplace la copie, même adresse
            now = time.time()
            for f in APP.rglob("*"):
                if f.is_file(): d = served / f.relative_to(APP); shutil.copy(f, d); os.utime(d, (now, now))   # fichiers nouveaux, datés d'aujourd'hui, comme après une publication
            # première ouverture en ligne après la publication, sans rien vider
            await pg.reload(); await pg.wait_for_selector(".kids", timeout=20000); await pg.wait_for_timeout(500)
            v1 = (await pg.inner_text(".home-foot .small")).strip()
            check(f"première ouverture en ligne après publication : v{real} affichée sans vider le cache", v1 == f"v{real}", v1)
            await pg.evaluate("navigator.serviceWorker.ready")
            ks = None
            for _ in range(30):
                ks = await pg.evaluate("caches.keys()")
                if ks == [f"kono-{real}"]: break
                await pg.wait_for_timeout(500)
            check(f"nouveau service worker actif : seul le cache kono-{real} reste, l'ancien est effacé", ks == [f"kono-{real}"], str(ks))
            # hors ligne avec la nouvelle version, après fermeture et réouverture
            srv.terminate(); srv.wait(); await ctx.set_offline(True); await pg.wait_for_timeout(300)
            await pg.reload(); await pg.wait_for_selector(".kids", timeout=20000)
            v2 = (await pg.inner_text(".home-foot .small")).strip()
            check(f"nouvelle version sans réseau : v{real} affichée", v2 == f"v{real}", v2)
            await pg.click(".kid[data-c]"); await pg.wait_for_selector(".tickets"); await pg.click("#today .boat-btn"); await pg.wait_for_timeout(800)
            check("nouvelle version sans réseau : une séance s'ouvre", await pg.evaluate("() => !!window.__kono.P()"))
            await b.close()
    finally:
        if srv.poll() is None: srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    print("MISE À JOUR :", "OK" if not fails else "ÉCHEC : " + ", ".join(fails))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
