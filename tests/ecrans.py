"""Écrans : téléphone, réglages d'affichage, lecteur d'écran.

- Téléphone (360 × 640) : chaque écran de l'enfant (accueil, espace enfant, séance : consigne, automatismes, clavier) sans débordement
  horizontal, compteur de poissons entièrement visible, Kono qui ne prend pas plus du quart de la hauteur, toutes les cibles
  tactiles de 44 px au moins (sauf les cases de la ligne des nombres, contiguës par nature). Captures dans $SHOTS.
- Réglages d'affichage (1280 × 800) : main gauche (clavier et flèche à gauche, Kono à droite), moins d'animations (Kono immobile),
  contraste renforcé (texte noir) ; posés depuis l'espace parent, gardés après rechargement.
- Lecteur d'écran : sur chaque écran visité, tout bouton, champ ou image visible a un nom (texte, aria-label, étiquette ou alt).

Lancer : python3 tests/ecrans.py      (démarre et arrête lui-même un serveur sur le port 8770)
"""
import asyncio, os, pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from ecole_test import ecole_test, CODE
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent; APP = ROOT / "app"
SHOTS = os.environ.get("SHOTS", "/tmp/corridor-tests/"); os.makedirs(SHOTS, exist_ok=True)
URL = "http://localhost:8770/#test"; PIN = "1234"
fails = []
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)

NAMES = r"""() => { const out = []; const vis = el => !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  const nameOf = el => (el.getAttribute('aria-label') || el.getAttribute('title') || (el.labels && [...el.labels].map(l => l.textContent).join(' ')) || (el.closest('label') ? el.closest('label').textContent : '') || el.textContent || el.getAttribute('placeholder') || '').replace(/\s+/g, ' ').trim();
  document.querySelectorAll('button, [role=button], input:not([type=hidden]), select, textarea').forEach(el => { if (vis(el) && !nameOf(el)) out.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).join('.') : '')); });
  document.querySelectorAll('img').forEach(i => { if (vis(i) && i.getAttribute('alt') == null) out.push('img sans alt ' + (i.getAttribute('src') || '')); });
  document.querySelectorAll('svg[role=img]').forEach(s => { if (!s.getAttribute('aria-label')) out.push('svg role=img sans aria-label'); });
  return out; }"""
PHONE = r"""() => { const W = innerWidth, H = innerHeight; const out = { overflow: document.documentElement.scrollWidth > W + 1, small: [], clipped: [], kono: 0 };
  const vis = el => !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  document.querySelectorAll('button, [role=button]').forEach(el => { if (!vis(el) || el.classList.contains('hit')) return; const r = el.getBoundingClientRect(); if (r.width < 44 || r.height < 44) out.small.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}.${[...el.classList].join('.')} ${Math.round(r.width)}×${Math.round(r.height)}`); });
  ['#catch', '.c-count', '#next:not([hidden])', '.icon-btn'].forEach(sel => document.querySelectorAll(sel).forEach(el => { if (!vis(el)) return; const r = el.getBoundingClientRect(); if (r.left < 0 || r.right > W + 0.5 || r.width < 20) out.clipped.push(`${sel} ${Math.round(r.left)}..${Math.round(r.right)} / ${W}`); }));
  const k = document.querySelector('.kono-btn .kono'); if (k) out.kono = +(k.getBoundingClientRect().height / H).toFixed(3);
  return out; }"""
STATE = "() => { const P = window.__kono.P(); if (!P) return null; const st = P.steps[P.i]; const n = document.querySelector('#next'); return { i: P.i, t: st && st.type, a: st && st.answer, next: n && !n.hidden ? n.dataset.mode : null }; }"
DRILL_JS = r"""() => { const e = document.querySelector('.drill .v-expr'); if (!e) return null; const q = e.textContent.trim(); let m;
  if ((m = q.match(/^(\d+) \+ \? = (\d+)$/))) return +m[2] - +m[1]; if ((m = q.match(/^(\d+) \+ (\d+)$/))) return +m[1] + +m[2];
  if ((m = q.match(/^le double de (\d+)$/))) return 2 * +m[1]; if ((m = q.match(/^(\d+) × (\d+)$/))) return +m[1] * +m[2]; return null; }"""

