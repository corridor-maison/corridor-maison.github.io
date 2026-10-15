# -*- coding: utf-8 -*-
"""Tableau par classe pour l'enseignante, à partir des rapports déposés par les familles.

Chaque famille enregistre son rapport du dimanche dans un fichier (Espace parent › Rapport › Enregistrer dans un fichier,
format rapport-1 ou rapport-2) et le dépose à l'école : clé USB, messagerie, ou le téléphone de l'enseignante. Ce script lit tous les
fichiers d'un ou plusieurs dossiers, garde le dernier rapport de chaque enfant, et écrit un tableau par classe :
séances de la semaine, compétences (réussite au premier essai), file de révision, enregistrements non écoutés.

Usage : python3 tools/tableau_classe.py DOSSIER [DOSSIER…] [--sortie print/]
        -> print/tableau-classes-<AAAA-MM-JJ>.html (à ouvrir ou imprimer) et print/tableau-classes-<AAAA-MM-JJ>.csv
Rend 0 si au moins un rapport a été lu, 1 sinon. Bibliothèque standard seulement ; rien n'est envoyé nulle part."""
import csv, datetime, html, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
esc = lambda s: html.escape(str(s if s is not None else ""))

def load_reports(dirs):
    out = []
    for d in dirs:
        for f in sorted(pathlib.Path(d).rglob("*.json")):
            try: r = json.loads(f.read_text(encoding="utf-8"))
            except Exception: continue
            if isinstance(r, dict) and r.get("app") == "corridor-a-la-maison" and r.get("format") in ("rapport-1", "rapport-2"): out.append((f, r))
    return out

def latest_children(reports):
    """Un enfant = (inscription, identifiant de profil). Le rapport le plus récent l'emporte."""
    best = {}
    for f, r in reports:
        ins = (r.get("inscription") or {}).get("id") or "libre"
        for p in r.get("profils", []):
            k = (ins, p.get("id"))
            if k not in best or str(r.get("date", "")) > best[k]["rapport"]:
                best[k] = dict(p, rapport=str(r.get("date", "")), inscription=ins, ecole=r.get("ecole", ""), fichier=f.name, version=r.get("version", ""))
    return sorted(best.values(), key=lambda c: (c.get("classe", ""), c["inscription"], c.get("prenom", "")))

def progression(parcours):
    try: return json.loads((APP / "progression" / f"{parcours}.json").read_text(encoding="utf-8"))
    except Exception: return {"skills": []}

def pct(a, n): return f"{round(100 * a / n)} %" if n else "—"
def level(a, n):
    if n < 3: return "peu"
    r = a / n
    return "bien" if r >= .8 else "moyen" if r >= .5 else "fragile"

CSS = """body{font-family:Andika,'Trebuchet MS',sans-serif;color:#1b2430;margin:18px;font-size:12.5px}h1{font-family:Nunito,sans-serif;margin:0 0 4px}h2{font-family:Nunito,sans-serif;margin:22px 0 6px;border-bottom:3px solid #2f7ea6;padding-bottom:3px}
h3{margin:12px 0 4px;font-size:13px}table{border-collapse:collapse;width:100%;margin-top:4px}th,td{border:1px solid #d7cfbd;padding:4px 6px;text-align:left;vertical-align:top}th{background:#f3ebdb;font-size:11.5px}
td.n{text-align:center;font-variant-numeric:tabular-nums}.bien{background:#def1e6}.moyen{background:#fff4d6}.fragile{background:#fcefe2;color:#8a3b2a;font-weight:700}.peu{color:#888}.muted{color:#5f6b70}.small{font-size:11px}
.warn{background:#fff4d6;border:1.5px solid #e8c766;border-radius:8px;padding:6px 10px;margin:6px 0}@media print{body{margin:8mm}h2{break-before:page}h2:first-of-type{break-before:auto}}"""

