# -*- coding: utf-8 -*-
"""Relecture d'une semaine avant publication, pour l'adulte qui relit (enseignant, fondateur).

Pour chaque séance de la semaine, dans l'ordre exact de la tablette : ce que Kono dit, ce que l'enfant voit (dessins
rendus comme sur les fiches), ce qu'il doit répondre, les erreurs expliquées, les aides, la fiche papier et la carte Maman.
Puis les contrôles : check_lessons (bloquant), et des avertissements : compétence absente de la progression, image absente
ou non préchargée, question sans erreur expliquée, escale vide, phrases sans fichier audio.

Usage : python3 tools/build_review.py S1 [--pdf]   -> print/Relecture_S1.html (et .pdf avec --pdf, Playwright requis)
Rend 0 si check_lessons rend 0, 1 sinon. Les avertissements n'empêchent rien : ils sont là pour être lus."""
import json, pathlib, re, subprocess, sys, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
sys.path.insert(0, str(ROOT / "tools"))
import build_print as bp   # mêmes dessins que les fiches : tenframe, numberline, blocks_svg, bar_svg, icon

WEEK = next((a for a in sys.argv[1:] if not a.startswith("--")), "S1")
PDF = "--pdf" in sys.argv
esc = lambda s: html.escape(str(s if s is not None else ""))
PRENOM = {"gs": "Awa", "ce1": "Ali"}

def key_of(t):
    """Même clé que app.js et build_audio.py : FNV-1a sur la phrase normalisée."""
    s = re.sub(r"\s+", " ", str(t or "").replace("«", "").replace("»", "").replace("★", " étoile ")).strip()
    h = 0x811c9dc5
    for b in s.encode("utf-8"): h ^= b; h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"
def sentences(t): return [p.strip() for p in re.findall(r"[^.!?…]+[.!?…]*", str(t or "").replace("«", "").replace("»", "").replace("★", " étoile ")) if p.strip()]

def fill(t, L): return str(t or "").replace("{prenom}", PRENOM.get(L["parcours"], "Awa")).replace("{e}", "e")
def said(st, L): return fill(st.get("say") or st.get("text") or "", L)

def show_html(v, warn, L):
    k = v.get("kind")
    if k == "title": return f"<div class='vt'>{esc(fill(v.get('text'), L))}</div>"
    if k == "expr": return f"<div class='vx'>{esc(v.get('text'))}</div>"
    if k == "text": return f"<div>{esc(v.get('text'))}</div>"
    if k == "word": return f"<div class='vw'>{esc(v.get('text'))}</div>"
    if k == "part": return f"<div class='vt'>Temps {esc(v.get('n'))} · {esc(v.get('title'))}</div>"
    if k == "maman": return "<div class='pill'>♥ Maman</div>"
    if k == "listen": return "<div class='pill'>👂 écoute</div>"
    if k == "tenframe": return bp.tenframe(int(v.get("filled", 0)), 22) + (" <span class='small'>cases vides en surbrillance</span>" if v.get("highlightEmpty") else "")
    if k == "numberline": return bp.numberline(v["from"], v["to"], marks=v.get("marks", ()), jumps=v.get("jumps", ()), w=360, top=26)
    if k == "blocks": return bp.blocks_svg(v.get("h", 0), v.get("t", 0), v.get("u", 0), c=6, regroup=bool(v.get("regroup"))) + (" <span class='small'>fermeture animée</span>" if v.get("regroup") else "")
    if k == "bar": return bp.bar_svg(v, w=300)
    if k == "fingers": return f"<div class='pill'>✋ {esc(v.get('up'))} doigt(s) levé(s)</div>"
    if k == "split": return f"<div class='pill'>{esc(v.get('whole'))} = {esc(' + '.join(str(p) for p in v.get('parts', [])))}</div>"
    if k in ("items", "hidden"):
        n = int(v.get("visible", v.get("n", 0)))
        out = "<div class='row'>" + bp.icon(check_img(v.get("item", "mangue"), warn), 26) * n + (f" + {bp.icon(check_img('calebasse', warn), 34)} <span class='small'>({v.get('total')} en tout, {int(v['total']) - n} cachée(s))</span>" if k == "hidden" else "") + "</div>"
        return out
    if k == "icon": return f"<div class='row'>{bp.icon(check_img(v.get('name'), warn), 40)} <span class='small'>{esc(v.get('name'))}</span></div>"
    if k == "syllables": return f"<div class='row'>{bp.icon(check_img(v.get('name'), warn), 40)} {'○ ' * int(v.get('n', 0))} <span class='small'>({v.get('n')} syllabes)</span></div>"
    if k == "scenes": return f"<div class='pill'>images de l'histoire : {esc(', '.join(v.get('scenes', [])))}</div>"
    if k == "none": return ""
    return f"<div class='pill'>{esc(k)} {esc(json.dumps({a: b for a, b in v.items() if a != 'kind'}, ensure_ascii=False))}</div>"

