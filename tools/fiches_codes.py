# -*- coding: utf-8 -*-
"""Fiches d'inscription à imprimer (QR code) et messages WhatsApp prêts à copier, à partir du fichier des codes de l'école.

Chaque famille reçoit son code de deux façons au choix :
- une fiche papier : le QR code ouvre l'application avec le code déjà saisi et vérifié ; le code est aussi écrit en grand ;
- un message WhatsApp : le lien fait la même chose ; le code est rappelé si le lien ne s'ouvre pas.
Le lien est https://corridor-maison.github.io/#code=XXX-XXX-XXX : la partie après # ne part jamais au serveur,
et l'application l'efface de l'adresse dès qu'elle l'a lue. Rien n'est envoyé : le code se vérifie sur le téléphone.

Usage :
  python3 tools/fiches_codes.py print/codes-2026-10-15.csv --classe CE1          tous les codes actifs de la classe CE1
  python3 tools/fiches_codes.py print/codes-2026-10-15.csv --ids C-0001,C-0004   seulement ces codes
  options : --pdf (PDF A4 par Chromium, Playwright requis) · --sortie <dossier> (par défaut print/)

Sorties (jamais commitées, .gitignore) : fiches-codes-<date>-<sélection>.html (et .pdf), whatsapp-codes-<date>-<sélection>.txt.
Seuls les codes dont l'empreinte est dans app/ecole.json et qui ne sont pas retirés sont imprimés ; les autres sont signalés
et l'outil rend 1. La colonne « famille » du fichier, si l'école l'a remplie, est imprimée sur la fiche.
Dépendance : segno (QR codes, pip install segno)."""
import argparse, csv, hashlib, html, json, pathlib, re, sys
import segno

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://corridor-maison.github.io/"

def norm(code): return re.sub(r"[^0-9A-Z]", "", code.upper()).replace("O", "0").replace("I", "1").replace("L", "1")
def h(code): return hashlib.sha256(norm(code).encode("utf-8")).hexdigest()
def link(code): return f"{SITE}#code={code}"

def read_codes(path):
    rows = list(csv.reader(open(path, encoding="utf-8"), delimiter=";"))
    return [{"id": r[0].strip(), "classe": r[1].strip(), "code": r[2].strip(), "famille": (r[4].strip() if len(r) > 4 else "")} for r in rows[1:] if len(r) >= 3 and r[0].strip()]

def whatsapp(c, ecole):
    return (f"Bonjour, message de {ecole} : voici l'inscription de votre enfant à Corridor à la maison.\n"
            f"1. Touchez ce lien, avec internet : {link(c['code'])}\n"
            f"2. Le code est vérifié tout seul. Choisissez ensuite un code parent à 4 chiffres, puis créez le profil de l'enfant.\n"
            f"Si le lien ne s'ouvre pas, allez sur corridor-maison.github.io et tapez ce code : {c['code']}\n"
            f"Gardez ce message. Rien n'est envoyé sur internet : le suivi de l'enfant reste sur le téléphone.")

def fiche(c, ecole, icon):
    qr = segno.make(link(c["code"]), error="m").svg_inline(scale=4, border=2, dark="#1f2a33")
    fam = f'<p class="fam">{html.escape(c["famille"])}</p>' if c["famille"] else '<p class="fam vide">Famille : ............................................</p>'
    cls = f' · classe {html.escape(c["classe"])}' if c["classe"] else ""
    return f'''<section class="fiche">
  <header><img src="{icon}" alt=""><div><h1>Corridor à la maison</h1><p>{html.escape(ecole)}{cls}</p></div></header>
  {fam}
  <div class="qr">{qr}</div>
  <p class="lab">Code d'inscription</p><p class="code">{html.escape(c["code"])}</p>
  <ol><li>Avec internet, visez ce QR code avec l'appareil photo du téléphone et touchez le lien.</li>
  <li>Le code est vérifié tout seul. Choisissez un code parent à 4 chiffres.</li>
  <li>Créez le profil de l'enfant. Rien n'est envoyé sur internet.</li></ol>
  <p class="pied">Sans QR code : ouvrez corridor-maison.github.io et tapez le code. Un code par famille, à garder. {html.escape(c["id"])}</p>
</section>'''