def main(argv):
    out_dir = ROOT / "print"; dirs = []
    i = 0
    while i < len(argv):
        if argv[i] == "--sortie": out_dir = pathlib.Path(argv[i + 1]); i += 2
        else: dirs.append(argv[i]); i += 1
    if not dirs: print(__doc__); return 1
    reports = load_reports(dirs)
    if not reports: print("aucun rapport (format rapport-1) trouvé dans", ", ".join(dirs)); return 1
    children = latest_children(reports)
    day = datetime.date.today().isoformat(); out_dir.mkdir(exist_ok=True)
    classes = {}
    for c in children: classes.setdefault(c.get("classe") or "?", []).append(c)
    H = [f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Corridor à la maison · tableau par classe · {day}</title><style>{CSS}</style></head><body>",
         f"<h1>Corridor à la maison · tableau par classe</h1><p class='muted'>Établi le {day} à partir de {len(reports)} rapport(s) de famille (format rapport-1) ; {len(children)} enfant(s), {len(classes)} classe(s). Dernier rapport de chaque enfant. Un enfant est identifié par le code d'inscription remis par l'école ; le registre de l'école fait le lien avec la famille.</p>"]
    rows_csv = []
    for classe, kids in sorted(classes.items()):
        parcours = sorted({k.get("parcours", "") for k in kids})
        skills = []
        for pc in parcours:
            for s in progression(pc).get("skills", []):
                if s["code"] not in [x["code"] for x in skills]: skills.append(s)
        seen = {code for k in kids for code in (k.get("competences") or {})}
        cols = [s for s in skills if s["code"] in seen] + [{"code": c, "label": c} for c in sorted(seen) if c not in [s["code"] for s in skills]]
        tot7 = sum(k["seances"]["terminees"] for k in kids); mins = sum(k["seances"]["minutes"] for k in kids)
        stale = [k for k in kids if (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(k["rapport"][:10])).days > 9] if all(len(k["rapport"]) >= 10 for k in kids) else []
        H.append(f"<h2>Classe {esc(classe)} <span class='small muted'>· {len(kids)} enfant(s) · parcours {esc(', '.join(parcours))}</span></h2>")
        H.append(f"<p>Cette semaine : <b>{tot7}</b> séance(s) terminée(s) en tout, soit {round(tot7 / len(kids), 1)} par enfant, <b>{mins}</b> minutes au total.</p>")
        if stale:
            names = ", ".join(f"{k['inscription']} ({k.get('prenom', '')})" for k in stale)
            H.append(f"<p class='warn'>Rapport de plus de 9 jours pour : {esc(names)}. Demander un nouveau fichier à la famille.</p>")
        H.append("<h3>Les enfants</h3><table><tr><th>Inscription</th><th>Prénom</th><th>Rapport du</th><th>Séances 7 j<br>terminées</th><th>arrêtées</th><th>Minutes</th><th>Séances depuis le début</th><th>Enregistrements<br>non écoutés</th><th>Défis à revoir</th><th>Séance en cours</th><th>Maîtrise 30 j<br>acquis / en cours / fragile</th><th>Automatismes (records)</th></tr>")
        for k in kids:
            s = k["seances"]; e = k.get("enregistrements") or {}; rp = k.get("reprise"); rec = k.get("records") or {}
            recs = " ; ".join(f"{kk} {v.get('best')} ({v.get('secs')} s)" for kk, v in rec.items()) or "—"
            encours = f"{rp['seance']} (étape {rp['etape']} sur {rp['sur']})" if rp else "—"
            ma = k.get("maitrise") or {}; mcount = " / ".join(str(sum(1 for v in ma.values() if v.get("palier") == lv)) for lv in ("acquis", "en-cours", "fragile")) if ma else "—"
            H.append(f"<tr><td>{esc(k['inscription'])}</td><td>{esc(k.get('prenom', ''))}</td><td>{esc(k['rapport'][:10])}</td><td class='n'>{s['terminees']}</td><td class='n'>{s['arretees']}</td><td class='n'>{s['minutes']}</td><td class='n'>{s['total']}</td><td class='n'>{e.get('nonEcoutes', 0)} / {e.get('total', 0)}</td><td>{esc(', '.join(k.get('revision') or [])) or '—'}</td><td>{esc(encours)}</td><td class='n'>{esc(mcount)}</td><td class='small'>{esc(recs)}</td></tr>")
            rows_csv.append({"classe": classe, "inscription": k["inscription"], "prenom": k.get("prenom", ""), "parcours": k.get("parcours", ""), "rapport_du": k["rapport"][:10], "seances_7j_terminees": s["terminees"], "seances_7j_arretees": s["arretees"], "minutes_7j": s["minutes"], "seances_total": s["total"],
                             "enregistrements_non_ecoutes": e.get("nonEcoutes", 0), "defis_a_revoir": " ".join(k.get("revision") or []), "maitrise_acquis_encours_fragile": mcount, "competences": " ; ".join(f"{c}={v['premier']}/{v['essais']}" for c, v in sorted((k.get("competences") or {}).items()))})
        H.append("</table>")
        if cols:
            H.append("<h3>Compétences, 7 derniers jours : réussite au premier essai (nombre d'essais)</h3><table><tr><th>Enfant</th>" + "".join(f"<th title='{esc(s['label'])}'>{esc(s['code'])}</th>" for s in cols) + "</tr>")
            for k in kids:
                cells = []
                for s in cols:
                    v = (k.get("competences") or {}).get(s["code"])
                    cells.append(f"<td class='n {level(v['premier'], v['essais'])}'>{pct(v['premier'], v['essais'])} ({v['essais']})</td>" if v else "<td class='n peu'>—</td>")
                H.append(f"<tr><td>{esc(k['inscription'])} · {esc(k.get('prenom', ''))}</td>{''.join(cells)}</tr>")
            agg = {}
            for k in kids:
                for c, v in (k.get("competences") or {}).items(): a = agg.setdefault(c, [0, 0]); a[0] += v["premier"]; a[1] += v["essais"]
            H.append("<tr><th>Classe</th>" + "".join(f"<th class='n {level(*agg[s['code']]) if s['code'] in agg else 'peu'}'>{pct(*agg[s['code']]) if s['code'] in agg else '—'}</th>" for s in cols) + "</tr></table>")
            H.append("<p class='small muted'>Vert : 80 % et plus · jaune : de 50 à 79 % · orange : moins de 50 % · gris : moins de 3 essais. " + " · ".join(f"<b>{esc(s['code'])}</b> {esc(s['label'])}" for s in cols) + "</p>")
            frag = [s for s in cols if s["code"] in agg and agg[s["code"]][1] >= 6 and agg[s["code"]][0] / agg[s["code"]][1] < .5]
            if frag: H.append("<p class='warn'>À reprendre en classe : " + " ; ".join(f"{esc(s['label'])} ({esc(s['code'])}, {pct(*agg[s['code']])})" for s in frag) + ".</p>")
    H.append("</body></html>")
    out_html = out_dir / f"tableau-classes-{day}.html"; out_html.write_text("\n".join(H), encoding="utf-8")
    out_csv = out_dir / f"tableau-classes-{day}.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_csv[0].keys()), delimiter=";"); w.writeheader(); w.writerows(rows_csv)
    print(f"{len(reports)} rapport(s) lu(s), {len(children)} enfant(s), {len(classes)} classe(s) : {out_html.relative_to(ROOT) if out_html.is_relative_to(ROOT) else out_html} et {out_csv.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
