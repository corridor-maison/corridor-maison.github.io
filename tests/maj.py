"""Mise à jour sans vider le cache : une tablette qui a une version ANCIENNE en cache hors ligne doit, à sa première ouverture
avec internet, afficher la nouvelle version en bas de l'accueil, puis la garder hors ligne ; l'ancien cache doit disparaître,
et les voix déjà gardées doivent être reprises sans être retéléchargées.

Déroulé : une copie de app/ est servie avec VERSION 0.0.1 et, comme service worker, celui publié sur main (celui qu'ont les
tablettes), cache renommé kono-0.0.1 : c'est l'« ancienne » version. Le navigateur l'ouvre, l'installe, la rouvre en ligne
(les voix se téléchargent), vérifie qu'elle marche sans réseau. Puis la vraie app/ remplace la copie sur le même serveur
(même adresse : c'est une publication). Le navigateur rouvre l'application, en ligne, sans rien vider : la vraie VERSION doit
s'afficher dès cette ouverture, le seul cache de version restant doit être le sien, les voix doivent rester sans nouveau
téléchargement (journal du serveur), et l'application doit encore marcher sans réseau.

Lancer : python3 tests/maj.py      (démarre et arrête lui-même un serveur sur le port 8773)
"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent; APP = ROOT / "app"
PIN = "1234"; fails = []
# voix gardées sur la tablette, tous caches confondus
AUDIO_N = "caches.keys().then(ks => Promise.all(ks.map(k => caches.open(k).then(c => c.keys())))).then(a => new Set(a.flat().map(r => r.url).filter(u => u.includes('/audio/gen/') || u.includes('/audio/rec/'))).size)"
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)

async def main():
    real = re.search(r"const VERSION = '([^']+)'", (APP / "app.js").read_text(encoding="utf-8")).group(1)
    nman = len(json.loads((APP / "audio" / "manifest.json").read_text(encoding="utf-8")).get("files", {}))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="corridor-maj-")); served = tmp / "app"
    shutil.copytree(APP, served)
    js = served / "app.js"; js.write_text(js.read_text(encoding="utf-8").replace(f"const VERSION = '{real}'", "const VERSION = '0.0.1'"), encoding="utf-8", newline="\n")
    old_sw = subprocess.run(["git", "-C", str(ROOT), "show", "origin/main:app/sw.js"], capture_output=True, text=True, encoding="utf-8").stdout or (APP / "sw.js").read_text(encoding="utf-8")
    (served / "sw.js").write_text(re.sub(r"const CACHE = 'kono-[^']+'", "const CACHE = 'kono-0.0.1'", old_sw), encoding="utf-8", newline="\n")
    journal = tmp / "serveur.log"; jl = open(journal, "w", encoding="utf-8")
    voix = lambda: sum(1 for ln in open(journal, encoding="utf-8", errors="replace") if "GET /audio/gen/" in ln or "GET /audio/rec/" in ln)
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8773", "--directory", str(served)], stdout=subprocess.DEVNULL, stderr=jl); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width": 1280, "height": 800}); pg = await ctx.new_page()
            await pg.goto("http://localhost:8773/#test"); await pg.wait_for_selector("#code")
            await pg.fill("#code", CODE); await pg.click("#go"); await pg.wait_for_selector("#pin"); await pg.fill("#pin", PIN); await pg.click("#go"); await pg.wait_for_selector("#p-name")
            await pg.fill("#p-name", "Awa"); await pg.fill("#p-dob", "2021-02-10"); await pg.click("[data-p='gs']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            await pg.evaluate("navigator.serviceWorker.ready"); await pg.wait_for_timeout(2500)
            v0 = (await pg.inner_text(".home-foot .small")).strip(); k0 = [k for k in await pg.evaluate("caches.keys()") if k != "kono-audio"]
            check("ancienne version installée : v0.0.1 affichée, cache kono-0.0.1", v0 == "v0.0.1" and k0 == ["kono-0.0.1"], f"{v0} {k0}")
            # 2e ouverture en ligne, contrôlée : l'ancien service worker télécharge les voix
            await pg.reload(); await pg.wait_for_selector(".kids", timeout=20000)
            na = 0
            for _ in range(240):
                na = await pg.evaluate(AUDIO_N)
                if na >= nman: break
                await pg.wait_for_timeout(500)
            check(f"ancienne version : les {nman} voix du manifeste sont gardées sur la tablette", na == nman, f"{na}/{nman}")
            # hors ligne avec l'ancienne version
            await ctx.set_offline(True); await pg.reload(); await pg.wait_for_selector(".kids", timeout=15000)
            check("ancienne version : marche sans réseau", (await pg.inner_text(".home-foot .small")).strip() == "v0.0.1")
            await ctx.set_offline(False)
            # publication : la vraie app/ remplace la copie, même adresse
            avant = voix(); now = time.time()
            for f in APP.rglob("*"):
                if f.is_file(): d = served / f.relative_to(APP); shutil.copy(f, d); os.utime(d, (now, now))   # fichiers nouveaux, datés d'aujourd'hui, comme après une publication
            # première ouverture en ligne après la publication, sans rien vider
            await pg.reload(); await pg.wait_for_selector(".kids", timeout=20000); await pg.wait_for_timeout(500)
            v1 = (await pg.inner_text(".home-foot .small")).strip()
            check(f"première ouverture en ligne après publication : v{real} affichée sans vider le cache", v1 == f"v{real}", v1)
            await pg.evaluate("navigator.serviceWorker.ready")
            ks = None
            for _ in range(30):
                ks = [k for k in await pg.evaluate("caches.keys()") if k != "kono-audio"]
                if ks == [f"kono-{real}"]: break
                await pg.wait_for_timeout(500)
            check(f"nouveau service worker actif : seul le cache kono-{real} reste, l'ancien est effacé (hors cache des voix)", ks == [f"kono-{real}"], str(ks))
            await pg.wait_for_timeout(4000)
            na2 = await pg.evaluate("caches.open('kono-audio').then(c => c.keys()).then(k => k.length)")
            check("mise à jour : les voix passent dans le cache des voix et ne sont pas retéléchargées", na2 == nman and voix() == avant, f"cache des voix {na2}/{nman}, voix téléchargées pendant la mise à jour : {voix() - avant}")
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
        jl.close(); shutil.rmtree(tmp, ignore_errors=True)
    print("MISE À JOUR :", "OK" if not fails else "ÉCHEC : " + ", ".join(fails))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
