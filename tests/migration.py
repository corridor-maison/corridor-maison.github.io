"""Test de migration : un état de la v0.2 (cases bleu et orange, avec séances faites, records, file de révision, mesures,
un enregistrement et une phrase de Maman dans IndexedDB) devient deux profils, sans aucune perte.
Écrit la comparaison avant/après dans $SHOTS/migration-avant-apres.json et l'imprime.

Lancer : python3 tests/migration.py      (démarre et arrête lui-même un serveur sur le port 8767)
"""
import asyncio, subprocess, time, sys, os, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
SHOTS = os.environ.get("SHOTS", "/tmp/corridor-tests/"); os.makedirs(SHOTS, exist_ok=True)
STATE = json.loads((ROOT / "tests" / "etat-v0.2.json").read_text(encoding="utf-8"))
SEED_DB = """async () => {
  const d = await new Promise((res, rej) => { const r = indexedDB.open('kono', 1);
    r.onupgradeneeded = () => { const d = r.result; d.createObjectStore('clips'); d.createObjectStore('recs', { keyPath: 'id', autoIncrement: true }); };
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const run = (store, fn) => new Promise((res, rej) => { const t = d.transaction(store, 'readwrite'); fn(t.objectStore(store)); t.oncomplete = res; t.onerror = () => rej(t.error); });
  await run('recs', s => { s.clear(); s.add({ child: 'bleu', lesson: 'bleu-s0-dizaine', title: 'Passer par la dizaine', kind: 'methode', q: 'Explique comment tu as fait.', ts: 1760000000000, dur: 7, mime: 'audio/webm', blob: new Blob(['audio-ali'], { type: 'audio/webm' }) });
                            s.add({ child: 'orange', lesson: 'orange-s0-amis10', title: 'Les amis de 10', kind: 'recit', q: 'Raconte l\\'histoire.', ts: 1760000100000, dur: 9, mime: 'audio/webm', blob: new Blob(['audio-awa'], { type: 'audio/webm' }) }); });
  await run('clips', s => { s.clear(); s.put(new Blob(['maman-bleu'], { type: 'audio/webm' }), 'bonjour_bleu'); s.put(new Blob(['maman-orange'], { type: 'audio/webm' }), 'fin_orange'); s.put(new Blob(['maman-fiche'], { type: 'audio/webm' }), 'fiche'); });
  return true; }"""
READ_DB = """async () => {
  const d = await new Promise((res, rej) => { const r = indexedDB.open('kono', 1); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const all = (store, fn) => new Promise((res, rej) => { const t = d.transaction(store, 'readonly'); const q = fn(t.objectStore(store)); t.oncomplete = () => res(q.result); t.onerror = () => rej(t.error); });
  const recs = await all('recs', s => s.getAll()); const keys = await all('clips', s => s.getAllKeys());
  return { recs: recs.map(r => ({ id: r.id, child: r.child, profile: r.profile, lesson: r.lesson, kind: r.kind, dur: r.dur, size: r.blob.size })), clips: keys.map(String).sort() }; }"""

def check(cond, msg, out): out.append(("OK " if cond else "ÉCHEC") + " " + msg); return cond

