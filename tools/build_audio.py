# -*- coding: utf-8 -*-
"""Chaîne audio de Corridor à la maison.

Ce que fait ce script, dans l'ordre :
  1. Relève chaque phrase que l'application peut dire (leçons + phrases.json), découpée exactement comme le moteur.
  2. Attribue un rôle : « conteur » (textes de lecture, histoires) ou « kono » (tout le reste).
  3. Tient un registre stable des numéros de phrases (voix/registre.json : on ajoute, on ne renumérote jamais).
  4. Écrit le script d'enregistrement : print/voix_a_enregistrer.md.
  5. Importe les enregistrements humains déposés dans voix/conteur/ et voix/kono/
     (fichier nommé par son numéro, ex. 012.m4a, ou par sa clé, ex. 3fa2c91b.m4a) -> app/audio/rec/<clé>.mp3
  6. Génère les phrases manquantes avec une voix de synthèse haut de gamme, si une clé est fournie :
       - Google (par défaut) : GOOGLE_TTS_API_KEY ; voix KONO_VOICE (défaut fr-FR-Chirp3-HD-Achird) et CONTEUR_VOICE
         (défaut fr-FR-Chirp3-HD-Sulafat, utilisée seulement si aucun enregistrement humain n'existe).
       - OpenAI (voix de la famille ChatGPT) : KONO_ENGINE=openai, OPENAI_API_KEY ; OPENAI_VOICE (défaut marin, conteur :
         OPENAI_CONTEUR_VOICE, défaut cedar), OPENAI_TTS_MODEL (défaut gpt-4o-mini-tts). Voix de synthèse : à signaler aux familles.
       - ElevenLabs : KONO_ENGINE=elevenlabs, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID (voix créée par « Voice Design »,
         jamais une voix copiée sur une personne réelle).
     -> app/audio/gen/<clé>.mp3
  7. Écrit app/audio/manifest.json (enregistrement humain prioritaire sur la synthèse).

Usage :
  python3 tools/build_audio.py            tout le cycle ci-dessus
  python3 tools/build_audio.py essai      le test à l'aveugle : 10 phrases dites par plusieurs voix,
                                          dans print/essai_voix/ (fichiers numérotés, la correspondance est dans cle.txt)
"""
import base64, json, os, pathlib, re, subprocess, sys, urllib.request, datetime, random

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
VOIX = ROOT / "voix"
AUDIO = APP / "audio"
APPNAME = "Corridor à la maison"

# ---------- même découpage et même clé que app.js ----------
def norm(t): return str(t or "").replace("«", "").replace("»", "").replace("★", " étoile ")
def sentences(t): return [p.strip() for p in re.findall(r"[^.!?…]+[.!?…]*", norm(t)) if p.strip()]
def key_of(t):
    s = re.sub(r"\s+", " ", norm(t)).strip()
    h = 0x811c9dc5
    for x in s.encode("utf-8"):
        h ^= x; h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"

WORD = {"velo": "vélo"}

def variants(t):
    """{e} : les deux accords ; {prenom} : phrase exclue (dite par la tablette, car le prénom change)."""
    out = []
    for v in ([t.replace("{e}", ""), t.replace("{e}", "e")] if "{e}" in t else [t]):
        out.extend(s for s in sentences(v) if "{prenom}" not in s)
    return out

def err_text(e): return e if isinstance(e, str) else (e or {}).get("text", "")

