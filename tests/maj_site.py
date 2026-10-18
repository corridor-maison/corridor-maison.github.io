"""Mise à jour sur le SITE PUBLIÉ, sans vider le cache (à lancer autour d'une publication) : passe 1 (maintenant) ouvre l'application dans un profil de navigateur
persistant et note la version servie et en cache ; passe 2 (après la publication suivante) rouvre le même profil, en ligne,
et attend la nouvelle version en bas de l'accueil, puis vérifie qu'elle tient hors ligne.
Usage : python3 tests/maj_site.py 1 <dossier-profil> <csv-codes>   avant la publication (ouvre et met en cache la version en ligne)
        python3 tests/maj_site.py 2 <dossier-profil> <version-attendue>   après la publication (même profil, rien n'est vidé)
Le fichier des codes est celui de l'école (print/codes-<date>.csv, non commité) ; le profil est un dossier quelconque."""
import asyncio, csv, json, pathlib, sys, time
from playwright.async_api import async_playwright
SITE = "https://corridor-maison.github.io/"
mode, prof = sys.argv[1], sys.argv[2]
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(prof, viewport={"width": 1280, "height": 800})
        pg = await ctx.new_page()
        if mode == "1":
            rows = list(csv.reader(open(sys.argv[3], encoding="utf-8"), delimiter=";")); code = [r for r in rows[1:] if r[1] == "CE1"][-2][2]
            await pg.goto(SITE + "#test"); await pg.wait_for_selector("#code, #pin, .kids")
            if await pg.is_visible("#code"): await pg.fill("#code", code); await pg.click("#go"); await pg.wait_for_selector("#pin")
            if await pg.is_visible("#pin"):
                await pg.fill("#pin", "1234"); await pg.click("#go"); await pg.wait_for_selector("#p-name")
                await pg.fill("#p-name", "Awa"); await pg.fill("#p-dob", "2021-02-10"); await pg.click("[data-p='gs']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            await pg.evaluate("navigator.serviceWorker.ready"); await pg.wait_for_timeout(4000)
            v = await pg.inner_text(".home-foot .small"); ks = await pg.evaluate("caches.keys()")
            print(f"passe 1 : accueil « {v} » · caches {ks}")
        else:
            want = sys.argv[3]
            await pg.goto(SITE + "#test"); await pg.wait_for_selector(".kids"); await pg.wait_for_timeout(1500)
            v1 = await pg.inner_text(".home-foot .small")
            # une seule ouverture en ligne doit suffire : la version attendue est affichée sans rien vider
            ok_v = v1.strip() == "v" + want
            print(f"passe 2 (en ligne, profil déjà en cache) : accueil « {v1} » → {'OK' if ok_v else 'ÉCHEC'} (attendu v{want})")
            await pg.evaluate("navigator.serviceWorker.ready"); await pg.wait_for_timeout(8000)
            ks = [k for k in await pg.evaluate("caches.keys()") if k != "kono-audio"]; ok_c = ks == ["kono-" + want]
            print(f"passe 2 : caches après activation {ks} → {'OK' if ok_c else 'ÉCHEC'} (attendu ['kono-{want}'] seul)")
            await ctx.set_offline(True)
            tm = await ctx.new_page()   # le témoin dans un autre onglet : la page d'erreur de Chrome ferait échouer la navigation suivante du même onglet
            try: await tm.goto("https://example.com/", timeout=8000); print("témoin : joignable (coupure NON effective)")
            except Exception: print("témoin example.com : injoignable → coupure effective")
            await tm.close()
            await pg.goto(SITE + "#test", timeout=30000); await pg.wait_for_selector(".kids", timeout=20000); await pg.wait_for_timeout(1000)
            v2 = await pg.inner_text(".home-foot .small"); ok_o = v2.strip() == "v" + want
            await pg.click(".kid[data-c]"); await pg.wait_for_selector(".tickets")
            map_ok = await pg.evaluate("() => !!document.querySelector('.map .bani path') && /Djenn/.test(document.querySelector('.map').innerText) && /Bani/.test(document.querySelector('.map').innerText)")
            print(f"passe 3 (hors ligne) : accueil « {v2} » → {'OK' if ok_o else 'ÉCHEC'} · carte avec le Bani et Djenné : {'OK' if map_ok else 'ÉCHEC'}")
            await ctx.close(); sys.exit(0 if ok_v and ok_c and ok_o and map_ok else 1)
        await ctx.close()
asyncio.run(main())