async def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "--directory", str(APP)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); ok = True; lines = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await (await b.new_context(viewport={"width": 1280, "height": 800})).new_page()
            await pg.goto("http://localhost:8767/#test"); await pg.wait_for_selector("#go")
            # avant : l'état v0.2 et la base IndexedDB de la v0.2
            await pg.evaluate("s => localStorage.setItem('kono-v1', JSON.stringify(s))", STATE)
            await pg.evaluate(SEED_DB)
            before_db = await pg.evaluate(READ_DB)
            await pg.reload(); await pg.wait_for_selector(".kids"); await pg.wait_for_timeout(500)
            await pg.screenshot(path=f"{SHOTS}migration-accueil.png")
            S = await pg.evaluate("JSON.parse(localStorage.getItem('kono-v1'))")
            after_db = await pg.evaluate(READ_DB)
            # après : deux profils, suivi identique, enregistrements et phrases de Maman rattachés aux profils
            prof = {pp["legacy"]: pp for pp in S.get("profiles", []) if pp.get("legacy")}
            ok &= check(S.get("schema") == 2 and len(S.get("profiles", [])) == 2, f"schéma 2, {len(S.get('profiles', []))} profils", lines)
            ok &= check(S.get("pin") == STATE["pin"] and S.get("voice") == STATE["voice"] and all(S.get("settings", {}).get(k) == v for k, v in STATE["settings"].items()) and all(S.get("settings", {}).get(k) is False for k in ("gaucher", "calme", "contraste")), "code parent, voix et réglages conservés (les réglages d'affichage nouveaux restent éteints)", lines)
            ok &= check("migrate" not in S, "drapeau de migration effacé après la migration de la base", lines)
            ok &= check(bool(S.get("ecole", {}).get("grandfathered")), "tablette installée avant le contrôle d'accès : accès conservé, à régulariser par l'école", lines)
            for c, pid, nm in (("bleu", "ce1", "Ali"), ("orange", "gs", "Awa")):
                pp = prof.get(c)
                ok &= check(pp is not None and pp["parcours"] == pid and pp["couleur"] == c and pp["name"] == nm and pp["girl"] == STATE["girl"][c], f"case {c} → profil {nm}, parcours {pid}, couleur {c}, fille={STATE['girl'][c]}", lines)
                if pp:
                    before = STATE["progress"][c]; after = pp["progress"]
                    same = all(after.get(k) == v for k, v in before.items())
                    ok &= check(same, f"{nm} : suivi identique clé par clé ({', '.join(before)})", lines)
                    ok &= check(pp["classe"] == {"ce1": "CE1", "gs": "GS"}[pid], f"{nm} : classe {pp['classe']} déduite du parcours", lines)
            ids = {c: prof[c]["id"] for c in prof}
            recs = after_db["recs"]
            ok &= check(len(recs) == len(before_db["recs"]) and all("child" not in r or r["child"] is None for r in recs), f"{len(recs)} enregistrements conservés, plus aucun champ child", lines)
            ok &= check(any(r["profile"] == ids.get("bleu") and r["lesson"] == "bleu-s0-dizaine" and r["size"] == 9 for r in recs), "enregistrement d'Ali rattaché à son profil, audio intact", lines)
            ok &= check(any(r["profile"] == ids.get("orange") and r["lesson"] == "orange-s0-amis10" and r["size"] == 9 for r in recs), "enregistrement d'Awa rattaché à son profil, audio intact", lines)
            ok &= check(sorted(after_db["clips"]) == sorted([f"bonjour@{ids.get('bleu')}", f"fin@{ids.get('orange')}", "fiche"]), f"phrases de Maman : {after_db['clips']}", lines)
            # rapport par profil
            await pg.click("#parent")
            for ch in STATE["pin"]: await pg.click(f"[data-k='{ch}']")
            await pg.click("[data-t='rapport']"); rep = await pg.input_value("#rep")
            ok &= check(rep.count("== Profil ") == 2 and "parcours ce1" in rep and "parcours gs" in rep, "rapport du dimanche émis par profil", lines)
            ok &= check("installée avant le contrôle" in rep, "rapport : ligne d'inscription (installation antérieure)", lines)
            json.dump({"avant": {"localStorage": STATE, "indexedDB": before_db}, "apres": {"localStorage": S, "indexedDB": after_db, "rapport": rep}, "verdict": lines},
                      open(f"{SHOTS}migration-avant-apres.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            await b.close()
    finally:
        if srv.poll() is None: srv.terminate()
    print("\n".join(lines)); print("MIGRATION :", "OK, aucune perte" if ok else "ÉCHEC")
    sys.exit(0 if ok else 1)
if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