SW_CORE = set(re.findall(r"'img/([a-z0-9-]+)\.svg'", (APP / "sw.js").read_text(encoding="utf-8")))
def check_img(name, warn):
    if not (APP / "img" / f"{name}.svg").exists(): warn.append(f"image absente : img/{name}.svg")
    elif name not in SW_CORE: warn.append(f"image non préchargée par sw.js : img/{name}.svg")
    return name if (APP / "img" / f"{name}.svg").exists() else "mangue"

def errors_html(st, L):
    e = st.get("errors") or {}
    if not e: return "<span class='warnc'>aucune erreur expliquée</span>"
    return "<ul class='err'>" + "".join(f"<li><b>{esc(k)}</b> → {esc(fill(v if isinstance(v, str) else v.get('text', ''), L))}{' <span class=small>(animation : ' + esc(', '.join(x.get('kind', '') for x in v.get('show', []))) + ')</span>' if isinstance(v, dict) and v.get('show') else ''}</li>" for k, v in e.items()) + "</ul>"

def question_row(n, st, L, warn, origin=""):
    t = st["type"]
    if t in ("number", "choice"):
        ans = f"<b>{esc(st.get('answer'))}</b>" + (f" · options : {esc(' | '.join(str(o) for o in st.get('options', [])))}" + (f" ({esc(st.get('optionKind'))})" if st.get("optionKind") else "") if t == "choice" else " · clavier")
        if t == "choice" and str(st.get("answer")) not in [str(o) for o in st.get("options", [])]: warn.append(f"{st.get('id')} : la réponse n'est pas parmi les options")
        if not (st.get("errors") or {}): warn.append(f"{st.get('id') or 'question'} : aucune erreur expliquée")
    elif t == "manip":
        m = st.get("mode")
        if m == "tenframe": ans = f"boîte de dix, départ {esc(st.get('start', 0))} jeton(s), but <b>{esc(st.get('goal'))}</b>, réponse <b>{esc(st.get('answer'))}</b>"
        elif m == "jumps": ans = f"sauts de {esc(st.get('from'))} à {esc(st.get('to'))}, départ {esc(st.get('start'))}, passage obligé par <b>{esc(st.get('via'))}</b>, arrivée <b>{esc(st.get('answer'))}</b>"
        else: ans = f"blocs : {esc(st.get('h', 0))} c, {esc(st.get('t', 0))} d, {esc(st.get('u', 0))} u" + (f" + {esc(st.get('add'))} u à poser" if st.get("add") else "") + f" → réponse <b>{esc(st.get('answer'))}</b>" + (" · centaines" if st.get("hundreds") else "")
    else: ans = ""
    shows = "".join(show_html(v, warn, L) for v in st.get("show", []) if isinstance(v, dict))
    after = "".join(show_html(v, warn, L) for v in st.get("after", []) if isinstance(v, dict))
    hints = "<br>".join(esc(fill(h, L)) for h in st.get("hints", []))
    return f"<tr><td class='n'>{n}</td><td>{esc(t)}{(' · ' + esc(st.get('mode'))) if t == 'manip' else ''}<br><span class='small muted'>{esc(st.get('id', ''))}{(' · ' + esc(origin)) if origin else ''}</span></td><td>{esc(said(st, L))}{('<br><span class=small>ask : ' + esc(fill(st.get('ask'), L)) + '</span>') if st.get('ask') else ''}</td><td>{shows}{('<div class=small>après : ' + after + '</div>') if after else ''}</td><td>{ans}</td><td>{errors_html(st, L)}{('<div class=small><b>aide :</b> ' + hints + '</div>') if hints else ''}{('<div class=small><b>sol :</b> ' + esc(fill(st.get('sol'), L)) + '</div>') if st.get('sol') else ''}</td><td class='small'>{esc(st.get('skill', ''))}</td></tr>"

