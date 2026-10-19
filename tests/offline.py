"""Test hors ligne : une seule ouverture avec réseau, puis coupure RÉELLE (le serveur est arrêté).
Attendu : l'accueil s'affiche et la séance du jour s'ouvre sans réseau (les séances d'après sont verrouillées depuis la v0.4.1 ;
le nombre de fichiers de séances en cache, compté plus bas, prouve que toutes sont gardées).
(La coupure simulée de Playwright ne s'applique pas au service worker : elle ne prouve rien.)

Lancer : python3 tests/offline.py      (démarre et arrête lui-même un serveur sur un port libre : le 8766 peut être pris par une autre application)
"""
import asyncio, subprocess, time, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
APP = pathlib.Path(__file__).resolve().parent.parent / "app"
PIN = "1234"
async def main():
    import socket
    with socket.socket() as so: so.bind(("127.0.0.1", 0)); PORT = so.getsockname()[1]   # port libre, choisi par le système
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", str(APP)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); ok = False
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await (await b.new_context(viewport={"width": 1280, "height": 800})).new_page()
            await pg.goto(f"http://localhost:{PORT}/#test"); await pg.wait_for_selector("#code")
            await pg.fill("#code", CODE); await pg.click("#go"); await pg.wait_for_selector("#pin")
            await pg.evaluate("navigator.serviceWorker.ready"); await pg.wait_for_timeout(1500)
            n = await pg.evaluate("caches.keys().then(ks => Promise.all(ks.map(k => caches.open(k).then(c => c.keys())))).then(a => a.flat().filter(r => r.url.includes('/lessons/')).length)")
            print("fichiers de séances en cache après une seule ouverture :", n)
            # réglage parent puis un profil GS, pendant que le réseau est encore là
            await pg.fill("#pin", PIN); await pg.click("#go"); await pg.wait_for_selector("#p-name")
            await pg.fill("#p-name", "Awa"); await pg.fill("#p-dob", "2021-02-10"); await pg.click("[data-p='gs']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            srv.terminate(); srv.wait(); time.sleep(0.5)
            await pg.reload(); await pg.wait_for_timeout(2000)
            home = "introuvables" not in await pg.inner_text("#app") and await pg.is_visible(".kid[data-c]")
            print("2e ouverture sans réseau :", "OK (accueil avec le profil)" if home else "LEÇONS INTROUVABLES")
            if home:
                last = await pg.evaluate("fetch('lessons/index.json').then(r => r.json()).then(i => i.lessons.filter(l => l.parcours === 'gs')[0].id)")   # la séance du jour : la première non faite
                await pg.click(".kid[data-c]"); await pg.wait_for_selector(".tickets"); await pg.click(f"[data-l='{last}']"); await pg.wait_for_selector(f".ticket.sel[data-l='{last}']"); await pg.click("#today .boat-btn"); await pg.wait_for_timeout(800)
                ok = await pg.evaluate("() => !!window.__kono.P()")
                print(f"séance {last} sans réseau :", "OK" if ok else "ÉCHEC")
            await b.close()
    finally:
        if srv.poll() is None: srv.terminate()
    sys.exit(0 if ok else 1)
if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