def collect():
    ph = json.loads((APP / "phrases.json").read_text(encoding="utf-8"))
    idx = json.loads((APP / "lessons" / "index.json").read_text(encoding="utf-8"))
    items = []  # (rôle, phrase, origine)
    def add(role, text, origin):
        if not text: return
        if role == "conteur":   # le conteur lit chaque phrase du texte d'un seul souffle : une unité = un élément du texte
            items.append((role, re.sub(r"\s+", " ", norm(text)).strip(), origin)); return
        for s in variants(text): items.append((role, re.sub(r"\s+", " ", s).strip(), origin))
    for k, v in ph.items():
        if k in ("_note", "clips"): continue
        for t in (v if isinstance(v, list) else [v]): add("kono", t, "moteur")
    for c in ph.get("clips", []): add("kono", c.get("kono"), "remplacement de Maman")
    def question(st, origin):
        for e in (st.get("errors") or {}).values(): add("kono", err_text(e), origin)
        for h in st.get("hints") or []: add("kono", h, origin)
        add("kono", st.get("sol"), origin)
        add("kono", st.get("ask"), origin)
        if st.get("type") == "choice":
            kind = st.get("optionKind") or ("text" if any(len(str(o)) > 4 for o in st.get("options", [])) else "plain")
            if kind == "text":
                for o in st["options"]: add("kono", str(o), origin + " (option)")
            if kind == "icon":
                for o in st["options"]: add("kono", WORD.get(o, o), origin + " (option)")
    def step(st, origin):
        t = st.get("type")
        spoken = st.get("say") or st.get("text")
        if t in ("say", "part", "number", "choice", "paper", "record", "drill", "manip", "order"): add("kono", spoken, origin)
        if t in ("number", "choice", "manip", "order"): question(st, origin)
        if t == "demo":
            for ln in st["lines"]: add("kono", ln.get("say") or ln.get("text"), origin)
        if t == "review":
            for f in st.get("fallback", []): step(f, origin)
        if t == "reading":
            for s in st["passage"]: add("conteur", s, origin)
        if t == "story":
            for s in st["sentences"]: add("conteur", s, origin)
            if not st.get("skipVocab"):
                for v in st.get("vocab", []): add("kono", v["say"], origin)
            for q in st.get("questions", []): step(q, origin)
            add("kono", st.get("retell"), origin)
    for l in idx["lessons"]:
        L = json.loads((APP / "lessons" / f'{l["id"]}.json').read_text(encoding="utf-8"))
        for st in L["steps"]: step(st, L["title"])
        for lv in L.get("paper", {}).get("levels", []):
            for it in lv["items"]:
                for e in (it.get("errors") or {}).values(): add("kono", err_text(e), L["title"] + " (fiche)")
    # Phrases que le moteur assemble mais qui sont prévisibles (titres, jours, escales, rappel du niveau) : produites d'avance,
    # pour que l'enfant n'entende qu'une voix. Même gabarit que app.js (screenChild, escOpen, recapOf) ; le prénom et les nombres
    # tirés au hasard restent dits par la tablette.
    for l in idx["lessons"]:
        L = json.loads((APP / "lessons" / f'{l["id"]}.json').read_text(encoding="utf-8")); title = l["title"]
        for t in (f"{title}.", f'{ph["recapToday"]} « {title} ».', f'{ph["recapLast"]} « {title} ».', f'{ph["recapResume"]} « {title} ».'):
            add("kono", t, "moteur (assemblée)")
        if L.get("day") and ph.get("ticketLocked"):
            add("kono", ph["ticketLocked"].replace("{jour}", L["day"]).replace("{titre}", title), "moteur (assemblée)")
    for pid, E in (idx.get("escales") or {}).items():
        for i, e in enumerate(E):
            if i == len(E) - 1:
                if ph.get("escaleEnd"): add("kono", ph["escaleEnd"].replace("{nom}", e["name"]), "moteur (escale)")
                continue
            nxt = E[i + 1]["name"]; n = sum(1 for l in idx["lessons"] if l["parcours"] == pid and l.get("escale") == e["n"])
            add("kono", f'De {e["name"]} à {nxt}.', "moteur (escale)")
            if n and ph.get("escaleLeg"):
                for k in range(n + 1): add("kono", ph["escaleLeg"].replace("{de}", e["name"]).replace("{a}", nxt).replace("{n}", str(n)).replace("{faites}", str(k)), "moteur (escale)")
    seen, uniq = set(), []
    for role, s, o in items:
        k = key_of(s)
        if k in seen: continue
        seen.add(k); uniq.append({"key": k, "role": role, "text": s, "origin": o})
    return uniq

def registry(entries):
    path = VOIX / "registre.json"; VOIX.mkdir(exist_ok=True)
    reg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    n = max([int(v) for v in reg.values()] or [0])
    for e in entries:
        if e["key"] not in reg: n += 1; reg[e["key"]] = n
        e["n"] = reg[e["key"]]
    path.write_text(json.dumps(reg, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    return reg

def import_recordings(entries):
    by_n = {e["n"]: e["key"] for e in entries}; keys = {e["key"] for e in entries}
    (AUDIO / "rec").mkdir(parents=True, exist_ok=True); done = 0
    for role in ("conteur", "kono"):
        d = VOIX / role
        if not d.exists(): continue
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.name.startswith("."): continue
            stem = f.stem.lower()
            key = stem if stem in keys else by_n.get(int(stem)) if stem.isdigit() else None
            if not key: print("  ignoré (nom non reconnu) :", f.name); continue
            out = AUDIO / "rec" / f"{key}.mp3"
            if out.exists() and out.stat().st_mtime >= f.stat().st_mtime: continue
            filt = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-16:TP=-1.5"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-ac", "1", "-ar", "44100", "-af", filt, "-b:a", "64k", str(out)], check=True)
            done += 1
    return done