def lesson_html(L, idx_entry, prog, audio, warn):
    skills = prog.get("skills", []); codes = {s["code"]: s["label"] for s in skills}
    for c in L.get("skills", []):
        if c not in codes: warn.append(f"compétence {c} absente de progression/{L['parcours']}.json")
    rows, n, missing, total = [], 0, 0, 0
    def count_voice(t):
        nonlocal missing, total
        for s in sentences(t):
            total += 1
            if key_of(s) not in audio: missing += 1
    for st in L["steps"]:
        t = st["type"]; n += 1
        if t == "maman": rows.append(f"<tr><td class='n'>{n}</td><td>maman</td><td colspan='5'>phrase de Maman « {esc(st.get('clip'))} » si elle est enregistrée, sinon Kono</td></tr>")
        elif t == "part": rows.append(f"<tr class='part'><td class='n'>{n}</td><td>temps {esc(st.get('n'))}</td><td colspan='5'><b>{esc(st.get('title'))}</b> · {esc(said(st, L))}</td></tr>"); count_voice(st.get("text"))
        elif t == "say": rows.append(f"<tr><td class='n'>{n}</td><td>say</td><td>{esc(said(st, L))}</td><td>{''.join(show_html(v, warn, L) for v in st.get('show', []))}</td><td colspan='3'></td></tr>"); count_voice(st.get("say") or st.get("text"))
        elif t == "demo":
            for j, ln in enumerate(st.get("lines", [])):
                rows.append(f"<tr><td class='n'>{n}{'' if j == 0 else ''}</td><td>demo {j + 1}/{len(st['lines'])}</td><td>{esc(said(ln, L))}</td><td>{''.join(show_html(v, warn, L) for v in ln.get('show', []))}</td><td colspan='3'></td></tr>"); count_voice(ln.get("say") or ln.get("text"))
        elif t in ("number", "choice", "manip"): rows.append(question_row(n, st, L, warn)); count_voice(st.get("say") or st.get("text"))
        elif t == "review":
            rows.append(f"<tr><td class='n'>{n}</td><td>review</td><td colspan='5'>défis de la file de révision de l'enfant (max {esc(st.get('max', 2))}{', complétés' if st.get('fill') else ''}) ; sinon, les défis de secours ci-dessous :</td></tr>")
            for fb in st.get("fallback", []): rows.append(question_row("", fb, L, warn, "secours")); count_voice(fb.get("say") or fb.get("text"))
        elif t == "drill":
            kinds = ", ".join(f"{k.get('kind')} (poids {k.get('w', 1)}{', n ' + str(k.get('n')) if k.get('n') else ''})" for k in st.get("kinds", []))
            rows.append(f"<tr><td class='n'>{n}</td><td>drill<br><span class='small muted'>{esc(st.get('id'))}</span></td><td>{esc(said(st, L))}</td><td class='small'>{esc(kinds)}</td><td>{esc(st.get('count'))} questions en {esc(st.get('seconds'))} s · saisie {esc(st.get('input', 'keypad'))}</td><td colspan='2' class='small'>questions tirées au sort, erreurs revues sans chronomètre</td></tr>"); count_voice(st.get("text"))
        elif t == "paper":
            rows.append(f"<tr><td class='n'>{n}</td><td>paper</td><td>{esc(said(st, L))}</td><td colspan='4'>fiche « {esc(L['paper'].get('title'))} » (ci-dessous)</td></tr>"); count_voice(st.get("say") or st.get("text"))
        elif t == "reading":
            words = len([w for w in " ".join(st.get("passage", [])).split() if re.search(r"[\w]", w)])
            rows.append(f"<tr><td class='n'>{n}</td><td>reading<br><span class='small muted'>{esc(st.get('id'))}</span></td><td>Kono lit, puis l'enfant lit à voix haute et s'enregistre{' (relecture)' if st.get('reread') else ''}</td><td colspan='4'><b>{esc(st.get('title'))}</b> · {len(st.get('passage', []))} phrases, {words} mots<br>{esc(' '.join(st.get('passage', [])))}</td></tr>")
            for s in st.get("passage", []): count_voice(s)
        elif t == "story":
            rows.append(f"<tr><td class='n'>{n}</td><td>story<br><span class='small muted'>{esc(st.get('id'))} · écoute {esc(st.get('pass', 1))}</span></td><td>{'(écoute sautée) ' if st.get('skipListen') else 'Kono raconte sans images'}{' · sans vocabulaire' if st.get('skipVocab') else ''}{' · sans images après' if st.get('noImages') else ''}{' · remise en ordre des images' if st.get('order') else ''}</td><td colspan='4'><b>{esc(st.get('title'))}</b> · {len(st.get('sentences', []))} phrases<br>{esc(' '.join(st.get('sentences', [])))}</td></tr>")
            for s in st.get("sentences", []): count_voice(s)
            if not st.get("skipVocab"):
                for v in st.get("vocab", []): rows.append(f"<tr><td></td><td>vocabulaire</td><td>{esc(fill(v.get('say'), L))}</td><td><div class='vw'>{esc(v.get('word'))}</div></td><td colspan='3'></td></tr>"); count_voice(v.get("say"))
            for q in st.get("questions", []): rows.append(question_row("", q, L, warn, "question d'histoire")); count_voice(q.get("say") or q.get("text"))
            rows.append(f"<tr><td></td><td>record · récit</td><td>{esc(fill(st.get('retell'), L))}</td><td>{'images : ' + esc(', '.join(st.get('scenes', []))) if not st.get('noImages') else 'sans images'}</td><td colspan='3'>l'enfant raconte, un parent note le récit (6 points)</td></tr>"); count_voice(st.get("retell"))
        elif t == "record": rows.append(f"<tr><td class='n'>{n}</td><td>record · {esc(st.get('kind', 'methode'))}</td><td>{esc(said(st, L))}</td><td>{''.join(show_html(v, warn, L) for v in st.get('show', []))}</td><td colspan='3'>enregistrement écouté par le parent</td></tr>"); count_voice(st.get("say") or st.get("text"))
        elif t == "order": rows.append(question_row(n, st, L, warn))
        elif t == "end": rows.append(f"<tr><td class='n'>{n}</td><td>end</td><td colspan='5'>poissons, carte, phrase de Maman « {esc(st.get('clip'))} »</td></tr>")
        else: rows.append(f"<tr><td class='n'>{n}</td><td>{esc(t)}</td><td colspan='5' class='warnc'>type non rendu par cette relecture</td></tr>")
    paper = L.get("paper", {}); P = []
    P.append(f"<p><b>Modèle :</b> {esc(paper.get('model', ''))}</p><div>{bp.model_visual(L) if paper.get('levels') else ''}</div>")
    for lv in paper.get("levels", []):
        P.append(f"<p><b>{'★' * int(lv.get('stars', 1))}</b> {esc(lv.get('ins'))} <span class='small muted'>({esc(lv.get('who'))})</span></p><table class='t'><tr><th>n°</th><th>énoncé</th><th>réponse</th><th>erreurs expliquées</th></tr>")
        for it in lv.get("items", []):
            P.append(f"<tr><td>{esc(it.get('id'))}</td><td>{esc(it.get('q'))}{(' <span class=small muted>(' + esc(it.get('short')) + ')</span>') if it.get('short') else ''}</td><td><b>{esc(it.get('answer', '')) if 'answer' in it else 'libre'}</b></td><td>{errors_html(it, L) if 'answer' in it else ''}</td></tr>")
            for s in [it.get("q")] + [e if isinstance(e, str) else e.get("text", "") for e in (it.get("errors") or {}).values()]: count_voice(s)
        P.append("</table>")
    mam = "".join(f"<li>{esc(m)}</li>" for m in paper.get("maman", []))
    head = f"<h2 id='{esc(L['id'])}'>{esc(idx_entry.get('day', '')).capitalize()} · {esc(L['title'])} <span class='small muted'>· {esc(L['id'])} · parcours {esc(L['parcours'])} · {esc(L.get('domain'))} · escale {esc(L.get('escale'))}</span></h2>"
    comp = " · ".join(f"<b>{esc(c)}</b> {esc(codes.get(c, '?'))}" for c in L.get("skills", []))
    meta = f"<p><b>Programme :</b> {esc(L.get('programme'))}<br><b>Objectif :</b> {esc(L.get('objective'))}<br><b>Compétences :</b> {comp}<br><b>Voix :</b> {total - missing} phrase(s) sur {total} ont un fichier audio{' <span class=warnc>(' + str(missing) + ' manquantes : synthèse de la tablette)</span>' if missing else ''}</p>"
    table = "<table class='t'><tr><th>n°</th><th>type</th><th>Kono dit</th><th>l'enfant voit</th><th>réponse attendue</th><th>erreurs expliquées · aides · solution</th><th>compétence</th></tr>" + "".join(rows) + "</table>"
    return head + meta + table + f"<h3>Fiche papier « {esc(paper.get('title'))} »</h3>" + "".join(P) + f"<h3>Carte Maman</h3><ul>{mam}</ul>", missing, total

