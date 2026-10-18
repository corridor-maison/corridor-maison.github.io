"""Sauvegarde Google Drive, avec Google simulé (aucun compte réel) : la connexion OAuth et l'API Drive sont remplacées par des routes Playwright.

Vérifie : bouton absent tant qu'aucun identifiant client n'est configuré ; « Sauvegarder sur Google Drive » envoie le parent chez Google
avec la bonne demande (client, portée drive.appdata, adresse de retour, state) ; au retour, l'adresse est nettoyée, le code parent est demandé,
puis la sauvegarde part dans appDataFolder avec le jeton ; une 2e sauvegarde met à jour le même fichier ; « Restaurer » remet le suivi ;
un retour de Google avec un state inconnu est ignoré (pas de jeton gardé) ; aucune erreur JavaScript.

Lancer : python3 tests/drive.py      (démarre et arrête lui-même un serveur sur le port 8774)
"""
import asyncio, json, pathlib, subprocess, sys, time, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
APP = pathlib.Path(__file__).resolve().parent.parent / "app"
BASE = "http://localhost:8774/"; PIN = "1234"; TOKEN = "jeton-de-test"
fails = []
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)

DRIVE = {"files": {}, "auth": [], "calls": [], "bad_auth": 0}
CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Authorization, Content-Type", "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS"}

async def google(route):
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(route.request.url).query)); DRIVE["auth"].append(q)
    back = q.get("redirect_uri", BASE) + "#test&access_token=" + TOKEN + "&token_type=Bearer&expires_in=3599&state=" + q.get("state", "")
    await route.fulfill(status=200, content_type="text/html", body=f"<!doctype html><title>Google (simulé)</title><script>location.replace({json.dumps(back)})</script>")

async def drive(route):
    r = route.request; u = urllib.parse.urlparse(r.url)
    if r.method == "OPTIONS": return await route.fulfill(status=204, headers=CORS)
    if r.headers.get("authorization") != "Bearer " + TOKEN:
        DRIVE["bad_auth"] += 1; return await route.fulfill(status=401, headers=CORS, body="{}")
    DRIVE["calls"].append(f"{r.method} {u.path}")
    if r.method == "GET" and u.path == "/drive/v3/files":
        q = dict(urllib.parse.parse_qsl(u.query)); ok = q.get("spaces") == "appDataFolder"
        files = [{"id": i, "name": f["name"], "modifiedTime": "2026-10-18T10:00:00Z"} for i, f in DRIVE["files"].items() if ok and f["name"] in q.get("q", "")]
        return await route.fulfill(status=200, headers=CORS, content_type="application/json", body=json.dumps({"files": files}))
    if r.method == "POST" and u.path == "/upload/drive/v3/files":
        body = r.post_data_buffer.decode("utf-8", "replace")
        i0 = body.index('{"name"'); meta = json.JSONDecoder().raw_decode(body[i0:])[0]
        i1 = body.index('{\n "app"') if '{\n "app"' in body else body.index('{"app"'); data = json.JSONDecoder().raw_decode(body[i1:])[0]
        DRIVE["files"]["f1"] = {"name": meta["name"], "parents": meta.get("parents"), "data": data}
        return await route.fulfill(status=200, headers=CORS, content_type="application/json", body='{"id":"f1"}')
    if r.method == "PATCH" and u.path.startswith("/upload/drive/v3/files/"):
        fid = u.path.rsplit("/", 1)[1]; DRIVE["files"][fid]["data"] = json.loads(r.post_data_buffer.decode("utf-8"))
        return await route.fulfill(status=200, headers=CORS, content_type="application/json", body='{"id":"%s"}' % fid)
    if r.method == "GET" and u.path.startswith("/drive/v3/files/") and "alt=media" in u.query:
        fid = u.path.rsplit("/", 1)[1]
        return await route.fulfill(status=200, headers=CORS, content_type="application/json", body=json.dumps(DRIVE["files"][fid]["data"]))
    await route.fulfill(status=404, headers=CORS, body="{}")

