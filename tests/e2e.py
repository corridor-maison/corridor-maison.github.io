"""Test de bout en bout de Corridor à la maison : joue toutes les séances publiées, puis la séance de révision,
pour Bleu et Orange, en mode #test (voix accélérée), et vérifie qu'il n'y a aucune erreur JavaScript.

Prérequis : pip install playwright && playwright install chromium
Lancer :    python3 -m http.server 8765 --directory app &   puis   python3 tests/e2e.py [1280x800]
Captures et rapport : dossier $SHOTS (défaut /tmp/corridor-tests/).
"""
import asyncio, json, sys, re, os, pathlib
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = os.environ.get("SHOTS", "/tmp/corridor-tests/"); os.makedirs(SHOTS, exist_ok=True)
SH = SHOTS + "e2e-"
VW, VH = (int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1280x800").split("x"))
FAST = "#test"
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
   next: n && !n.hidden ? n.dataset.mode : null, lesson: P.lesson.id }; }"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        ctx = await b.new_context(viewport={"width": VW, "height": VH}, permissions=["microphone"])
        pg = await ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errs.append("CONSOLE " + m.text) if m.type == "error" else None)
        await pg.goto("http://localhost:8765/" + FAST); await pg.wait_for_selector("#go")
        await pg.fill("#n-bleu", "Ali"); await pg.fill("#n-orange", "Awa"); await pg.click("[data-g='orange:1']"); await pg.fill("#pin", "1234"); await pg.click("#go")
        shots = set(); log = []
        async def shot(tag, force=False):
            if tag in shots and not force: return
            shots.add(tag); await pg.screenshot(path=f"{SH}{VW}x{VH}-{tag}.png")
        async def typ(v):
            for ch in str(v): await pg.click(f"#answer [data-k='{ch}']")
            await pg.click("#answer [data-k='ok']")
        async def wait_idle(): await pg.wait_for_timeout(60)
        WRONG = {"seul-29-4": 213, "b-27-5": 212, "guide-8": None, "seul-dizaines-13": 313}
        async def run_lesson(child, lid):
            if lid is None:
                await pg.click("#revise"); lid = "revision"
            else:
                await pg.click(f".kid.{child}") if await pg.is_visible(f".kid.{child}") else None
                await pg.wait_for_selector(".tickets")
                await pg.click(f"[data-l='{lid}']")
            wrong_done = set(); guard = 0; last = None; same = 0
            while guard < 900:
                guard += 1; await wait_idle()
                s = await pg.evaluate(STATE)
                if s is None: break
                key = (s["i"], s["t"]); same = same + 1 if key == last else 0; last = key
                if same > 250: log.append(f"BLOQUÉ {lid} étape {s}"); return False
                if s["next"] == "end":
                    await shot(f"{child}-fin"); await pg.click("#next"); await pg.wait_for_selector(".tickets"); return True
                t = s["t"]
                if t in ("number", "choice"):
                    if await pg.is_visible("#answer .keypad") or await pg.is_visible("#answer .choices"):
                        if s["id"] in WRONG and s["id"] not in wrong_done:
                            wrong_done.add(s["id"])
                            if t == "number": await typ(WRONG[s["id"]])
                            else:
                                other = await pg.evaluate("(a) => [...document.querySelectorAll('#answer [data-o]')].map(b=>b.dataset.o).find(o => o !== String(a))", s["a"])
                                await pg.click(f"#answer [data-o=\"{other}\"]")
                            await pg.wait_for_timeout(250); await shot(f"{lid}-erreur-{s['id']}"); continue
                        await shot(f"{lid}-{t}-{s['id']}")
                        if t == "number": await typ(s["a"])
                        else: await pg.click(f"#answer [data-o=\"{s['a']}\"]")
                        await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                if t == "manip":
                    if s["mode"] == "tenframe" and await pg.is_visible("#check"):
                        need = s["a"] if s["goal"] == "add" else s["a"] - (s["start"] or 0)
                        idx_cells = await pg.evaluate("() => [...document.querySelectorAll('#stage .cell:not(.fixed)')].map(c => c.dataset.i)")
                        for ci in idx_cells[:need]: await pg.click(f"#stage .cell[data-i='{ci}']")
                        await shot(f"{lid}-manip-tf-{s['id']}"); await pg.click("#check")
                        await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                    if s["mode"] == "jumps" and await pg.is_visible("#check"):
                        if s["via"] is not None: await pg.click(f"#stage .hit[data-n='{s['via']}']")
                        await pg.click(f"#stage .hit[data-n='{s['a']}']")
                        await shot(f"{lid}-manip-jumps-{s['id']}"); await pg.click("#check")
                        await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                    if s["mode"] == "blocks":
                        if await pg.is_visible("#answer .keypad"):
                            await shot(f"{lid}-manip-blocks-ask-{s['id']}")
                            if s["id"] in WRONG and s["id"] not in wrong_done:
                                wrong_done.add(s["id"]); await typ(WRONG[s["id"]]); await pg.wait_for_timeout(300); await shot(f"{lid}-erreur-{s['id']}"); continue
                            await typ(s["a"]); await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                        rdy = await pg.evaluate("() => { const b = document.querySelector('#stage .board'); return b ? (b.classList.contains('ready-u') ? 'u' : b.classList.contains('ready-t') ? 't' : '') : null; }")
                        if rdy:
                            await shot(f"{lid}-manip-blocks-ready{rdy}-{s['id']}")
                            await pg.click(f"#stage .board .col-{rdy}"); await pg.wait_for_timeout(120); continue
                        if await pg.is_visible("#stage .tray .pc"):
                            await shot(f"{lid}-manip-blocks-{s['id']}")
                            await pg.click("#stage .tray"); await pg.wait_for_timeout(60); continue
                        continue
                if t == "order" and await pg.is_visible("#stage .sc-card"):
                    await shot(f"{lid}-order")
                    n = await pg.evaluate("() => window.__kono.P().steps[window.__kono.P().i].scenes.length")
                    # une erreur volontaire d'abord
                    await pg.click("#stage .sc-card[data-i='1']"); await pg.wait_for_timeout(50)
                    for k in range(n): await pg.click(f"#stage .sc-card[data-i='{k}']"); await pg.wait_for_timeout(30)
                    await pg.wait_for_selector("#next:not([hidden])", timeout=8000); await pg.click("#next"); continue
                if t == "drill":
                    if await pg.is_visible("#go"):
                        await shot(f"{child}-drill-intro"); await pg.click("#go")
                        first = True
                        for _ in range(60):
                            await pg.wait_for_timeout(30)
                            if await pg.is_visible("#next:not([hidden])"): break
                            ans = await pg.evaluate(DRILL_JS)
                            if ans is None: continue
                            if isinstance(ans, str): log.append(ans); break
                            if not await pg.is_visible("#answer .keypad, #answer .choices"): continue
                            val = (ans + 1) if first else ans
                            if await pg.is_visible("#answer .keypad"): await shot(f"{child}-drill-item"); await typ(val)
                            else:
                                if not await pg.is_visible(f"#answer [data-o='{val}']"): val = ans
                                await shot(f"{child}-drill-item"); await pg.click(f"#answer [data-o='{val}']")
                            first = False; await pg.wait_for_timeout(40)
                        await pg.wait_for_selector("#next:not([hidden])", timeout=15000); await shot(f"{child}-drill-fin"); await pg.click("#next")
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
                        await shot(f"{lid}-{t}"); await pg.click("#rb", force=True); await pg.wait_for_timeout(700); await pg.click("#rb", force=True)
                        
                        try: await pg.wait_for_selector("#keep", timeout=5000)
                        except Exception:
                            await shot("debug-keep", True); log.append("PAS DE #keep : " + (await pg.inner_html("#answer"))[:300] + " | " + str(errs[-3:])); return False
                        await shot(f"{lid}-{t}-garder"); await pg.click("#keep"); await pg.wait_for_timeout(200)
                    continue
                if s["next"] in ("next",):
                    if t in ("say", "demo", "listen"): await shot(f"{lid}-{t}-{s['i']}")
                    await pg.click("#next"); continue
            log.append(f"GARDE DÉPASSÉE {lid}"); return False
        idx = json.load(open(ROOT / "app" / "lessons" / "index.json"))
        try:
          await body(pg, idx, run_lesson, shot, log)
        finally:
          print("\n".join(log)); print("ERREURS JS :", "\n".join(errs) or "aucune")
        await b.close()
        if errs or not log or any(("ÉCHEC" in l) or ("BLOQUÉ" in l) or ("GARDE" in l) for l in log): sys.exit(1)
