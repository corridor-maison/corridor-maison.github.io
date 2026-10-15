"""Tests unitaires du juge et du moteur, dans le vrai moteur (Chromium) : les fonctions pures exposées par window.__kono.unit
sont appelées avec des données construites ici, sans jouer de séance. Le test échoue à la première assertion fausse.

Couvre : normalisation des codes d'inscription, clés et découpage des phrases (mêmes règles que build_audio.py), prénom et accord,
âge, options des automatismes, générateur des automatismes (invariants sur 300 tirages par sorte), verdict du juge (3 essais,
erreur typique, aide, réponse montrée, dernier choix), statistiques et maîtrise par compétence, carte du voyage (escales),
lecture d'un état (schéma 2, v0.2, inconnu), identifiants, rappel du niveau, révision ciblée sur les compétences fragiles.

Lancer : python3 tests/unite.py      (démarre et arrête lui-même un serveur sur le port 8769)
"""
import asyncio, json, pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent; APP = ROOT / "app"
fails, n = [], 0
def check(name, ok, detail=""):
    global n; n += 1
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)

async def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8769", "--directory", str(APP)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(); pg = await (await b.new_context(viewport={"width": 1280, "height": 800})).new_page()
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto("http://localhost:8769/#test"); await pg.wait_for_selector("#code")
            U = lambda js: pg.evaluate("(U => { " + js + " })(window.__kono.unit)")
            # --- codes d'inscription
            r = await U("return [U.normCode('abc-o1l'), U.normCode(' tst tst tst '), U.normCode('k7f 29q h43'), U.normCode('')];")
            check("normCode : majuscules, sans séparateurs, O→0, I/L→1", r == ["ABC011", "TSTTSTTST", "K7F29QH43", ""], str(r))
            # --- phrases et clés (mêmes règles que tools/build_audio.py)
            r = await U("return [U.keyOf('Bonjour  « Kono » !') === U.keyOf('Bonjour Kono !'), U.keyOf('a') !== U.keyOf('b'), /^[0-9a-f]{8}$/.test(U.keyOf('x')), U.sentences('Un. Deux ! Trois… Quatre').length, U.sentences('').length, U.sentences('Il a dit « oui ». Bien.')];")
            check("keyOf : guillemets et espaces ignorés, 8 hexadécimaux, clés distinctes", r[0] and r[1] and r[2], str(r[:3]))
            check("sentences : découpage sur . ! ? … et guillemets retirés (les espaces restent, comme dans build_audio.py)", r[3] == 4 and r[4] == 0 and r[5] == ["Il a dit  oui .", "Bien."], str(r[3:]))
            # --- prénom, accord, âge
            r = await U("return [U.fill('Coucou {prenom} !'), U.fill('trompé{e}'), U.fill(''), U.ageOf('2019-03-15'), U.ageOf(''), U.ageOf('bad'), U.ageOf('2021-02-10')];")
            check("fill : sans enfant, le prénom et l'accord disparaissent proprement", r[0] == "Coucou !" and r[1] == "trompé" and r[2] == "", str(r[:3]))
            check("ageOf : 7 ans (né le 15 mars 2019), 5 ans (10 février 2021), null sinon", r[3] == 7 and r[6] == 5 and r[4] is None and r[5] is None, str(r[3:]))
            # --- options et générateur d'automatismes
            r = await U("""const out = []; for (let i = 0; i < 300; i++) { const a = Math.floor(Math.random() * 11), o = U.opts3(a, 10 - a); out.push(o.length === 3 && new Set(o).size === 3 && o.includes(a) && o.every(x => x >= 0 && x <= 10)); } return out.every(Boolean);""")
            check("opts3 : trois options distinctes dans 0..10, la bonne incluse (300 tirages)", r is True)
            r = await U("""const bad = {}; const kinds = [{kind:'complement10'},{kind:'complement-next-ten'},{kind:'through10'},{kind:'double'},{kind:'table', n:[2,5]},{kind:'tf-complement'},{kind:'count-tf'},{kind:'decomp', n:[5,6]}];
              for (const k of kinds) for (let i = 0; i < 300; i++) { const it = U.genItem(k); let ok = true, m;
                if (k.kind === 'complement10') { m = it.q.match(/^(\\d+) \\+ \\? = 10$/); ok = !!m && +m[1] + it.answer === 10 && it.answer >= 1 && it.answer <= 9; }
                if (k.kind === 'complement-next-ten') { m = it.q.match(/^(\\d+) \\+ \\? = (\\d+)$/); ok = !!m && +m[1] + it.answer === +m[2] && +m[2] % 10 === 0 && it.answer >= 1 && it.answer <= 9; }
                if (k.kind === 'through10') { m = it.q.match(/^(\\d+) \\+ (\\d+)$/); ok = !!m && +m[1] + +m[2] === it.answer && (+m[1] % 10) + +m[2] >= 10 && it.answer <= 99; }
                if (k.kind === 'double') { m = it.q.match(/^le double de (\\d+)$/); ok = !!m && 2 * +m[1] === it.answer; }
                if (k.kind === 'table') { m = it.q.match(/^(\\d+) × (\\d+)$/); ok = !!m && +m[1] * +m[2] === it.answer && [2, 5].includes(+m[1]); }
                if (k.kind === 'tf-complement') ok = it.show[0].kind === 'tenframe' && it.show[0].filled + it.answer === 10 && it.options.includes(it.answer) && it.options.length === 3;
                if (k.kind === 'count-tf') ok = it.show[0].kind === 'tenframe' && it.show[0].filled === it.answer && it.options.includes(it.answer);
                if (k.kind === 'decomp') { m = it.q.match(/^(\\d+), c'est (\\d+) et combien \\?$/); ok = !!m && +m[1] - +m[2] === it.answer && [5, 6].includes(+m[1]) && it.show[0].kind === 'fingers' && it.show[0].up === +m[1] && it.options.includes(it.answer); }
                if (!ok) bad[k.kind] = (bad[k.kind] || 0) + 1; }
              return bad;""")
            check("genItem : question et réponse cohérentes pour les 8 sortes d'automatismes (300 tirages chacune)", r == {}, str(r))
            # --- le juge
            st = "{ answer: 33, errors: { '213': 'Tu as écrit 13 à côté du 2.', '23': { text: 'Tu as oublié la dizaine.', show: [{ kind: 'blocks', t: 2, u: 13 }] } }, hints: ['Aide un.', 'Aide deux.'] }"
            r = await U(f"""const st = {st}; const PH = U.PH();
              return [U.isRight(st, '33'), U.isRight(st, 33), U.isRight(st, '34'),
                U.verdict(st, '213', 1, 9), U.verdict(st, '23', 2, 9), U.verdict(st, '40', 1, 9), U.verdict(st, '40', 2, 9), U.verdict(st, '41', 3, 9), U.verdict(st, '5', 1, 1), U.verdict(st, '5', 2, 2),
                U.verdict({{ answer: 4 }}, '5', 1, 9).why === PH.lookAgain, U.verdict(st, '33', 1, 9, 'Tu n\\'es pas passé par 30.').why];""")
            check("isRight : comparaison en texte (33, '33' justes ; '34' faux)", r[0] and r[1] and not r[2])
            check("verdict : 1er essai faux typique → explication de l'erreur, sans la montrer", r[3]["kind"] == "retry" and r[3]["why"] == "Tu as écrit 13 à côté du 2." and r[3]["typed"] and r[3]["show"] is None, str(r[3]))
            check("verdict : erreur objet → explication et dessin", r[4]["kind"] == "retry" and r[4]["why"] == "Tu as oublié la dizaine." and r[4]["show"] == [{"kind": "blocks", "t": 2, "u": 13}], str(r[4]))
            check("verdict : erreur non typique → aide 1 puis aide 2", r[5]["why"] == "Aide un." and not r[5]["typed"] and r[6]["why"] == "Aide deux.", str([r[5]["why"], r[6]["why"]]))
            check("verdict : 3e essai faux → réponse montrée", r[7]["kind"] == "reveal")
            check("verdict : plus qu'une option possible → réponse montrée ; deux options → on réessaie", r[8]["kind"] == "reveal" and r[9]["kind"] == "retry")
            check("verdict : sans erreur typique ni aide → « Regarde encore » ; erreur forcée (via) → son texte", r[10] is True and r[11] == "Tu n'es pas passé par 30.", str(r[11]))
            # --- statistiques et maîtrise
            prof = """const it = (skill, ok, first) => ({ skill, answers: ['x'], ok, first }); const now = Date.now();
              const p = { id: 'tst1', name: 'Test', parcours: 'gs', progress: Object.assign(U.kid(), { runs: [
                { lesson: 'vieux', title: 'Vieux', date: '2026-08-01', start: now - 60 * 864e5, end: now - 60 * 864e5 + 60000, done: true, items: [it('E', true, true), it('E', true, true), it('E', true, true)], drill: null },
                { lesson: 'orange-s0-amis10', title: 'Les amis de 10', date: '2026-10-14', start: now - 2 * 864e5, end: now - 2 * 864e5 + 60000, done: true, items: [it('A', true, true), it('A', true, true), it('A', true, true), it('A', true, true), it('B', false, false), it('B', false, false), it('B', false, false), it('C', true, true), it('C', true, true), it('D', true, true), it('D', true, true), it('D', true, false), it('D', false, false)], drill: null } ] }) };"""
            r = await U(prof + " const s = U.skillStats(p, 7), m = U.masteryOf(p); return { s, m, m60: U.masteryOf(p, 90) };")
            s, m = r["s"], r["m"]
            check("skillStats (7 jours) : A 4 essais au 1er essai ; B 3 montrées ; D 2 + 1 après aide + 1 montrée ; E hors fenêtre", s["A"] == {"n": 4, "first": 4, "after": 0, "shown": 0} and s["B"]["shown"] == 3 and s["D"] == {"n": 4, "first": 2, "after": 1, "shown": 1} and "E" not in s, str(s))
            check("masteryOf (30 jours) : A acquis (100 %), B fragile (0 %), C peu travaillée (2 essais), D en cours (62 %, l'après-aide compte moitié)", m["A"]["level"] == "acquis" and m["A"]["score"] == 1 and m["B"]["level"] == "fragile" and m["B"]["score"] == 0 and m["C"]["level"] == "peu" and m["D"]["level"] == "en-cours" and m["D"]["score"] == 0.625 and "E" not in m, str({k: (v["level"], round(v["score"], 2), v["n"]) for k, v in m.items()}))
            check("masteryOf (90 jours) : E acquis apparaît", r["m60"].get("E", {}).get("level") == "acquis")
            # --- carte du voyage (escales gs : Bamako 4, Ségou 32, Djenné et Mopti 36, Tombouctou 40, Gao 0)
            r = await U("""const mk = n => ({ parcours: 'gs', progress: Object.assign(U.kid(), { done: Object.fromEntries(Array.from({ length: n }, (_, i) => ['l' + i, '2026-10-01'])) }) });
              return [0, 1, 4, 36, 72, 112, 500].map(n => { const j = U.journey(mk(n)); return [n, +j.f.toFixed(3), j.stamps]; });""")
            exp = [[0, 0, []], [1, 0.06, [1]], [4, 0.24, [1, 2]], [36, 0.45, [1, 2, 3]], [72, 0.73, [1, 2, 3, 4]], [112, 1, [1, 2, 3, 4, 5]], [500, 1, [1, 2, 3, 4, 5]]]
            check("journey : position de la pinasse et tampons du passeport selon le nombre de séances faites", r == exp, str(r))
            # --- lecture d'un état enregistré
            r = await U("""const a = U.fromStore(null), b = U.fromStore({ schema: 2, setup: true, pin: '1234', settings: { sounds: false }, profiles: [{ id: 'abcd', name: 'Awa', parcours: 'gs', couleur: 'orange', progress: { runs: [] } }] });
              const c = U.fromStore({ setup: true, pin: '9999', names: { bleu: 'Ali', orange: '' }, progress: { bleu: { runs: [{ x: 1 }], done: { 'bleu-s0-dizaine': '2026-10-01' } }, orange: {} } });
              return { a: [a.schema, a.setup, a.profiles.length, a.settings.gaucher, a.settings.sounds], b: [b.setup, b.pin, b.settings.sounds, b.settings.subtitles, b.settings.gaucher, b.profiles[0].progress.review.length, b.profiles[0].progress.resume],
                c: [c.profiles.length, c.profiles[0].parcours, c.profiles[0].legacy, c.profiles[0].name, c.profiles[0].progress.runs.length, c.migrate, c.pin] };""")
            check("fromStore : état vide → réglages par défaut (sons oui, main gauche non)", r["a"] == [2, False, 0, False, True], str(r["a"]))
            check("fromStore : schéma 2 → réglages complétés, suivi complété (review, resume)", r["b"] == [True, "1234", False, False, False, 0, None], str(r["b"]))
            check("fromV02 : case bleu avec suivi → profil Ali (ce1, legacy bleu), case orange vide ignorée, migration demandée", r["c"] == [1, "ce1", "bleu", "Ali", 1, True, "9999"], str(r["c"]))
            r = await U("const l = [{ id: 'aaaa' }]; const ids = new Set(); for (let i = 0; i < 200; i++) ids.add(U.newId(l)); return [ids.size, [...ids].every(x => /^[a-z0-9]{4}$/.test(x) && x !== 'aaaa')];")
            check("newId : 4 caractères, jamais un identifiant déjà pris, 200 tirages distincts", r[0] == 200 and r[1], str(r))
            # --- rappel du niveau
            r = await U(prof + " const PH = U.PH(); const fresh = { parcours: 'gs', progress: U.kid() }; return [U.recapOf(fresh, null, { title: 'Les amis de 10' }, false), U.recapOf(p, null, null, true), U.recapOf(p, { title: 'La calebasse magique' }, null, false), PH.recapFirst, PH.recapRevision, PH.recapResumeAsk, PH.recapGood, PH.recapAgain];")
            check("recapOf : première séance → bienvenue puis la séance du jour", r[3] in r[0] and "Les amis de 10" in r[0], r[0][:120])
            check("recapOf : avec historique → dernière séance, réussites (A), à revoir (D, B), puis révision", "Les amis de 10" in r[1] and f"{r[6]} A." in r[1] and f"{r[7]} D, B." in r[1] and r[4] in r[1], r[1][:200])
            check("recapOf : séance à reprendre → la nomme et propose de reprendre", "La calebasse magique" in r[2] and r[5] in r[2], r[2][:120])
            # --- révision ciblée : les défis de rappel visent d'abord la compétence fragile
            r = await U("""const L = window.__kono.LESSONS(); const ids = Object.keys(L).filter(k => L[k].parcours === 'gs' && !L[k].synthetic); const now = Date.now();
              const it = (skill, ok) => ({ skill, answers: ['x'], ok, first: ok });
              const p = { id: 'tst2', name: 'T', parcours: 'gs', progress: Object.assign(U.kid(), { done: Object.fromEntries(ids.map(i => [i, '2026-10-01'])),
                runs: [{ lesson: ids[0], title: 't', date: '2026-10-14', start: now - 864e5, end: now, done: true, items: [it('GS.N.amis10', false), it('GS.N.amis10', false), it('GS.N.amis10', false), it('GS.N.decomposer', true), it('GS.N.decomposer', true), it('GS.N.decomposer', true), it('GS.O.recit', true), it('GS.O.recit', true), it('GS.O.recit', true)], drill: null }] }) };
              const pool = U.retrievalPool(p); const skillOf = s => s.skill || (L[s.origin].skills || [])[0];
              const R = window.__kono.makeRevision(p); const rev = R.steps.find(s => s.type === 'review'); const retr = rev.fallback;
              return { pool: pool.length, nAmis: pool.filter(s => skillOf(s) === 'GS.N.amis10').length, retr: retr.map(skillOf), parts: R.steps.filter(s => s.type === 'part').length, hasDrill: R.steps.some(s => s.type === 'drill'), hasStory: R.steps.some(s => s.type === 'story'), end: R.steps[R.steps.length - 1].type };""")
            check("makeRevision : les défis de rappel visent d'abord la compétence fragile (GS.N.amis10)", r["pool"] > 3 and r["nAmis"] >= 3 and all(s == "GS.N.amis10" for s in r["retr"]), str(r))
            check("makeRevision : quatre temps, automatismes, histoire, fin", r["parts"] == 4 and r["hasDrill"] and r["hasStory"] and r["end"] == "end", str(r))
            # --- rapport (format 2) sans enfant, et réglages d'affichage
            r = await U("const t = window.__kono.report(); const d = window.__kono.reportData(t); return [t.split('\\n')[0], t.includes('Aucun enfant.'), d.format, d.profils.length, typeof d.texte];")
            check("report / reportData : en-tête « format 2 », fichier rapport-2, texte joint", r[0].endswith("RAPPORT · format 2") and r[1] and r[2] == "rapport-2" and r[3] == 0 and r[4] == "string", str(r))
            r = await U("const S = window.__kono.S; S.settings.gaucher = true; S.settings.calme = true; U.applySettings(); const a = [...document.body.classList]; const c1 = U.calm(); S.settings.gaucher = false; S.settings.calme = false; U.applySettings(); return [a.includes('gaucher'), a.includes('calme'), c1, [...document.body.classList].includes('gaucher')];")
            check("applySettings / calm : classes sur body posées puis retirées", r == [True, True, True, False], str(r))
            check("aucune erreur JavaScript pendant les tests unitaires", not errs, "\n".join(errs)[:300])
            await b.close()
    finally:
        if srv.poll() is None: srv.terminate()
    print(f"UNITÉ : {n} contrôles, {'OK' if not fails else 'ÉCHEC : ' + ', '.join(fails)}")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
