"""Test des outils de la chaîne de contenu et de l'école. Chaque outil est lancé comme le fondateur le lance ;
le test échoue au premier outil qui ne rend pas 0 ou dont la sortie n'a pas ce qu'on attend.

- tools/check_lessons.py : 0.
- tools/codes.py verifier : 0 (ecole.json conforme, aucun code en clair).
- tools/build_review.py S1 : print/Relecture_S1.html produit, chaque séance de S1 présente, check_lessons à 0 dans la relecture.
- tools/tableau_classe.py : sur le rapport enregistré par tests/e2e.py ($SHOTS/e2e-<taille>-rapport.json, s'il existe)
  et sur un rapport d'exemple construit ici ; tableau HTML et CSV produits, une ligne par enfant, compétences présentes.

Lancer : python3 tests/outils.py
"""
import json, os, pathlib, subprocess, sys, tempfile, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = [sys.executable, "-X", "utf8"]
SHOTS = os.environ.get("SHOTS", "/tmp/corridor-tests/")
fails = []
def run(args, cwd=ROOT):
    r = subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout + r.stderr).strip()
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'ÉCHEC'}] {name}" + (f" · {detail}" if detail else ""))
    if not ok: fails.append(name)

code, out = run(["tools/check_lessons.py"]); check("check_lessons.py rend 0", code == 0, out.splitlines()[-1] if out else "")
code, out = run(["tools/codes.py", "verifier"]); check("codes.py verifier rend 0", code == 0, out.splitlines()[-1] if out else "")

idx = json.loads((ROOT / "app" / "lessons" / "index.json").read_text(encoding="utf-8"))
week = idx["lessons"][0]["week"]
code, out = run(["tools/build_review.py", week])
html = (ROOT / "print" / f"Relecture_{week}.html")
txt = html.read_text(encoding="utf-8") if html.exists() else ""
titles = [l["title"] for l in idx["lessons"] if l["week"] == week]
check(f"build_review.py {week} rend 0 et produit print/Relecture_{week}.html", code == 0 and html.exists(), out.splitlines()[0] if out else "")
check("la relecture contient chaque séance de la semaine, le tableau des étapes et les contrôles", all(t.replace("'", "&#x27;") in txt or t in txt for t in titles) and "Kono dit" in txt and "check_lessons.py" in txt and "0 erreur, publication possible" in txt, f"{len(titles)} séances")

# tableau de classe : rapport d'exemple (deux enfants, deux classes) + rapport du test de bout en bout s'il existe
with tempfile.TemporaryDirectory() as d:
    today = datetime.date.today().isoformat()
    sample = {"app": "corridor-a-la-maison", "format": "rapport-1", "version": "test", "date": today, "ecole": "École de test", "inscription": {"id": "C-0001", "classe": "CE1"}, "acces": "Inscription : C-0001", "texte": "RAPPORT",
              "profils": [{"id": "aaaa", "prenom": "Ali", "parcours": "ce1", "classe": "CE1", "age": 7, "seances": {"terminees": 4, "arretees": 1, "minutes": 52, "total": 4, "derniere": today},
                           "competences": {"C.dizaine": {"libelle": "x", "essais": 6, "premier": 5, "apres": 1, "montree": 0}, "N.echange": {"libelle": "y", "essais": 4, "premier": 1, "apres": 1, "montree": 2}}, "records": {"calcul-express": {"best": 7, "secs": 40, "date": today}}, "mesures": [], "enregistrements": {"total": 4, "nonEcoutes": 2}, "revision": ["seul-29-4"], "reprise": None}]}
    sample2 = dict(sample, inscription={"id": "C-0021", "classe": "GS"}, profils=[{"id": "bbbb", "prenom": "Awa", "parcours": "gs", "classe": "GS", "age": 5, "seances": {"terminees": 3, "arretees": 0, "minutes": 30, "total": 3, "derniere": today}, "competences": {"GS.N.amis10": {"libelle": "z", "essais": 8, "premier": 7, "apres": 1, "montree": 0}}, "records": {}, "mesures": [], "enregistrements": {"total": 0, "nonEcoutes": 0}, "revision": [], "reprise": {"seance": "gs-s1-cache", "etape": 5, "sur": 21}}])
    pathlib.Path(d, "corridor-rapport-C-0001.json").write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")
    pathlib.Path(d, "corridor-rapport-C-0021.json").write_text(json.dumps(sample2, ensure_ascii=False), encoding="utf-8")
    e2e = sorted(pathlib.Path(SHOTS).glob("e2e-*-rapport.json")) if pathlib.Path(SHOTS).exists() else []
    if e2e: pathlib.Path(d, "corridor-rapport-e2e.json").write_text(e2e[-1].read_text(encoding="utf-8"), encoding="utf-8")
    code, out = run(["tools/tableau_classe.py", d, "--sortie", d])
    outs = sorted(pathlib.Path(d).glob("tableau-classes-*.html")); csvs = sorted(pathlib.Path(d).glob("tableau-classes-*.csv"))
    t = outs[0].read_text(encoding="utf-8") if outs else ""; c = csvs[0].read_text(encoding="utf-8") if csvs else ""
    check("tableau_classe.py rend 0 et produit le tableau HTML et le CSV", code == 0 and outs and csvs, out)
    check("le tableau a une section par classe, une ligne par enfant, les compétences et la séance en cours", "Classe CE1" in t and "Classe GS" in t and "C-0001" in t and "C-0021" in t and "C.dizaine" in t and "GS.N.amis10" in t and "gs-s1-cache (étape 5 sur 21)" in t and c.count("\n") >= 3)
    if e2e:
        data = json.loads(e2e[-1].read_text(encoding="utf-8")); ins = (data.get("inscription") or {}).get("id")
        check("le rapport exporté par le test de bout en bout entre dans le tableau", bool(ins) and ins in t and all(p["prenom"] in t for p in data["profils"]), f"{len(data['profils'])} profils, inscription {ins}")
    else: print("[—] pas de rapport du test de bout en bout dans", SHOTS, ": contrôle non fait")

print("OUTILS :", "OK" if not fails else "ÉCHEC : " + ", ".join(fails))
sys.exit(1 if fails else 0)
