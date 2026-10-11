# -*- coding: utf-8 -*-
"""Contrôle des leçons selon CONTRAT_LECONS.md (§ 7). Rend 0 si tout est conforme, 1 sinon.
Usage : python3 tools/check_lessons.py [dossier app]   (par défaut : app/ du dépôt)
Bibliothèque standard seulement : il tourne sur la machine du générateur comme dans le workflow de déploiement."""
import json, pathlib, re, sys

STEP_TYPES = {"maman", "say", "review", "demo", "number", "choice", "paper", "record", "part", "drill", "reading", "story", "end"}
DRILL_KINDS = {"complement10", "complement-next-ten", "through10", "double", "table", "tf-complement", "count-tf", "decomp"}
SHOW_KINDS = {"title", "expr", "text", "numberline", "split", "tenframe", "fingers", "part", "word", "listen", "scenes"}
ROOT_KEYS = ["id", "parcours", "order", "week", "title", "domain", "programme", "objective", "escale", "steps", "paper"]
INDEX_KEYS = ["id", "parcours", "order", "week", "title", "escale"]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
COLOUR_RE = re.compile(r"\b(fiche|parcours|enfant)s? (bleue?s?|oranges?|vertes?|violettes?)\b", re.I)
SKIP_KEYS = {"id", "clip", "kind", "type", "parcours", "couleur", "who", "scenes", "input", "story", "lesson"}

def main(app):
    errs = []
    def err(m): errs.append(m)
    try: par = json.loads((app / "parcours.json").read_text(encoding="utf-8"))
    except Exception as e: print("parcours.json illisible :", e); return 1
    ids = [p.get("id") for p in par.get("parcours", [])]
    for p in par.get("parcours", []):
        if not ID_RE.match(str(p.get("id", ""))): err(f"parcours.json : identifiant invalide {p.get('id')!r}")
        for k in ("label", "classe", "age_min", "age_max", "couleur"):
            if k not in p: err(f"parcours.json : {p.get('id')} sans {k}")
    if len(set(ids)) != len(ids): err("parcours.json : identifiants en double")
    try: idx = json.loads((app / "lessons" / "index.json").read_text(encoding="utf-8"))
    except Exception as e: print("index.json illisible :", e); return 1
    if idx.get("schema") != 2: err(f"index.json : schema attendu 2, trouvé {idx.get('schema')!r}")
    if not re.match(r"^S\d+-\d{4}-\d{2}-\d{2}$", str(idx.get("version", ""))): err(f"index.json : version {idx.get('version')!r} hors format S<n>-AAAA-MM-JJ")
    esc = idx.get("escales") or {}
    if not isinstance(esc, dict): err("index.json : escales doit être un objet par parcours"); esc = {}
    for pid, lst in esc.items():
        if pid not in ids: err(f"index.json : escales pour un parcours inconnu {pid!r}")
        ns = [e.get("n") for e in lst]
        if sorted(ns) != list(range(1, len(ns) + 1)): err(f"index.json : escales[{pid}] numérotées {ns}, attendu 1..{len(ns)}")
        for e in lst:
            if not e.get("name") or not isinstance(e.get("sessions"), int): err(f"index.json : escale {pid}/{e.get('n')} sans name ou sessions")
    seen, orders = set(), {}
    files = {f.name for f in (app / "lessons").glob("*.json")} - {"index.json"}
    for e in idx.get("lessons", []):
        for k in INDEX_KEYS:
            if k not in e: err(f"index.json : entrée {e.get('id')!r} sans {k}")
        lid = str(e.get("id", ""))
        if not ID_RE.match(lid): err(f"index.json : identifiant de leçon invalide {lid!r}")
        if lid in seen: err(f"index.json : leçon {lid} en double")
        seen.add(lid)
        if "child" in e: err(f"index.json : {lid} porte encore child")
        if e.get("parcours") not in ids: err(f"index.json : {lid} parcours inconnu {e.get('parcours')!r}")
        key = (e.get("parcours"), e.get("order"))
        if key in orders: err(f"index.json : order {e.get('order')} en double dans le parcours {e.get('parcours')} ({orders[key]} et {lid})")
        orders[key] = lid
        if not re.match(r"^S\d+$", str(e.get("week", ""))): err(f"index.json : {lid} week {e.get('week')!r} hors format S<n>")
        if e.get("parcours") in esc and e.get("escale") not in [x.get("n") for x in esc[e["parcours"]]]: err(f"index.json : {lid} escale {e.get('escale')} absente de escales[{e.get('parcours')}]")
        fn = f"{lid}.json"
        if fn not in files: err(f"index.json : fichier manquant lessons/{fn}"); continue
        check_lesson(app / "lessons" / fn, e, ids, err)
    for fn in sorted(files - {f"{i}.json" for i in seen}): err(f"lessons/{fn} n'est pas dans l'index")
    for m in errs: print("ERREUR :", m)
    print(f"{len(seen)} leçon(s), {len(errs)} erreur(s)")
    return 1 if errs else 0