CSS = bp.face("Andika", "andika-400.woff2", 400) + bp.face("Andika", "andika-700.woff2", 700) + bp.face("Nunito", "nunito-800.woff2", 800) + """
body{font-family:Andika,sans-serif;color:#1b2430;margin:16px;font-size:11.5px;line-height:1.35}h1{font-family:Nunito;margin:0}h2{font-family:Nunito;margin:26px 0 6px;border-bottom:3px solid #2f7ea6;padding-bottom:3px;font-size:17px}
h3{font-family:Nunito;margin:14px 0 4px;font-size:13px}table.t{border-collapse:collapse;width:100%}table.t th,table.t td{border:1px solid #d7cfbd;padding:4px 5px;vertical-align:top;text-align:left}table.t th{background:#f3ebdb;font-size:10.5px}
td.n{text-align:center;color:#888}tr.part td{background:#eef5f9}.small{font-size:10px}.muted{color:#5f6b70}.vt{font-family:Nunito;font-size:14px;color:#2f7ea6}.vx{font-family:Nunito;font-size:18px}.vw{font-family:Nunito;font-size:14px;background:#f3ebdb;border-radius:8px;padding:2px 8px;display:inline-block}
.pill{display:inline-block;background:#eef5f9;border-radius:99px;padding:1px 8px;margin:1px 0}.row{display:flex;flex-wrap:wrap;gap:2px;align-items:center}ul.err{margin:0;padding-left:16px}.warnc{color:#a31226;font-weight:700}
.box{border:1.5px solid #d7cfbd;border-radius:10px;padding:8px 12px;margin:8px 0}.ok{color:#2c8554;font-weight:700}@media print{h2{break-before:page}body{margin:8mm}}"""

