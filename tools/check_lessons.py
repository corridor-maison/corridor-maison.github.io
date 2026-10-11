# -*- coding: utf-8 -*-
"""Contrôle des leçons selon CONTRAT_LECONS.md (§ 7 et annexe A). Rend 0 si tout est conforme, 1 sinon.
Usage : python3 tools/check_lessons.py [dossier app]   (par défaut : app/ du dépôt)
Bibliothèque standard seulement : il tourne sur la machine du générateur comme dans le workflow de déploiement."""
import json, pathlib, re, sys

STEP_TYPES = {"maman", "say", "review", "demo", "number", "choice", "manip", "order", "paper", "record", "part", "drill", "reading", "story", "end"}
DRILL_KINDS = {"complement10", "complement-next-ten", "through10", "double", "table", "tf-complement", "count-tf", "decomp"}
SHOW_KINDS = {"title", "expr", "text", "numberline", "split", "tenframe", "fingers", "part", "word", "listen", "scenes",
              "bar", "blocks", "hidden", "icon", "items", "syllables"}
MANIP_MODES = {"tenframe": ("goal",), "blocks": (), "jumps": ("from", "to", "start")}
OPTION_KINDS = {"text", "icon", "dots"}
ROOT_KEYS = ["id", "parcours", "order", "week", "title", "domain", "programme", "objective", "escale", "steps", "paper"]
INDEX_KEYS = ["id", "parcours", "order", "week", "title", "escale"]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
COLOUR_RE = re.compile(r"\b(fiche|parcours|enfant)s? (bleue?s?|oranges?|vertes?|violettes?)\b", re.I)
SKIP_KEYS = {"id", "clip", "kind", "type", "parcours", "couleur", "who", "scenes", "input", "story", "lesson", "mode", "item", "name", "goal", "optionKind"}

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

def is_bool(v): return isinstance(v, bool)
def is_int(v): return isinstance(v, int) and not isinstance(v, bool)

def check_step(lid, i, st, err, where="étape"):
    t = st.get("type")
    if t not in STEP_TYPES: err(f"{lid} : {where} {i} type inconnu {t!r}"); return
    if t == "drill":
        for k in st.get("kinds", []):
            kk = k.get("kind") if isinstance(k, dict) else k
            if kk not in DRILL_KINDS: err(f"{lid} : {where} {i} kind d'automatisme inconnu {kk!r}")
        if st.get("input") not in ("keypad", "choice"): err(f"{lid} : {where} {i} input doit être keypad ou choice")
    if t == "choice" and "optionKind" in st and st["optionKind"] not in OPTION_KINDS: err(f"{lid} : {where} {i} optionKind inconnu {st['optionKind']!r}")
    if t == "manip":
        mode = st.get("mode")
        if mode not in MANIP_MODES: err(f"{lid} : {where} {i} mode de manipulation inconnu {mode!r}")
        else:
            for k in ("id", "answer") + MANIP_MODES[mode]:
                if k not in st: err(f"{lid} : {where} {i} manip {mode} sans {k}")
            if mode == "tenframe" and st.get("goal") not in ("add", "total"): err(f"{lid} : {where} {i} manip tenframe : goal doit être add ou total")
            if mode == "blocks" and not (is_int(st.get("add")) or is_int(st.get("addTens"))): err(f"{lid} : {where} {i} manip blocks sans add ni addTens")
    if t == "order":
        if not isinstance(st.get("scenes"), list) or not st.get("scenes"): err(f"{lid} : {where} {i} order sans scenes")
        if "id" not in st: err(f"{lid} : {where} {i} order sans id")
    if t == "story":
        for k in ("skipVocab", "order", "noImages"):
            if k in st and not is_bool(st[k]): err(f"{lid} : {where} {i} story : {k} doit être vrai ou faux")
        if "pass" in st and not (is_int(st["pass"]) and st["pass"] >= 1): err(f"{lid} : {where} {i} story : pass doit être un entier ≥ 1")
    if t == "reading" and "reread" in st and not is_bool(st["reread"]): err(f"{lid} : {where} {i} reading : reread doit être vrai ou faux")
    if t == "review":
        if "max" in st and not (is_int(st["max"]) and st["max"] >= 1): err(f"{lid} : {where} {i} review : max doit être un entier ≥ 1")
        if "fill" in st and not is_bool(st["fill"]): err(f"{lid} : {where} {i} review : fill doit être vrai ou faux")
        for j, f in enumerate(st.get("fallback", [])): check_step(lid, f"{i}.fallback[{j}]", f, err)
    check_errors(lid, f"{where} {i}", st.get("errors"), err)
    for v in walk_shows(st):
        if v.get("kind") not in SHOW_KINDS: err(f"{lid} : {where} {i} dessin inconnu {v.get('kind')!r}")

def check_errors(lid, where, errors, err):
    if errors is None: return
    if not isinstance(errors, dict): err(f"{lid} : {where} errors doit être un objet"); return
    for k, e in errors.items():
        if not isinstance(k, str): err(f"{lid} : {where} clé d'erreur non textuelle {k!r}")
        if isinstance(e, str): continue
        if not isinstance(e, dict) or not isinstance(e.get("text"), str): err(f"{lid} : {where} erreur {k!r} : une phrase, ou un objet avec text"); continue
        for k2 in e:
            if k2 not in ("text", "show"): err(f"{lid} : {where} erreur {k!r} : clé inconnue {k2!r}")

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
    for i, st in enumerate(L.get("steps", [])): check_step(lid, i, st, err)
    paper = L.get("paper") or {}
    levels = paper.get("levels") or []
    if not any(lv.get("who", "seul") == "seul" for lv in levels): err(f"{lid} : la fiche n'a aucun niveau « seul »")
    for lv in levels:
        for it in lv.get("items", []):
            if "answer" in it: check_errors(lid, f"fiche {it.get('id')}", it.get("errors", {}), err)
    for where, txt in walk_text(L):
        if COLOUR_RE.search(txt): err(f"{lid} : couleur utilisée comme identité dans {where} : « {txt[:60]} »")

def walk_shows(st):
    out = list(st.get("show") or []) + list(st.get("after") or [])
    for ln in st.get("lines") or []: out += ln.get("show") or []
    for q in st.get("questions") or []: out += q.get("show") or []
    errors = st.get("errors")
    if isinstance(errors, dict):
        for e in errors.values():
            if isinstance(e, dict): out += e.get("show") or []
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
