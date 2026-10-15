"""Aide de test : pendant un test, app/ecole.json est remplacé par une liste contenant un seul code d'inscription connu,
puis remis à l'identique. Le code de test n'existe que dans ce fichier et n'est jamais publié.

    from ecole_test import ecole_test, CODE
    with ecole_test():
        ...
"""
import contextlib, hashlib, json, pathlib
APP = pathlib.Path(__file__).resolve().parent.parent / "app"
ECOLE = APP / "ecole.json"
CODE = "TST-TST-TST"
def _h(code):
    s = "".join(ch for ch in code.upper() if ch.isalnum()).replace("O", "0").replace("I", "1").replace("L", "1")
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
@contextlib.contextmanager
def ecole_test():
    before = ECOLE.read_bytes() if ECOLE.exists() else None
    ECOLE.write_text(json.dumps({"schema": 1, "acces": "code", "ecole": "École de test", "codes": [{"id": "C-9999", "classe": "GS", "h": _h(CODE)}]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    try:
        yield CODE
    finally:
        if before is None: ECOLE.unlink(missing_ok=True)
        else: ECOLE.write_bytes(before)