def tts_google(text, voice, rate):
    api = os.environ["GOOGLE_TTS_API_KEY"]
    body = json.dumps({"input": {"text": text}, "voice": {"languageCode": voice[:5], "name": voice},
                       "audioConfig": {"audioEncoding": "MP3", "speakingRate": rate}}).encode()
    req = urllib.request.Request(f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api}", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return base64.b64decode(json.loads(r.read())["audioContent"])

def tts_eleven(text, voice_id):
    body = json.dumps({"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
                       "voice_settings": {"stability": 0.55, "similarity_boost": 0.75}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}", data=body,
                                 headers={"Content-Type": "application/json", "xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

OPENAI_STYLE = {
    "kono": "Parle en français de France. Tu es Kono, un martin-pêcheur bienveillant qui guide un enfant de 5 à 8 ans : voix chaleureuse, souriante, calme, débit posé, articulation nette.",
    "conteur": "Parle en français de France. Tu racontes une histoire à un enfant de 5 à 8 ans : voix douce et expressive, débit lent, pauses naturelles.",
}
def tts_openai(text, voice, role="kono"):
    body = json.dumps({"model": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "voice": voice, "input": text,
                       "instructions": OPENAI_STYLE.get(role, OPENAI_STYLE["kono"]), "response_format": "mp3"}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

def generate(entries):
    engine = os.environ.get("KONO_ENGINE", "google")
    if engine == "elevenlabs" and not (os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_VOICE_ID")):
        return 0, "ELEVENLABS_API_KEY ou ELEVENLABS_VOICE_ID manquant : génération sautée"
    if engine == "openai" and not os.environ.get("OPENAI_API_KEY"):
        return 0, "pas de clé OPENAI_API_KEY : génération sautée"
    if engine == "google" and not os.environ.get("GOOGLE_TTS_API_KEY"):
        return 0, "pas de clé GOOGLE_TTS_API_KEY : génération sautée"
    kv = os.environ.get("KONO_VOICE", "fr-FR-Chirp3-HD-Achird"); cv = os.environ.get("CONTEUR_VOICE", "fr-FR-Chirp3-HD-Sulafat")
    (AUDIO / "gen").mkdir(parents=True, exist_ok=True); n = 0
    for e in entries:
        out = AUDIO / "gen" / f'{e["key"]}.mp3'
        if out.exists() or (AUDIO / "rec" / f'{e["key"]}.mp3').exists(): continue
        if engine == "elevenlabs": data = tts_eleven(e["text"], os.environ["ELEVENLABS_VOICE_ID"])
        elif engine == "openai": data = tts_openai(e["text"], os.environ.get("OPENAI_VOICE", "marin") if e["role"] == "kono" else os.environ.get("OPENAI_CONTEUR_VOICE", "cedar"), e["role"])
        else: data = tts_google(e["text"], kv if e["role"] == "kono" else cv, 0.95 if e["role"] == "kono" else 0.9)
        out.write_bytes(data); n += 1
    if engine == "openai": return n, f"OpenAI, Kono : {os.environ.get('OPENAI_VOICE', 'marin')}, conteur : {os.environ.get('OPENAI_CONTEUR_VOICE', 'cedar')}"
    return n, (f"ElevenLabs, voix {os.environ.get('ELEVENLABS_VOICE_ID')}" if engine == "elevenlabs" else f"Google, Kono : {kv}, conteur : {cv}")

ESSAI = [
    "Salut ! Moi, c'est Kono, le martin-pêcheur du fleuve.",
    "Regarde ce calcul : trente-huit plus sept.",
    "Trente-huit, c'est tout près de quarante. Il lui manque deux.",
    "Pas encore. Tu as écrit treize à côté du deux.",
    "Dix unités ! Touche-les pour fermer la dizaine.",
    "Poisson doré ! Tu t'es trompé, tu as cherché encore, et tu as trouvé.",
    "Combien de syllabes dans ce mot ? Bal… lon.",
    "Le panier de mangues tombe et roule jusqu'au fleuve !",
    "Une nouvelle escale sur le fleuve ! Regarde ton passeport.",
    "Séance terminée. Regarde tous les poissons que tu as pêchés !",
]
def essai():
    """Test à l'aveugle : les enfants écoutent, sans savoir qui est qui, et choisissent la voix de Kono."""
    voices = [v for v in os.environ.get("ESSAI_VOICES", "fr-FR-Chirp3-HD-Achird,fr-FR-Chirp3-HD-Puck,fr-FR-Chirp3-HD-Sadachbia,fr-FR-Chirp3-HD-Leda").split(",") if v]
    cands = []
    if os.environ.get("GOOGLE_TTS_API_KEY"): cands += [("google", v) for v in voices]
    if os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_VOICE_ID"): cands.append(("elevenlabs", os.environ["ELEVENLABS_VOICE_ID"]))
    if os.environ.get("OPENAI_API_KEY"): cands += [("openai", v) for v in os.environ.get("ESSAI_OPENAI_VOICES", "marin,cedar,coral,sage").split(",") if v]
    if not cands: print("Aucune clé : définir GOOGLE_TTS_API_KEY, OPENAI_API_KEY et/ou ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID."); return
    random.shuffle(cands)
    out = ROOT / "print" / "essai_voix"; out.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, (eng, v) in enumerate(cands, 1):
        audio = b"".join(tts_eleven(t, v) if eng == "elevenlabs" else tts_openai(t, v) if eng == "openai" else tts_google(t, v, 0.95) for t in ESSAI)
        (out / f"voix_{i}.mp3").write_bytes(audio); lines.append(f"voix_{i}.mp3 = {eng} {v}")
    (out / "cle.txt").write_text("À ouvrir seulement après le choix des enfants.\n" + "\n".join(lines), encoding="utf-8", newline="\n")
    print(f"{len(cands)} voix dans {out} (la correspondance est dans cle.txt)")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "essai": return essai()
    entries = collect(); registry(entries)
    nrec = import_recordings(entries)
    ngen, note = generate(entries)
    files = {}
    for e in entries:
        if (AUDIO / "rec" / f'{e["key"]}.mp3').exists(): files[e["key"]] = f'rec/{e["key"]}.mp3'
        elif (AUDIO / "gen" / f'{e["key"]}.mp3').exists(): files[e["key"]] = f'gen/{e["key"]}.mp3'
    (AUDIO / "manifest.json").write_text(json.dumps({"version": datetime.datetime.now().isoformat(timespec="seconds"), "files": files}, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    lines = [f"# Phrases à enregistrer · {APPNAME}", "",
             "Enregistrer une phrase par fichier, nommé par son numéro (ex. `012.m4a`), dans `voix/conteur/` ou `voix/kono/`.",
             "Pièce calme ; téléphone à 20 cm ; lire lentement, avec l'intonation d'un conte pour le rôle conteur.", ""]
    for role, titre in (("conteur", "Rôle conteur (voix humaine expressive)"), ("kono", "Rôle Kono (voix humaine, ou synthèse si une clé est fournie)")):
        rows = sorted([e for e in entries if e["role"] == role], key=lambda e: e["n"])
        lines += [f"## {titre}", "", "| N° | Texte | Séance | Statut |", "| --- | --- | --- | --- |"]
        for e in rows:
            st = "enregistrée" if files.get(e["key"], "").startswith("rec/") else "générée" if e["key"] in files else "à faire"
            lines.append(f'| {e["n"]:03d} | {e["text"]} | {e["origin"]} | {st} |')
        lines.append("")
    (ROOT / "print").mkdir(exist_ok=True)
    (ROOT / "print" / "voix_a_enregistrer.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    nk = sum(1 for e in entries if e["role"] == "kono"); nc = len(entries) - nk
    chars = sum(len(e["text"]) for e in entries)
    print(f"{len(entries)} phrases ({nk} Kono, {nc} conteur, {chars} caractères) · {len(files)} ont un audio · importés : {nrec} · générés : {ngen} ({note})")

if __name__ == "__main__":
    main()
