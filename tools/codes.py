# -*- coding: utf-8 -*-
"""Codes d'inscription délivrés par l'école (accès autorisé à l'application).

Le dépôt ne contient que les empreintes SHA-256 des codes, dans app/ecole.json : ni les codes, ni un nom d'enfant.
Les codes eux-mêmes sont écrits dans print/codes-<date>.csv, à remettre à l'école et jamais commité (.gitignore).
L'école note dans son registre quel code a été remis à quelle famille.

Usage :
  python3 tools/codes.py nouveau 20 CE1            crée 20 codes pour la classe CE1 (classe : GS, CE1… ou - pour aucune)
  python3 tools/codes.py retirer C-0007            retire un code (l'application le refusera à la prochaine ouverture)
  python3 tools/codes.py acces code|libre          exige un code à l'installation, ou non
  python3 tools/codes.py ecole "École de Bamako"   nom affiché à l'enfant et dans le rapport
  python3 tools/codes.py verifier                  vérifie app/ecole.json ; rend 0 si tout est conforme
Bibliothèque standard seulement."""
import csv, datetime, hashlib, json, pathlib, re, secrets, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ECOLE = ROOT / "app" / "ecole.json"
ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"   # ni 0/O, ni 1/I/L : l'application les confond volontairement à la saisie
ID_RE = re.compile(r"^C-\d{4}$")

def norm(code): return re.sub(r"[^0-9A-Z]", "", code.upper()).replace("O", "0").replace("I", "1").replace("L", "1")
def h(code): return hashlib.sha256(norm(code).encode("utf-8")).hexdigest()
def fmt(raw): return f"{raw[0:3]}-{raw[3:6]}-{raw[6:9]}"
def load():
    if not ECOLE.exists(): return {"schema": 1, "acces": "code", "ecole": "", "codes": []}
    return json.loads(ECOLE.read_text(encoding="utf-8"))
def save(d):
    ECOLE.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

def verifier(d):
    errs = []
    if d.get("schema") != 1: errs.append(f"schema attendu 1, trouvé {d.get('schema')!r}")
    if d.get("acces") not in ("code", "libre"): errs.append(f"acces doit être code ou libre, trouvé {d.get('acces')!r}")
    ids, hs = set(), set()
    for c in d.get("codes", []):
        if not ID_RE.match(str(c.get("id", ""))): errs.append(f"identifiant invalide {c.get('id')!r}")
        if c.get("id") in ids: errs.append(f"identifiant en double {c.get('id')}")
        ids.add(c.get("id"))
        if not re.match(r"^[0-9a-f]{64}$", str(c.get("h", ""))): errs.append(f"{c.get('id')} : empreinte invalide")
        if c.get("h") in hs: errs.append(f"{c.get('id')} : empreinte en double")
        hs.add(c.get("h"))
        for k in c:
            if k not in ("id", "classe", "h", "revoque", "cree"): errs.append(f"{c.get('id')} : clé inconnue {k!r} (aucun nom, aucun code en clair)")
    return errs

def main(argv):
    d = load()
    if not argv or argv[0] == "verifier":
        errs = verifier(d)
        for e in errs: print("ERREUR :", e)
        actifs = sum(1 for c in d.get("codes", []) if not c.get("revoque"))
        print(f"{len(d.get('codes', []))} code(s), {actifs} actif(s), accès {d.get('acces')}, école « {d.get('ecole', '')} », {len(errs)} erreur(s)")
        return 1 if errs else 0
    cmd = argv[0]
    if cmd == "nouveau":
        n = int(argv[1]); classe = argv[2] if len(argv) > 2 and argv[2] != "-" else ""
        start = max([int(c["id"][2:]) for c in d["codes"]] + [0]) + 1
        now = datetime.datetime.now(); day = now.strftime("%Y-%m-%d")
        out = ROOT / "print" / f"codes-{now.strftime('%Y-%m-%d')}.csv"; out.parent.mkdir(exist_ok=True)   # un fichier par jour, complété sans rien écraser
        rows, seen = [], {c["h"] for c in d["codes"]}
        for k in range(n):
            while True:
                code = fmt("".join(secrets.choice(ALPHABET) for _ in range(9)))
                if h(code) not in seen: break
            seen.add(h(code)); cid = f"C-{start + k:04d}"
            entry = {"id": cid, "h": h(code), "cree": day}
            if classe: entry["classe"] = classe
            d["codes"].append(entry); rows.append((cid, classe, code, day))
        errs = verifier(d)
        if errs: print("\n".join("ERREUR : " + e for e in errs)); return 1
        save(d)
        new_file = not out.exists()
        with open(out, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            if new_file: w.writerow(["identifiant", "classe", "code d'inscription", "créé le", "famille (à remplir par l'école)"])
            for cid, cl, code, day in rows: w.writerow([cid, cl, code, day, ""])
        print(f"{n} code(s) créé(s) pour la classe « {classe or '-'} » : empreintes dans {ECOLE.relative_to(ROOT)}, codes dans {out.relative_to(ROOT)} (à remettre à l'école, jamais commité).")
        print(f"  identifiants {rows[0][0]} à {rows[-1][0]} ; les codes ne s'affichent pas ici, ils sont dans le fichier.")
        return 0
    if cmd == "retirer":
        for cid in argv[1:]:
            c = next((x for x in d["codes"] if x["id"] == cid), None)
            if not c: print("inconnu :", cid); return 1
            c["revoque"] = datetime.date.today().isoformat(); print("retiré :", cid)
        save(d); return 0
    if cmd == "acces":
        if argv[1] not in ("code", "libre"): print("acces : code ou libre"); return 1
        d["acces"] = argv[1]; save(d); print("accès :", argv[1]); return 0
    if cmd == "ecole":
        d["ecole"] = " ".join(argv[1:]); save(d); print("école :", d["ecole"]); return 0
    print(__doc__); return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