async def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8770", "--directory", str(APP)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1); names = {}
    async def audit(pg, screen):
        v = await pg.evaluate(NAMES)
        if v: names[screen] = v
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
            errs = []
            # ---------------- téléphone 360 × 640
            ctx = await b.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True, device_scale_factor=2, permissions=["microphone"])
            pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
            async def typ(v):
                for ch in str(v): await pg.click(f"#answer [data-k='{ch}']")
                await pg.click("#answer [data-k='ok']")
            async def phone(tag):
                r = await pg.evaluate(PHONE); await pg.screenshot(path=f"{SHOTS}tel-360x640-{tag}.png")
                check(f"téléphone · {tag} : pas de débordement, rien de tronqué, cibles ≥ 44 px" + (", Kono ≤ 25 % de la hauteur" if r["kono"] else ""),
                      not r["overflow"] and not r["clipped"] and not r["small"] and r["kono"] <= 0.25, f"débordement={r['overflow']} tronqué={r['clipped']} petits={r['small'][:4]} kono={r['kono']}")
            await pg.goto(URL); await pg.wait_for_selector("#code"); await audit(pg, "code d'inscription"); await phone("code")
            await pg.fill("#code", CODE); await pg.click("#go"); await pg.wait_for_selector("#pin"); await audit(pg, "réglage parent")
            await pg.fill("#pin", PIN); await pg.click("#go"); await pg.wait_for_selector("#p-name"); await audit(pg, "profil")
            await pg.fill("#p-name", "Ali"); await pg.fill("#p-dob", "2019-03-15"); await pg.click("[data-p='ce1']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            await audit(pg, "accueil"); await phone("accueil")
            await pg.click(".kid[data-c]"); await pg.wait_for_selector(".tickets"); await pg.wait_for_timeout(300); await audit(pg, "espace enfant"); await phone("enfant")
            # carte : le Bani et Djenné (losange plein, pas un cercle d'escale), noms des fleuves lisibles ; billets : titre sur 3 lignes au plus
            carte = await pg.evaluate("""() => { const m = document.querySelector('.map'); const t = m.innerText; const lab = [...m.querySelectorAll('text')].filter(x => /Niger|Bani/.test(x.textContent));
              const fs = lab.map(x => x.getBoundingClientRect().height); const dj = m.querySelector('.bani rect.ville'); const cercles = m.querySelectorAll('.escales circle').length;
              const titres = [...document.querySelectorAll('.ticket .t-title')].map(x => ({ t: x.textContent, lignes: Math.round(x.getBoundingClientRect().height / parseFloat(getComputedStyle(x).lineHeight)) }));
              return { bani: !!m.querySelector('.bani path'), djenne: /Djenn/.test(t) && !!dj, noms: lab.length, hauteurMin: Math.min(...fs), escales: cercles, titres }; }""")
            check("carte : le Bani dessiné, Djenné en losange plein (pas une escale), les deux fleuves nommés et lisibles (≥ 12 px à l'écran), 5 cercles d'escale", carte["bani"] and carte["djenne"] and carte["noms"] == 2 and carte["hauteurMin"] >= 12 and carte["escales"] == 5, str({k: v for k, v in carte.items() if k != 'titres'}))
            check("billets : chaque titre de séance tient sur 3 lignes au plus", all(x["lignes"] <= 3 for x in carte["titres"]), str(carte["titres"]))
            await pg.click("#today .boat-btn"); await pg.wait_for_selector("#stage"); await pg.wait_for_timeout(300)
            seen = set(); guard = 0
            while guard < 400 and len(seen) < 3:
                guard += 1; await pg.wait_for_timeout(50); s = await pg.evaluate(STATE)
                if s is None: break
                if s["t"] == "say" and "consigne" not in seen and s["next"]: seen.add("consigne"); await audit(pg, "séance : consigne"); await phone("seance-consigne")
                if s["t"] == "drill":
                    if await pg.is_visible("#go"):
                        if "intro" not in seen: seen.add("intro"); await audit(pg, "séance : automatismes"); await phone("seance-automatismes")
                        await pg.click("#go"); continue
                    if await pg.is_visible("#answer .keypad"):
                        if "clavier" not in seen: seen.add("clavier"); await audit(pg, "séance : clavier"); await phone("seance-clavier")
                        ans = await pg.evaluate(DRILL_JS)
                        if ans is not None: await typ(ans); await pg.wait_for_timeout(60)
                        continue
                if s["next"]: await pg.click("#next"); continue
            check("téléphone : consigne, automatismes et clavier atteints dans la séance", seen == {"consigne", "intro", "clavier"}, str(seen))
            await pg.click("#quit"); await pg.wait_for_selector("#qa-leave"); await audit(pg, "séance : arrêter ?"); await pg.click("#qa-leave"); await pg.wait_for_selector(".tickets")
            await pg.click("#back"); await pg.wait_for_selector(".kids"); await pg.click("#parent"); await pg.wait_for_selector(".pin"); await audit(pg, "code parent")
            for ch in PIN: await pg.click(f"[data-k='{ch}']")
            await pg.wait_for_selector("#pane"); await pg.wait_for_timeout(300)
            for t in ("suivi", "maman", "kono", "rapport", "reglages"):
                await pg.click(f"[data-t='{t}']"); await pg.wait_for_timeout(350); await audit(pg, f"espace parent : {t}")
            await pg.screenshot(path=f"{SHOTS}tel-360x640-parent-reglages.png")
            await ctx.close()
            # ---------------- réglages d'affichage, 1280 × 800
            ctx = await b.new_context(viewport={"width": 1280, "height": 800}, permissions=["microphone"]); pg = await ctx.new_page(); pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
            await pg.goto(URL); await pg.wait_for_selector("#code"); await pg.fill("#code", CODE); await pg.click("#go"); await pg.wait_for_selector("#pin")
            await pg.fill("#pin", PIN); await pg.click("#go"); await pg.wait_for_selector("#p-name"); await pg.fill("#p-name", "Awa"); await pg.fill("#p-dob", "2021-02-10"); await pg.click("[data-p='ce1']"); await pg.click("#go"); await pg.wait_for_selector(".kids")
            await pg.click("#parent")
            for ch in PIN: await pg.click(f"[data-k='{ch}']")
            await pg.wait_for_selector("#pane"); await pg.click("[data-t='kono']"); await pg.wait_for_selector("#st-gauch")
            await pg.click("#st-gauch"); await pg.click("#st-calme"); await pg.click("#st-contr"); await pg.wait_for_timeout(100)
            cls = await pg.evaluate("[...document.body.classList]"); stored = await pg.evaluate("JSON.parse(localStorage.getItem('kono-v1')).settings")
            check("réglages : main gauche, moins d'animations, contraste posés depuis l'espace parent et enregistrés", all(c in cls for c in ("gaucher", "calme", "contraste")) and stored["gaucher"] and stored["calme"] and stored["contraste"], str(cls))
            await pg.reload(); await pg.wait_for_selector(".kids"); cls = await pg.evaluate("[...document.body.classList]")
            check("réglages : gardés après rechargement", all(c in cls for c in ("gaucher", "calme", "contraste")), str(cls))
            color = await pg.evaluate("getComputedStyle(document.body).color"); anim = await pg.evaluate("getComputedStyle(document.querySelector('.kono .k-body')).animationName")
            check("contraste renforcé : texte noir · moins d'animations : Kono immobile", color == "rgb(0, 0, 0)" and anim == "none", f"couleur {color}, animation {anim}")
            await pg.screenshot(path=f"{SHOTS}reglages-contraste-accueil.png")
            await pg.click(".kid[data-c]"); await pg.wait_for_selector(".tickets"); await pg.click("#today .boat-btn"); await pg.wait_for_selector("#stage")
            got = {}; guard = 0
            while guard < 400 and len(got) < 2:
                guard += 1; await pg.wait_for_timeout(50); s = await pg.evaluate(STATE)
                if s is None: break
                if s["t"] == "say" and s["next"] and "fleche" not in got:
                    got["fleche"] = await pg.evaluate("() => { const n = document.querySelector('#next').getBoundingClientRect(), k = document.querySelector('.guide').getBoundingClientRect(), w = document.querySelector('#work').getBoundingClientRect(); return { nextLeft: n.left < innerWidth / 2, konoRight: k.left > w.left }; }")
                    await pg.screenshot(path=f"{SHOTS}reglages-gaucher-consigne.png")
                if s["t"] == "drill":
                    if await pg.is_visible("#go"): await pg.click("#go"); continue
                    if await pg.is_visible("#answer .keypad"):
                        if "clavier" not in got:
                            got["clavier"] = await pg.evaluate("() => { const a = document.querySelector('#answer').getBoundingClientRect(), s = document.querySelector('#stage').getBoundingClientRect(); return { padLeft: a.left < s.left }; }")
                            await pg.screenshot(path=f"{SHOTS}reglages-gaucher-clavier.png")
                        ans = await pg.evaluate(DRILL_JS)
                        if ans is not None: await typ(ans); await pg.wait_for_timeout(60)
                        continue
                if s["next"]: await pg.click("#next"); continue
            check("main gauche : la flèche à gauche, Kono à droite de la zone de travail", got.get("fleche", {}).get("nextLeft") and got.get("fleche", {}).get("konoRight"), str(got.get("fleche")))
            check("main gauche : le clavier à gauche du dessin", got.get("clavier", {}).get("padLeft"), str(got.get("clavier")))
            await audit(pg, "séance (réglages)")
            await ctx.close(); await b.close()
            for scr, v in names.items(): check(f"lecteur d'écran · {scr} : chaque bouton, champ et image a un nom", False, ", ".join(v[:6]))
            if not names: check("lecteur d'écran : sur tous les écrans visités, chaque bouton, champ et image a un nom", True)
            check("aucune erreur JavaScript", not errs, "\n".join(errs)[:300])
    finally:
        if srv.poll() is None: srv.terminate()
    print("ÉCRANS :", "OK" if not fails else "ÉCHEC : " + " ; ".join(fails))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    with ecole_test():
        asyncio.run(main())