def main():
    idx = json.loads((APP / "lessons" / "index.json").read_text(encoding="utf-8"))
    entries = sorted([l for l in idx["lessons"] if l.get("week") == WEEK], key=lambda l: (list(bp.PARCOURS).index(l["parcours"]) if l["parcours"] in bp.PARCOURS else 9, l["order"]))
    if not entries: print(f"aucune séance de la semaine {WEEK} dans l'index"); return 1
    try: audio = set(json.loads((APP / "audio" / "manifest.json").read_text(encoding="utf-8")).get("files", {}).keys())
    except Exception: audio = set()
    prog = {p: json.loads((APP / "progression" / f"{p}.json").read_text(encoding="utf-8")) if (APP / "progression" / f"{p}.json").exists() else {"skills": []} for p in bp.PARCOURS}
    chk = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "check_lessons.py")], capture_output=True, text=True, encoding="utf-8")
    warn_all, parts, summary, tot_missing, tot_total = [], [], [], 0, 0
    for e in entries:
        L = json.loads((APP / "lessons" / f"{e['id']}.json").read_text(encoding="utf-8")); warn = []
        h, missing, total = lesson_html(L, L, prog[L["parcours"]], audio, warn)
        nq = sum(1 for s in L["steps"] if s["type"] in ("number", "choice", "manip")) + sum(len(s.get("questions", [])) for s in L["steps"] if s["type"] == "story")
        summary.append(f"<tr><td><a href='#{esc(L['id'])}'>{esc(L['title'])}</a></td><td>{esc(L['parcours'])}</td><td>{esc(L.get('day', ''))}</td><td>{esc(L.get('domain'))}</td><td class='n'>{len(L['steps'])}</td><td class='n'>{nq}</td><td class='n'>{len(L.get('paper', {}).get('levels', []))}</td><td class='n'>{total - missing} / {total}</td><td>{'<span class=warnc>' + str(len(warn)) + '</span>' if warn else '<span class=ok>0</span>'}</td></tr>")
        if warn: h += "<div class='box'><b>Avertissements :</b><ul>" + "".join(f"<li>{esc(w)}</li>" for w in sorted(set(warn))) + "</ul></div>"
        warn_all += [f"{L['id']} : {w}" for w in sorted(set(warn))]; parts.append(h); tot_missing += missing; tot_total += total
    for pid, esc_list in (idx.get("escales") or {}).items():
        for k, es in enumerate(esc_list[:-1]):
            if not es.get("sessions"): warn_all.append(f"index : escale « {es.get('name')} » du parcours {pid} à 0 séance (elle ne sera jamais atteinte)")
    ok = chk.returncode == 0
    ctrl = f"<div class='box'><b>check_lessons.py :</b> {'<span class=ok>0 erreur, publication possible</span>' if ok else '<span class=warnc>ERREURS, publication refusée</span>'}<pre class='small'>{esc(chk.stdout.strip() or chk.stderr.strip())}</pre>" + (f"<b>Avertissements ({len(warn_all)}) :</b><ul>" + "".join(f"<li>{esc(w)}</li>" for w in warn_all) + "</ul>" if warn_all else "<b>Aucun avertissement.</b>") + "</div>"
    doc = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Relecture {esc(WEEK)}</title><style>{CSS}</style></head><body>