async def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8774", "--directory", str(APP)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    errs = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            # identifiant client vidé (comme avant la configuration) : la carte annonce la fonction, aucun bouton
            ctx = await b.new_context(viewport={"width": 1280, "height": 800}); await ctx.add_init_script("window.KONO_GDRIVE_CLIENT = ' ';")
            pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
            async def enrol():
                await pg.goto(BASE + "#test"); await pg.wait_for_selector("#code"); await pg.fill("#code", CODE); await pg.click("#go")
                await pg.wait_for_selector("#pin"); await pg.fill("#pin", PIN); await pg.click("#go"); await pg.wait_for_selector("#p-name")
                await pg.fill("#p-name", "Awa"); await pg.fill("#p-dob", "2021-02-10"); await pg.click("[data-p='gs']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            async def pin():
                await pg.wait_for_selector(".pin")
                for ch in PIN: await pg.click(f"[data-k='{ch}']")
            async def reglages():
                await pg.click("#parent"); await pin(); await pg.wait_for_selector("#pane"); await pg.click("[data-t='reglages']"); await pg.wait_for_selector("#maj")
            await enrol(); await reglages()
            txt = await pg.inner_text("#pane")
            check("sans identifiant client : « Bientôt » et aucun bouton Google Drive", "Bientôt : sauvegarde du suivi sur le Google Drive" in txt and not await pg.query_selector("#gd-save"))
            await ctx.close()
            # avec identifiant client et Google simulé
            ctx = await b.new_context(viewport={"width": 1280, "height": 800}); await ctx.add_init_script("window.KONO_GDRIVE_CLIENT = 'client-de-test.apps.googleusercontent.com';")
            await ctx.route("https://accounts.google.com/**", google); await ctx.route("https://www.googleapis.com/**", drive)
            pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
            await enrol(); await reglages()
            await pg.click("#gd-save"); await pg.wait_for_selector(".pin", timeout=20000)
            a = DRIVE["auth"][-1] if DRIVE["auth"] else {}
            check("Sauvegarder → chez Google avec le bon client, la portée drive.appdata, l'adresse de retour et un state", a.get("client_id") == "client-de-test.apps.googleusercontent.com" and a.get("scope") == "https://www.googleapis.com/auth/drive.appdata" and a.get("response_type") == "token" and a.get("redirect_uri") == BASE and len(a.get("state", "")) == 24, str({k: a.get(k) for k in ("client_id", "scope", "redirect_uri", "response_type")}))
            h = await pg.evaluate("() => ({ hash: location.hash, jeton: !!sessionStorage.getItem('kono-drive'), stocke: JSON.stringify(window.__kono.S).includes('" + TOKEN + "') })")
            check("retour de Google : adresse nettoyée, jeton gardé pour l'onglet seulement (pas dans le suivi), code parent demandé", h["hash"] == "#test" and h["jeton"] and not h["stocke"], str(h))
            await pin(); await pg.wait_for_function("() => /Sauvegardé sur Google Drive|échoué/.test((document.querySelector('#gd-msg') || {}).textContent || '')", timeout=20000)
            msg = await pg.inner_text("#gd-msg"); f = DRIVE["files"].get("f1", {})
            check("après le code parent, la sauvegarde part dans appDataFolder avec le jeton", "Sauvegardé sur Google Drive" in msg and f.get("name") == "corridor-sauvegarde.json" and f.get("parents") == ["appDataFolder"] and any(pp.get("name") == "Awa" for pp in f.get("data", {}).get("store", {}).get("profiles", [])), msg)
            await pg.click("#gd-save"); await pg.wait_for_function("() => /Sauvegardé sur Google Drive/.test(document.querySelector('#gd-msg').textContent)", timeout=20000)
            check("2e sauvegarde : le même fichier est mis à jour (PATCH), sans nouvelle connexion", any(c.startswith("PATCH /upload/drive/v3/files/f1") for c in DRIVE["calls"]) and len(DRIVE["auth"]) == 1, str(DRIVE["calls"][-3:]))
            await pg.evaluate("() => { window.__kono.S.profiles[0].name = 'Zed'; }")
            await pg.click("#gd-load"); await pg.wait_for_function("() => /restaurée depuis Google Drive|échoué|Aucune/.test(document.querySelector('#gd-msg').textContent)", timeout=20000)
            nm = await pg.evaluate("() => window.__kono.S.profiles.map(p => p.name)"); msg = await pg.inner_text("#gd-msg")
            check("Restaurer depuis Google Drive : le suivi sauvegardé revient (prénom Awa)", nm == ["Awa"] and "restaurée depuis Google Drive" in msg, f"{nm} · {msg}")
            # retour de Google avec un state inconnu : ignoré
            await pg.evaluate("() => sessionStorage.clear()")
            await pg.goto(BASE + "?retour=1#test&access_token=pirate&expires_in=3599&state=inconnu")   # ?retour : vraie navigation (un simple changement de # ne recharge pas); await pg.wait_for_selector(".kids")
            r = await pg.evaluate("() => ({ jeton: sessionStorage.getItem('kono-drive'), pin: !!document.querySelector('.pin'), hash: location.hash })")
            check("retour de Google avec un state inconnu : ignoré (pas de jeton, pas d'action), adresse nettoyée", r["jeton"] is None and not r["pin"] and r["hash"] == "#test", str(r))
            check("aucune requête à Drive sans le bon jeton", DRIVE["bad_auth"] == 0, str(DRIVE["bad_auth"]))
            await b.close()
        check("aucune erreur JavaScript", not errs, "\n".join(errs)[:300])
    finally:
        if srv.poll() is None: srv.terminate()
    print("GOOGLE DRIVE :", "OK" if not fails else "ÉCHEC : " + " ; ".join(fails))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
