"""Test de bout en bout de Corridor à la maison, avec profils.
Deux profils (CE1 et GS) jouent toutes les séances publiées de leur parcours jusqu'au bout, puis la séance de révision,
en mode #test (voix accélérée). Le test échoue à la moindre erreur JavaScript, à la moindre séance bloquée,
et si la couverture attendue n'est pas atteinte : boîte de dix en ajout et en total, blocs avec fermeture des unités
puis des dizaines, sauts avec arrêt obligatoire, remise en ordre de l'histoire, au moins une erreur expliquée par une animation.

Prérequis : pip install playwright && playwright install chromium
Lancer :    python3 -m http.server 8765 --directory app &   puis   python3 tests/e2e.py [1280x800]
Captures et rapport : dossier $SHOTS (défaut /tmp/corridor-tests/).
"""
import asyncio, json, sys, os, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = os.environ.get("SHOTS", "/tmp/corridor-tests/"); os.makedirs(SHOTS, exist_ok=True)
VW, VH = (int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1280x800").split("x"))
SH = f"{SHOTS}e2e-{VW}x{VH}-"
URL = "http://localhost:8765/#test"
PIN = "1234"
PROFILES = [("ce1", "Ali", "2019-03-15", False), ("gs", "Awa", "2021-02-10", True)]
REQUIRED = ["tenframe:add", "tenframe:total", "blocks:fermeture-unites", "blocks:fermeture-dizaines", "jumps:via", "order", "erreur-animee", "reprise", "rappel", "acces", "profil-export", "journal", "navigation", "rapport-fichier", "maitrise", "reglages-affichage", "verrou", "escale", "programme"]
NAMES = r"""() => { const out = []; const vis = el => !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  const nameOf = el => (el.getAttribute('aria-label') || el.getAttribute('title') || (el.labels && [...el.labels].map(l => l.textContent).join(' ')) || (el.closest('label') ? el.closest('label').textContent : '') || el.textContent || el.getAttribute('placeholder') || '').replace(/\s+/g, ' ').trim();
  document.querySelectorAll('button, [role=button], input:not([type=hidden]), select, textarea').forEach(el => { if (vis(el) && !nameOf(el)) out.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).join('.') : '')); });
  document.querySelectorAll('img').forEach(i => { if (vis(i) && i.getAttribute('alt') == null) out.push('img sans alt ' + (i.getAttribute('src') || '')); });
  return out; }"""
DRILL_JS = r"""() => {
  const e = document.querySelector('.drill .v-expr'); if (!e) return null;
  const q = e.textContent.trim(); const svg = document.querySelector('.drill svg[aria-label]'); const lab = svg ? svg.getAttribute('aria-label') : '';
  let m, f = (m = lab.match(/avec (\d+) points/)) ? +m[1] : null;
  if ((m = q.match(/^(\d+) \+ \? = (\d+)$/))) return +m[2] - +m[1];
  if ((m = q.match(/^(\d+) \+ (\d+)$/))) return +m[1] + +m[2];
  if ((m = q.match(/^le double de (\d+)$/))) return 2 * +m[1];
  if ((m = q.match(/^(\d+) × (\d+)$/))) return +m[1] * +m[2];
  if (q === 'Combien de cases vides ?') return 10 - f;
  if (q === 'Combien de points ?') return f;
  if ((m = q.match(/^(\d+), c'est (\d+) et combien \?$/))) return +m[1] - +m[2];
  return 'INCONNU:' + q;
}"""
STATE = """() => { const P = window.__kono.P(); if (!P) return null; const st = P.steps[P.i]; const n = document.querySelector('#next');
 return { i: P.i, n: P.steps.length, t: st && st.type, id: st && st.id, mode: st && st.mode, a: st && st.answer, via: st && st.via, start: st && st.start, goal: st && st.goal,
   hundreds: !!(st && st.hundreds), shows: (st && st.show || []).map(v => v.kind), optionKind: st && st.optionKind,
   next: n && !n.hidden ? n.dataset.mode : null, lesson: P.lesson.id }; }"""
ANIM = "() => !!document.querySelector('#stage .board[data-regroup=\"1\"], #stage .arc, #stage .pulse')"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        ctx = await b.new_context(viewport={"width": VW, "height": VH}, permissions=["microphone"])
        pg = await ctx.new_page(); errs = []; log = []; cov = collections.Counter(); shots = set(); a11y = {}
        pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errs.append("CONSOLE " + m.text) if m.type == "error" else None)
        async def shot(tag, force=False):
            if tag in shots and not force: return
            shots.add(tag); await pg.screenshot(path=f"{SH}{tag}.png")
            v = await pg.evaluate(NAMES)   # lecteur d'écran : à chaque capture, tout bouton, champ ou image visible a un nom
            if v: a11y[tag] = v
        async def typ(v):
            for ch in str(v): await pg.click(f"#answer [data-k='{ch}']")
            await pg.click("#answer [data-k='ok']")
        async def type_pin():
            await pg.wait_for_selector(".pin")
            for ch in PIN: await pg.click(f"[data-k='{ch}']")
        async def create_profile(parcours, name, dob, girl):
            await pg.wait_for_selector("#p-name"); await pg.fill("#p-name", name); await pg.fill("#p-dob", dob)
            if girl: await pg.click("[data-g='1']")
            await pg.click(f"[data-p='{parcours}']"); await shot(f"profil-{parcours}"); await pg.click("#go"); await pg.wait_for_selector(".kids")
        async def wait_idle(): await pg.wait_for_timeout(60)
        WRONG = {"seul-29-4": 213, "b-27-5": 212, "guide-8": None, "seul-dizaines-13": 313}

        # ---- première installation : réglage parent, puis un profil ; puis un deuxième profil (code parent demandé)
        # accès autorisé par l'école : un code faux est refusé, le code de test ouvre le réglage parent
        await pg.goto(URL); await pg.wait_for_selector("#code"); await shot("code-ecole")
        await pg.fill("#code", "AAA-AAA-AAA"); await pg.click("#go"); await pg.wait_for_timeout(400)
        refused = ("Code inconnu" in await pg.inner_text("#err")) and await pg.is_visible("#code")
        await pg.fill("#code", CODE); await pg.click("#go"); await pg.wait_for_selector("#pin"); await shot("setup")
        if refused: cov["acces"] += 1
        log.append(f"accès école : code faux refusé {'OK' if refused else 'ÉCHEC'} · code de test accepté")
        await pg.fill("#pin", PIN); await pg.click("#go")
        await create_profile(*PROFILES[0])
        await pg.click("#add"); await type_pin(); await create_profile(*PROFILES[1])
        await shot("accueil-profils")
        profiles = await pg.evaluate("window.__kono.S.profiles.map(p => ({ id: p.id, parcours: p.parcours, name: p.name, couleur: p.couleur }))")
        log.append("profils : " + ", ".join(f"{p['name']} ({p['parcours']}, {p['id']})" for p in profiles))

        async def run_lesson(prof, lid, via="ticket", stop=None):
            pc = prof["parcours"]
            if via == "revise":
                await pg.click("#revise"); lid = "revision"
            elif via == "resume":
                await pg.click("#resume")
            elif via == "ticket":
                # navigation sans lecture : toucher un billet le sélectionne et Kono nomme la séance ; la pinasse (bouton unique) la lance
                await pg.wait_for_selector(".tickets"); await pg.evaluate("window.__spoken = []"); await pg.click(f"[data-l='{lid}']")
                await pg.wait_for_selector(f".ticket.sel[data-l='{lid}']"); await pg.wait_for_timeout(150)
                said = " ".join(await pg.evaluate("() => window.__spoken || []")); title = (await pg.inner_text(f".ticket[data-l='{lid}'] .t-title")).strip()
                if title and title in said and "pinasse" in said: cov["navigation"] += 1
                else: log.append(f"NAVIGATION {lid} : Kono n'a pas nommé la séance touchée (« {said[:100]} »)")
                if "ticket-touche" not in shots: await shot("ticket-touche")
                await pg.click("#today .boat-btn")
            wrong_done = set(); guard = 0; last = None; same = 0; kinds_shot = set()
            while guard < 900:
                guard += 1; await wait_idle()
                s = await pg.evaluate(STATE)
                if s is None: break
                if stop and stop(s): return "STOP"
                key = (s["i"], s["t"]); same = same + 1 if key == last else 0; last = key
                if same > 250: log.append(f"BLOQUÉ {lid} étape {s}"); return False
                if s["next"] == "end":
                    await shot(f"{pc}-fin"); await pg.click("#next"); await pg.wait_for_selector(".tickets"); return True
                t = s["t"]
                for k in s["shows"]:
                    if k in ("bar", "hidden", "icon", "items", "syllables", "numberline", "blocks") and k not in kinds_shot: kinds_shot.add(k); await shot(f"{lid}-show-{k}-{s['i']}")
                async def wrong_then_check(sid):
                    await pg.wait_for_timeout(350)
                    if await pg.evaluate(ANIM): cov["erreur-animee"] += 1; await shot(f"{lid}-erreur-animee-{sid}")
                    await shot(f"{lid}-erreur-{sid}")
                if t in ("number", "choice"):
                    if await pg.is_visible("#answer .keypad") or await pg.is_visible("#answer .choices"):
                        if s["id"] in WRONG and s["id"] not in wrong_done:
                            wrong_done.add(s["id"])
                            if t == "number": await typ(WRONG[s["id"]])
                            else:
                                other = await pg.evaluate("(a) => [...document.querySelectorAll('#answer [data-o]')].map(b=>b.dataset.o).find(o => o !== String(a))", s["a"])
                                await pg.click(f"#answer [data-o=\"{other}\"]")
                            await wrong_then_check(s["id"]); continue
                        kind = s["optionKind"] or ("text" if await pg.is_visible("#answer .choices.k-text") else "plain")
                        if t == "choice" and f"choice-{kind}" not in shots: await shot(f"choice-{kind}")
                        await shot(f"{lid}-{t}-{s['id']}")
                        if t == "number": await typ(s["a"])
                        else: await pg.click(f"#answer [data-o=\"{s['a']}\"]")
                        await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                if t == "manip":
                    if s["mode"] == "tenframe" and await pg.is_visible("#check"):
                        need = s["a"] if s["goal"] == "add" else s["a"] - (s["start"] or 0)
                        idx_cells = await pg.evaluate("() => [...document.querySelectorAll('#stage .cell:not(.fixed)')].map(c => c.dataset.i)")
                        for ci in idx_cells[:need]: await pg.click(f"#stage .cell[data-i='{ci}']")
                        await shot(f"{lid}-manip-tf-{s['goal']}-{s['id']}"); await pg.click("#check")
                        cov[f"tenframe:{s['goal']}"] += 1
                        await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                    if s["mode"] == "jumps" and await pg.is_visible("#check"):
                        if s["via"] is not None: await pg.click(f"#stage .hit[data-n='{s['via']}']"); cov["jumps:via"] += 1
                        await pg.click(f"#stage .hit[data-n='{s['a']}']")
                        await shot(f"{lid}-manip-jumps-{s['id']}"); await pg.click("#check")
                        await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                    if s["mode"] == "blocks":
                        if await pg.is_visible("#answer .keypad"):
                            await shot(f"{lid}-manip-blocks-ask-{s['id']}")
                            if s["id"] in WRONG and s["id"] not in wrong_done:
                                wrong_done.add(s["id"]); await typ(WRONG[s["id"]]); await wrong_then_check(s["id"]); continue
                            await typ(s["a"]); await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                        rdy = await pg.evaluate("() => { const b = document.querySelector('#stage .board'); return b ? (b.classList.contains('ready-u') ? 'u' : b.classList.contains('ready-t') ? 't' : '') : null; }")
                        if rdy:
                            await shot(f"{lid}-manip-blocks-ready{rdy}-{s['id']}")
                            await pg.click(f"#stage .board .col-{rdy}"); await pg.wait_for_timeout(120)
                            cov["blocks:fermeture-unites" if rdy == "u" else "blocks:fermeture-dizaines"] += 1; continue
                        if await pg.is_visible("#stage .tray .pc"):
                            await shot(f"{lid}-manip-blocks-{s['id']}")
                            await pg.click("#stage .tray"); await pg.wait_for_timeout(60); continue
                        continue
                if t == "order" and await pg.is_visible("#stage .sc-card"):
                    await shot(f"{lid}-order")
                    n = await pg.evaluate("() => window.__kono.P().steps[window.__kono.P().i].scenes.length")
                    await pg.click("#stage .sc-card[data-i='1']"); await pg.wait_for_timeout(50)   # une erreur volontaire d'abord
                    for k in range(n): await pg.click(f"#stage .sc-card[data-i='{k}']"); await pg.wait_for_timeout(30)
                    cov["order"] += 1
                    await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                if t == "drill":
                    if await pg.is_visible("#go"):
                        await shot(f"{pc}-drill-intro"); await pg.click("#go")
                        first = True
                        for _ in range(60):
                            await pg.wait_for_timeout(30)
                            if await pg.is_visible("#next:not([hidden])"): break
                            ans = await pg.evaluate(DRILL_JS)
                            if ans is None: continue
                            if isinstance(ans, str): log.append(ans); break
                            if not await pg.is_visible("#answer .keypad, #answer .choices"): continue
                            val = (ans + 1) if first else ans
                            if await pg.is_visible("#answer .keypad"): await shot(f"{pc}-drill-item"); await typ(val)
                            else:
                                if not await pg.is_visible(f"#answer [data-o='{val}']"): val = ans
                                await shot(f"{pc}-drill-item"); await pg.click(f"#answer [data-o='{val}']")
                            first = False; await pg.wait_for_timeout(40)
                        await pg.wait_for_selector("#next:not([hidden])", timeout=15000); await shot(f"{pc}-drill-fin"); await pg.click("#next")
                    continue
                if t == "paper":
                    if await pg.is_visible("#fini"):
                        await shot(f"{lid}-fiche-appel"); await pg.click("#fini")
                        items = await pg.evaluate("() => { const P = window.__kono.P(); const out=[]; P.lesson.paper.levels.forEach(l => l.items.forEach(it => { if (it.answer !== undefined) out.push([it.id, it.answer]); })); return out; }")
                        for k, (iid, ans) in enumerate(items):
                            await pg.click(f"[data-i='{iid}']")
                            v = str(ans) if k else str(ans) + "1"
                            for ch in v: await pg.click(f"#answer [data-k='{ch}']")
                        await pg.click("#answer [data-k='ok']"); await pg.wait_for_timeout(200); await shot(f"{lid}-fiche-verif")
                        if not await pg.is_visible("#next:not([hidden])"):
                            await pg.click(f"[data-i='{items[0][0]}']")
                            for _ in range(6): await pg.click("#answer [data-k='del']")
                            for ch in str(items[0][1]): await pg.click(f"#answer [data-k='{ch}']")
                            await pg.click("#answer [data-k='ok']")
                        await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next")
                    continue
                if t in ("reading", "record"):
                    if await pg.is_visible("#rb"):
                        await shot(f"{lid}-{t}"); await pg.click("#rb", force=True)
                        await pg.wait_for_selector(".rec-btn.on", timeout=10000); await pg.wait_for_timeout(600); await pg.click("#rb", force=True)
                        try: await pg.wait_for_selector("#keep", timeout=5000)
                        except Exception:
                            await shot("debug-keep", True); log.append("PAS DE #keep : " + (await pg.inner_html("#answer"))[:300] + " | " + str(errs[-3:])); return False
                        await shot(f"{lid}-{t}-garder"); await pg.click("#keep"); await pg.wait_for_timeout(200)
                    continue
                if s["next"] in ("next",):
                    if t in ("say", "demo", "listen"): await shot(f"{lid}-{t}-{s['i']}")
                    await pg.click("#next"); continue
            log.append(f"GARDE DÉPASSÉE {lid}"); return False

        idx = json.load(open(ROOT / "app" / "lessons" / "index.json", encoding="utf-8"))
        try:
            for prof in profiles:
                await pg.wait_for_selector(".kids"); await pg.click(f".kid[data-c='{prof['id']}']"); await pg.wait_for_selector(".tickets")
                await shot(f"{prof['parcours']}-enfant")
                # ordre des séances : toucher le dernier billet (verrouillé) ne change pas la sélection (la première séance) et Kono dit laquelle vient d'abord
                lids = [l["id"] for l in sorted([l for l in idx["lessons"] if l["parcours"] == prof["parcours"]], key=lambda l: l["order"])]
                if await pg.is_visible(f".ticket.locked[data-l='{lids[-1]}']"):
                    await pg.evaluate("window.__spoken = []"); await pg.click(f"[data-l='{lids[-1]}']"); await pg.wait_for_timeout(150)
                    said = " ".join(await pg.evaluate("() => window.__spoken || []")); selid = await pg.evaluate("() => { const s = document.querySelector('.ticket.sel'); return s ? s.dataset.l : null; }")
                    if selid == lids[0] and "D'abord" in said: cov["verrou"] += 1
                    else: log.append(f"VERROU {prof['parcours']} : sélection {selid}, dit « {said[:80]} »")
                    await shot("verrou")
                else: log.append(f"VERROU {prof['parcours']} : le dernier billet n'est pas verrouillé")
                # escale : Bamako est un bouton qui ouvre les séances de l'étape (4 publiées) et Kono les compte
                await pg.evaluate("window.__spoken = []"); await pg.click("[data-esc='1']"); await pg.wait_for_selector("#escale:not([hidden]) .esc-row")
                nrows = await pg.evaluate("document.querySelectorAll('#escale .esc-row').length"); said = " ".join(await pg.evaluate("() => window.__spoken || []"))
                if nrows == 4 and "Bamako" in said and "Ségou" in said: cov["escale"] += 1
                else: log.append(f"ESCALE {prof['parcours']} : {nrows} lignes, dit « {said[:80]} »")
                await shot("escale"); await pg.click("#esc-close"); await pg.wait_for_timeout(100)
                for l in sorted([l for l in idx["lessons"] if l["parcours"] == prof["parcours"]], key=lambda l: l["order"]):
                    ok = await run_lesson(prof, l["id"]); log.append(f"{l['id']}: {'OK' if ok else 'ÉCHEC'}")
                    if not ok: await shot(f"bloque-{l['id']}", True); break
                await shot(f"{prof['parcours']}-carte-fin")
                if await pg.is_visible("#revise"):
                    if not await pg.is_visible("[data-l='revision']"): log.append(f"révision {prof['parcours']}: billet de révision ÉCHEC (absent)")
                    await shot(f"{prof['parcours']}-revision-proposee")
                    ok = await run_lesson(prof, None, via="revise"); log.append(f"révision {prof['parcours']}: {'OK' if ok else 'ÉCHEC'}")
                    await shot(f"{prof['parcours']}-apres-revision", True)
                else: log.append(f"révision {prof['parcours']}: NON PROPOSÉE")
                await pg.click("#back")
            # espace parent : suivi par profil, puis rapport
            # contrôle du moteur : la boîte de dix « en ajout » n'est utilisée par aucune séance S1 ; on l'exerce sur un
            # troisième profil de contrôle (GS, couleur verte) avec une étape injectée, signalée comme telle.
            await pg.click("#add"); await type_pin(); await pg.wait_for_selector("#p-name")
            await pg.fill("#p-name", "Contrôle"); await pg.fill("#p-dob", "2021-05-01"); await pg.click("[data-p='gs']"); await pg.click(".swatch[data-t='vert']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            ctrl = await pg.evaluate("window.__kono.S.profiles.slice(-1)[0].id")
            await pg.click(f".kid[data-c='{ctrl}']"); await pg.wait_for_selector(".tickets")
            # reprise : six étapes, arrêt par le bouton, fermeture du navigateur (rechargement), reprise là où l'enfant s'est arrêté, fin
            cp = {"parcours": "gs"}; RL = "orange-s0-amis10"
            r = await run_lesson(cp, RL, stop=lambda s: s["i"] >= 6)
            assert r == "STOP", "la séance n'a pas atteint l'étape 6"
            await pg.click("#quit"); await pg.wait_for_selector("#qa-leave"); await pg.click("#qa-leave"); await pg.wait_for_selector("#resume")
            rs = await pg.evaluate(f"() => {{ const p = window.__kono.profileOf('{ctrl}'); const r = p.progress.resume; return r && {{ lesson: r.lesson, i: r.i, n: r.steps.length, done: r.run.items.filter(it => it.done).length, items: r.run.items.length }}; }}")
            await shot("reprise-proposee")
            await pg.reload(); await pg.wait_for_selector(".kids"); await pg.evaluate("window.__spoken = []")
            await pg.click(f".kid[data-c='{ctrl}']"); await pg.wait_for_selector(".tickets"); await pg.wait_for_timeout(300)
            spoken = " ".join(await pg.evaluate("() => window.__spoken || []"))
            after = await pg.evaluate(f"() => {{ const r = window.__kono.profileOf('{ctrl}').progress.resume; return r && {{ lesson: r.lesson, i: r.i }}; }}")
            ok_prop = await pg.is_visible("#resume") and after and after["lesson"] == RL and after["i"] == rs["i"] and "au milieu de la séance" in spoken
            log.append(f"reprise proposée après fermeture : {'OK' if ok_prop else 'ÉCHEC'} (étape {rs and rs['i']}/{rs and rs['n']}, {rs and rs['done']} réponses gardées, rappel dit : {'oui' if 'au milieu de la séance' in spoken else 'non'})")
            r = await run_lesson(cp, RL, via="resume", stop=lambda s: s["lesson"] == RL and s["i"] == rs["i"] and not getattr(run_lesson, "_checked", False))
            run_lesson._checked = True
            st_now = await pg.evaluate("() => { const P = window.__kono.P(); return { i: P.i, items: P.run.items.length, fish: P.fish + P.gold }; }")
            ok_pos = st_now["i"] == rs["i"] and st_now["items"] == rs["done"]
            log.append(f"reprise à la bonne étape : {'OK' if ok_pos else 'ÉCHEC'} (étape {st_now['i']}, {st_now['items']} réponses, {st_now['fish']} poissons)")
            ok = await run_lesson(cp, RL, via=None); log.append(f"{RL} reprise jusqu'au bout : {'OK' if ok else 'ÉCHEC'}")
            fin = await pg.evaluate(f"() => {{ const p = window.__kono.profileOf('{ctrl}'); const r = p.progress.runs.slice(-1)[0]; return {{ resume: !!p.progress.resume, done: r && r.done, lesson: r && r.lesson, items: r ? r.items.length : 0 }}; }}")
            ok_fin = ok and not fin["resume"] and fin["done"] and fin["lesson"] == RL and fin["items"] >= rs["done"]
            log.append(f"historique après reprise : {'OK' if ok_fin else 'ÉCHEC'} (séance {fin['lesson']} terminée={fin['done']}, {fin['items']} réponses, reprise effacée={not fin['resume']})")
            if ok_prop and ok_pos and ok_fin: cov["reprise"] += 1
            await pg.click("#back"); await pg.wait_for_selector(".kids"); await pg.evaluate("window.__spoken = []")
            await pg.click(f".kid[data-c='{ctrl}']"); await pg.wait_for_selector(".tickets"); await pg.wait_for_timeout(300)
            spoken = " ".join(await pg.evaluate("() => window.__spoken || []"))
            if "La dernière fois, tu as fait" in spoken and "Aujourd'hui" in spoken: cov["rappel"] += 1
            await shot("enfant-billets", True)
            log.append(f"rappel du niveau à l'ouverture : {'OK' if cov['rappel'] else 'ÉCHEC'} · « {spoken[:140]} »")
            await shot("rappel-niveau")
            await pg.evaluate("""() => { window.__kono.LESSONS()['controle-moteur'] = { id: 'controle-moteur', parcours: 'gs', order: 998, week: 'S1', title: 'Contrôle du moteur', domain: 'Contrôle', programme: 'Contrôle', objective: 'Boîte de dix en ajout.', skills: [], escale: 1, synthetic: true, paper: { title: 'Contrôle', levels: [] },
              steps: [ { type: 'manip', mode: 'tenframe', id: 'controle-pose-3', start: 7, goal: 'add', answer: 3, text: 'Il y a 7 jetons. Pose les jetons qui manquent pour faire 10.' }, { type: 'end', clip: 'fin' } ] };
              window.__kono.startLesson('controle-moteur'); }""")
            guard = 0
            while guard < 200:
                guard += 1; await wait_idle(); s = await pg.evaluate(STATE)
                if s is None: break
                if s["t"] == "manip" and s["mode"] == "tenframe" and await pg.is_visible("#check"):
                    cells = await pg.evaluate("() => [...document.querySelectorAll('#stage .cell:not(.fixed)')].map(c => c.dataset.i)")
                    for ci in cells[:s["a"]]: await pg.click(f"#stage .cell[data-i='{ci}']")
                    await shot("controle-manip-tf-add"); await pg.click("#check"); await pg.wait_for_selector("#next:not([hidden])", timeout=8000)
                    cov[f"tenframe:{s['goal']}"] += 1; await pg.click("#next"); continue
                if s["next"] == "end": await pg.click("#next"); await pg.wait_for_selector(".tickets"); break
            log.append("contrôle moteur (étape injectée, profil Contrôle) : boîte de dix en ajout " + ("OK" if cov.get("tenframe:add") else "ÉCHEC"))
            await pg.click("#back")
            await pg.click("#parent"); await type_pin(); await pg.wait_for_timeout(400); await shot("parent-suivi")
            # rappel de sauvegarde (jamais faite, suivi présent), journal d'erreurs, export puis import d'un profil
            backup = await pg.is_visible("#tobackup"); log.append(f"rappel de sauvegarde affiché : {'OK' if backup else 'ÉCHEC'}")
            await pg.evaluate("window.__kono.logError('essai du journal')")
            suivi = await pg.inner_text("#pane")
            if "Maîtrise par compétence" in suivi and "acquis" in suivi: cov["maitrise"] += 1
            log.append(f"maîtrise par compétence dans le Suivi : {'OK' if cov['maitrise'] else 'ÉCHEC'}")
            # réglages d'affichage : main gauche, moins d'animations, contraste ; posés puis retirés (les captures suivantes restent standard)
            await pg.click("[data-t='kono']"); await pg.wait_for_selector("#st-gauch"); await pg.click("#st-gauch"); await pg.click("#st-calme"); await pg.click("#st-contr"); await pg.wait_for_timeout(100)
            cls = await pg.evaluate("[...document.body.classList]"); await shot("parent-reglages-affichage")
            if all(c in cls for c in ("gaucher", "calme", "contraste")): cov["reglages-affichage"] += 1
            log.append(f"réglages d'affichage (main gauche, calme, contraste) : {'OK' if cov['reglages-affichage'] else 'ÉCHEC'} {cls}")
            await pg.click("#st-gauch"); await pg.click("#st-calme"); await pg.click("#st-contr"); await pg.wait_for_timeout(100)
            # onglet Programme : le voyage, la semaine publiée, la progression de l'année, l'état par enfant
            await pg.click("[data-t='programme']"); await pg.wait_for_timeout(300); ptxt = await pg.inner_text("#pane"); await shot("parent-programme")
            if "Le voyage" in ptxt and "Semaine S1" in ptxt and "Progression de l'année" in ptxt and "faite" in ptxt and "Bamako" in ptxt: cov["programme"] += 1
            log.append(f"onglet Programme (voyage, semaine S1, progression, état par enfant) : {'OK' if cov['programme'] else 'ÉCHEC'}")
            await pg.click("[data-t='reglages']"); await pg.wait_for_timeout(300)
            jtxt = await pg.inner_text("#pane")
            if "essai du journal" in jtxt and "1 erreur notée" in jtxt: cov["journal"] += 1
            log.append(f"journal d'erreurs visible dans Réglages : {'OK' if cov['journal'] else 'ÉCHEC'}")
            n0 = len(profiles) + 1
            async with pg.expect_download() as dl: await pg.click(f"[data-exp='{profiles[0]['id']}']")
            fpath = await (await dl.value).path()
            await pg.set_input_files("#impp", str(fpath)); await pg.wait_for_timeout(800)
            after = await pg.evaluate("() => window.__kono.S.profiles.map(p => ({ name: p.name, parcours: p.parcours, runs: p.progress.runs.length, done: Object.keys(p.progress.done).length }))")
            src = next(p for p in after if p["name"] == profiles[0]["name"]); twin = [p for p in after if p["name"] == profiles[0]["name"]]
            recs = await pg.evaluate("() => window.__kono.S.profiles.map(p => p.id)")
            ok_imp = len(after) == n0 + 1 and len(twin) == 2 and twin[0]["runs"] == twin[1]["runs"] and twin[0]["done"] == twin[1]["done"] and twin[1]["parcours"] == src["parcours"]
            if ok_imp: cov["profil-export"] += 1
            log.append(f"export puis import d'un profil : {'OK' if ok_imp else 'ÉCHEC'} ({twin[1]['runs'] if len(twin) > 1 else '?'} séances et {twin[1]['done'] if len(twin) > 1 else '?'} faites retrouvées)")
            await shot("parent-reglages")
            await pg.click("[data-t='rapport']"); await pg.wait_for_timeout(300)
            rep = await pg.input_value("#rep"); open(SH + "rapport.txt", "w", encoding="utf-8").write(rep)
            log.append(f"rapport : ligne d'inscription {'OK' if 'Inscription : C-9999' in rep else 'ÉCHEC'} · format 2 et rubrique 8 (maîtrise) {'OK' if 'RAPPORT · format 2' in rep and '8. MAÎTRISE' in rep and ' | acquis | ' in rep else 'ÉCHEC'}")
            # rapport enregistré dans un fichier (format rapport-1) : mêmes profils, même texte, chiffres présents
            async with pg.expect_download() as dl: await pg.click("#repfile")
            rp = await (await dl.value).path(); data = json.load(open(rp, encoding="utf-8")); open(SH + "rapport.json", "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
            p0 = (data.get("profils") or [{}])[0]
            ok_rf = data.get("format") == "rapport-2" and isinstance(p0.get("maitrise"), dict) and any(v.get("palier") == "acquis" for v in p0["maitrise"].values()) and (data.get("inscription") or {}).get("id") == "C-9999" and len(data.get("profils", [])) == n0 + 1 and data.get("texte") == rep and all(k in p0 for k in ("seances", "competences", "revision", "enregistrements")) and p0["seances"]["terminees"] >= 4 and len(p0["competences"]) >= 2
            if ok_rf: cov["rapport-fichier"] += 1
            log.append(f"rapport enregistré dans un fichier : {'OK' if ok_rf else 'ÉCHEC'} ({len(data.get('profils', []))} profils, inscription {(data.get('inscription') or {}).get('id')}, {p0.get('seances', {}).get('terminees')} séances terminées, {len(p0.get('competences', {}))} compétences)")
            sp = await pg.evaluate("() => window.__spoken || []"); open(SH + "spoken.json", "w", encoding="utf-8").write(json.dumps(sp, ensure_ascii=False))
        finally:
            print("\n".join(log))
            print("COUVERTURE : " + " · ".join(f"{k} = {cov.get(k, 0)}" for k in REQUIRED))
            print("ERREURS JS :", "\n".join(errs) or "aucune")
            print("LECTEUR D'ÉCRAN :", "tout nommé sur " + str(len(shots)) + " captures" if not a11y else "SANS NOM : " + " ; ".join(f"{k} → {', '.join(v[:5])}" for k, v in a11y.items()))
        await b.close()
        missing = [k for k in REQUIRED if not cov.get(k)]
        if missing: print("COUVERTURE MANQUANTE :", ", ".join(missing))
        if errs or a11y or not log or missing or any(("ÉCHEC" in l) or ("BLOQUÉ" in l) or ("GARDE" in l) or ("NON PROPOSÉE" in l) for l in log): sys.exit(1)
        print("E2E : OK")
if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
