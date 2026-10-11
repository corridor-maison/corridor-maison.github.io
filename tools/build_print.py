# -*- coding: utf-8 -*-
"""Fiches imprimables de Corridor à la maison, générées depuis les MÊMES fichiers de leçon que la tablette.
Usage : python3 tools/build_print.py S1   -> print/Fiches_S1.pdf
"""
import asyncio, base64, json, pathlib, sys, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
WEEK = sys.argv[1] if len(sys.argv) > 1 else "S1"
esc = lambda s: html.escape(str(s))

def face(fam, f, w):
    b = base64.b64encode((APP / "fonts" / f).read_bytes()).decode()
    return f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b}) format('woff2');font-weight:{w}}}"

BLEU, ORANGE = "#1c5aa6", "#c35713"
CSS = face("Andika", "andika-400.woff2", 400) + face("Andika", "andika-700.woff2", 700) + face("Nunito", "nunito-800.woff2", 800) + f"""
@page {{ size: A4; margin: 0 }} * {{ box-sizing: border-box }} body {{ margin: 0; font-family: Andika, sans-serif; color: #1b2430; -webkit-print-color-adjust: exact; print-color-adjust: exact }}
.page {{ width: 210mm; height: 297mm; padding: 11mm 13mm 12mm; position: relative; overflow: hidden; break-after: page }}
.page:last-child {{ break-after: auto }}
.band {{ display: flex; justify-content: space-between; align-items: center; border-radius: 12px; padding: 7px 14px; color: #fff; font-family: Nunito }}
.band b {{ font-size: 15pt }} .band .what {{ font-size: 11pt; font-weight: 800 }}
.band .pr {{ background: #fff; color: #333; border-radius: 8px; padding: 5px 10px; font-size: 10.5pt; min-width: 58mm; font-weight: 800 }}
h1 {{ font-size: 20pt; margin: 3.5mm 0 0 }}
.model {{ border: 2px dashed #b9b9b3; border-radius: 12px; padding: 3mm 5mm; margin-top: 3mm; font-size: 13pt; display: flex; align-items: center; gap: 5mm }}
.lv {{ border: 1.6px solid #cfcfca; border-radius: 12px; padding: 2.5mm 4mm; margin-top: 2.8mm }}
.lvh {{ display: flex; align-items: center; gap: 8px; font-weight: 700; margin-bottom: 1.5mm }}
.tag {{ margin-left: auto; font-family: Nunito; font-size: 9pt; border-radius: 99px; padding: 2px 9px; border: 1.3px solid #999; color: #555 }}
.tag.m {{ border-color: #7a4ea3; color: #7a4ea3 }}
.it {{ display: flex; align-items: center; gap: 4mm; margin: 1.2mm 0; }}
.it .k {{ font-weight: 700; color: #555; width: 6mm; flex: none }}
.box {{ display: inline-block; width: 24mm; height: 11mm; border: 1.6px solid #555; border-radius: 7px; vertical-align: middle; background: #fff }}
.wl {{ height: 10mm; border-bottom: 1.3px solid #9a9a95; position: relative }} .wl::before {{ content: ''; position: absolute; left: 0; right: 0; bottom: 4.2mm; border-bottom: 1px dotted #c4c4bf }}
.grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm }} .grid3 .box {{ width: 17mm }}
.cell {{ display: flex; flex-direction: column; align-items: center; gap: 2mm }}
.foot {{ position: absolute; bottom: 6mm; left: 13mm; right: 13mm; display: flex; justify-content: space-between; font-size: 8.5pt; color: #8a8a85; font-family: Nunito }}
.adult {{ font-size: 9.6pt; line-height: 1.4 }} .page.adult {{ height: auto; min-height: 297mm; overflow: visible }} .page.adult .foot {{ position: static; margin-top: 6mm }} .adult h1 {{ font-family: Nunito; font-size: 18pt }}
.adult h2 {{ font-family: Nunito; font-size: 12pt; margin: 4mm 0 1.5mm }}
.corr {{ border: 1.4px solid; border-radius: 10px; padding: 3mm 4mm; margin-top: 3mm }}
table.a {{ border-collapse: collapse; width: 100% }} table.a td {{ border-top: 1px solid #deded8; padding: 1.2mm 2mm; vertical-align: top }}
"""
STAR = "12,2 14.9,8.6 22,9.3 16.6,14 18.2,21 12,17.3 5.8,21 7.4,14 2,9.3 9.1,8.6"
def stars(n): return "".join(f'<svg width="20" height="20" viewBox="0 0 24 24"><polygon points="{STAR}" fill="#e0a100" stroke="#8a6400"/></svg>' for _ in range(n))
def lines(k): return '<div class="wl"></div>' * k
def tenframe(k, c=30):
    s = ""
    for i in range(10):
        x, y = 2 + (i % 5) * c, 2 + (i // 5) * c
        s += f'<rect x="{x}" y="{y}" width="{c}" height="{c}" fill="#fff" stroke="#1b2430" stroke-width="2"/>'
        if i < k: s += f'<circle cx="{x + c / 2}" cy="{y + c / 2}" r="{c * .32}" fill="#c35713"/>'
    return f'<svg width="{5 * c + 4}" height="{2 * c + 4}" viewBox="0 0 {5 * c + 4} {2 * c + 4}">{s}</svg>'
def numberline(a, b, marks=(), jumps=(), w=520, top=0):
    x0, x1, y = 16, w - 16, 38 + top; X = lambda n: x0 + (n - a) * (x1 - x0) / (b - a)
    s = f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#1b2430" stroke-width="2"/>'
    for n in range(a, b + 1):
        big = n % 10 == 0; h = 9 if big else (7 if n % 5 == 0 else 4)
        s += f'<line x1="{X(n)}" y1="{y - h}" x2="{X(n)}" y2="{y + h}" stroke="#1b2430" stroke-width="{2 if big else 1}"/>'
        if big: s += f'<text x="{X(n)}" y="{y + 24}" text-anchor="middle" font-family="Nunito" font-weight="800" font-size="14">{n}</text>'
    for p, q, lab in jumps:
        xa, xb = X(p), X(q); h = 14 + (xb - xa) * .3
        s += f'<path d="M{xa} {y - 4} Q{(xa + xb) / 2} {y - 4 - 2 * h} {xb} {y - 4}" fill="none" stroke="{BLEU}" stroke-width="2.5"/><text x="{(xa + xb) / 2}" y="{y - 8 - h}" text-anchor="middle" font-family="Nunito" font-weight="800" font-size="14" fill="{BLEU}">{lab}</text>'
    for n in marks:
        s += f'<circle cx="{X(n)}" cy="{y}" r="5" fill="{BLEU}"/>'
        if n % 10: s += f'<text x="{X(n)}" y="{y + 24}" text-anchor="middle" font-family="Nunito" font-weight="800" font-size="14" fill="{BLEU}">{n}</text>'
    return f'<svg width="{w}" height="{66 + top}" viewBox="0 0 {w} {66 + top}">{s}</svg>'

def err_text(e): return e if isinstance(e, str) else (e or {}).get("text", "")
def icon(name, px=70):
    b = base64.b64encode((APP / "img" / f"{name}.svg").read_bytes()).decode()
    return f'<img src="data:image/svg+xml;base64,{b}" width="{px}" height="{px}" style="display:block">'
def blocks_svg(h=0, t=0, u=0, c=9, regroup=False):
    """Dizaines (barres de 10), unités (carrés, rangées de 5), centaines (plaques). Avec regroup : avant → après."""
    def one(h, t, u):
        x, parts, H = 0, [], 10 * c
        for _ in range(h):
            g = "".join(f'<line x1="{x}" y1="{k * c}" x2="{x + H}" y2="{k * c}" stroke="#8a3b2a" stroke-width=".8"/><line x1="{x + k * c}" y1="0" x2="{x + k * c}" y2="{H}" stroke="#8a3b2a" stroke-width=".8"/>' for k in range(1, 10))
            parts.append(f'<rect x="{x}" y="0" width="{H}" height="{H}" fill="#e7a08f" stroke="#1b2430" stroke-width="1.4"/>{g}'); x += H + 6
        for _ in range(t):
            g = "".join(f'<line x1="{x}" y1="{k * c}" x2="{x + c}" y2="{k * c}" stroke="#1b2430" stroke-width=".7"/>' for k in range(1, 10))
            parts.append(f'<rect x="{x}" y="0" width="{c}" height="{H}" fill="#9cc8e3" stroke="#1b2430" stroke-width="1.4"/>{g}'); x += c + 4
        if t or h: x += 6
        for k in range(u):
            parts.append(f'<rect x="{x + (k % 5) * (c + 2)}" y="{(k // 5) * (c + 2)}" width="{c}" height="{c}" fill="#f6cf7a" stroke="#1b2430" stroke-width="1.2"/>')
        w = x + (min(u, 5) * (c + 2) if u else 0)
        return "".join(parts), max(w, 1), H
    a, wa, H = one(h, t, u)
    if not regroup:
        return f'<svg width="{wa}" height="{H}" viewBox="0 0 {wa} {H}">{a}</svg>'
    h2, t2, u2 = h, t, u
    while u2 >= 10: u2 -= 10; t2 += 1
    if h: 
        while t2 >= 10: t2 -= 10; h2 += 1
    elif t2 >= 10 and t >= 10: t2 -= 10; h2 += 1
    b, wb, _ = one(h2, t2, u2)
    return f'<svg width="{wa + wb + 40}" height="{H}" viewBox="0 0 {wa + wb + 40} {H}">{a}<path d="M{wa + 8} {H / 2} h22 m-7 -6 l7 6 l-7 6" fill="none" stroke="#1b2430" stroke-width="2.2"/><g transform="translate({wa + 40} 0)">{b}</g></svg>'
def bar_svg(v, w=330):
    parts = v.get("parts", []); known = sum(p for p in parts if p is not None)
    total = v["whole"] if v.get("whole") is not None else known
    vals = [p if p is not None else max(total - known, total * .15) for p in parts]; S = sum(vals) or 1
    x, out, unit = 4, "", (" " + v["unit"]) if v.get("unit") else ""
    for i, val in enumerate(vals):
        ww = (w - 8) * val / S; q = parts[i] is None; dash = 'stroke-dasharray="5 4"' if q else ""
        out += f'<rect x="{x}" y="30" width="{ww}" height="30" fill="{"#fff" if q else ("#fbe9c8" if i % 2 == 0 else "#e2ebf7")}" stroke="#1b2430" stroke-width="1.6" {dash}/>'
        out += f'<text x="{x + ww / 2}" y="51" text-anchor="middle" font-family="Nunito" font-weight="800" font-size="14">{"?" if q else str(parts[i]) + unit}</text>'
        if v.get("labels") and i < len(v["labels"]): out += f'<text x="{x + ww / 2}" y="76" text-anchor="middle" font-family="Andika" font-size="11" fill="#55554f">{esc(v["labels"][i])}</text>'
        x += ww
    wq = v.get("whole") is None
    out += f'<path d="M4 25 q0 -7 7 -7 H{w / 2 - 7} q7 0 7 -7 q0 7 7 7 H{w - 11} q7 0 7 7" fill="none" stroke="#1b2430" stroke-width="1.6"/><text x="{w / 2}" y="8" text-anchor="middle" font-family="Nunito" font-weight="800" font-size="14">{"?" if wq else str(v["whole"]) + unit}</text>'
    return f'<svg width="{w}" height="82" viewBox="0 -4 {w} 86">{out}</svg>'
def model_visual(L):
    v = L["paper"].get("model_visual")
    if v is None:
        return numberline(30, 50, marks=(38, 40, 45), jumps=((38, 40, "+2"), (40, 45, "+5")), w=330, top=26) if L["child"] == "bleu" else tenframe(7, 26)
    k = v.get("kind")
    if k == "numberline": return numberline(v["from"], v["to"], marks=v.get("marks", ()), jumps=v.get("jumps", ()), w=330, top=26)
    if k == "tenframe": return tenframe(v.get("filled", 0), 26)
    if k == "blocks": return blocks_svg(v.get("h", 0), v.get("t", 0), v.get("u", 0), c=7 if v.get("regroup") else 8, regroup=v.get("regroup", False))
    if k == "bar": return bar_svg(v)
    if k == "items": return '<div style="display:grid;grid-template-columns:repeat(5,auto);gap:2px">' + icon(v.get("item", "mangue"), 30) * v["n"] + "</div>"
    return ""

def item_html(it, color):
    q = it["q"]
    if "blocks" in it:
        b = it["blocks"]
        return f'<div class="cell">{blocks_svg(b.get("h", 0), b.get("t", 0), b.get("u", 0), c=6)}<span style="font-size:11pt;text-align:center">{esc(q)}</span><span class="box"></span></div>'
    if "syll" in it:
        circ = "".join('<svg width="22" height="22"><circle cx="11" cy="11" r="9" fill="#fff" stroke="#1b2430" stroke-width="1.8"/></svg>' for _ in range(3))
        return f'<div class="cell">{icon(it["syll"]["name"], 74)}<div style="display:flex;gap:4px">{circ}</div><span class="box" style="width:16mm"></span></div>'
    if "draw" in it:
        return f'<div class="it" style="align-items:flex-start"><span class="k">{esc(it["id"])})</span><div style="flex:1;font-size:13pt">{esc(q)}<div style="height:30mm;border:1.6px dashed #9a9a95;border-radius:10px;margin-top:2mm"></div></div></div>' 
    if "tenframe" in it:
        if "answer" in it: return f'<div class="cell">{tenframe(it["tenframe"])}<span class="box"></span></div>'
        return f'<div class="it"><span class="k">{esc(it["id"])})</span><div>{esc(q)}<div style="margin-top:2mm">{tenframe(0, 34)}</div>{lines(it.get("lines", 1))}</div></div>'
    if "line" in it:
        return f'<div class="it"><span class="k">{esc(it["id"])})</span><span style="font-size:15pt;white-space:nowrap">{esc(q)} = <span class="box"></span></span>{numberline(*it["line"], w=420)}</div>'
    if "?" in q and len(q) < 20:
        return f'<div class="it"><span class="k">{esc(it["id"])})</span><span style="font-size:16pt">{esc(q).replace("?", "</span><span class=box></span><span style=font-size:16pt>")}</span></div>'
    if len(q) > 24:
        ans = '<div class="it" style="margin-left:10mm">Réponse : <span class="box"></span></div>' if "answer" in it else ""
        return f'<div class="it" style="align-items:flex-start"><span class="k">{esc(it["id"])})</span><div style="flex:1;font-size:13pt">{esc(q)}{lines(it.get("lines", 0))}{ans}</div></div>'
    return f'<div class="it"><span class="k">{esc(it["id"])})</span><span style="font-size:16pt;white-space:nowrap">{esc(q)} =</span><span class="box" style="width:19mm"></span></div>'

def kid_page(L, n):
    c = L["child"]; color = BLEU if c == "bleu" else ORANGE; P = L["paper"]
    who = "BLEU · 7 ans" if c == "bleu" else "ORANGE · 5 ans ½"
    model = P.get("model", "")
    visual = model_visual(L)
    body = ""
    for lv in P["levels"]:
        items = lv["items"]
        if all(("tenframe" in it and "answer" in it) or "blocks" in it or "syll" in it or (len(it["q"]) < 12 and "?" not in it["q"] and "line" not in it and "tenframe" not in it) for it in items):
            inner = '<div class="grid3">' + "".join(item_html(it, color) for it in items) + "</div>"
        else:
            inner = "".join(item_html(it, color) for it in items)
        tag = '<span class="tag m">Avec Maman</span>' if lv.get("who") == "maman" else '<span class="tag">Seul</span>'
        body += f'<div class="lv"><div class="lvh">{stars(lv["stars"])}<span style="font-size:{14 if c == "bleu" else 16}pt">{esc(lv["ins"])}</span>{tag}</div>{inner}</div>'
    return f'''<section class="page"><div class="band" style="background:{color}"><span><b>{who}</b> &nbsp;<span class="what">{esc(L["week"])} · {esc(L["domain"])}</span></span><span class="pr">Prénom :</span></div>
<h1 style="color:{color}">{esc(P["title"])}</h1>
<div class="model"><div style="flex:1"><b>Ce que Kono m'a montré</b><br>{esc(model)}</div>{visual}</div>
{body}
<div class="foot"><span>Corridor à la maison · {esc(L["week"])} · {esc(L.get("day", ""))} · même contenu que la tablette</span><span>{n}</span></div></section>'''

def reading_pages(L, n0):
    out = []
    for st in L["steps"]:
        if st.get("type") != "reading" or st.get("reread"): continue
        total, rows = 0, ""
        nwords = sum(len([w for w in x.split() if any(ch.isalnum() for ch in w)]) for x in st["passage"])
        fs = 17 if nwords <= 70 else 15.5 if nwords <= 85 else 14.5
        for sent in st["passage"]:
            total += len([w for w in sent.split() if any(ch.isalnum() for ch in w)])
            rows += f'<tr><td style="font-size:{fs}pt;line-height:1.65;padding:1.3mm 3mm">{esc(sent)}</td><td style="width:14mm;text-align:right;color:#8a8a85;font-family:Nunito;font-weight:800">{total}</td></tr>'
        mes = "".join(f'<tr><td>{k}</td><td></td><td></td><td></td><td></td></tr>' for k in range(1, 5))
        color = BLEU if L["child"] == "bleu" else ORANGE
        out.append(f'''<section class="page"><div class="band" style="background:{color}"><span><b>TEXTE À RELIRE</b> &nbsp;<span class="what">{esc(L["week"])} · Lecture</span></span><span class="pr">Prénom :</span></div>
<h1 style="color:{color}">{esc(st["title"])}</h1>
<p style="font-size:11pt;color:#55554f;margin:0 0 3mm">À relire chaque jour, à voix haute, pour lire de plus en plus facilement. Le nombre à droite compte les mots depuis le début.</p>
<table style="width:100%;border-collapse:collapse">{rows}</table>
<div class="lv" style="margin-top:8mm"><div class="lvh" style="font-family:Nunito">Pour l'adulte : la mesure d'une minute</div>
<p style="font-size:10.5pt;margin:0 0 2mm">Chronométrer une minute. Compter les mots lus correctement (le nombre de la ligne atteinte, moins les erreurs). Objectif de fin de CE1 : 70 mots par minute. Comparer l'enfant à lui-même, jamais aux autres.</p>
<table class="a" style="font-size:10.5pt"><tr><td><b>Mesure</b></td><td><b>Date</b></td><td><b>Mots lus</b></td><td><b>Erreurs</b></td><td><b>Mots par minute</b></td></tr>{mes}</table></div>
<div class="foot"><span>Corridor à la maison · {esc(L["week"])} · même texte que la tablette</span><span>{n0 + len(out)}</span></div></section>''')
    return out

def maman_page(lessons, n):
    blocks = ""
    for L in lessons:
        color = BLEU if L["child"] == "bleu" else ORANGE
        rows = ""
        for lv in L["paper"]["levels"]:
            for it in lv["items"]:
                errs = "; ".join(f"{k} : {err_text(v)}" for k, v in (it.get("errors") or {}).items())
                rows += f'<tr><td style="white-space:nowrap">{"★" * lv["stars"]} {esc(it["id"])})</td><td>{esc(it.get("short") or it["q"])}</td><td><b>{esc(it.get("answer", "réponse libre"))}</b></td><td class="small" style="color:#6b6b66">{esc(errs)}</td></tr>'
        notes = "".join(f"<li>{esc(t)}</li>" for t in L["paper"].get("maman", []))
        blocks += f'''<div class="corr" style="border-color:{color}"><h2 style="margin-top:0;color:{color}">{"Bleu" if L["child"] == "bleu" else "Orange"} · {esc(L["title"])}</h2>
<p style="margin:0 0 2mm"><b>Objectif :</b> {esc(L["objective"])} <span style="color:#6b6b66">({esc(L.get("programme_label", L.get("programme", "")))})</span></p>
<ul style="margin:0 0 2mm 4mm;padding-left:3mm">{notes}</ul>
<table class="a"><tr><td><b>Niveau</b></td><td><b>Exercice</b></td><td><b>Réponse</b></td><td><b>Erreurs typiques et ce que dit la tablette</b></td></tr>{rows}</table></div>'''
    return f'''<section class="page adult"><div style="border-bottom:3px solid #2b2b28;padding-bottom:2mm"><div style="font-family:Nunito;font-weight:800;color:#7a4ea3;letter-spacing:1.5px;font-size:9pt">CARTE MAMAN · {esc(WEEK)}</div><h1 style="margin:1mm 0 0">Réponses et points à surveiller · {"Bleu" if lessons[0]["child"] == "bleu" else "Orange"}</h1></div>
<p style="margin:3mm 0 0">La tablette explique, montre un exemple, fait pratiquer, puis demande à l'enfant de faire sa fiche et de taper ses réponses. Votre rôle : être à portée de voix, regarder la fiche à la fin, et écouter le soir l'enregistrement où l'enfant explique sa méthode (Espace parent › Suivi).</p>
{blocks}
<div class="foot"><span>Corridor à la maison · {esc(WEEK)} · généré depuis les fichiers de leçon</span><span>{n}</span></div></section>'''

async def main():
    idx = json.loads((APP / "lessons" / "index.json").read_text())
    lessons = [json.loads((APP / "lessons" / f'{l["id"]}.json').read_text()) for l in idx["lessons"] if l["week"] == WEEK]
    lessons.sort(key=lambda L: (L["child"] != "bleu", L["order"]))
    pages = [kid_page(L, i + 1) for i, L in enumerate(lessons)]
    for L in lessons: pages += reading_pages(L, len(pages) + 1)
    pages += [maman_page([L], len(pages) + 1 + i) for i, L in enumerate(lessons)]
    doc = f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(pages)}</body></html>'
    out_html = ROOT / "print" / f"Fiches_{WEEK}.html"; out_html.write_text(doc, encoding="utf-8")
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.goto(out_html.as_uri()); await pg.evaluate("document.fonts.ready")
        over = await pg.evaluate("""() => [...document.querySelectorAll('.page')].map((p,i)=>{const f=p.querySelector('.foot').getBoundingClientRect().top;let m=0;[...p.children].forEach(c=>{if(!c.classList.contains('foot'))m=Math.max(m,c.getBoundingClientRect().bottom)});return [i+1,Math.round(f-m)]})""")
        print("marges (px) :", over)
        await pg.pdf(path=str(ROOT / "print" / f"Fiches_{WEEK}.pdf"), format="A4", print_background=True, prefer_css_page_size=True)
        await b.close()
    print("PDF :", ROOT / "print" / f"Fiches_{WEEK}.pdf")

asyncio.run(main())