<h1>Corridor à la maison · relecture de la semaine {esc(WEEK)}</h1><p class='muted'>Généré depuis les fichiers de leçon, dans l'ordre exact de la tablette. Le prénom est remplacé par Awa (GS) ou Ali (CE1). Index version {esc(idx.get('version'))}.</p>
<h2>Vue d'ensemble</h2><table class='t'><tr><th>Séance</th><th>Parcours</th><th>Jour</th><th>Domaine</th><th>Étapes</th><th>Questions</th><th>Niveaux de fiche</th><th>Voix (fichiers / phrases)</th><th>Avertissements</th></tr>{''.join(summary)}</table>
<h2>Contrôles</h2>{ctrl}{''.join(parts)}</body></html>"""
    out = ROOT / "print" / f"Relecture_{WEEK}.html"; out.parent.mkdir(exist_ok=True); out.write_text(doc, encoding="utf-8")
    print(f"{len(entries)} séance(s) de {WEEK} · check_lessons : {'0' if ok else chk.returncode} · {len(warn_all)} avertissement(s) · voix : {tot_total - tot_missing} / {tot_total} phrases avec fichier · {out.relative_to(ROOT)}")
    for w in warn_all: print("  AVERTISSEMENT :", w)
    if PDF:
        import asyncio
        from playwright.async_api import async_playwright
        async def pdf():
            async with async_playwright() as p:
                b = await p.chromium.launch(); pg = await b.new_page(); await pg.goto(out.as_uri()); await pg.evaluate("document.fonts.ready")
                await pg.pdf(path=str(out.with_suffix(".pdf")), format="A4", landscape=True, print_background=True, margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"}); await b.close()
        asyncio.run(pdf()); print("PDF :", out.with_suffix(".pdf").relative_to(ROOT))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