async def body(pg, idx, run_lesson, shot, log):
        for child in ("bleu", "orange"):
            if await pg.is_visible("#back"): await pg.click("#back")
            await pg.wait_for_selector(".kids"); await pg.click(f".kid.{child}")
            for l in [l for l in idx["lessons"] if l["child"] == child]:
                ok = await run_lesson(child, l["id"]); log.append(f"{l['id']}: {'OK' if ok else 'ÉCHEC'}")
                if not ok: await shot(f"bloque-{l['id']}", True); break
            await shot(f"{child}-carte-fin")
            if await pg.is_visible("#revise"):
                await shot(f"{child}-revision-proposee")
                ok = await run_lesson(child, None); log.append(f"révision {child}: {'OK' if ok else 'ÉCHEC'}")
                await shot(f"{child}-apres-revision", True)
            # séance de révision
            if await pg.is_visible("#back"): await pg.click("#back")
        # rapport
        await pg.click("#parent"); 
        for ch in "1234": await pg.click(f"[data-k='{ch}']")
        await pg.wait_for_timeout(400); await shot("parent-suivi")
        await pg.click("[data-t='rapport']"); await pg.wait_for_timeout(300)
        rep = await pg.input_value("#rep"); open(SH + "rapport.txt", "w").write(rep)
        sp = await pg.evaluate("() => window.__spoken || []"); open(SH + "spoken.json", "w").write(json.dumps(sp, ensure_ascii=False))
if __name__ == "__main__":
    asyncio.run(main())