CSS = """@page { size: A4; margin: 8mm; }
body { margin: 0; font-family: 'Trebuchet MS', system-ui, sans-serif; color: #1f2a33; }
.page { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; width: 194mm; height: 281mm; page-break-after: always; }
.page:last-child { page-break-after: auto; }
.fiche { border: 1px dashed #9aa3a6; padding: 6mm 7mm; display: flex; flex-direction: column; align-items: center; gap: 2.2mm; box-sizing: border-box; }
header { display: flex; align-items: center; gap: 3mm; align-self: stretch; }
header img { width: 15mm; height: 15mm; border-radius: 3mm; }
h1 { font-size: 15pt; margin: 0; color: #1f63c6; } header p { margin: 0; font-size: 9pt; color: #5b6770; }
.fam { margin: 0; font-size: 11pt; font-weight: bold; align-self: stretch; } .fam.vide { font-weight: normal; color: #5b6770; }
.qr svg { width: 40mm; height: 40mm; display: block; }
.lab { margin: 0; font-size: 9pt; color: #5b6770; }
.code { margin: 0; font-size: 21pt; font-weight: bold; letter-spacing: 1.5mm; font-family: 'Consolas', monospace; }
ol { margin: 0; padding-left: 5mm; font-size: 9pt; line-height: 1.35; align-self: stretch; } li { margin-bottom: .8mm; }
.pied { margin: auto 0 0; font-size: 7.5pt; color: #5b6770; text-align: center; }"""

def main(argv):
    ap = argparse.ArgumentParser(description="Fiches d'inscription (QR code) et messages WhatsApp")
    ap.add_argument("csv"); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--classe"); g.add_argument("--ids")
    ap.add_argument("--pdf", action="store_true"); ap.add_argument("--sortie", default=str(ROOT / "print"))
    a = ap.parse_args(argv)
    ec = json.loads((ROOT / "app" / "ecole.json").read_text(encoding="utf-8"))
    actifs = {c["h"]: c for c in ec.get("codes", []) if not c.get("revoque")}
    ecole = ec.get("ecole") or "votre école"
    codes = read_codes(a.csv)
    if a.classe: sel = [c for c in codes if c["classe"].upper() == a.classe.upper()]; tag = a.classe.upper()
    else:
        want = [x.strip() for x in a.ids.split(",") if x.strip()]; sel = [c for c in codes if c["id"] in want]; tag = "-".join(want) if len(want) <= 3 else f"{len(want)}-codes"
        missing = [x for x in want if x not in {c["id"] for c in sel}]
        if missing: print("absents du fichier :", ", ".join(missing))
    ok, refus = [], []
    for c in sel:
        e = actifs.get(h(c["code"]))
        (ok if e and e["id"] == c["id"] else refus).append(c)
    for c in refus: print(f"REFUSÉ {c['id']} : code retiré ou inconnu de app/ecole.json, pas imprimé")
    if not ok: print("Aucun code à imprimer."); return 1
    out = pathlib.Path(a.sortie); out.mkdir(parents=True, exist_ok=True)
    date = re.search(r"(\d{4}-\d{2}-\d{2})", pathlib.Path(a.csv).name); base = f"{date.group(1) if date else 'codes'}-{tag}"
    icon = (ROOT / "app" / "icons" / "icon-192.png").resolve().as_uri()
    pages = [ok[i:i + 4] for i in range(0, len(ok), 4)]
    doc = f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Fiches d\'inscription {html.escape(tag)}</title><style>{CSS}</style></head><body>' + "".join(
        f'<div class="page">{"".join(fiche(c, ecole, icon) for c in p)}</div>' for p in pages) + "</body></html>"
    fh = out / f"fiches-codes-{base}.html"; fh.write_text(doc, encoding="utf-8")
    fw = out / f"whatsapp-codes-{base}.txt"
    fw.write_text("\n\n".join(f"===== {c['id']}{' · ' + c['classe'] if c['classe'] else ''}{' · ' + c['famille'] if c['famille'] else ''} (cette ligne ne s'envoie pas) =====\n{whatsapp(c, ecole)}" for c in ok) + "\n", encoding="utf-8")
    print(f"{len(ok)} fiche(s) sur {len(pages)} page(s) : {fh}\nmessages WhatsApp : {fw}")
    if a.pdf:
        import asyncio
        from playwright.async_api import async_playwright
        async def pdf():
            async with async_playwright() as p:
                b = await p.chromium.launch(); pg = await b.new_page(); await pg.goto(fh.resolve().as_uri()); await pg.wait_for_timeout(300)
                await pg.pdf(path=str(fh.with_suffix(".pdf")), format="A4", print_background=True, margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"}); await b.close()
        asyncio.run(pdf()); print("PDF :", fh.with_suffix(".pdf"))
    return 1 if refus else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