def check_lesson(path, entry, ids, err):
    lid = entry["id"]
    try: L = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e: err(f"{lid} : JSON illisible ({e})"); return
    for k in ROOT_KEYS:
        if k not in L: err(f"{lid} : clé racine manquante {k}")
    if "child" in L: err(f"{lid} : porte encore child")
    for k in ("id", "parcours", "order", "week", "title", "escale"):
        if k in L and L[k] != entry.get(k): err(f"{lid} : {k} diffère entre la leçon ({L[k]!r}) et l'index ({entry.get(k)!r})")
    if L.get("parcours") not in ids: err(f"{lid} : parcours inconnu {L.get('parcours')!r}")
    for i, st in enumerate(L.get("steps", [])):
        t = st.get("type")
        if t not in STEP_TYPES: err(f"{lid} : étape {i} type inconnu {t!r}")
        if t == "drill":
            for k in st.get("kinds", []):
                kk = k.get("kind") if isinstance(k, dict) else k
                if kk not in DRILL_KINDS: err(f"{lid} : étape {i} kind d'automatisme inconnu {kk!r}")
            if st.get("input") not in ("keypad", "choice"): err(f"{lid} : étape {i} input doit être keypad ou choice")
        for v in walk_shows(st):
            if v.get("kind") not in SHOW_KINDS: err(f"{lid} : étape {i} dessin inconnu {v.get('kind')!r}")
        if t == "review":
            for f in st.get("fallback", []):
                if f.get("type") not in STEP_TYPES: err(f"{lid} : étape {i} fallback de type inconnu {f.get('type')!r}")
    paper = L.get("paper") or {}
    levels = paper.get("levels") or []
    if not any(lv.get("who", "seul") == "seul" for lv in levels): err(f"{lid} : la fiche n'a aucun niveau « seul »")
    for lv in levels:
        for it in lv.get("items", []):
            if "answer" in it and not isinstance(it.get("errors", {}), dict): err(f"{lid} : fiche {it.get('id')} errors doit être un objet")
            for k in (it.get("errors") or {}):
                if not isinstance(k, str): err(f"{lid} : fiche {it.get('id')} clé d'erreur non textuelle {k!r}")
    for where, txt in walk_text(L):
        if COLOUR_RE.search(txt): err(f"{lid} : couleur utilisée comme identité dans {where} : « {txt[:60]} »")

def walk_shows(st):
    out = list(st.get("show") or []) + list(st.get("after") or [])
    for ln in st.get("lines") or []: out += ln.get("show") or []
    for q in st.get("questions") or []: out += q.get("show") or []
    for f in st.get("fallback") or []: out += walk_shows(f)
    return [v for v in out if isinstance(v, dict)]

def walk_text(o, where="racine"):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in SKIP_KEYS: continue
            yield from walk_text(v, f"{where}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk_text(v, f"{where}[{i}]")
    elif isinstance(o, str): yield where, o

if __name__ == "__main__":
    app = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / "app"
    sys.exit(main(app))
