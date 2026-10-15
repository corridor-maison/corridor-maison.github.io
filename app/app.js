/* Corridor à la maison — moteur de séances guidées par la voix (v0.3.3).
   Guide : Kono, le martin-pêcheur du fleuve Niger. Un profil par enfant, routé par son parcours (app/parcours.json).
   Une séance = un fichier JSON (lessons/*.json), en quatre temps : automatismes, leçon, lecture ou histoire, méthode.
   Le même fichier produit les fiches imprimables (tools/build_print.py) et la liste des phrases à enregistrer (tools/build_audio.py).
   Format des séances : CONTRAT_LECONS.md. */
'use strict';
(() => {
const VERSION = '0.3.5';
const APPNAME = 'Corridor à la maison';
const FAST = location.hash === '#test';
const app = document.getElementById('app');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sleep = ms => new Promise(r => setTimeout(r, FAST ? 5 : ms));
const pick = a => a[Math.floor(Math.random() * a.length)];
const rnd = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const shuffle = a => { const b = a.slice(); for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; };
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const $ = s => app.querySelector(s);
const WORD = { velo: 'vélo', jeton: 'jeton' };
const wordOf = n => WORD[n] || n;

/* ============================ données ============================ */
const KEY = 'kono-v1';   /* clé interne inchangée depuis la v0.1 : le suivi des tablettes est conservé */
const THEMES = ['bleu', 'orange', 'vert', 'violet'];
const kid = () => ({ runs: [], review: [], done: {}, records: {}, drillMisses: {}, skills: {}, measures: [], resume: null });
/* Un profil par enfant : prénom, garçon ou fille, date de naissance, classe et parcours (confirmés par un parent), couleur, suivi.
   Tout reste dans la tablette. Un identifiant de profil ne change jamais : il nomme les enregistrements et les phrases de Maman. */
const blank = () => ({ schema: 2, setup: false, pin: '', voice: { name: '', rate: 0.9 }, settings: { subtitles: false, sounds: true, gaucher: false, calme: false, contraste: false }, profiles: [] });
function newId(list) {
  const a = 'abcdefghjkmnpqrstuvwxyz23456789', b = new Uint8Array(4);
  try { crypto.getRandomValues(b); } catch (e) { for (let i = 0; i < 4; i++) b[i] = Math.floor(Math.random() * 256); }
  const id = Array.from(b, x => a[x % a.length]).join('');
  return (list || []).some(p => p.id === id) ? newId(list) : id;
}
/* Données de la v0.2 : les deux cases fixes (bleu, orange) deviennent deux profils. Le suivi est gardé tel quel. */
function fromV02(s, b) {
  Object.assign(b, { setup: !!s.setup, pin: s.pin || '', voice: Object.assign(b.voice, s.voice || {}), settings: Object.assign(b.settings, s.settings || {}) });
  const LEG = { bleu: 'ce1', orange: 'gs' };
  ['bleu', 'orange'].forEach(c => {
    const pr = Object.assign(kid(), (s.progress || {})[c] || {}), nm = String((s.names || {})[c] || '').trim();
    if (!nm && !pr.runs.length && !Object.keys(pr.done).length) return;
    b.profiles.push({ id: newId(b.profiles), name: nm, girl: !!(s.girl || {})[c], dob: '', classe: '', parcours: LEG[c], couleur: c, legacy: c, progress: pr });
  });
  b.migrate = true;
  return b;
}
/* Lit un état enregistré (schéma 2, ou v0.2 à migrer) et le complète avec les valeurs par défaut. */
function fromStore(s) {
  const b = blank();
  if (s && Array.isArray(s.profiles)) {
    Object.assign(b, s);
    b.settings = Object.assign(blank().settings, s.settings || {});
    b.profiles.forEach(p => { p.progress = Object.assign(kid(), p.progress || {}); });
  } else if (s && s.progress) fromV02(s, b);
  return b;
}
function loadStore() { try { return fromStore(JSON.parse(localStorage.getItem(KEY) || 'null')); } catch (e) { return blank(); } }
const S = loadStore();
/* Point de sauvegarde de la séance en cours : à chaque enregistrement, la position, les poissons et le temps passé
   sont mis à jour dans le profil, pour reprendre là où l'enfant s'est arrêté même si la tablette ferme l'application. */
function save() {
  try {
    if (P && child && child.progress.resume && child.progress.resume.run === P.run) Object.assign(child.progress.resume, { i: P.i, fish: P.fish, gold: P.gold, elapsed: Date.now() - P.run.start, ts: Date.now() });
    localStorage.setItem(KEY, JSON.stringify(S));
  } catch (e) {}
}

const DB = (() => {
  let p = null;
  const open = () => p || (p = new Promise((res, rej) => {
    if (!('indexedDB' in window)) return rej(new Error('pas de stockage'));
    const r = indexedDB.open('kono', 1);
    r.onupgradeneeded = () => { const d = r.result; d.createObjectStore('clips'); d.createObjectStore('recs', { keyPath: 'id', autoIncrement: true }); };
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
  }));
  const run = async (store, mode, fn) => { const d = await open(); return new Promise((res, rej) => { const t = d.transaction(store, mode); const q = fn(t.objectStore(store)); t.oncomplete = () => res(q ? q.result : undefined); t.onerror = () => rej(t.error); }); };
  const safe = f => async (...a) => { try { return await f(...a); } catch (e) { return undefined; } };
  return {
    getClip: safe(id => run('clips', 'readonly', s => s.get(id))),
    putClip: safe((id, b) => run('clips', 'readwrite', s => s.put(b, id))),
    delClip: safe(id => run('clips', 'readwrite', s => s.delete(id))),
    clipKeys: safe(() => run('clips', 'readonly', s => s.getAllKeys())),
    addRec: safe(r => run('recs', 'readwrite', s => s.add(r))),
    putRec: safe(r => run('recs', 'readwrite', s => s.put(r))),
    recs: safe(() => run('recs', 'readonly', s => s.getAll())),
    delRec: safe(id => run('recs', 'readwrite', s => s.delete(id))),
  };
})();

let CLIPS = [];
let LESSONS = {}, INDEX = [], ESCALES = {}, PARCOURS = [], PH = {}, AUDIO = { files: {} }, PROG = {}, ECOLE = { acces: 'libre', codes: [] };
async function getJSON(u) { const r = await fetch(u, { cache: 'no-cache' }); if (!r.ok) throw new Error(u); return r.json(); }
const parcoursOf = id => PARCOURS.find(p => p.id === id) || null;
const escalesOf = pid => ESCALES[pid] || [];
async function loadAll() {
  PARCOURS = (await getJSON('parcours.json')).parcours || [];
  const idx = await getJSON('lessons/index.json');
  if (idx.schema === undefined) {
    /* Index de la v0.2 (clé child) : accepté le temps d'une mise à jour, jamais au-delà. */
    const LEG = { bleu: 'ce1', orange: 'gs' };
    idx.lessons.forEach(l => { if (!l.parcours) l.parcours = LEG[l.child] || l.child; });
    idx.escales = Object.fromEntries(PARCOURS.map(p => [p.id, Array.isArray(idx.escales) ? idx.escales : []]));
  } else if (idx.schema !== 2) throw new Error('schema ' + idx.schema);
  INDEX = idx.lessons.slice().sort((a, b) => a.order - b.order);
  ESCALES = idx.escales || {};
  await Promise.all(INDEX.map(async l => { LESSONS[l.id] = await getJSON(`lessons/${l.id}.json`); }));
  PH = await getJSON('phrases.json');
  CLIPS = PH.clips || [];
  try { AUDIO = await getJSON('audio/manifest.json'); if (!AUDIO.files) AUDIO.files = {}; } catch (e) { AUDIO = { files: {} }; }
  /* La progression de chaque parcours (codes de compétences), quand elle est publiée. */
  for (const p of PARCOURS) { try { PROG[p.id] = await getJSON(`progression/${p.id}.json`); } catch (e) { PROG[p.id] = { skills: [], drillKinds: {} }; } }
  /* L'école : mode d'accès et empreintes des codes d'inscription (jamais les codes eux-mêmes). */
  try { ECOLE = await getJSON('ecole.json'); if (!Array.isArray(ECOLE.codes)) ECOLE.codes = []; } catch (e) { ECOLE = { acces: 'libre', codes: [] }; }
}
const skillLabel = (pid, code) => { const s = ((PROG[pid] || {}).skills || []).find(x => x.code === code); return s ? s.label : code; };

/* ============================ sons et voix ============================ */
let AC = null, analyser = null;
function audioCtx() {
  if (FAST) return null;
  try {
    if (!AC) { const C = window.AudioContext || window.webkitAudioContext; if (!C) return null; AC = new C(); analyser = AC.createAnalyser(); analyser.fftSize = 512; analyser.connect(AC.destination); }
    if (AC.state === 'suspended') AC.resume();
  } catch (e) { AC = null; }
  return AC;
}
/* Appelé à chaque toucher : le navigateur n'autorise le son qu'après un geste. */
document.addEventListener('pointerdown', () => { audioCtx(); }, { passive: true });

/* Bruitages fabriqués sur place : pas de fichier, pas de réseau. Doux, courts, jamais pendant que Kono parle. */
function sfx(kind) {
  if (!S.settings.sounds) return;
  const ac = audioCtx(); if (!ac || ac.state !== 'running') return;
  const t = ac.currentTime, out = ac.createGain(); out.gain.value = 0.16; out.connect(ac.destination);
  const tone = (f, at, dur, type = 'sine', vol = 1, f2) => {
    const o = ac.createOscillator(), g = ac.createGain(); o.type = type; o.frequency.setValueAtTime(f, t + at);
    if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + at + dur);
    g.gain.setValueAtTime(0.0001, t + at); g.gain.exponentialRampToValueAtTime(vol, t + at + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t + at + dur);
    o.connect(g); g.connect(out); o.start(t + at); o.stop(t + at + dur + 0.02);
  };
  const noise = (at, dur, vol, freq) => {
    const n = Math.floor(ac.sampleRate * dur), b = ac.createBuffer(1, n, ac.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain(); s.buffer = b; f.type = 'bandpass'; f.frequency.value = freq; g.gain.value = vol;
    s.connect(f); f.connect(g); g.connect(out); s.start(t + at);
  };
  switch (kind) {
    case 'tap': tone(660, 0, 0.06, 'sine', 0.5); break;
    case 'pop': tone(520, 0, 0.09, 'triangle', 0.8, 980); break;
    case 'unpop': tone(700, 0, 0.08, 'triangle', 0.5, 380); break;
    case 'good': tone(784, 0, 0.16, 'sine', 0.7); tone(988, 0.09, 0.16, 'sine', 0.7); tone(1319, 0.18, 0.32, 'sine', 0.6); break;
    case 'gold': tone(659, 0, 0.14); tone(880, 0.08, 0.14); tone(1109, 0.16, 0.14); tone(1319, 0.24, 0.4, 'sine', 0.7); break;
    case 'soft': tone(440, 0, 0.18, 'sine', 0.45); tone(392, 0.14, 0.26, 'sine', 0.4); break;
    case 'clac': noise(0, 0.08, 1.2, 1800); tone(180, 0.02, 0.18, 'triangle', 0.9, 120); break;
    case 'whoosh': noise(0, 0.32, 0.7, 900); break;
    case 'hop': tone(400, 0, 0.14, 'sine', 0.6, 820); break;
    case 'next': tone(587, 0, 0.08, 'sine', 0.4); tone(784, 0.06, 0.1, 'sine', 0.4); break;
  }
}

let child = null; /* le profil de l'enfant en cours */
const name = p => ((p || child) && (p || child).name) || '';
const profileOf = id => S.profiles.find(p => p.id === id) || null;
const progressOfRec = r => (profileOf(r.profile) || {}).progress;
function ageOf(dob) {
  if (!dob) return null;
  const d = new Date(dob + 'T00:00:00'), t = new Date(); if (isNaN(d)) return null;
  let a = t.getFullYear() - d.getFullYear(); if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a--;
  return a;
}
function fill(t) {
  if (!t) return '';
  const n = name();
  let s = n ? String(t).replace(/\{prenom\}/g, n) : String(t).replace(/ ?\{prenom\}/g, '');
  return s.replace(/\{e\}/g, child && child.girl ? 'e' : '');
}
/* Même découpage et même clé que tools/build_audio.py : une phrase = un fichier audio. */
const normSpeech = t => String(t || '').replace(/[«»]/g, '').replace(/★/g, ' étoile ');
const sentences = t => (normSpeech(t).match(/[^.!?…]+[.!?…]*/g) || []).map(p => p.trim()).filter(Boolean);
function keyOf(t) {
  const s = normSpeech(t).replace(/\s+/g, ' ').trim(); const b = new TextEncoder().encode(s);
  let h = 0x811c9dc5; for (const x of b) { h ^= x; h = Math.imul(h, 0x01000193) >>> 0; }
  return h.toString(16).padStart(8, '0');
}
let voices = [];
function loadVoices() { try { voices = speechSynthesis.getVoices().filter(v => /^fr/i.test(v.lang)); } catch (e) { voices = []; } }
if ('speechSynthesis' in window) { loadVoices(); try { speechSynthesis.onvoiceschanged = loadVoices; } catch (e) {} }
const pickVoice = () => voices.find(v => v.name === S.voice.name) || voices.find(v => /fr[-_]FR/i.test(v.lang)) || voices[0] || null;
/* Sans voix française ni audio préparé, l'enfant n'entendrait rien : on affiche alors les sous-titres. */
const mustSubtitle = () => !FAST && !Object.keys(AUDIO.files).length && !voices.length;

let token = 0, curAudio = null, lipRAF = 0;
function setTalking(on) { document.body.classList.toggle('talking', !!on); if (!on) { cancelAnimationFrame(lipRAF); document.body.classList.remove('lipsync'); setBeak(0); } }
function setBeak(v) { document.documentElement.style.setProperty('--beak', v.toFixed(3)); }
function stopSpeech() {
  token++;
  try { speechSynthesis.cancel(); } catch (e) {}
  if (curAudio) { try { curAudio.pause(); } catch (e) {} curAudio = null; }
  setTalking(false);
}
/* Le bec de Kono suit le volume réel de la voix quand elle vient d'un fichier audio. */
function lipsync(a) {
  const ac = audioCtx(); if (!ac || ac.state !== 'running' || !analyser) return false;
  try { const src = ac.createMediaElementSource(a); src.connect(analyser); } catch (e) { return false; }
  const buf = new Uint8Array(analyser.fftSize);
  document.body.classList.add('lipsync');
  const loop = () => {
    if (curAudio !== a) return;
    analyser.getByteTimeDomainData(buf); let s = 0; for (const x of buf) { const v = (x - 128) / 128; s += v * v; }
    setBeak(Math.min(1, Math.sqrt(s / buf.length) * 5));
    lipRAF = requestAnimationFrame(loop);
  };
  lipRAF = requestAnimationFrame(loop);
  return true;
}
function playFile(src, withLips) {
  return new Promise(res => {
    const a = new Audio(src); a.crossOrigin = 'anonymous'; curAudio = a; let done = false;
    const fin = ok => { if (!done) { done = true; clearTimeout(t); res(ok); } };
    const t = setTimeout(() => fin(true), 60000);
    a.onended = () => fin(true); a.onerror = () => fin(false);
    if (withLips) lipsync(a);
    a.play().catch(() => fin(false));
  });
}
function ttsOne(text) {
  return new Promise(res => {
    if (FAST || !('speechSynthesis' in window)) { setTimeout(res, FAST ? 5 : Math.min(7000, 500 + text.length * 60)); return; }
    let done = false; const fin = () => { if (!done) { done = true; clearTimeout(t); res(); } };
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'fr-FR'; const v = pickVoice(); if (v) u.voice = v; u.rate = S.voice.rate || 0.9;
    u.onend = fin; u.onerror = fin;
    const t = setTimeout(fin, 3000 + text.length * 120 / u.rate);
    try { speechSynthesis.speak(u); } catch (e) { fin(); }
  });
}
async function speakOne(text) {
  if (FAST) (window.__spoken || (window.__spoken = [])).push(text);   /* test : relevé de tout ce qui est dit */
  const f = AUDIO.files[keyOf(text)];
  if (f && !FAST) { const ok = await playFile('audio/' + f, true); if (ok) return; }
  await ttsOne(text);
}
/* Voix du conteur : un élément de texte = un enregistrement, sinon découpage normal. */
async function speakWhole(text) {
  const f = AUDIO.files[keyOf(text)];
  if (!f || FAST) return speak(text);
  stopSpeech(); const my = token; setTalking(true);
  await playFile('audio/' + f, false);
  if (my === token) setTalking(false);
  return my === token;
}
/* onSentence(i) est appelé avant chaque phrase : sert au surlignage de la lecture. */
async function speak(text, onSentence) {
  stopSpeech(); const my = token;
  const parts = sentences(text);
  setTalking(true);
  for (let i = 0; i < parts.length; i++) { if (my !== token) return false; if (onSentence) onSentence(i); await speakOne(parts[i]); }
  if (my === token) setTalking(false);
  return my === token;
}
/* Une phrase « par enfant » (bonjour, fin) est enregistrée une fois par profil, sous la clé <phrase>@<profil>. */
function clipKey(id, p) { const def = CLIPS.find(c => c.id === id); return def && def.perChild && (p || child) ? `${id}@${(p || child).id}` : id; }
async function hasClip(id) { return !!(await DB.getClip(clipKey(id))); }
async function playClip(id, onMaman) {
  const def = CLIPS.find(c => c.id === id);
  const blob = await DB.getClip(clipKey(id));
  if (blob && !FAST) {
    stopSpeech(); if (onMaman) onMaman(true);
    await playFile(URL.createObjectURL(blob), false); curAudio = null; return true;
  }
  if (def && def.kono) { if (onMaman) onMaman(false, fill(def.kono)); await speak(fill(def.kono)); }
  return false;
}
/* ============================ Kono ============================ */
/* Martin-pêcheur huppé, l'oiseau du fleuve. Vu de face pour regarder l'enfant.
   Il respire, cligne des yeux, ouvre le bec quand il parle, et change d'expression (classe mood-*). */
const KONO = `<svg class="kono" viewBox="0 0 200 212" aria-hidden="true">
<path d="M14 200 Q100 188 188 197" stroke="#7a5236" stroke-width="9" stroke-linecap="round" fill="none"/><path d="M152 195 q16 -18 34 -15 q-11 16 -34 15z" fill="#5e8f4e"/>
<path d="M86 182 v12 M79 195 h14 M114 182 v12 M107 195 h14" stroke="#e0662f" stroke-width="5" stroke-linecap="round"/>
<g class="k-all"><g class="k-body">
 <ellipse cx="100" cy="142" rx="50" ry="46" fill="#2b6cb0"/><ellipse cx="100" cy="150" rx="35" ry="36" fill="#ec8a3c"/>
 <g class="k-wing-l"><path d="M56 118 q-26 30 -8 62 q24 -6 32 -40z" fill="#1d5490"/><path d="M50 140 l14 -4 M48 152 l16 -4 M50 164 l14 -4" stroke="#79c6d4" stroke-width="3" stroke-linecap="round"/></g>
 <g class="k-wing-r"><path d="M144 118 q26 30 8 62 q-24 -6 -32 -40z" fill="#1d5490"/><path d="M150 140 l-14 -4 M152 152 l-16 -4 M150 164 l-14 -4" stroke="#79c6d4" stroke-width="3" stroke-linecap="round"/></g>
</g><g class="k-head">
 <path d="M66 46 q6 -34 36 -36 q-7 9 -5 16 q15 -15 33 -8 q-11 4 -15 15 q12 -4 20 4 q-12 2 -16 10z" fill="#2fb7c4"/><path d="M84 30 l8 6 M100 22 l4 8 M118 22 l-2 8" stroke="#16416e" stroke-width="3" stroke-linecap="round"/>
 <circle cx="100" cy="84" r="50" fill="#2b6cb0"/>
 <path d="M58 70 q20 -10 40 -2 q20 -8 44 2" stroke="#2fb7c4" stroke-width="4" fill="none" opacity=".55"/>
 <ellipse cx="60" cy="104" rx="15" ry="11" fill="#ec8a3c"/><ellipse cx="140" cy="104" rx="15" ry="11" fill="#ec8a3c"/>
 <ellipse cx="100" cy="126" rx="22" ry="9" fill="#fff4e4"/>
 <g class="k-eyes-open"><circle cx="79" cy="82" r="16" fill="#fff"/><circle cx="121" cy="82" r="16" fill="#fff"/>
  <g class="k-pupils"><circle cx="81" cy="84" r="9.5" fill="#1b2430"/><circle cx="123" cy="84" r="9.5" fill="#1b2430"/><circle cx="85" cy="79" r="3.6" fill="#fff"/><circle cx="127" cy="79" r="3.6" fill="#fff"/></g>
  <g class="k-lids"><ellipse cx="79" cy="82" rx="17" ry="17" fill="#2b6cb0"/><ellipse cx="121" cy="82" rx="17" ry="17" fill="#2b6cb0"/></g></g>
 <g class="k-eyes-happy"><path d="M66 86 q13 -16 26 0 M108 86 q13 -16 26 0" stroke="#1b2430" stroke-width="5.5" fill="none" stroke-linecap="round"/></g>
 <g class="k-brows"><path d="M64 60 q12 -6 26 2 M136 60 q-12 -6 -26 2" stroke="#16416e" stroke-width="5" fill="none" stroke-linecap="round"/></g>
 <ellipse class="k-mouth" cx="100" cy="106" rx="9" ry="8" fill="#7a1d12"/>
 <path class="k-low" d="M90 103 L110 103 L100 127 Z" fill="#c23a22"/>
 <path d="M84 95 Q100 90 116 95 L100 115 Z" fill="#e8502f"/>
</g></g></svg>`;
function mood(m) { const g = document.querySelector('.guide .kono'); if (!g) return; g.classList.remove('mood-happy', 'mood-oops', 'mood-think', 'mood-listen'); if (m) { void g.getBoundingClientRect(); g.classList.add('mood-' + m); } }

/* ============================ dessins ============================ */
const ICON = (n, cls = '') => `<img class="ic ${cls}" src="img/${esc(n)}.svg" alt="${esc(wordOf(n))}" draggable="false">`;
const UI = {
  home: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 24 L24 9 L40 24" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 22 V39 H35 V22" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"/></svg>',
  next: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 24 H36 M25 12 L37 24 L25 36" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  check: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 25 L20 35 L38 13" fill="none" stroke="currentColor" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  back: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M38 24 H12 M23 12 L11 24 L23 36" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  del: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M17 10 H40 V38 H17 L5 24 Z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/><path d="M22 18 L33 30 M33 18 L22 30" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>',
  undo: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M14 18 H30 a9 9 0 0 1 0 18 H18" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/><path d="M20 10 L12 18 L20 26" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  play: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M16 10 L38 24 L16 38 Z" fill="currentColor"/></svg>',
  redo: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M36 22 a13 13 0 1 1 -4 -10" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/><path d="M34 4 V14 H24" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  ear: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M12 20 a12 12 0 1 1 22 7 c-3 4 -6 5 -6 10 a6 6 0 0 1 -11 2" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/><path d="M20 22 a4 4 0 1 1 7 3" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>',
  speaker: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 19 H16 L26 10 V38 L16 29 H8 Z" fill="currentColor"/><path d="M32 17 q5 7 0 14 M36 12 q10 12 0 24" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>',
  mic: '<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="17" y="6" width="14" height="24" rx="7" fill="currentColor"/><path d="M11 22 a13 13 0 0 0 26 0 M24 35 V42 M17 42 H31" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>',
  stop: '<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="13" y="13" width="22" height="22" rx="4" fill="currentColor"/></svg>',
  paper: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M12 6 H30 L38 14 V42 H12 Z" fill="#fff" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/><path d="M18 22 H32 M18 29 H32 M18 36 H26" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/></svg>',
  heart: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 40 C6 28 6 12 16 10 C21 9 24 14 24 14 C24 14 27 9 32 10 C42 12 42 28 24 40 Z" fill="currentColor"/></svg>',
  skip: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 12 L26 24 L10 36 Z M26 12 L40 24 L26 36 Z" fill="currentColor"/></svg>',
};
/* Les quatre temps d'une séance, en images : chrono, ampoule, livre, bulle. */
const PART_ICON = {
  1: '<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="27" r="15" fill="none" stroke="currentColor" stroke-width="4.5"/><path d="M24 27 V18 M19 6 H29 M24 6 V12" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/></svg>',
  2: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M17 30 a12 12 0 1 1 14 0 V35 H17 Z" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linejoin="round"/><path d="M18 41 H30" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/></svg>',
  3: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 13 C18 9 11 9 6 11 V38 C11 36 18 36 24 40 C30 36 37 36 42 38 V11 C37 9 30 9 24 13 Z M24 13 V40" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/></svg>',
  4: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 12 H40 V32 H22 L13 40 V32 H8 Z" fill="none" stroke="currentColor" stroke-width="4.5" stroke-linejoin="round"/><path d="M16 22 H32" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/></svg>',
};
/* Une image par séance, d'après son domaine : l'enfant qui ne lit pas encore reconnaît la séance, et Kono la nomme au toucher. */
const DOMAIN_ICON = {
  nombres: '<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="4" y="13" width="40" height="22" rx="3" fill="none" stroke="currentColor" stroke-width="3.5"/><path d="M12 13 V35 M20 13 V35 M28 13 V35 M36 13 V35 M4 24 H44" stroke="currentColor" stroke-width="2.5"/><circle cx="8" cy="18.5" r="2.6" fill="currentColor"/><circle cx="16" cy="18.5" r="2.6" fill="currentColor"/><circle cx="24" cy="18.5" r="2.6" fill="currentColor"/></svg>',
  problemes: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M7 19 H41 L37 40 H11 Z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/><path d="M15 19 L24 7 L33 19" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 26 V33 M24 26 V33 M31 26 V33" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></svg>',
  'langage oral': '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 10 H40 V31 H22 L13 39 V31 H8 Z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/><circle cx="16" cy="20.5" r="2.8" fill="currentColor"/><circle cx="24" cy="20.5" r="2.8" fill="currentColor"/><circle cx="32" cy="20.5" r="2.8" fill="currentColor"/></svg>',
  lecture: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 13 C18 9 11 9 6 11 V38 C11 36 18 36 24 40 C30 36 37 36 42 38 V11 C37 9 30 9 24 13 Z M24 13 V40" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/></svg>',
  revision: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M36 22 a13 13 0 1 1 -4 -10" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/><path d="M34 4 V14 H24" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  autre: '<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="9" fill="currentColor"/><path d="M24 4 V10 M24 38 V44 M4 24 H10 M38 24 H44 M10 10 L14 14 M34 34 L38 38 M10 38 L14 34 M34 14 L38 10" stroke="currentColor" stroke-width="4" stroke-linecap="round"/></svg>',
};
const domainKey = d => String(d || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const domainIcon = L => DOMAIN_ICON[domainKey(L && L.domain)] || DOMAIN_ICON.autre;
const BOAT = `<g class="boat"><path d="M-32 0 Q0 15 32 0 L26 8 Q0 18 -26 8 Z" fill="#5a3a22"/><path d="M-13 1 Q-13 -13 0 -13 Q13 -13 13 1" fill="#fbe8d9" stroke="#c35713" stroke-width="3"/><path d="M-30 1 L-38 -6 M30 1 L38 -6" stroke="#5a3a22" stroke-width="4" stroke-linecap="round"/></g>`;
const FONT = 'Nunito, Andika, sans-serif';
function vNumberline(v) {
  const W = 640, x0 = 30, x1 = 610, y = 104, span = v.to - v.from; const X = n => x0 + (n - v.from) * (x1 - x0) / span;
  let s = `<line x1="${x0}" y1="${y}" x2="${x1}" y2="${y}" stroke="#22303c" stroke-width="3"/>`;
  for (let n = v.from; n <= v.to; n++) {
    const big = n % 10 === 0, mid = n % 5 === 0;
    s += `<line x1="${X(n)}" y1="${y - (big ? 12 : mid ? 9 : 6)}" x2="${X(n)}" y2="${y + (big ? 12 : mid ? 9 : 6)}" stroke="#22303c" stroke-width="${big ? 3 : 1.6}"/>`;
    if (big) s += `<text x="${X(n)}" y="${y + 38}" text-anchor="middle" font-size="22" font-family="${FONT}" font-weight="800" fill="#22303c">${n}</text>`;
  }
  (v.jumps || []).forEach(([a, b, lab], k) => {
    const xa = X(a), xb = X(b), h = 26 + (xb - xa) * 0.35, mx = (xa + xb) / 2;
    s += `<path class="arc" style="animation-delay:${k * 0.35}s" d="M${xa} ${y - 6} Q${mx} ${y - 6 - 2 * h} ${xb} ${y - 6}" fill="none" stroke="var(--c)" stroke-width="3.5" marker-end="url(#ar)" pathLength="1"/>`;
    s += `<text x="${mx}" y="${y - 12 - h}" text-anchor="middle" font-size="24" font-family="${FONT}" font-weight="800" fill="var(--c)">${esc(lab)}</text>`;
  });
  (v.marks || []).forEach(n => {
    s += `<circle cx="${X(n)}" cy="${y}" r="8" fill="var(--c)" stroke="#fff" stroke-width="2"/>`;
    if (n % 10 !== 0) s += `<text x="${X(n)}" y="${y + 38}" text-anchor="middle" font-size="22" font-family="${FONT}" font-weight="800" fill="var(--c)">${n}</text>`;
  });
  return `<svg class="v-svg" viewBox="0 0 ${W} 150" role="img" aria-label="ligne des nombres de ${v.from} à ${v.to}"><defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--c)"/></marker></defs>${s}</svg>`;
}
function vSplit(v) {
  const [a, b] = v.parts, circ = (cx, cy, r, val, q) => `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${q ? '#fff' : 'var(--c-soft)'}" stroke="var(--c)" stroke-width="3" ${q ? 'stroke-dasharray="6 5"' : ''}/><text x="${cx}" y="${cy + 11}" text-anchor="middle" font-size="32" font-family="${FONT}" font-weight="800" fill="${q ? 'var(--c)' : '#22303c'}">${val == null ? '?' : val}</text>`;
  return `<svg class="v-svg small" viewBox="0 0 260 160" role="img" aria-label="${v.whole} coupé en ${a == null ? '?' : a} et ${b == null ? '?' : b}"><line x1="130" y1="44" x2="70" y2="118" stroke="#22303c" stroke-width="3"/><line x1="130" y1="44" x2="190" y2="118" stroke="#22303c" stroke-width="3"/>${circ(130, 38, 30, v.whole)}${circ(70, 122, 28, a, a == null)}${circ(190, 122, 28, b, b == null)}</svg>`;
}
function vTenframe(v) {
  const c = 58; let s = '';
  for (let i = 0; i < 10; i++) {
    const x = 3 + (i % 5) * c, y = 3 + Math.floor(i / 5) * c, full = i < v.filled;
    s += `<rect x="${x}" y="${y}" width="${c}" height="${c}" fill="${!full && v.highlightEmpty ? '#ffe27a' : '#fff'}" ${!full && v.highlightEmpty ? 'class="pulse"' : ''} stroke="#22303c" stroke-width="3"/>`;
    if (full) s += `<circle cx="${x + c / 2}" cy="${y + c / 2}" r="${c * 0.32}" fill="var(--tok, #c35713)"/>`;
  }
  return `<svg class="v-svg" style="max-width:${v.small ? 260 : 440}px" viewBox="0 0 ${5 * c + 6} ${2 * c + 6}" role="img" aria-label="boîte à dix avec ${v.filled} points">${s}</svg>`;
}
function vFingers(v) {
  const hand = (x0, n0) => {
    let h = `<rect x="${x0 - 6}" y="96" width="156" height="52" rx="22" fill="#b07a55"/>`;
    for (let k = 0; k < 5; k++) {
      const up = n0 + k < v.up, x = x0 + k * 30, hgt = up ? 84 - (k === 0 ? 24 : 0) : 30;
      h += `<rect x="${x}" y="${104 - hgt}" width="22" height="${hgt + 8}" rx="11" fill="${up ? '#b07a55' : '#d8d2cc'}" stroke="${up ? '#7a4f33' : '#b8b0a8'}" stroke-width="2"/>`;
    }
    return h;
  };
  return `<svg class="v-svg" style="max-width:440px" viewBox="0 0 370 160" role="img" aria-label="${v.up} doigts levés">${hand(18, 0) + hand(200, 5)}</svg>`;
}
/* Scènes de l'histoire (en attendant le kit de l'illustrateur). */
const person = (x, y, s, dress, wrap, arm) => `<g transform="translate(${x} ${y}) scale(${s})"><path d="M-14 0 L14 0 L9 -38 L-9 -38 Z" fill="${dress}"/><circle cx="0" cy="-48" r="11" fill="#6b4226"/>${wrap ? `<path d="M-12 -52 Q0 -68 12 -52 Z" fill="${wrap}"/>` : ''}${arm || ''}</g>`;
const mango = (x, y, r = 7) => `<ellipse cx="${x}" cy="${y}" rx="${r}" ry="${r * 0.78}" fill="#f6b73c" stroke="#9a5b12" stroke-width="1.2"/>`;
const basket = (x, y, rot = 0) => `<g transform="translate(${x} ${y}) rotate(${rot})"><path d="M-22 -14 L22 -14 L16 8 L-16 8 Z" fill="#a0703f" stroke="#6b4a26" stroke-width="1.5"/>${mango(-10, -18)}${mango(2, -20)}${mango(13, -17)}</g>`;
const SCENES = {
  marche: `<rect x="0" y="0" width="240" height="160" fill="#fbf3e2"/><rect x="0" y="120" width="240" height="40" fill="#e8d6b5"/><rect x="120" y="60" width="100" height="10" fill="#c35713"/><path d="M115 60 L170 36 L225 60 Z" fill="#e89a2b"/><rect x="128" y="70" width="6" height="50" fill="#8a5a3c"/><rect x="206" y="70" width="6" height="50" fill="#8a5a3c"/>${basket(168, 112)}${person(70, 124, 1, '#7a4ea3', '', '')}${person(105, 124, 1.25, '#2c8554', '#e0a100', '')}`,
  vent: `<rect x="0" y="0" width="240" height="160" fill="#fbf3e2"/><rect x="0" y="120" width="160" height="40" fill="#e8d6b5"/><rect x="160" y="112" width="80" height="48" fill="#7fb4cf"/><path d="M10 40 q30 -12 60 0 t60 0 M20 62 q30 -12 60 0 t60 0 M5 84 q30 -12 60 0" fill="none" stroke="#9aa7ad" stroke-width="4" stroke-linecap="round"/>${basket(120, 116, 35)}${mango(150, 118)}${mango(172, 122)}${person(50, 124, 1, '#7a4ea3', '', '<path d="M-10 -34 L-26 -50 M10 -34 L26 -50" stroke="#6b4226" stroke-width="5" stroke-linecap="round"/>')}`,
  pecheur: `<rect x="0" y="0" width="240" height="160" fill="#fbf3e2"/><rect x="0" y="80" width="240" height="80" fill="#7fb4cf"/><path d="M0 92 q20 -6 40 0 t40 0 t40 0 t40 0 t40 0 t40 0" fill="none" stroke="#dcebf3" stroke-width="3"/><path d="M40 118 Q100 140 170 118 L162 128 Q100 148 48 128 Z" fill="#5a3a22"/>${person(100, 120, 1.1, '#3d7fa3', '', '<path d="M10 -30 L34 10" stroke="#8a5a3c" stroke-width="4"/>')}${basket(200, 104, -10)}`,
  merci: `<rect x="0" y="0" width="240" height="160" fill="#fbf3e2"/><rect x="0" y="120" width="240" height="40" fill="#e8d6b5"/>${person(80, 124, 1, '#7a4ea3', '', '<path d="M10 -32 L30 -40" stroke="#6b4226" stroke-width="5" stroke-linecap="round"/>')}${mango(120, 83, 9)}${person(160, 124, 1.2, '#3d7fa3', '', '<path d="M-10 -32 L-32 -40" stroke="#6b4226" stroke-width="5" stroke-linecap="round"/>')}<path d="M112 50 q8 -10 16 0 q8 -10 16 0 q0 12 -16 22 q-16 -10 -16 -22z" fill="#d7263d" transform="translate(-8 -8)"/>`,
};
const sceneSVG = (k, label) => `<svg viewBox="0 0 240 160" role="img" aria-label="${esc(label || 'image de l\'histoire')}">${SCENES[k] || ''}</svg>`;
function vScenes(v) {
  return `<div class="scenes">${v.scenes.map((k, i) => `<figure class="scene">${sceneSVG(k, 'image ' + (i + 1) + " de l'histoire")}<figcaption>${i + 1}</figcaption></figure>`).join('')}</div>`;
}
/* Dizaines et unités : planche en HTML pour pouvoir animer les échanges (10 unités → 1 dizaine, 10 dizaines → 1 centaine). */
const COLS = { h: 'centaines', t: 'dizaines', u: 'unités' };
const pieceHTML = c => c === 'u' ? '<i class="pc u"></i>' : c === 't' ? '<i class="pc t"></i>' : '<i class="pc h"></i>';
function boardHTML(v, opts = {}) {
  const cols = (v.h != null || v.hundreds) ? ['h', 't', 'u'] : ['t', 'u'];
  return `<div class="board ${opts.counts ? 'counts' : ''}" data-cols="${cols.join('')}">${cols.map(c => {
    const n = v[c] || 0;
    return `<div class="col col-${c}" data-col="${c}" role="group" aria-label="${COLS[c]}"><div class="col-lab">${COLS[c]}</div><div class="pile">${Array.from({ length: n }, () => pieceHTML(c)).join('')}</div><div class="col-n">${n}</div></div>`;
  }).join('')}</div>`;
}
function boardCount(board, c) { return board.querySelectorAll(`.col-${c} .pile .pc`).length; }
function boardRefresh(board) { board.querySelectorAll('.col').forEach(col => { col.querySelector('.col-n').textContent = col.querySelectorAll('.pile .pc').length; }); }
function flyOverlay(cls, r, from) {
  const o = document.createElement('i'); o.className = 'pc fly ' + cls;
  if (from) o.style.setProperty('--cube', getComputedStyle(from).getPropertyValue('--cube'));
  Object.assign(o.style, { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' });
  document.body.appendChild(o); return o;
}
/* Ferme 10 pièces de la colonne « from » en une pièce de la colonne suivante, avec animation. */
async function regroup(board, from) {
  const to = from === 'u' ? 't' : 'h';
  const pile = board.querySelector(`.col-${from} .pile`), dst = board.querySelector(`.col-${to} .pile`);
  if (!pile || !dst) return false;
  const els = [...pile.querySelectorAll('.pc')].slice(0, 10); if (els.length < 10) return false;
  board.classList.remove('ready-u', 'ready-t');
  const target = document.createElement('i'); target.className = 'pc ' + to; target.style.visibility = 'hidden'; dst.appendChild(target);
  if (FAST || !els[0].animate) { els.forEach(e => e.remove()); target.style.visibility = ''; boardRefresh(board); sfx('clac'); return true; }
  const r0 = els[0].getBoundingClientRect();
  const step = from === 'u' ? r0.height : r0.width;
  sfx('clac');
  await Promise.all(els.map((el, i) => {
    const r = el.getBoundingClientRect();
    const dx = from === 'u' ? r0.left - r.left : (r0.left + i * step) - r.left, dy = from === 'u' ? (r0.top + i * step) - r.top : r0.top - r.top;
    return el.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx}px,${dy}px)` }], { duration: 420, delay: i * 22, easing: 'ease-in-out', fill: 'forwards' }).finished.catch(() => {});
  }));
  if (!board.isConnected) return false;
  const merged = { left: r0.left, top: r0.top, width: from === 'u' ? r0.width : step * 10, height: from === 'u' ? step * 10 : r0.height };
  const fly = flyOverlay(to, merged, board);
  els.forEach(e => { e.style.visibility = 'hidden'; });
  const rt = target.getBoundingClientRect();
  sfx('whoosh');
  await fly.animate([{ transform: 'translate(0,0) scale(1)' }, { transform: `translate(${rt.left - merged.left}px,${rt.top - merged.top}px) scale(${rt.width / merged.width},${rt.height / merged.height})` }],
    { duration: 650, easing: 'cubic-bezier(.5,0,.3,1)', fill: 'forwards' }).finished.catch(() => {});
  fly.remove(); els.forEach(e => e.remove()); target.style.visibility = ''; boardRefresh(board);
  return true;
}
async function autoRegroup(board) {
  await sleep(900);
  while (board.isConnected && boardCount(board, 'u') >= 10) { if (!await regroup(board, 'u')) break; await sleep(350); }
  while (board.isConnected && board.querySelector('.col-h') && boardCount(board, 't') >= 10) { if (!await regroup(board, 't')) break; await sleep(350); }
  if (board.isConnected) board.classList.add('counts');
}
/* Modèle en barres (méthode de Singapour) : les parties et le tout. */
function vBar(v) {
  const parts = v.parts || [], known = parts.filter(x => x != null).reduce((a, b) => a + b, 0);
  const total = v.whole != null ? v.whole : (parts.every(x => x != null) ? known : known * 1.3 || parts.length);
  const vals = parts.map(x => x != null ? x : Math.max(total - known, total * 0.15));
  const sum = vals.reduce((a, b) => a + b, 0) || 1, x0 = 30, W = 580, y = 78, h = 58, u = v.unit ? ' ' + v.unit : '';
  let x = x0, s = '';
  vals.forEach((val, i) => {
    const w = W * val / sum, q = parts[i] == null;
    s += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="6" fill="${q ? '#fff' : i % 2 ? 'var(--c-soft)' : '#fbe9c8'}" stroke="#22303c" stroke-width="3" ${q ? 'stroke-dasharray="8 6"' : ''}/>`;
    s += `<text x="${x + w / 2}" y="${y + h / 2 + 11}" text-anchor="middle" font-size="30" font-family="${FONT}" font-weight="800" fill="${q ? 'var(--c)' : '#22303c'}">${q ? '?' : parts[i] + u}</text>`;
    if (v.labels && v.labels[i]) s += `<text x="${x + w / 2}" y="${y + h + 30}" text-anchor="middle" font-size="19" font-family="Andika, sans-serif" font-weight="700" fill="#5f6b70">${esc(v.labels[i])}</text>`;
    x += w;
  });
  const wq = v.whole == null;
  s += `<path d="M${x0} ${y - 10} q0 -14 14 -14 H${x0 + W / 2 - 14} q14 0 14 -12 q0 12 14 12 H${x0 + W - 14} q14 0 14 14" fill="none" stroke="#22303c" stroke-width="3"/>`;
  s += `<text x="${x0 + W / 2}" y="${y - 44}" text-anchor="middle" font-size="30" font-family="${FONT}" font-weight="800" fill="${wq ? 'var(--c)' : '#22303c'}">${wq ? '?' : v.whole + u}</text>`;
  return `<svg class="v-svg" viewBox="0 0 640 ${v.labels ? 182 : 150}" role="img" aria-label="modèle en barres">${s}</svg>`;
}
const rowsOf = (n, html) => `<div class="items" style="--n:${Math.min(5, n)}">${Array.from({ length: n }, () => html).join('')}</div>`;
function dotsHTML(n) { return `<span class="dots-n" style="--n:${Math.min(5, n)}">${Array.from({ length: n }, () => '<i></i>').join('')}</span>`; }
function visual(list) {
  return (list || []).map(v => {
    if (v.kind === 'title') return `<div class="v-title">${esc(fill(v.text))}</div>`;
    if (v.kind === 'expr') return `<div class="v-expr">${esc(v.text)}</div>`;
    if (v.kind === 'text') return `<div class="v-text">${esc(v.text)}</div>`;
    if (v.kind === 'part') return `<div class="v-part"><span>${PART_ICON[v.n] || v.n}</span><b>${esc(v.title)}</b></div>`;
    if (v.kind === 'word') return `<div class="v-word"><b>${esc(v.text)}</b></div>`;
    if (v.kind === 'maman') return `<div class="v-maman">${UI.heart}</div>`;
    if (v.kind === 'listen') return `<div class="v-listen">${UI.ear}</div>`;
    if (v.kind === 'numberline') return vNumberline(v);
    if (v.kind === 'split') return vSplit(v);
    if (v.kind === 'tenframe') return vTenframe(v);
    if (v.kind === 'fingers') return vFingers(v);
    if (v.kind === 'scenes') return vScenes(v);
    if (v.kind === 'blocks') return boardHTML(v, { counts: !v.regroup && v.counts !== false }).replace('class="board', `data-regroup="${v.regroup ? 1 : 0}" class="board`);
    if (v.kind === 'bar') return vBar(v);
    if (v.kind === 'items') return rowsOf(v.n, ICON(v.item || 'mangue'));
    if (v.kind === 'hidden') return `<div class="hidden-v">${rowsOf(v.visible, ICON(v.item || 'mangue'))}<div class="cal">${ICON('calebasse', 'big')}</div></div>`;
    if (v.kind === 'icon') return `<figure class="v-icon">${ICON(v.name, 'big')}${v.label ? `<figcaption>${esc(v.label)}</figcaption>` : ''}</figure>`;
    if (v.kind === 'syllables') return `<figure class="v-syll">${ICON(v.name, 'big')}<div class="syll-dots">${Array.from({ length: v.n }, (_, k) => `<i style="animation-delay:${0.6 + k * 0.75}s"></i>`).join('')}</div></figure>`;
    return '';
  }).join('');
}
/* Après chaque dessin : lance les animations qui en ont besoin. */
function animateVisuals(root) { (root || app).querySelectorAll('.board[data-regroup="1"]').forEach(b => autoRegroup(b)); }
const FISH = gold => `<svg width="40" height="25" viewBox="0 0 40 25" aria-hidden="true"><path d="M30 12.5 L40 3 L40 22 Z" fill="${gold ? '#e0a100' : '#7fb4cf'}" stroke="${gold ? '#8a6400' : '#3d7fa3'}" stroke-width="1.5"/><ellipse cx="17" cy="12.5" rx="15" ry="9.5" fill="${gold ? '#e0a100' : '#7fb4cf'}" stroke="${gold ? '#8a6400' : '#3d7fa3'}" stroke-width="1.5"/><circle cx="9" cy="10.5" r="1.8" fill="#1b2430"/></svg>`;

/* ============================ carte du voyage ============================ */
/* La pinasse avance d'une étape à chaque séance terminée (révisions comprises), sur les escales du parcours de l'enfant.
   Escales (index.json) : Bamako (départ), Ségou après 4 séances, puis Djenné et Mopti, Tombouctou, Gao. */
const RIVER = 'M40 290 C 110 285, 150 262, 205 250 S 290 238, 318 205 S 360 110, 420 88 S 520 92, 575 160';
const escAt = list => list.length === 5 ? [0, 0.24, 0.45, 0.73, 1] : list.map((e, i) => list.length < 2 ? 0 : i / (list.length - 1));
function journey(p) {
  const E = escalesOf(p.parcours), AT = escAt(E);
  const count = Object.keys(p.progress.done).length;
  let cum = 0, f = 0; const stamps = count > 0 && E.length ? [E[0].n] : [];
  for (let i = 0; i < E.length - 1; i++) {
    const leg = E[i].sessions || 28;
    if (count >= cum + leg) { stamps.push(E[i + 1].n); f = AT[i + 1]; cum += leg; continue; }
    f = AT[i] + (AT[i + 1] - AT[i]) * Math.max(0, count - cum) / leg; break;
  }
  return { f: Math.min(1, f), stamps, count };
}
function mapHTML(p) {
  const j = journey(p), E = escalesOf(p.parcours);
  return `<div class="map"><svg viewBox="0 0 620 330" role="img" aria-label="Carte du voyage sur le fleuve Niger">
  <rect x="0" y="0" width="620" height="330" rx="22" fill="#f3e6c8"/>
  <path d="M300 30 q60 -10 120 10 q70 20 150 0" fill="none" stroke="#e8d3a2" stroke-width="34" stroke-linecap="round" opacity=".8"/>
  <path d="M0 320 q120 -30 220 -6 q90 20 160 -10" fill="none" stroke="#e2cf9f" stroke-width="26" opacity=".6"/>
  <g fill="#8fae6a">${[[70, 238], [150, 222], [262, 212], [300, 278], [470, 150], [540, 120]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="9"/><rect x="${x - 2}" y="${y + 6}" width="4" height="10" fill="#7a5236"/>`).join('')}</g>
  <path d="${RIVER}" fill="none" stroke="#8cc0da" stroke-width="20" stroke-linecap="round"/>
  <path class="river" d="${RIVER}" fill="none" stroke="#2f7ea6" stroke-width="3" stroke-dasharray="2 12" stroke-linecap="round"/>
  <g class="escales"></g><g class="boat-pos">${BOAT}</g></svg>
  <div class="passport">${E.map(e => `<span class="stamp ${j.stamps.includes(e.n) ? 'on' : ''}">${esc(e.name)}</span>`).join('')}</div></div>`;
}
function drawMap(root, p, from) {
  const svg = root.querySelector('.map svg'); if (!svg) return;
  const path = svg.querySelector('.river'), L = path.getTotalLength(), g = svg.querySelector('.escales'), E = escalesOf(p.parcours), AT = escAt(E);
  const st = journey(p).stamps;
  g.innerHTML = E.map((e, i) => { const pt = path.getPointAtLength(L * AT[i]); const on = st.includes(e.n); return `<circle cx="${pt.x}" cy="${pt.y}" r="${on ? 10 : 8}" fill="${on ? '#e0a100' : '#fff'}" stroke="#22303c" stroke-width="3"/><text x="${pt.x}" y="${pt.y + (i === 3 ? -20 : 32)}" text-anchor="middle" font-family="${FONT}" font-weight="800" font-size="18" fill="#22303c">${esc(e.name)}</text>`; }).join('');
  const boat = svg.querySelector('.boat-pos'), to = journey(p).f;
  const place = f => { const pt = path.getPointAtLength(L * f); boat.setAttribute('transform', `translate(${pt.x} ${pt.y - 18}) scale(1.7)`); };
  if (from == null || from === to || FAST || calm()) { place(to); return; }
  const t0 = performance.now();
  const step = t => { const k = Math.min(1, (t - t0) / 1800); place(from + (to - from) * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
/* ============================ écrans ============================ */
function setChild(p) { child = p || null; document.body.dataset.child = p ? p.couleur : ''; }
function kidLabel(p) { const pr = p && parcoursOf(p.parcours); return name(p) || (pr ? pr.label : 'Enfant'); }
function parcoursLabel(p) { const pr = p && parcoursOf(p.parcours); return pr ? `Parcours ${pr.label}` : `Parcours ${p ? p.parcours : '?'}`; }
/* C'est l'application qui nomme la fiche, d'après la couleur du parcours (la bande de la fiche imprimée). */
const FICHE = { bleu: 'bleue', orange: 'orange', vert: 'verte', violet: 'violette' };
function ficheOf(p) { const pr = p && parcoursOf(p.parcours); return 'fiche' + (pr && FICHE[pr.couleur] ? ' ' + FICHE[pr.couleur] : ''); }
function screen(nameOf) { document.body.dataset.screen = nameOf; window.scrollTo(0, 0); }

/* ============================ accès autorisé par l'école ============================ */
/* L'école remet un code d'inscription à chaque famille. Le dépôt ne contient que l'empreinte SHA-256 des codes :
   ni les codes, ni un nom d'enfant. La vérification se fait sur la tablette, hors ligne. Une tablette installée
   avant ce contrôle garde son accès ; l'école la régularise avec un code depuis l'espace parent. */
const normCode = s => String(s || '').toUpperCase().replace(/[^0-9A-Z]/g, '').replace(/O/g, '0').replace(/[IL]/g, '1');
async function sha256Hex(s) { const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)); return Array.from(new Uint8Array(b), x => x.toString(16).padStart(2, '0')).join(''); }
const accessRequired = () => !!(ECOLE && ECOLE.acces === 'code');
const codeStillValid = h => (ECOLE.codes || []).some(c => c.h === h && !c.revoque);
async function checkCode(raw) {
  const code = normCode(raw); if (code.length < 6) return null;
  const h = await sha256Hex(code);
  const e = (ECOLE.codes || []).find(c => c.h === h && !c.revoque);
  return e ? { id: e.id, classe: e.classe || '', h, date: today() } : null;
}
function screenEcole(next, msg) {
  setChild(null); stopSpeech(); screen('ecole');
  app.innerHTML = `<div class="page stack">
  <div class="brand">${KONO}<div><h1>${APPNAME}</h1><p class="muted">${esc(msg || `${ECOLE.ecole || 'L\'école'} vous a remis un code d'inscription.`)}</p></div></div>
  <div class="card stack"><h3>Code d'inscription</h3><input type="text" id="code" autocomplete="off" aria-label="Code d'inscription" autocapitalize="characters" spellcheck="false" placeholder="ex. K7F-29Q-H43" style="font-family:var(--display);font-size:1.5rem;letter-spacing:.12em;text-transform:uppercase"><p class="small muted">Délivré par l'école, une fois par famille. Sans ce code, l'application ne s'ouvre pas. Il reste sur la tablette, rien n'est envoyé.</p></div>
  <div class="row"><button class="btn big" id="go" style="--c:var(--river)">Vérifier</button><span id="err" class="small" style="color:var(--try)"></span></div></div>`;
  $('#go').onclick = async () => {
    const ok = await checkCode($('#code').value);
    if (!ok) { $('#err').textContent = 'Code inconnu. Vérifiez-le avec l\'école.'; return; }
    S.ecole = ok; save(); next();
  };
}
function ecoleLine() {
  if (!accessRequired()) return 'Inscription : accès libre (aucun contrôle de l\'école)';
  if (!S.ecole || !S.ecole.id) return 'Inscription : installée avant le contrôle d\'accès de l\'école, à régulariser avec un code';
  return `Inscription : ${S.ecole.id}${S.ecole.classe ? ' · classe ' + S.ecole.classe : ''}${ECOLE.ecole ? ' · ' + ECOLE.ecole : ''}`;
}

/* ============================ export et import d'un profil ============================ */
/* Un profil se déplace vers une autre tablette par un fichier : suivi, phrases de Maman et enregistrements de l'enfant. */
const blobToB64 = b => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(',')[1] || ''); r.onerror = rej; r.readAsDataURL(b); });
const b64ToBlob = (s, type) => { const bin = atob(s || ''); const a = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return new Blob([a], { type: type || 'audio/webm' }); };
function download(name, data, type) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([data], { type })); a.download = name; document.body.appendChild(a); a.click(); a.remove(); }
async function exportProfile(p) {
  if (!p) return;
  const keys = (await DB.clipKeys()) || []; const clips = [];
  for (const k of keys) if (String(k).endsWith('@' + p.id)) { const b = await DB.getClip(k); if (b) clips.push({ phrase: String(k).split('@')[0], type: b.type, b64: await blobToB64(b) }); }
  const recs = [];
  for (const r of (await DB.recs()) || []) if (r.profile === p.id) { const o = Object.assign({}, r); delete o.id; delete o.profile; delete o.blob; o.type = r.blob && r.blob.type; o.b64 = r.blob ? await blobToB64(r.blob) : ''; recs.push(o); }
  const data = JSON.stringify({ app: 'corridor-a-la-maison', format: 'profil-1', version: VERSION, date: new Date().toISOString(), profile: p, clips, recs });
  download(`corridor-profil-${(p.name || 'enfant').replace(/[^\w-]+/g, '_')}-${today()}.json`, data, 'application/json');
}
async function importProfile(d) {
  if (!d || d.app !== 'corridor-a-la-maison' || d.format !== 'profil-1' || !d.profile) throw new Error('fichier inconnu');
  const p = Object.assign({}, d.profile); p.progress = Object.assign(kid(), p.progress || {});
  if (!parcoursOf(p.parcours)) throw new Error('parcours inconnu');
  if (!p.id || S.profiles.some(x => x.id === p.id)) p.id = newId(S.profiles);
  if (!THEMES.includes(p.couleur)) p.couleur = THEMES[0];
  S.profiles.push(p); save();
  for (const c of d.clips || []) await DB.putClip(`${c.phrase}@${p.id}`, b64ToBlob(c.b64, c.type));
  for (const r of d.recs || []) { const rec = Object.assign({}, r); delete rec.b64; delete rec.type; delete rec.id; rec.profile = p.id; rec.blob = b64ToBlob(r.b64, r.type); await DB.addRec(rec); }
  RECS_CACHE = (await DB.recs()) || [];
  return p.name;
}
/* Rappel de sauvegarde : jamais faite, ou plus de 7 jours, alors qu'il y a du suivi à perdre. */
function backupWarnHTML() {
  const has = S.profiles.some(p => p.progress.runs.length);
  const days = S.lastBackup ? Math.floor((Date.now() - new Date(S.lastBackup).getTime()) / DAY_MS) : null;
  if (!has || (days !== null && days < 7)) return '';
  return `<p class="warn">Le suivi n'a ${days === null ? 'jamais été sauvegardé' : `pas été sauvegardé depuis ${days} jours`}. Une tablette réinitialisée le perd. <button class="btn sm" id="tobackup" style="--c:var(--river)">Sauvegarder maintenant</button></p>`;
}

/* ============================ journal d'erreurs ============================ */
/* Les 50 dernières erreurs, sur la tablette seulement, lisibles et copiables dans Réglages. Rien n'est envoyé. */
function logError(m) {
  try { (S.log || (S.log = [])).push({ ts: new Date().toISOString(), v: VERSION, ecran: document.body.dataset.screen || '', m: String(m).slice(0, 300) }); if (S.log.length > 50) S.log.splice(0, S.log.length - 50); save(); } catch (e) {}
}
window.addEventListener('error', e => logError((e.message || 'erreur') + (e.filename ? ` (${String(e.filename).split('/').pop()}:${e.lineno})` : '')));
window.addEventListener('unhandledrejection', e => logError('promesse : ' + ((e.reason && e.reason.message) || e.reason)));

/* Réglages d'affichage : main gauche, moins d'animations, contraste renforcé. Des classes sur <body>, lues par styles.css. */
function applySettings() { const s = S.settings || {}; ['gaucher', 'calme', 'contraste'].forEach(k => document.body.classList.toggle(k, !!s[k])); }
const calm = () => !!(S.settings && S.settings.calme) || !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
function screenSetup() {
  setChild(null); stopSpeech(); screen('setup');
  const first = !S.setup;
  app.innerHTML = `<div class="page stack">
  <div class="brand">${KONO}<div><h1>${APPNAME}</h1><p class="muted">${first ? 'Réglage de départ, à faire une seule fois par un parent.' : 'Code parent et voix de Kono.'}</p></div></div>
  <div class="card stack"><h3>Code parent (4 chiffres)</h3><input type="password" id="pin" inputmode="numeric" maxlength="4" aria-label="Code parent" value="${esc(S.pin)}" placeholder="ex. 2468"><p class="small muted">Il protège l'espace parent : suivi, enregistrements, voix de Maman, et l'ajout d'un enfant.</p></div>
  <div class="card stack"><h3>La voix de Kono</h3>${voiceControls()}</div>
  <div class="row"><button class="btn big" id="go" style="--c:var(--river)">${first ? 'Enregistrer et ajouter un enfant' : 'Enregistrer'}</button>${first ? '' : '<button class="btn ghost" id="cancel">Annuler</button>'}<span id="err" class="small" style="color:var(--try)"></span></div></div>`;
  bindVoiceControls();
  const c = $('#cancel'); if (c) c.onclick = () => screenParent('reglages');
  $('#go').onclick = () => {
    const pin = $('#pin').value.trim();
    if (!/^\d{4}$/.test(pin)) { $('#err').textContent = 'Le code doit faire 4 chiffres.'; return; }
    S.pin = pin; S.setup = true; save();
    if (first || !S.profiles.length) screenProfile(null); else screenParent('reglages');
  };
}
/* Créer ou modifier le profil d'un enfant. La classe est proposée d'après l'âge, puis confirmée par le parent : c'est la classe réelle qui compte. */
function screenProfile(p) {
  setChild(null); stopSpeech(); screen('profile');
  const edit = !!p; const f = p ? Object.assign({}, p) : { name: '', girl: false, dob: '', parcours: '', couleur: '' };
  const draw = () => {
    const age = ageOf(f.dob), prop = age == null ? null : PARCOURS.find(x => age >= x.age_min && age <= x.age_max);
    if (!f.parcours && !edit && S.ecole && S.ecole.classe) { const pc = PARCOURS.find(x => x.classe === S.ecole.classe); if (pc) f.parcours = pc.id; }   /* la classe du code d'inscription */
    if (!f.parcours && prop) f.parcours = prop.id;
    const used = S.profiles.filter(x => !p || x.id !== p.id).map(x => x.couleur), pr = parcoursOf(f.parcours);
    if (!f.couleur) f.couleur = THEMES.find(t => !used.includes(t) && pr && t === pr.couleur) || THEMES.find(t => !used.includes(t)) || (pr ? pr.couleur : THEMES[0]);
    app.innerHTML = `<div class="page stack">
    <div class="brand">${KONO}<div><h1>${edit ? 'Modifier le profil' : 'Un enfant de plus'}</h1><p class="muted">${edit ? esc(p.name) : 'Le parent remplit, l\'enfant choisit sa couleur.'}</p></div></div>
    <div class="card stack"><h3>L'enfant</h3>
      <div class="row"><label class="f" style="flex:1 1 220px">Prénom<input type="text" id="p-name" value="${esc(f.name)}" autocomplete="off"></label>
      <div class="seg" role="group" aria-label="Fille ou garçon"><button data-g="0" class="${f.girl ? '' : 'on'}">Garçon</button><button data-g="1" class="${f.girl ? 'on' : ''}">Fille</button></div></div>
      <label class="f" style="max-width:260px">Date de naissance<input type="date" id="p-dob" value="${esc(f.dob)}" max="${today()}"></label>
      <p class="small muted" style="margin:0">Le prénom sert à saluer l'enfant. Garçon ou fille sert à accorder les phrases. L'âge sert à proposer la classe.</p></div>
    <div class="card stack"><h3>La classe</h3>
      <div class="seg wrap" role="group" aria-label="Classe">${PARCOURS.map(x => `<button data-p="${esc(x.id)}" class="${f.parcours === x.id ? 'on' : ''}">${esc(x.label)}</button>`).join('')}</div>
      <p class="small muted" style="margin:0">${age == null ? 'Indiquez la date de naissance pour une proposition.' : prop ? `À ${age} ans, la classe proposée est ${esc(prop.label)}. C'est la classe réelle de l'enfant qui compte : changez-la si besoin.` : `${age} ans : aucune classe prévue pour cet âge. Choisissez la classe réelle de l'enfant.`}</p></div>
    <div class="card stack"><h3>Sa couleur</h3><div class="swatches">${THEMES.map(t => `<button class="swatch ${t} ${f.couleur === t ? 'on' : ''}" data-t="${t}" aria-label="${t}"></button>`).join('')}</div></div>
    <div class="row"><button class="btn big" id="go" style="--c:var(--river)">${edit ? 'Enregistrer' : 'Créer le profil'}</button><button class="btn ghost" id="cancel">Annuler</button><span id="err" class="small" style="color:var(--try)"></span></div></div>`;
    $('#p-name').oninput = e => { f.name = e.target.value; };
    $('#p-dob').onchange = e => { f.dob = e.target.value; if (!edit) f.parcours = ''; draw(); };
    app.querySelectorAll('[data-g]').forEach(b => b.onclick = () => { f.girl = b.dataset.g === '1'; draw(); });
    app.querySelectorAll('[data-p]').forEach(b => b.onclick = () => { f.parcours = b.dataset.p; draw(); });
    app.querySelectorAll('[data-t]').forEach(b => b.onclick = () => { f.couleur = b.dataset.t; draw(); });
    $('#cancel').onclick = () => edit ? screenParent('reglages') : (S.profiles.length ? screenHome() : screenSetup());
    $('#go').onclick = () => {
      f.name = $('#p-name').value.trim(); f.dob = $('#p-dob').value;
      if (!f.name) { $('#err').textContent = 'Le prénom manque.'; return; }
      if (!f.dob || ageOf(f.dob) == null) { $('#err').textContent = 'La date de naissance manque.'; return; }
      if (!parcoursOf(f.parcours)) { $('#err').textContent = 'Choisissez la classe.'; return; }
      f.classe = parcoursOf(f.parcours).classe;
      if (edit) Object.assign(p, { name: f.name, girl: f.girl, dob: f.dob, classe: f.classe, parcours: f.parcours, couleur: f.couleur });
      else S.profiles.push({ id: newId(S.profiles), name: f.name, girl: f.girl, dob: f.dob, classe: f.classe, parcours: f.parcours, couleur: f.couleur, created: today(), progress: kid() });
      save(); edit ? screenParent('reglages') : screenHome();
    };
  };
  draw();
}
async function removeProfile(id) {
  const k = S.profiles.findIndex(p => p.id === id); if (k < 0) return;
  const recs = (await DB.recs()) || []; for (const r of recs) if (r.profile === id) await DB.delRec(r.id);
  const keys = (await DB.clipKeys()) || []; for (const key of keys) if (String(key).endsWith('@' + id)) await DB.delClip(key);
  S.profiles.splice(k, 1); save();
}
function voiceControls() {
  loadVoices();
  const nFiles = Object.keys(AUDIO.files).length;
  const opts = voices.map(v => `<option value="${esc(v.name)}" ${v.name === (pickVoice() || {}).name ? 'selected' : ''}>${esc(v.name)} (${esc(v.lang)})${v.localService ? ' · hors ligne' : ''}</option>`).join('');
  return `<p class="small" style="margin:0">${nFiles ? `${nFiles} phrases ont une voix enregistrée ou générée à l'avance. La voix de la tablette ne sert que pour les autres.` : `Aucune voix générée à l'avance pour l'instant : c'est la voix de la tablette qui parle.`}</p>
  ${voices.length ? `<label class="f">Voix française de la tablette<select id="v-name">${opts}</select></label>` : `<p class="small" style="color:var(--try)">Aucune voix française trouvée sur cet appareil. Android : Paramètres › Synthèse vocale › Moteur Google › Installer les données vocales › Français (France). Puis rouvrir l'application. En attendant, les sous-titres s'affichent.</p>`}
  <label class="f">Vitesse<input type="range" id="v-rate" min="0.7" max="1.1" step="0.05" value="${S.voice.rate}"></label>
  <div class="row"><button class="btn soft" id="v-test" type="button">Écouter Kono</button><span class="small muted">Choisissez de préférence une voix marquée « hors ligne ».</span></div>`;
}
function bindVoiceControls() {
  const sel = $('#v-name'), rate = $('#v-rate');
  if (sel) sel.onchange = () => { S.voice.name = sel.value; save(); };
  if (rate) rate.oninput = () => { S.voice.rate = Number(rate.value); save(); };
  const t = $('#v-test'); if (t) t.onclick = () => speak(PH.voiceTest);
}

function screenHome() {
  setChild(null); stopSpeech(); screen('home');
  const done = p => Object.keys(p.progress.done).length;
  app.innerHTML = `<div class="page home">
  <div class="hero"><div class="hero-kono">${KONO}</div><div><h1>${APPNAME}</h1><p class="muted">${S.profiles.length ? 'Qui voyage avec Kono aujourd\'hui ?' : 'avec Kono, l\'oiseau du fleuve'}</p></div></div>
  <div class="kids">
    ${S.profiles.map(p => `<button class="kid ${esc(p.couleur)}" data-c="${esc(p.id)}"><svg class="kid-boat" viewBox="-40 -20 80 40" aria-hidden="true">${BOAT}</svg><b>${esc(kidLabel(p))}</b><span>${esc(parcoursLabel(p))} · ${done(p)} séance${done(p) > 1 ? 's' : ''} sur le fleuve</span></button>`).join('')}
    <button class="kid add" id="add"><b>+</b><span>Ajouter un enfant</span></button>
  </div>
  <div class="home-foot"><button class="link" id="parent">Espace parent</button><span class="small muted">v${VERSION}</span></div></div>`;
  app.querySelectorAll('[data-c]').forEach(b => b.onclick = () => { const p = profileOf(b.dataset.c); if (p) { sfx('tap'); screenChild(p); } });
  $('#add').onclick = () => screenPin(() => screenProfile(null));
  $('#parent').onclick = () => screenPin(() => screenParent('suivi'));
}
function nextLesson(p) { return INDEX.filter(l => l.parcours === p.parcours).find(l => !p.progress.done[l.id]) || null; }
const revisionId = () => 'revision-' + today();
/* La séance à reprendre d'un profil, si elle existe encore et n'est pas finie. */
function resumeOf(p) {
  const rs = p.progress.resume;
  if (!rs || !rs.run || !Array.isArray(rs.steps) || !(rs.i < rs.steps.length)) return null;
  if (!rs.synthetic && !LESSONS[rs.lesson]) return null;
  return rs;
}
/* Une séance abandonnée (l'enfant en commence une autre) passe dans l'historique comme « arrêtée avant la fin ». */
function abandonResume(p) {
  const rs = p.progress.resume; if (!rs) { return; }
  if (rs.run && !rs.run.end) {
    const items = (rs.run.items || []).filter(it => it.done);
    Object.assign(rs.run, { items, end: Date.now(), done: false, fish: items.filter(it => it.ok && it.first).length, gold: items.filter(it => it.ok && !it.first).length });
    p.progress.runs.push(rs.run);
  }
  p.progress.resume = null; save();
}
/* Le rappel du niveau : ce que l'enfant a fait la dernière fois, ce qu'il réussit, ce qu'on revoit, ce qu'il fait aujourd'hui. */
function recapOf(p, rs, nx, canRevise) {
  const parts = [];
  if (rs) parts.push(`${PH.recapResume} « ${rs.title} ». ${PH.recapResumeAsk}`);
  else {
    const last = p.progress.runs.filter(r => r.done).slice(-1)[0];
    parts.push(last ? `${PH.recapLast} « ${last.title} ».` : PH.recapFirst);
  }
  const st = skillStats(p, 7), lab = k => skillLabel(p.parcours, k);
  const good = Object.keys(st).filter(k => st[k].n >= 3 && st[k].first / st[k].n >= 0.8).sort((a, b) => st[b].n - st[a].n).slice(0, 2);
  const again = Object.keys(st).filter(k => st[k].n >= 3 && (st[k].shown + st[k].after) / st[k].n >= 0.5).sort((a, b) => st[b].n - st[a].n).slice(0, 2);
  if (good.length) parts.push(`${PH.recapGood} ${good.map(lab).join(', ')}.`);
  if (again.length) parts.push(`${PH.recapAgain} ${again.map(lab).join(', ')}.`);
  if (!rs) parts.push(nx ? `${PH.recapToday} « ${nx.title} ».` : canRevise ? PH.recapRevision : PH.recapDone);
  return fill(parts.join(' '));
}
function screenChild(p, opts = {}) {
  setChild(p); stopSpeech(); screen('child');
  const pr = p.progress, list = INDEX.filter(l => l.parcours === p.parcours), nx = nextLesson(p), rs = resumeOf(p);
  if (pr.resume && !rs) abandonResume(p);
  const revDone = pr.done[revisionId()];
  const canRevise = !nx && list.length && !revDone;
  const lastWeek = list.length ? list[list.length - 1].week : '';
  const tickets = list.filter(l => l.week === lastWeek || !pr.done[l.id]);
  const DAY = { lundi: 'Lun', mardi: 'Mar', mercredi: 'Mer', jeudi: 'Jeu', vendredi: 'Ven' };
  const recap = recapOf(p, rs, nx, canRevise);
  /* Navigation sans lecture : chaque billet porte une image et Kono nomme la séance quand l'enfant la touche ;
     un seul bouton, la pinasse, lance la séance choisie (la reprise, sinon celle du jour, sinon la révision). */
  let sel = rs ? rs.lesson : nx ? nx.id : canRevise ? 'revision' : null;
  const titleOf = id => id === 'revision' ? 'Séance de révision' : ((INDEX.find(l => l.id === id) || LESSONS[id] || {}).title || '');
  const iconOf = id => id === 'revision' ? DOMAIN_ICON.revision : domainIcon(LESSONS[id]);
  const todayHTML = () => {
    if (!sel) return list.length ? `<h2>À demain !</h2><p class="muted">Toutes les séances sont faites.</p>` : `<h2>Pas encore de séance</h2><p class="muted">Les séances de ce parcours arrivent avec la prochaine publication.</p>`;
    const resuming = !!(rs && rs.lesson === sel), bid = resuming ? 'resume' : sel === 'revision' ? 'revise' : 'start';
    const lab = `${resuming ? 'Reprendre' : 'Commencer'} « ${titleOf(sel)} »`;
    return `<p class="muted">${resuming ? 'Séance commencée' : sel !== 'revision' && pr.done[sel] ? 'Séance déjà faite, à refaire' : 'Séance du jour'}</p>
      <div class="t-sel"><span class="t-big">${iconOf(sel)}</span><h2>${esc(titleOf(sel))}</h2></div>
      <button class="btn big go boat-btn" id="${bid}" aria-label="${esc(lab)}" title="${esc(lab)}"><svg class="go-boat" viewBox="-40 -22 80 44" aria-hidden="true">${BOAT}</svg>${UI.play}</button>
      <p class="small muted">${resuming ? `Étape ${rs.i + 1} sur ${rs.steps.length}, commencée le ${esc(rs.date || '')}.` : sel === 'revision' ? 'On revoit ce que tu as appris.' : `Prépare ton crayon et ta ${esc(ficheOf(p))}.`}</p>`;
  };
  const ticketHTML = (id, day, title, done, icon) => `<button class="ticket ${done ? 'done' : ''} ${rs && rs.lesson === id ? 'pending' : ''} ${sel === id ? 'sel' : ''}" data-l="${esc(id)}" aria-label="${esc(day ? `Séance de ${day} : ${title}` : title)}"><span class="t-ic">${icon}</span><span class="t-day">${esc(DAY[day] || (id === 'revision' ? 'Rév.' : lastWeek))}</span><span class="t-title">${esc(title)}</span><span class="t-mark">${done ? UI.check : rs && rs.lesson === id ? UI.play : ''}</span></button>`;
  app.innerHTML = `<div class="page child">
  <header class="c-head"><button class="icon-btn" id="back" aria-label="Retour">${UI.back}</button><h2>${esc(kidLabel(p))}</h2><span class="c-count" aria-label="Poissons pêchés">${FISH(false)}<b>${pr.runs.reduce((a, r) => a + (r.fish || 0) + (r.gold || 0), 0)}</b></span></header>
  <div class="c-grid">
    <div class="card c-map">${mapHTML(p)}</div>
    <div class="c-side">
      <div class="card today"><div id="today">${todayHTML()}</div><p class="recap" id="recap" ${subtitlesOn() ? '' : 'hidden'}>${esc(recap)}</p></div>
      <div class="tickets">${tickets.map(l => ticketHTML(l.id, (LESSONS[l.id] || {}).day || '', l.title, !!pr.done[l.id], domainIcon(LESSONS[l.id]))).join('')}${canRevise ? ticketHTML('revision', '', 'Séance de révision', false, DOMAIN_ICON.revision) : ''}</div>
    </div>
  </div></div>`;
  drawMap(app, p);
  $('#back').onclick = screenHome;
  const go = id => {
    audioCtx();
    if (id === 'revision') { if (rs) abandonResume(p); return startLesson(makeRevision(p).id); }
    if (rs && rs.lesson === id) return startLesson(id, rs);
    if (rs) abandonResume(p);
    startLesson(id);
  };
  const bind = () => ['start', 'revise', 'resume'].forEach(k => { const b = $('#' + k); if (b) b.onclick = () => go(sel); });
  bind();
  app.querySelectorAll('[data-l]').forEach(b => b.onclick = () => {
    sfx('tap'); sel = b.dataset.l;
    app.querySelectorAll('[data-l]').forEach(x => x.classList.toggle('sel', x.dataset.l === sel));
    $('#today').innerHTML = todayHTML(); bind();
    speak(`${titleOf(sel)}. ${PH.ticketGo || 'Touche la pinasse pour commencer.'}`);
  });
  if (!opts.quiet) speak(recap);
}

/* ============================ séance de révision ============================ */
/* Si aucune nouvelle semaine n'est arrivée, la tablette compose seule une séance :
   automatismes, défis ratés de la file de révision, rappel espacé de questions déjà vues, relecture ou histoire, explication. */
function retrievalPool(p) {
  const out = [];
  INDEX.filter(l => l.parcours === p.parcours && p.progress.done[l.id]).forEach(l => {
    const L = LESSONS[l.id]; if (!L) return;
    const all = L.steps.concat(...L.steps.filter(x => x.type === 'review').map(x => x.fallback || []));
    all.forEach(s => { if (['number', 'choice', 'manip'].includes(s.type) && s.id) out.push(Object.assign({}, s, { origin: l.id })); });
  });
  return out;
}
function makeRevision(p) {
  const id = revisionId();
  const mine = INDEX.filter(l => l.parcours === p.parcours).map(l => LESSONS[l.id]).filter(Boolean);
  const findLast = t => { for (let i = mine.length - 1; i >= 0; i--) { const s = mine[i].steps.find(x => x.type === t); if (s) return s; } return null; };
  const drill = findLast('drill'), reading = findLast('reading'), story = findLast('story');
  /* L'explication de la méthode est enregistrée si les séances du parcours le font déjà ; sinon elle se dit à Maman. */
  const records = mine.some(L => L.steps.some(x => x.type === 'record' && (x.kind || 'methode') === 'methode'));
  /* Les défis de rappel visent d'abord les compétences fragiles (maîtrise sur 30 jours), puis en cours, puis peu travaillées, puis acquises. */
  const m = masteryOf(p), RANK = { fragile: 0, 'en-cours': 1, peu: 2, acquis: 3 };
  const rank = s => RANK[(m[s.skill || lessonSkill(s.origin)] || { level: 'peu' }).level];
  const retr = shuffle(retrievalPool(p)).sort((a, b) => rank(a) - rank(b)).slice(0, 3);
  const steps = [{ type: 'maman', clip: 'bonjour' },
    { type: 'say', text: PH.revisionIntro, show: [{ kind: 'title', text: 'Séance de révision' }] }];
  if (drill) steps.push({ type: 'part', n: 1, title: drill.title, text: PH.revisionPart1 }, drill);
  steps.push({ type: 'part', n: 2, title: 'On revoit', text: PH.revisionPart2 }, { type: 'review', max: 4, fill: true, fallback: retr });
  if (reading) steps.push({ type: 'part', n: 3, title: 'Lecture', text: PH.revisionPart3 }, Object.assign({}, reading, { id: 'revision-lecture', reread: true }));
  else if (story) steps.push({ type: 'part', n: 3, title: 'Histoire', text: PH.revisionPart3 }, Object.assign({}, story, { skipVocab: true, questions: [], order: false }));
  steps.push({ type: 'part', n: 4, title: 'Ta méthode', text: PH.revisionPart4 },
    records ? { type: 'record', kind: 'methode', text: PH.revisionMethod } : { type: 'say', text: PH.revisionMethod, show: [{ kind: 'maman' }] },
    { type: 'end', clip: 'fin' });
  const L = { id, parcours: p.parcours, order: 999, week: 'R', title: 'Séance de révision', domain: 'Révision', programme: 'Révision', objective: 'Revoir ce qui a été appris.', skills: [], steps, synthetic: true };
  LESSONS[id] = L;
  return L;
}

/* ============================ lecteur de séance ============================ */
let P = null, wake = null;
function expandSteps(lesson) {
  const out = [];
  lesson.steps.forEach(st => {
    if (st.type === 'review') {
      const q = child.progress.review.slice(0, st.max || 2).map(r => {
        const L = LESSONS[r.lesson]; if (!L) return null;
        const pool = L.steps.concat(...L.steps.filter(x => x.type === 'review').map(x => x.fallback || []), ...L.steps.filter(x => x.type === 'story').map(x => x.questions || []));
        const s = pool.find(x => x.id === r.id);
        return s ? Object.assign({}, s, { fromReview: r, text: PH.reviewIntro + ' ' + s.text, say: PH.reviewIntro + ' ' + (s.say || s.text) }) : null;
      }).filter(Boolean);
      if (st.fill) out.push(...q, ...(st.fallback || []).filter(f => !q.some(x => x.id === f.id)).slice(0, Math.max(0, (st.max || 2) - q.length)));
      else out.push(...(q.length ? q : st.fallback || []));
      return;
    }
    if (st.type === 'story') {
      if (!st.skipListen) out.push({ type: 'listen', title: st.title, sentences: st.sentences, pass: st.pass || 1 });
      if (!st.skipVocab) (st.vocab || []).forEach(v => out.push({ type: 'say', text: v.say, show: [{ kind: 'word', text: v.word }] }));
      out.push(...(st.questions || []).map(q => Object.assign({ skill: 'GS.O.recit' }, q)));
      if (st.order) out.push({ type: 'order', id: `${st.id}-ordre-${st.pass || 1}`, text: PH.orderAsk, scenes: st.scenes, skill: 'GS.O.recit' });
      else if (!st.noImages) out.push({ type: 'say', text: PH.storyScenes, show: [{ kind: 'scenes', scenes: st.scenes }] });
      out.push({ type: 'record', kind: 'recit', story: st.id, text: st.retell, show: st.noImages ? [{ kind: 'title', text: st.title }, { kind: 'listen' }] : [{ kind: 'scenes', scenes: st.scenes }] });
      return;
    }
    out.push(st);
  });
  return out;
}
async function startLesson(id, rs) {
  const lesson = rs && rs.synthetic ? (LESSONS[id] = rs.synthetic) : LESSONS[id];
  if (rs) {
    /* Reprise : mêmes étapes, même position, mêmes réponses déjà données ; l'étape en cours repart de son début. */
    const items = (rs.run.items || []).filter(it => it.done);
    rs.run.items = items; rs.run.start = Date.now() - (rs.elapsed || 0);
    P = { lesson, steps: rs.steps, i: rs.i, stepToken: 0, fish: items.filter(it => it.ok && it.first).length, gold: items.filter(it => it.ok && !it.first).length,
      fromF: journey(child).f, fromStamps: journey(child).stamps.length, run: rs.run, resumed: true };
  } else {
    const steps = expandSteps(lesson);
    P = { lesson, steps, i: 0, stepToken: 0, fish: 0, gold: 0, fromF: journey(child).f, fromStamps: journey(child).stamps.length,
      run: { lesson: id, title: lesson.title, week: lesson.week, date: today(), start: Date.now(), end: null, done: false, items: [], recs: 0, drill: null } };
  }
  child.progress.resume = { lesson: id, title: lesson.title, date: P.run.date, i: P.i, fish: P.fish, gold: P.gold, elapsed: Date.now() - P.run.start, ts: Date.now(), steps: P.steps, run: P.run, synthetic: lesson.synthetic ? lesson : null };
  save();
  try { if ('wakeLock' in navigator) wake = await navigator.wakeLock.request('screen'); } catch (e) { wake = null; }
  screen('lesson');
  app.innerHTML = `<div class="lesson">
    <header class="l-head"><button class="icon-btn" id="quit" aria-label="Arrêter la séance">${UI.home}</button><div class="trail" id="parts"></div><div class="catch" id="catch" role="status" aria-label="Poissons pêchés">${FISH(false)}<b id="nfish">${P.fish + P.gold}</b></div></header>
    <div class="l-body">
      <aside class="guide"><button class="kono-btn" id="repeat" aria-label="Réécouter Kono">${KONO}<span class="ear">${UI.ear}</span></button><div class="bubble" id="bubble" hidden></div></aside>
      <main class="l-work" id="work"><section class="stage" id="stage"></section><section class="answer" id="answer"></section></main>
    </div>
    <button class="next-btn" id="next" hidden aria-label="Continuer">${UI.next}</button>
    <div class="quit-ask" id="quitask" hidden><div class="qa-card"><p>${esc(PH.quitAsk)}</p><div class="row" style="justify-content:center"><button class="btn big" id="qa-stay" style="--c:var(--good)" aria-label="Continuer la séance">${UI.play}</button><button class="btn big ghost" id="qa-leave" aria-label="Arrêter la séance">${UI.home}</button></div></div></div></div>`;
  $('#quit').onclick = () => { stopSpeech(); $('#quitask').hidden = false; speak(PH.quitAsk); };
  $('#qa-stay').onclick = () => { stopSpeech(); $('#quitask').hidden = true; if (P && P.repeat) P.repeat(); };
  /* Arrêter garde la séance au point de sauvegarde : elle sera proposée à la reprise. */
  $('#qa-leave').onclick = () => { stopSpeech(); save(); endWake(); P = null; screenChild(child, { quiet: true }); };
  $('#next').onclick = () => { if (P.nextHandler) return P.nextHandler(); sfx('next'); P.i++; runStep(); };
  $('#repeat').onclick = () => { if (P && P.repeat) { sfx('tap'); P.repeat(); } };
  if (rs) { bubble(PH.resumeHere); await speak(PH.resumeHere); if (!P) return; }
  runStep();
}
function endWake() { try { if (wake) wake.release(); } catch (e) {} wake = null; }
const subtitlesOn = () => S.settings.subtitles || mustSubtitle();
function bubble(text, kind) {
  const b = $('#bubble'); if (!b) return;
  b.className = 'bubble' + (kind ? ' ' + kind : '');
  b.innerHTML = esc(text);
  b.hidden = !subtitlesOn() || !text;
}
function stage(list) { const s = $('#stage'); s.className = 'stage'; s.innerHTML = visual(list) || ''; animateVisuals(s); }
function layout(pad) { const w = $('#work'); if (w) w.classList.toggle('has-pad', !!pad); }
let nudgeT = 0;
function showNext(on = true, mode) {
  const n = $('#next'); if (!n) return;
  clearTimeout(nudgeT); n.classList.remove('nudge', 'appear');
  n.hidden = !on; n.dataset.mode = mode || 'next';
  n.innerHTML = mode === 'end' ? UI.home : mode === 'skip' ? UI.skip : UI.next;
  n.setAttribute('aria-label', mode === 'end' ? 'Terminer' : mode === 'skip' ? 'Passer' : 'Continuer');
  if (on) { void n.offsetWidth; n.classList.add('appear'); nudgeT = setTimeout(() => n.classList.add('nudge'), 5000); }
}
function drawParts() {
  const parts = P.steps.map((s, k) => [s, k]).filter(([s]) => s.type === 'part');
  const el = $('#parts'); if (!el) return;
  if (!parts.length) { el.innerHTML = ''; return; }
  const cur = parts.filter(([, k]) => k <= P.i).length;
  el.innerHTML = `<div class="trail-river"></div>${parts.map(([s], j) => `<span class="tp ${j + 1 < cur ? 'done' : j + 1 === cur ? 'on' : ''}" title="${esc(s.title)}">${PART_ICON[s.n] || s.n}</span>`).join('')}`;
  el.style.setProperty('--at', cur ? (cur - 1) / Math.max(1, parts.length - 1) : 0);
}
function bumpFish(gold) {
  const c = $('#catch'); if (!c) return;
  $('#nfish').textContent = P.fish + P.gold;
  c.classList.remove('bump'); void c.offsetWidth; c.classList.add('bump');
  sfx(gold ? 'gold' : 'good');
}

async function runStep() {
  if (!P) return;
  stopSpeech(); showNext(false); $('#answer').innerHTML = ''; P.repeat = null; P.nextHandler = null; mood(null); layout(false);
  const st = P.steps[P.i]; if (!st) return;
  save();   /* point de sauvegarde : la position de l'étape */
  drawParts();
  const my = ++P.stepToken;
  const alive = () => P && P.stepToken === my;
  switch (st.type) {
    case 'maman': {
      stage([]);
      const said = await playClip(st.clip, (isMaman, txt) => { if (isMaman) stage([{ kind: 'maman' }]); bubble(isMaman ? '' : txt, isMaman ? 'maman' : ''); });
      if (!alive()) return;
      if (said) await sleep(300);
      if (alive()) { P.i++; runStep(); }
      return;
    }
    case 'part': {
      stage([{ kind: 'part', n: st.n, title: st.title }]); bubble(st.text);
      await speak(st.text); await sleep(600);
      if (alive()) { P.i++; runStep(); }
      return;
    }
    case 'say': {
      stage(st.show); bubble(fill(st.text));
      P.repeat = () => { stage(st.show); speak(fill(st.say || st.text)); };
      await speak(fill(st.say || st.text)); if (alive()) showNext();
      return;
    }
    case 'demo': {
      let demoRun = 0;
      const play = async () => {
        const me = ++demoRun; showNext(false);
        for (const ln of st.lines) {
          if (!alive() || me !== demoRun) return;
          stage(ln.show); bubble(fill(ln.text));
          await speak(fill(ln.say || ln.text)); await sleep(500);
          if (ln.show && ln.show.some(v => v.kind === 'blocks' && v.regroup)) await sleep(1800);
        }
        if (alive() && me === demoRun) showNext();
      };
      P.repeat = play; return play();
    }
    case 'number': case 'choice': return askStep(st, alive);
    case 'manip': return manipStep(st, alive);
    case 'order': return orderStep(st, alive);
    case 'drill': return drillStep(st, alive);
    case 'paper': return paperStep(st, alive);
    case 'reading': return readingStep(st, alive);
    case 'listen': return listenStep(st, alive);
    case 'record': return recordStep(st, alive);
    case 'end': return endStep(st, alive);
    default: P.i++; return runStep();
  }
}

function addReview(st) { if (!st.id) return; const r = { lesson: st.fromReview ? st.fromReview.lesson : (st.origin || P.lesson.id), id: st.id }; const q = child.progress.review; if (!q.some(x => x.lesson === r.lesson && x.id === r.id)) q.push(r); }
function dropReview(st) {
  const q = child.progress.review;
  const ref = st.fromReview || (st.origin ? { lesson: st.origin, id: st.id } : null); if (!ref) return;
  const k = q.findIndex(x => x.lesson === ref.lesson && x.id === ref.id); if (k >= 0) q.splice(k, 1);
}
const lessonSkill = id => ((LESSONS[id] || {}).skills || [])[0];
const skillOf = st => st.skill || (st.fromReview && lessonSkill(st.fromReview.lesson)) || (st.origin && lessonSkill(st.origin)) || lessonSkill(P.lesson.id) || '';
function newItem(st, q) { const it = { id: st.id || '', q: q || st.text, answer: st.answer, answers: [], ok: false, first: false, review: !!st.fromReview, skill: skillOf(st) }; P.run.items.push(it); return it; }
function keypadHTML(okIcon = UI.check) { return `<div class="keypad">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => `<button class="key" data-k="${n}">${n}</button>`).join('')}<button class="key del" data-k="del" aria-label="Effacer">${UI.del}</button><button class="key" data-k="0">0</button><button class="key ok" data-k="ok" aria-label="Valider">${okIcon}</button></div>`; }
function keyInput(get, set, onOk) {
  return b => {
    const k = b.dataset.k, v = get();
    if (k === 'del') { set(v.slice(0, -1)); sfx('unpop'); }
    else if (k === 'ok') { if (v !== '') onOk(v); return true; }
    else if (v.length < 5) { set((v === '0' ? '' : v) + k); sfx('tap'); }
    return false;
  };
}
const errText = e => fill(typeof e === 'string' ? e : (e && e.text) || '');
const errShow = e => (e && typeof e === 'object' && e.show) || null;

/* Le cœur du juge, sans écran, pour une réponse fausse : tries = essais faux, celui-ci compris ; left = options encore possibles.
   Rend « reveal » (on montre la réponse) ou « retry » avec l'explication de l'erreur typique, sinon l'aide du moment, sinon « Regarde encore ». */
function verdict(st, val, tries, left, forceWhy) {
  if (tries >= 3 || left <= 1) return { kind: 'reveal' };
  const e = forceWhy != null ? forceWhy : (st.errors && st.errors[String(val)]);
  return { kind: 'retry', why: errText(e) || fill((st.hints && st.hints[Math.min(tries - 1, st.hints.length - 1)]) || PH.lookAgain), show: errShow(e), typed: !!e };
}
const isRight = (st, val) => String(val) === String(st.answer);

/* Juge commun à toutes les questions : 3 essais, explication de chaque erreur typique, puis la réponse montrée. */
function makeJudge(st, item, alive, h) {
  let tries = 0; const wrong = [];
  h = Object.assign({ redraw: () => {}, onRight: () => {}, onReveal: () => {}, left: () => 9, after: () => { if (st.after) stage(st.after); } }, h);
  const api = {
    done: false, wrong,
    async submit(val, recorded, forceWhy) {
      if (api.done) return;
      item.answers.push(String(recorded != null ? recorded : val));
      if (forceWhy == null && isRight(st, val)) {
        api.done = true; item.done = true; item.ok = true; item.first = tries === 0;
        if (item.first) { P.fish++; dropReview(st); } else { P.gold++; addReview(st); }
        save(); bumpFish(!item.first); mood('happy'); h.onRight(); h.after(); h.redraw();
        const msg = (item.first ? pick(PH.good) : fill(PH.gold)) + (st.sol ? ' ' + fill(st.sol) : '');
        bubble(msg, 'good'); await speak(msg);
        if (!item.first && alive() && await hasClip('bravo_effort')) { stage([{ kind: 'maman' }]); await playClip('bravo_effort'); if (alive()) h.after(); }
        if (alive()) showNext();
        return;
      }
      tries++; wrong.push(String(val)); sfx('soft'); mood('oops');
      const v = verdict(st, val, tries, h.left(), forceWhy);
      if (v.kind === 'reveal') {
        api.done = true; item.done = true; item.ok = false; addReview(st); save();
        h.onReveal(); h.after(); h.redraw();
        const msg = `${PH.revealStart} ${st.sol ? fill(st.sol) : st.answer} ${PH.revealEnd}`;
        bubble(msg, 'try'); await speak(msg); if (alive()) showNext();
        return;
      }
      if (v.show) stage(v.show);
      h.redraw();
      const msg = PH.notYet + ' ' + (tries > 1 ? PH.otherWay + ' ' : '') + v.why;
      bubble(msg, 'try'); await speak(msg);
      if (alive() && !api.done) mood('think');
    },
  };
  return api;
}

function askStep(st, alive, opts = {}) {
  if (!opts.keepStage) stage(st.show);
  const q = fill(st.ask || st.text);
  bubble(q);
  const item = newItem(st, opts.q);
  let value = '';
  P.repeat = () => speak(fill(opts.say || st.say || st.text));
  speak(fill(opts.say || st.say || st.text)).then(() => { if (alive() && !J.done) mood('think'); });
  const kind = st.optionKind || (st.options && st.options.some(o => String(o).length > 4) ? 'text' : 'plain');
  const J = makeJudge(st, item, alive, {
    redraw: () => draw(),
    left: () => st.type === 'choice' ? st.options.filter(o => !J.wrong.includes(String(o))).length : 9,
    onReveal: () => { if (st.type === 'number') value = String(st.answer); },
    after: () => { if (st.after) stage(st.after); },
  });
  const optHTML = o => {
    const dis = J.done || J.wrong.includes(String(o)) ? 'disabled' : '';
    const cls = `choice ${kind} ${J.wrong.includes(String(o)) ? 'no' : ''} ${J.done && String(o) === String(st.answer) ? 'yes' : ''}`;
    if (kind === 'dots') return `<button class="${cls}" data-o="${esc(o)}" aria-label="${esc(o)}" ${dis}>${dotsHTML(Number(o))}</button>`;
    if (kind === 'icon') return `<div class="opt"><button class="${cls}" data-o="${esc(o)}" aria-label="${esc(wordOf(o))}" ${dis}>${ICON(o)}</button><button class="say-opt" data-say="${esc(wordOf(o))}" aria-label="Écouter">${UI.speaker}</button></div>`;
    if (kind === 'text') return `<div class="opt txt"><button class="say-opt" data-say="${esc(o)}" aria-label="Écouter">${UI.speaker}</button><button class="${cls}" data-o="${esc(o)}" ${dis}>${esc(o)}</button></div>`;
    return `<button class="${cls}" data-o="${esc(o)}" ${dis}>${esc(o)}</button>`;
  };
  const draw = () => {
    if (st.type === 'number') {
      layout(true);
      $('#answer').innerHTML = `<div class="ans-box ${value ? 'filled' : ''} ${J.done && item.ok ? 'right' : ''}" aria-live="polite">${esc(value) || '&nbsp;'}</div>` + (J.done ? '' : keypadHTML());
      const press = keyInput(() => value, v => { value = v; }, v => J.submit(v));
      $('#answer').querySelectorAll('[data-k]').forEach(b => b.onclick = () => { if (!press(b) && !J.done) draw(); else if (b.dataset.k === 'ok') value = ''; });
    } else {
      $('#answer').innerHTML = `<div class="choices k-${kind}">${st.options.map(optHTML).join('')}</div>`;
      $('#answer').querySelectorAll('[data-o]').forEach(b => b.onclick = () => J.submit(b.dataset.o));
      $('#answer').querySelectorAll('[data-say]').forEach(b => b.onclick = e => { e.stopPropagation(); sfx('tap'); speak(b.dataset.say); });
    }
  };
  draw();
  return J;
}

/* ---------- manipulations ---------- */
function manipStep(st, alive) {
  if (st.mode === 'tenframe') return manipTenframe(st, alive);
  if (st.mode === 'blocks') return manipBlocks(st, alive);
  if (st.mode === 'jumps') return manipJumps(st, alive);
  P.i++; return runStep();
}
function checkBtn(extra = '') { return `<div class="m-ctrl">${extra}<button class="btn big check" id="check" aria-label="Vérifier">${UI.check}</button></div>`; }
function manipTenframe(st, alive) {
  const start = st.start || 0, item = newItem(st), added = new Set(), mango = st.item === 'mangue';
  const value = () => st.goal === 'add' ? added.size : start + added.size;
  const draw = () => {
    $('#stage').innerHTML = `<div class="tf-manip ${mango ? 'mango' : ''}">${Array.from({ length: 10 }, (_, i) => {
      const s = i < start, a = added.has(i);
      return `<button class="cell ${s ? 'fixed' : ''}" data-i="${i}" aria-label="case ${i + 1}" ${s || J.done ? 'disabled' : ''}>${s ? `<span class="tok start">${mango ? ICON('mangue') : ''}</span>` : a ? `<span class="tok add">${mango ? ICON('mangue') : ''}</span>` : ''}</button>`;
    }).join('')}</div>`;
    $('#stage').querySelectorAll('.cell:not(.fixed)').forEach(b => b.onclick = () => {
      if (J.done) return; const i = Number(b.dataset.i);
      if (added.has(i)) { added.delete(i); sfx('unpop'); } else { added.add(i); sfx('pop'); }
      draw();
    });
    $('#answer').innerHTML = J.done ? '' : checkBtn();
    const ck = $('#check'); if (ck) ck.onclick = () => { if (!added.size && st.goal !== 'total') { speak(PH.manipEmpty); return; } J.submit(value()); };
  };
  const J = makeJudge(st, item, alive, {
    redraw: () => draw(),
    onReveal: () => { added.clear(); const need = st.goal === 'add' ? st.answer : st.answer - start; for (let i = start; i < start + need && i < 10; i++) added.add(i); },
    after: () => {},
  });
  P.repeat = () => speak(fill(st.say || st.text));
  bubble(fill(st.text)); draw();
  speak(fill(st.say || st.text)).then(() => { if (alive() && !J.done) mood('think'); });
}
async function moveTo(el, dest, cls) {
  const r = el.getBoundingClientRect();
  const target = document.createElement('i'); target.className = 'pc ' + cls; target.style.visibility = 'hidden'; dest.appendChild(target);
  const rt = target.getBoundingClientRect();
  el.remove();
  if (FAST || !document.body.animate) { target.style.visibility = ''; return; }
  const fly = flyOverlay(cls, r, dest.closest('.board') || dest);
  await fly.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${rt.left - r.left}px,${rt.top - r.top}px)` }], { duration: 300, easing: 'ease-out', fill: 'forwards' }).finished.catch(() => {});
  fly.remove(); target.style.visibility = '';
}
function manipBlocks(st, alive) {
  const v = { t: st.t || 0, u: st.u || 0 }; if (st.hundreds) { v.h = st.h || 0; v.hundreds = true; }
  const addCls = st.addTens ? 't' : 'u', nAdd = st.addTens || st.add || 0;
  $('#stage').className = 'stage';
  $('#stage').innerHTML = `<div class="blocks-manip">${boardHTML(v)}<div class="tray" role="button" tabindex="0" aria-label="Unités à poser : touche pour en poser une"><div class="pile">${Array.from({ length: nAdd }, () => pieceHTML(addCls)).join('')}</div></div></div>`;
  const board = $('#stage .board'), tray = $('#stage .tray .pile');
  let busy = false, asked = false, saidTen = false, saidHundred = false;
  bubble(fill(st.text));
  P.repeat = () => speak(fill(st.say || st.text));
  speak(fill(st.say || st.text));
  const ready = () => {
    const u = boardCount(board, 'u'), t = boardCount(board, 't');
    board.classList.toggle('ready-u', u >= 10);
    board.classList.toggle('ready-t', !!board.querySelector('.col-h') && u < 10 && t >= 10);
    if (u >= 10 && !saidTen) { saidTen = true; speak(PH.manipTen); }
    else if (board.classList.contains('ready-t') && !saidHundred) { saidHundred = true; speak(PH.manipHundred); }
    if (!tray.children.length && !board.classList.contains('ready-u') && !board.classList.contains('ready-t') && !asked) {
      asked = true;
      setTimeout(() => { if (!alive()) return; board.classList.add('counts-hidden'); askStep(Object.assign({}, st, { type: 'number' }), alive, { keepStage: true, q: st.text, say: st.ask || PH.manipAsk }); }, FAST ? 5 : 500);
    }
  };
  tray.parentElement.onclick = async () => {
    if (busy || !alive()) return; const pc = tray.querySelector('.pc'); if (!pc) return;
    busy = true; sfx('pop');
    await moveTo(pc, board.querySelector(`.col-${addCls} .pile`), addCls);
    boardRefresh(board); busy = false; ready();
  };
  tray.parentElement.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tray.parentElement.onclick(); } };
  board.onclick = async e => {
    if (busy) return;
    const col = e.target.closest('.col'); if (!col) return;
    if (col.dataset.col === 'u' && board.classList.contains('ready-u')) { busy = true; await regroup(board, 'u'); busy = false; saidHundred = false; ready(); }
    else if (col.dataset.col === 't' && board.classList.contains('ready-t')) { busy = true; await regroup(board, 't'); busy = false; ready(); }
  };
  ready();
}
function manipJumps(st, alive) {
  const from = st.from, to = st.to, W = 680, x0 = 34, x1 = 646, y = 132; const X = n => x0 + (n - from) * (x1 - x0) / (to - from);
  const item = newItem(st); let path = [st.start], fresh = false;
  const cur = () => path[path.length - 1];
  const svg = () => {
    let s = `<line x1="${x0}" y1="${y}" x2="${x1}" y2="${y}" stroke="#22303c" stroke-width="3"/>`;
    for (let n = from; n <= to; n++) {
      const big = n % 10 === 0, mid = n % 5 === 0, on = path.includes(n);
      s += `<line x1="${X(n)}" y1="${y - (big ? 14 : mid ? 10 : 7)}" x2="${X(n)}" y2="${y + (big ? 14 : mid ? 10 : 7)}" stroke="#22303c" stroke-width="${big ? 3.2 : 1.8}"/>`;
      s += `<text x="${X(n)}" y="${y + 40}" text-anchor="middle" font-size="${big ? 22 : n > 99 ? 12.5 : 15}" font-family="${FONT}" font-weight="800" fill="${on ? 'var(--c)' : big ? '#22303c' : '#8a959a'}">${n}</text>`;
    }
    for (let k = 1; k < path.length; k++) {
      const a = path[k - 1], b = path[k], xa = X(a), xb = X(b), h = 22 + (xb - xa) * 0.3, mx = (xa + xb) / 2;
      s += `<path class="${k === path.length - 1 && fresh ? 'arc' : ''}" d="M${xa} ${y - 6} Q${mx} ${y - 6 - 2 * h} ${xb} ${y - 6}" fill="none" stroke="var(--c)" stroke-width="4" pathLength="1" marker-end="url(#arj)"/><text x="${mx}" y="${y - 12 - h}" text-anchor="middle" font-size="24" font-family="${FONT}" font-weight="800" fill="var(--c)">+${b - a}</text>`;
    }
    path.forEach(n => { s += `<circle cx="${X(n)}" cy="${y}" r="9" fill="var(--c)" stroke="#fff" stroke-width="3"/>`; });
    s += `<g transform="translate(${X(cur())} ${y - 22}) scale(.9)">${BOAT}</g>`;
    const hits = Array.from({ length: to - from + 1 }, (_, k) => `<rect class="hit" data-n="${from + k}" role="button" tabindex="0" aria-label="${from + k}" x="${X(from + k) - (x1 - x0) / (to - from) / 2}" y="${y - 70}" width="${(x1 - x0) / (to - from)}" height="130" fill="transparent"/>`).join('');
    return `<svg class="v-svg jumps" viewBox="0 0 ${W} 190" role="img" aria-label="ligne des nombres de ${from} à ${to}"><defs><marker id="arj" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--c)"/></marker></defs>${s}${hits}</svg>`;
  };
  const draw = () => {
    $('#stage').innerHTML = `<div class="jumps-wrap">${visual(st.show)}${svg()}</div>`;
    $('#stage').querySelectorAll('.hit').forEach(r => {
      r.onclick = () => {
        if (J.done) return; const n = Number(r.dataset.n);
        if (n <= cur()) { sfx('soft'); return; }
        path.push(n); sfx('hop'); fresh = true; draw(); fresh = false;
      };
      r.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); r.onclick(); } };
    });
    $('#answer').innerHTML = J.done ? '' : checkBtn(`<button class="btn big ghost" id="undo" aria-label="Annuler le dernier saut">${UI.undo}</button>`);
    const u = $('#undo'); if (u) u.onclick = () => { if (path.length > 1) { path.pop(); sfx('unpop'); draw(); } };
    const ck = $('#check'); if (ck) ck.onclick = () => {
      if (path.length < 2) { speak(PH.jumpsHelp); return; }
      const rec = path.join('→'), val = cur();
      if (st.via != null && val === st.answer && !path.includes(st.via) && st.errors && st.errors.via) { J.submit(val, rec, st.errors.via); path = [st.start]; return; }
      J.submit(val, rec).then(() => { if (!J.done) { path = [st.start]; draw(); } });
    };
  };
  const J = makeJudge(st, item, alive, {
    redraw: () => draw(),
    onReveal: () => { path = st.via != null ? [st.start, st.via, st.answer] : [st.start, st.answer]; },
    after: () => {},
  });
  bubble(fill(st.text)); draw();
  P.repeat = () => speak(fill(st.say || st.text));
  speak(fill(st.say || st.text)).then(() => { if (alive() && !J.done) mood('think'); });
}
/* ---------- remettre l'histoire dans l'ordre ---------- */
function orderStep(st, alive) {
  const item = newItem(st, 'Remettre les images de l\'histoire dans l\'ordre'); item.answer = st.scenes.map((_, i) => i + 1).join('-');
  const deck = shuffle(st.scenes.map((k, i) => ({ k, i })));
  let placed = 0, miss = 0, missHere = 0;
  const draw = () => {
    $('#stage').innerHTML = `<div class="order"><div class="slots">${st.scenes.map((k, i) => `<div class="slot ${i < placed ? 'full' : i === placed ? 'next' : ''}"><span class="n">${i + 1}</span>${i < placed ? sceneSVG(k) : ''}</div>`).join('')}</div>
      <div class="deck">${deck.filter(d => d.i >= placed).map(d => `<button class="sc-card" data-i="${d.i}" aria-label="image">${sceneSVG(d.k)}</button>`).join('')}</div></div>`;
    $('#stage').querySelectorAll('.sc-card').forEach(b => b.onclick = async () => {
      const i = Number(b.dataset.i);
      if (i === placed) {
        placed++; missHere = 0; sfx('pop'); item.answers.push(String(i + 1)); draw();
        if (placed === st.scenes.length) {
          item.ok = true; item.done = true; item.first = miss === 0; if (item.first) P.fish++; else { P.gold++; addReview(st); } save(); bumpFish(!item.first); mood('happy');
          bubble(PH.orderDone, 'good'); await speak(PH.orderDone); if (alive()) showNext();
        }
        return;
      }
      miss++; missHere++; sfx('soft'); mood('oops'); item.answers.push('x' + (i + 1));
      b.classList.remove('shake'); void b.offsetWidth; b.classList.add('shake');
      if (missHere >= 3) { placed++; missHere = 0; draw(); await speak(PH.orderShow); return; }
      await speak(fill((st.hints && st.hints[Math.min(missHere - 1, st.hints.length - 1)]) || PH.orderTry));
    });
  };
  P.repeat = () => speak(fill(st.say || st.text));
  bubble(fill(st.text)); draw(); speak(fill(st.say || st.text));
}
/* ---------- automatismes : calcul express / jeu rapide ---------- */
function opts3(ans, near) {
  const set = new Set([ans]); const cand = shuffle([near, ans + 1, ans - 1, ans + 2, ans - 2].filter(x => x != null && x >= 0 && x <= 10 && x !== ans));
  for (const x of cand) { if (set.size >= 3) break; set.add(x); }
  return shuffle([...set]);
}
function genItem(k) {
  switch (k.kind) {
    case 'complement10': { const a = rnd(1, 9); return { q: `${a} + ? = 10`, answer: 10 - a }; }
    case 'complement-next-ten': { const t = rnd(2, 9) * 10, a = t - rnd(1, 9); return { q: `${a} + ? = ${t}`, answer: t - a }; }
    case 'through10': { let a, b; do { a = rnd(1, 8) * 10 + rnd(5, 9); b = rnd(3, 9); } while (a % 10 + b < 10 || a + b > 99); return { q: `${a} + ${b}`, answer: a + b }; }
    case 'double': { const n = rnd(k.min || 5, k.max || 25); return { q: `le double de ${n}`, answer: 2 * n }; }
    case 'table': { const n = pick(k.n || [2]), m = rnd(1, 10); return { q: `${n} × ${m}`, answer: n * m }; }
    case 'tf-complement': { const f = rnd(1, 9); return { q: 'Combien de cases vides ?', show: [{ kind: 'tenframe', filled: f, small: true }], answer: 10 - f, options: opts3(10 - f, f) }; }
    case 'count-tf': { const f = rnd(2, 10); return { q: 'Combien de points ?', show: [{ kind: 'tenframe', filled: f, small: true }], answer: f, options: opts3(f, 10 - f) }; }
    case 'decomp': { const n = pick(k.n || [5]), a = rnd(0, n); return { q: `${n}, c'est ${a} et combien ?`, show: [{ kind: 'fingers', up: n }], answer: n - a, options: opts3(n - a, a) }; }
    default: return { q: '1 + 1', answer: 2 };
  }
}
function weightedKind(kinds) {
  const sk = child.progress.skills;
  const ws = kinds.map(k => { const s = sk[k.kind]; const err = s && s.n >= 3 ? s.ko / s.n : 0; return (k.w || 1) * (1 + 2 * err); });
  let r = Math.random() * ws.reduce((a, b) => a + b, 0);
  for (let i = 0; i < kinds.length; i++) { r -= ws[i]; if (r <= 0) return kinds[i]; }
  return kinds[kinds.length - 1];
}
function drillHead(k, n, pct) { return `<div class="dtrack"><div class="dwater"><i style="width:${pct}%"></i></div><svg class="dboat" style="left:${pct}%" viewBox="-40 -20 80 40" aria-hidden="true">${BOAT}</svg></div><p class="d-count">${k} / ${n}</p>`; }
function drillStep(st, alive) {
  const prog = child.progress, rec = prog.records[st.id];
  stage([{ kind: 'title', text: st.title }]);
  bubble(st.text);
  const intro = st.text + ' ' + PH.drillGo;
  P.repeat = () => speak(intro); speak(intro);
  $('#answer').innerHTML = `<div class="center stack"><p class="muted" style="margin:0">${rec ? `Ton record : <b>${rec.best} sur ${st.count}</b>` : 'Pas encore de record.'}</p><div><button class="btn big go" id="go">${UI.play}<span>C'est parti !</span></button></div></div>`;
  $('#go').onclick = () => {
    stopSpeech(); P.repeat = null; sfx('next');
    const misses = (prog.drillMisses[st.id] || []).slice(0, 3);
    const items = misses.concat(Array.from({ length: Math.max(0, st.count - misses.length) }, () => { const k = weightedKind(st.kinds); return Object.assign(genItem(k), { kind: k.kind }); }));
    let i = 0, score = 0, value = '', over = false; const missed = [], kinds = {}; const t0 = Date.now();
    const pct = () => Math.min(100, (Date.now() - t0) / (st.seconds * 10));
    const bar = () => { const p = pct(); const w = $('#stage .dwater i'), b = $('#stage .dboat'); if (w) w.style.width = p + '%'; if (b) b.style.left = p + '%'; };
    const timer = setInterval(() => { if (!alive()) { clearInterval(timer); return; } bar(); if (Date.now() - t0 >= st.seconds * 1000) finish(); }, 250);
    const draw = flash => {
      const it = items[i];
      $('#stage').className = 'stage';
      $('#stage').innerHTML = `<div class="drill">${drillHead(i + 1, items.length, pct())}${visual(it.show)}<div class="v-expr">${esc(it.q)}</div>${flash || ''}</div>`;
      if (st.input === 'keypad') {
        layout(true);
        $('#answer').innerHTML = `<div class="ans-box ${value ? 'filled' : ''}">${esc(value) || '&nbsp;'}</div>` + keypadHTML();
        const press = keyInput(() => value, v => { value = v; }, v => answer(v));
        $('#answer').querySelectorAll('[data-k]').forEach(b => b.onclick = () => { if (over) return; if (!press(b)) draw(); });
      } else {
        $('#answer').innerHTML = `<div class="choices">${it.options.map(o => `<button class="choice" data-o="${o}">${o}</button>`).join('')}</div>`;
        $('#answer').querySelectorAll('[data-o]').forEach(b => b.onclick = () => { if (!over) answer(b.dataset.o); });
      }
    };
    const answer = async val => {
      const it = items[i], ok = String(val) === String(it.answer);
      const sk = prog.skills[it.kind] || (prog.skills[it.kind] = { n: 0, ko: 0 }); sk.n++; if (!ok) sk.ko++;
      const kk = kinds[it.kind] || (kinds[it.kind] = { n: 0, ok: 0 }); kk.n++; if (ok) kk.ok++;
      if (ok) { score++; sfx('pop'); } else { missed.push({ q: it.q, answer: it.answer, show: it.show, options: it.options, kind: it.kind }); sfx('soft'); }
      value = ''; over = true;
      draw(ok ? '<div class="flash ok">' + UI.check + '</div>' : `<div class="flash ko">${esc(it.answer)}</div>`);
      $('#answer').innerHTML = '';
      await sleep(ok ? 380 : 1400); over = false;
      if (!alive() || finish.done) return;
      i++; if (i >= items.length) finish(); else draw();
    };
    const finish = async () => {
      if (!alive() || finish.done) return; finish.done = true; clearInterval(timer); over = true; layout(false);
      const secs = Math.round((Date.now() - t0) / 1000);
      const best = prog.records[st.id];
      const isRecord = !best || score > best.best || (score === best.best && secs < best.secs);
      prog.records[st.id] = isRecord ? { best: score, secs, date: today() } : best;
      prog.drillMisses[st.id] = missed.slice(0, 5);
      P.run.drill = { id: st.id, score, count: items.length, secs, record: isRecord, kinds };
      save();
      $('#stage').innerHTML = `<div class="drill"><div class="v-title">${score} sur ${items.length}</div><p class="muted" style="margin:0">en ${Math.floor(secs / 60)} min ${String(secs % 60).padStart(2, '0')} s</p>${isRecord ? '<p class="badge">Record !</p>' : `<p class="muted">Ton record : ${best.best} sur ${items.length}</p>`}</div>`;
      $('#answer').innerHTML = '';
      if (isRecord) { mood('happy'); sfx('gold'); }
      const msg = !best ? PH.drillFirst : isRecord ? PH.drillRecord : PH.drillNoRecord;
      bubble(msg, 'good'); await speak(msg);
      if (!alive()) return;
      if (missed.length) {
        bubble(PH.drillMisses); await speak(PH.drillMisses);
        for (const m of missed) {
          if (!alive()) return;
          const ok = await quickRetry(m, st.input);
          if (ok) { const k = prog.drillMisses[st.id].findIndex(x => x.q === m.q); if (k >= 0) prog.drillMisses[st.id].splice(k, 1); }
        }
        layout(false); save();
      }
      if (alive()) showNext();
    };
    draw();
  };
}
function quickRetry(m, input) {
  return new Promise(res => {
    let value = '';
    const draw = () => {
      $('#stage').innerHTML = `<div class="drill">${visual(m.show)}<div class="v-expr">${esc(m.q)}</div></div>`;
      if (input === 'keypad') {
        layout(true);
        $('#answer').innerHTML = `<div class="ans-box ${value ? 'filled' : ''}">${esc(value) || '&nbsp;'}</div>` + keypadHTML();
        const press = keyInput(() => value, v => { value = v; }, v => done(v));
        $('#answer').querySelectorAll('[data-k]').forEach(b => b.onclick = () => { if (!press(b)) draw(); });
      } else {
        $('#answer').innerHTML = `<div class="choices">${m.options.map(o => `<button class="choice" data-o="${o}">${o}</button>`).join('')}</div>`;
        $('#answer').querySelectorAll('[data-o]').forEach(b => b.onclick = () => done(b.dataset.o));
      }
    };
    const done = async v => {
      const ok = String(v) === String(m.answer);
      $('#answer').innerHTML = ''; sfx(ok ? 'pop' : 'soft');
      $('#stage .drill').insertAdjacentHTML('beforeend', ok ? '<div class="flash ok">' + UI.check + '</div>' : `<div class="flash ko">${esc(m.answer)}</div>`);
      await sleep(ok ? 450 : 1500); res(ok);
    };
    draw();
  });
}

/* ---------- la fiche papier ---------- */
function paperItems() {
  const out = [];
  (P.lesson.paper.levels || []).forEach(lv => lv.items.forEach(it => { if (it.answer !== undefined) out.push(Object.assign({ stars: lv.stars }, it)); }));
  return out;
}
const STAR = '<svg viewBox="0 0 24 24" aria-hidden="true"><polygon points="12,2 14.9,8.6 22,9.3 16.6,14 18.2,21 12,17.3 5.8,21 7.4,14 2,9.3 9.1,8.6" fill="#e0a100" stroke="#8a6400"/></svg>';
function paperStep(st, alive) {
  $('#stage').className = 'stage';
  $('#stage').innerHTML = `<div class="paper-call"><div class="paper-ic">${UI.paper}</div><div class="v-title">Ta ${esc(ficheOf(child))}</div><div class="v-text">« ${esc(P.lesson.paper.title)} »</div></div>`;
  bubble(fill(st.text));
  P.repeat = () => speak(fill(st.say || st.text)); speak(fill(st.say || st.text));
  $('#answer').innerHTML = `<div class="center"><button class="btn big go" id="fini">${UI.check}<span>J'ai fini ma fiche</span></button></div>`;
  $('#fini').onclick = () => {
    stopSpeech(); sfx('next');
    const items = paperItems(); const vals = {}, res = {}; let sel = items[0] ? items[0].id : null, round = 0;
    const draw = () => {
      $('#stage').className = 'stage top';
      $('#stage').innerHTML = `<div class="paper-list">${items.map(it => {
        const r = res[it.id];
        return `<button class="p-item ${sel === it.id && round < 2 && (!r || !r.ok) ? 'sel' : ''} ${r ? (r.ok ? 'ok' : 'ko') : ''}" data-i="${it.id}"><span class="lab"><span class="stars">${STAR.repeat(it.stars)}</span> ${esc(it.short || it.q)}${r && !r.ok && r.why ? `<span class="why">${esc(r.why)}</span>` : ''}</span><span class="val">${esc(vals[it.id] || '')}</span><span class="mark">${r ? (r.ok ? UI.check : '✗') : ''}</span></button>`;
      }).join('')}</div>`;
      layout(round < 2);
      $('#answer').innerHTML = round < 2 ? keypadHTML() : '';
      $('#stage').querySelectorAll('[data-i]').forEach(b => b.onclick = () => { if (round < 2) { sel = b.dataset.i; sfx('tap'); draw(); } });
      $('#answer').querySelectorAll('[data-k]').forEach(b => b.onclick = () => {
        const k = b.dataset.k; if (k === 'ok') return check();
        if (!sel || (res[sel] && res[sel].ok)) return;
        let v = vals[sel] || ''; if (k === 'del') v = v.slice(0, -1); else if (v.length < 5) v = (v === '0' ? '' : v) + k;
        vals[sel] = v; if (res[sel]) delete res[sel]; sfx('tap');
        draw();
      });
    };
    const check = async () => {
      if (!items.some(it => vals[it.id])) { bubble(PH.paperEmpty, 'try'); speak(PH.paperEmpty); return; }
      round++; let firstWhy = '', nOk = 0, nKo = 0;
      items.forEach(it => {
        const v = vals[it.id]; if (v === undefined || v === '') return;
        if (res[it.id] && res[it.id].ok) { nOk++; return; }
        const ok = String(v) === String(it.answer);
        let rec = P.run.items.find(x => x.id === 'fiche-' + it.id);
        if (!rec) { rec = { id: 'fiche-' + it.id, q: 'Fiche ' + '★'.repeat(it.stars) + ' ' + (it.short || it.q), answer: it.answer, answers: [], ok: false, first: false, paper: true, skill: it.skill || (P.lesson.skills || [])[0] || '' }; P.run.items.push(rec); }
        rec.answers.push(String(v)); rec.ok = ok; rec.first = ok && rec.answers.length === 1;
        const why = ok ? '' : (errText(it.errors && it.errors[String(v)]) || (round >= 2 ? `La réponse était ${it.answer}.` : PH.paperLook));
        rec.done = ok || round >= 2;
        res[it.id] = { ok, why };
        if (ok) { nOk++; if (rec.first) P.fish++; else P.gold++; } else { nKo++; if (!firstWhy && it.errors && it.errors[String(v)]) firstWhy = why; }
      });
      if (round >= 2) items.forEach(it => { if (res[it.id] && !res[it.id].ok) vals[it.id] = String(it.answer); });
      $('#nfish').textContent = P.fish + P.gold;
      save(); draw(); sfx(nKo ? 'soft' : 'good'); mood(nKo ? 'oops' : 'happy');
      const said = nKo === 0 ? PH.paperAllGood : round < 2 ? PH.paperFix + (firstWhy ? ' ' + firstWhy : '') : PH.paperFinal;
      bubble(said, nKo ? 'try' : 'good'); await speak(said);
      if (alive() && (nKo === 0 || round >= 2)) { round = 2; draw(); showNext(); }
    };
    draw();
  };
}

/* ---------- enregistreur réutilisable ---------- */
function recorder(onKeep, onSkip) {
  const canRec = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  if (!canRec) { $('#answer').innerHTML = `<p class="center">${esc(PH.micOff)}</p>`; onSkip(); return; }
  let rec = null, chunks = [], blob = null, t0 = 0, dur = 0, timer = null, stream = null;
  const draw = state => {
    $('#answer').innerHTML = state === 'idle' ? `<button class="rec-btn" id="rb" aria-label="Enregistrer">${UI.mic}</button>`
      : state === 'on' ? `<button class="rec-btn on" id="rb" aria-label="Arrêter">${UI.stop}</button><p class="center rec-time"><b id="tm">0 s</b></p>`
      : `<div class="rec-done"><button class="btn big soft" id="play" aria-label="Écouter">${UI.play}</button><button class="btn big ghost" id="redo" aria-label="Recommencer">${UI.redo}</button><button class="btn big" id="keep" style="--c:var(--good)" aria-label="Garder">${UI.check}</button></div>`;
    const rb = $('#rb'); if (rb) rb.onclick = state === 'idle' ? start : stop;
    if (state === 'done') {
      $('#play').onclick = () => { stopSpeech(); playFile(URL.createObjectURL(blob), false); };
      $('#redo').onclick = () => { blob = null; draw('idle'); };
      $('#keep').onclick = async () => { showNext(false); $('#keep').disabled = true; sfx('good'); mood('happy'); await onKeep(blob, dur); };
    }
  };
  const start = async () => {
    stopSpeech(); mood('listen');
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch (e) { $('#answer').innerHTML = `<p class="center">${esc(PH.micOff)}</p>`; onSkip(); return; }
    chunks = []; rec = new MediaRecorder(stream); rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    rec.onstop = () => { blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' }); stream.getTracks().forEach(t => t.stop()); clearInterval(timer); dur = Math.max(1, Math.round((Date.now() - t0) / 1000)); mood(null); draw('done'); };
    rec.start(); t0 = Date.now(); draw('on');
    timer = setInterval(() => { const s = Math.round((Date.now() - t0) / 1000); const el = $('#tm'); if (el) el.textContent = s + ' s'; if (s >= 150) stop(); }, 500);
  };
  const stop = () => { try { if (rec && rec.state !== 'inactive') rec.stop(); } catch (e) {} };
  draw('idle');
}
async function saveRecording(kind, q, blob, dur, extra) {
  await DB.addRec(Object.assign({ profile: child.id, lesson: P.lesson.id, title: P.lesson.title, kind, q, ts: Date.now(), dur, mime: blob.type, blob, heard: false }, extra || {}));
  P.run.recs++; save();
}
function recordStep(st, alive) {
  stage(st.show || [{ kind: 'title', text: 'Explique avec ta voix' }]);
  bubble(fill(st.text));
  P.repeat = () => speak(fill(st.say || st.text));
  (async () => { await speak(fill(st.say || st.text)); if (alive() && st.clip && await hasClip(st.clip)) { await playClip(st.clip); } })();
  recorder(async (blob, dur) => { await saveRecording(st.kind || 'methode', st.text, blob, dur, st.story ? { story: st.story } : null); if (alive()) { P.i++; runStep(); } }, () => showNext());
  showNext(true, 'skip');
}

/* ---------- lecture répétée (fluence) ---------- */
function passageHTML(sents, hl) { return `<div class="passage">${sents.map((s, i) => `<span class="${i === hl ? 'hl' : ''}">${esc(s)}</span>`).join(' ')}</div>`; }
function readingStep(st, alive) {
  const words = st.passage.join(' ').split(/\s+/).filter(w => /[\p{L}\p{N}]/u.test(w)).length;
  const listen = async () => {
    showNext(false); $('#answer').innerHTML = '';
    $('#stage').className = 'stage top';
    $('#stage').innerHTML = `<div class="v-title read-title">${esc(st.title)}</div>` + passageHTML(st.passage, -1);
    if (st.reread) { bubble(PH.rereadIntro); await speak(PH.rereadIntro); if (!alive()) return; }
    bubble(PH.readListen); await speak(PH.readListen);
    for (let i = 0; i < st.passage.length; i++) {
      if (!alive()) return;
      $('#stage').querySelector('.passage').outerHTML = passageHTML(st.passage, i);
      const ok = await speakWhole(st.passage[i]); if (!ok) return; await sleep(250);
    }
    if (!alive()) return;
    $('#stage').querySelector('.passage').outerHTML = passageHTML(st.passage, -1);
    bubble(PH.readYourTurn); speak(PH.readYourTurn);
    recorder(async (blob, dur) => {
      await saveRecording('lecture', st.title, blob, dur, { passage: st.passage, words, reread: !!st.reread });
      if (alive()) { P.i++; runStep(); }
    }, () => showNext());
    showNext(true, 'skip');
  };
  P.repeat = listen; listen();
}
/* ---------- histoire : écoute sans images ---------- */
function listenStep(st, alive) {
  const play = async () => {
    showNext(false);
    stage([{ kind: 'listen' }, { kind: 'title', text: st.title }]);
    const intro = st.pass > 1 ? PH.storyListenAgain : PH.storyListen;
    bubble(intro); await speak(intro); if (!alive()) return;
    bubble('');
    mood('listen');
    for (const s of st.sentences) { if (!alive()) return; const ok = await speakWhole(s); if (!ok) return; await sleep(350); }
    mood(null);
    if (alive()) { bubble(PH.listenAgain); speak(PH.listenAgain); showNext(); }
  };
  P.repeat = play; play();
}

/* ---------- fin de séance ---------- */
function saveRun(done) {
  if (!P || P.run.end) return;
  P.run.end = Date.now(); P.run.done = done; P.run.fish = P.fish; P.run.gold = P.gold;
  child.progress.runs.push(P.run);
  if (done) child.progress.done[P.lesson.id] = today();
  child.progress.resume = null;
  save();
}
async function endStep(st, alive) {
  saveRun(true); endWake();
  const mins = Math.max(1, Math.round((P.run.end - P.run.start) / 60000));
  $('#stage').className = 'stage top';
  $('#stage').innerHTML = `<div class="v-title">Séance terminée</div><div class="fishes">${Array.from({ length: P.fish }, () => FISH(false)).join('')}${Array.from({ length: P.gold }, () => FISH(true)).join('')}</div>${mapHTML(child)}`;
  drawMap($('#stage'), child, P.fromF);
  mood('happy'); sfx('gold');
  bubble(`${mins} minute${mins > 1 ? 's' : ''} de travail · ${P.fish + P.gold} réponse${P.fish + P.gold > 1 ? 's' : ''} trouvée${P.fish + P.gold > 1 ? 's' : ''}${P.gold ? `, dont ${P.gold} après une erreur` : ''}.`, 'good');
  await speak(PH.endDone + (P.gold ? ' ' + PH.endGold : '') + ' ' + PH.mapMove);
  if (!alive()) return;
  if (journey(child).stamps.length > P.fromStamps) { sfx('gold'); await speak(PH.newEscale); if (!alive()) return; if (await hasClip('bravo_escale')) await playClip('bravo_escale'); if (!alive()) return; }
  await playClip(st.clip);
  if (!alive()) return;
  showNext(true, 'end'); P.nextHandler = () => { P = null; screenChild(child, { quiet: true }); };
}

/* ============================ espace parent ============================ */
function screenPin(onOk) {
  setChild(null); stopSpeech(); screen('parent');
  let v = '';
  const draw = () => {
    app.innerHTML = `<div class="page stack" style="max-width:420px">
    <div class="row" style="justify-content:space-between"><button class="icon-btn" id="back" aria-label="Retour">${UI.back}</button><h2>Espace parent</h2></div>
    <p class="center muted">Tapez le code parent.</p><div class="pin">${[0, 1, 2, 3].map(k => `<span>${v[k] ? '•' : ''}</span>`).join('')}</div>
    <div class="keypad" style="--c:var(--river);--c-soft:var(--river-soft)">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => `<button class="key" data-k="${n}">${n}</button>`).join('')}<button class="key del" data-k="del" aria-label="Effacer">${UI.del}</button><button class="key" data-k="0">0</button><span></span></div>
    <p class="center small" id="msg" style="color:var(--try)"></p></div>`;
    $('#back').onclick = screenHome;
    app.querySelectorAll('[data-k]').forEach(b => b.onclick = () => {
      const k = b.dataset.k; if (k === 'del') v = v.slice(0, -1); else if (v.length < 4) v += k;
      if (v.length === 4) { if (v === S.pin) return onOk(); v = ''; draw(); $('#msg').textContent = 'Code incorrect.'; return; }
      draw();
    });
  };
  draw();
}
function fmtDate(ts) { const d = new Date(ts); return d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' }) + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }); }
function status(it) { return it.ok ? (it.first ? '<span class="pill first">1er essai</span>' : '<span class="pill after">après erreur</span>') : (it.answers.length ? '<span class="pill shown">réponse montrée</span>' : '<span class="pill shown">non fait</span>'); }
const RECIT = ['Les personnages (Bintou, la grand-mère, le pêcheur)', 'Le lieu (le marché, le fleuve)', 'Le problème (le panier tombe dans le fleuve)', 'Les étapes dans l\'ordre', 'La fin (merci, la mangue offerte)', 'Les émotions (la peur, puis la joie)'];
function measureLine(m) { return m.type === 'fluence' ? `Lecture : <b>${m.wcpm} mots par minute</b> (${m.read} lus, ${m.errors} erreur${m.errors > 1 ? 's' : ''}, ${m.secs} s) · repère de fin de CE1 : 70` : `Récit : <b>${m.score} sur ${RECIT.length}</b>`; }
const recKind = r => r.kind === 'lecture' ? (r.reread ? 'Relecture' : 'Lecture') : r.kind === 'recit' ? 'Récit' : 'Méthode';
async function markHeard(r) { if (r && !r.heard) { r.heard = true; await DB.putRec(r); } }
async function screenParent(tab) {
  setChild(null); stopSpeech(); screen('parent');
  const tabs = [['suivi', 'Suivi'], ['maman', 'Voix de Maman'], ['kono', 'Voix et affichage'], ['rapport', 'Rapport'], ['reglages', 'Réglages']];
  app.innerHTML = `<div class="page stack"><div class="row" style="justify-content:space-between"><h2>Espace parent</h2><button class="btn ghost" id="out" style="--c:var(--river)">Sortir</button></div>
  <div class="tabs">${tabs.map(([k, l]) => `<button class="tab ${k === tab ? 'on' : ''}" data-t="${k}">${l}</button>`).join('')}</div><div id="pane" class="stack"></div></div>`;
  $('#out').onclick = screenHome;
  app.querySelectorAll('[data-t]').forEach(b => b.onclick = () => screenParent(b.dataset.t));
  const pane = $('#pane');
  if (tab === 'suivi') {
    const recs = (await DB.recs()) || [];
    const cards = S.profiles.map(p => {
      const pr = p.progress, runs = pr.runs.slice().reverse(), rr = recs.filter(r => r.profile === p.id).sort((a, b) => b.ts - a.ts);
      const unheard = rr.filter(r => !r.heard).length;
      const recsDrill = Object.entries(pr.records).map(([k, r]) => `${esc(k)} : ${r.best} (${r.secs} s, ${esc(r.date)})`).join(' · ');
      return `<div class="card stack"><h3 style="color:var(--${esc(p.couleur)})">${esc(kidLabel(p))} <span class="small muted">· ${esc(parcoursLabel(p))}</span></h3>
      ${unheard ? `<p class="warn">${unheard} enregistrement${unheard > 1 ? 's' : ''} pas encore écouté${unheard > 1 ? 's' : ''}. L'enfant s'applique davantage quand il sait qu'on l'écoute.</p>` : ''}
      ${resumeOf(p) ? `<p class="warn">Séance à reprendre : « ${esc(resumeOf(p).title)} », étape ${resumeOf(p).i + 1} sur ${resumeOf(p).steps.length}, commencée le ${esc(resumeOf(p).date || '')}. L'enfant la retrouve en touchant son prénom.</p>` : ''}
      ${skillTableHTML(p)}
      ${masteryTableHTML(p)}
      ${pr.measures.length ? `<div><h3 style="font-size:1rem">Mesures</h3>${pr.measures.slice().reverse().map(m => `<p class="small" style="margin:2px 0">${esc(m.date)} · ${measureLine(m)}</p>`).join('')}</div>` : ''}
      ${recsDrill ? `<p class="small" style="margin:0"><b>Records d'automatismes :</b> ${recsDrill}</p>` : ''}
      <h3 style="font-size:1rem">Enregistrements</h3>
      ${rr.length ? rr.map(r => `<div class="clip"><span class="txt"><b>${recKind(r)}</b> · ${esc(r.title)} · ${fmtDate(r.ts)} · ${r.dur || '?'} s ${r.heard ? '<span class="pill first">écouté</span>' : '<span class="pill shown">pas encore écouté</span>'}<br><span class="small muted">${esc(r.q)}</span></span><button class="btn soft sm" data-play="${r.id}">Écouter</button>${r.kind === 'lecture' ? `<button class="btn sm" data-measure="${r.id}" style="--c:var(--river)">Mesurer</button>` : r.kind === 'recit' ? `<button class="btn sm" data-grade="${r.id}" style="--c:var(--river)">Noter le récit</button>` : ''}<button class="link" data-del="${r.id}">Supprimer</button></div>`).join('') : '<p class="muted small">Aucun enregistrement.</p>'}
      <details><summary>Détail des séances (${runs.length})</summary>${runs.length ? runs.map(r => `<div><p style="margin:8px 0 4px"><b>${esc(r.title)}</b> · ${fmtDate(r.start)} · ${Math.max(1, Math.round(((r.end || r.start) - r.start) / 60000))} min ${r.done ? '' : '· <span class="pill shown">arrêtée avant la fin</span>'}${r.drill ? ` · automatismes ${r.drill.score}/${r.drill.count} en ${r.drill.secs} s` : ''}</p>
        <div class="table-wrap"><table class="t"><tr><th>Question</th><th>Réponses tapées</th><th>Résultat</th></tr>${r.items.map(it => `<tr><td>${esc(it.q)}</td><td>${esc(it.answers.join(' → ') || '—')}</td><td>${status(it)}</td></tr>`).join('')}</table></div></div>`).join('') : '<p class="muted">Pas encore de séance.</p>'}</details>
      <p class="small muted">À revoir automatiquement : ${pr.review.length} défi${pr.review.length > 1 ? 's' : ''} de leçon, ${Object.values(pr.drillMisses).reduce((a, b) => a + b.length, 0)} calcul${Object.values(pr.drillMisses).reduce((a, b) => a + b.length, 0) > 1 ? 's' : ''} d'automatismes.</p></div>`;
    }).join('') || '<p class="muted">Aucun enfant pour l\'instant.</p>';
    pane.innerHTML = backupWarnHTML() + cards;
    const tb = $('#tobackup'); if (tb) tb.onclick = () => screenParent('reglages');
    pane.querySelectorAll('[data-play]').forEach(b => b.onclick = async () => { const r = recs.find(x => String(x.id) === b.dataset.play); if (r) { stopSpeech(); playFile(URL.createObjectURL(r.blob), false); await markHeard(r); const p = b.parentElement.querySelector('.pill.shown'); if (p) { p.className = 'pill first'; p.textContent = 'écouté'; } } });
    pane.querySelectorAll('[data-del]').forEach(b => { let armed = false; b.onclick = async () => { if (!armed) { armed = true; b.textContent = 'Confirmer la suppression'; return; } await DB.delRec(Number(b.dataset.del)); screenParent('suivi'); }; });
    pane.querySelectorAll('[data-measure]').forEach(b => b.onclick = () => screenMeasure(recs.find(x => String(x.id) === b.dataset.measure)));
    pane.querySelectorAll('[data-grade]').forEach(b => b.onclick = () => screenGrade(recs.find(x => String(x.id) === b.dataset.grade)));
  }
  if (tab === 'maman') {
    const keys = new Set((await DB.clipKeys()) || []);
    pane.innerHTML = `<div class="card"><p style="margin-top:0">Maman enregistre ces phrases une fois, avec ses mots à elle. Kono les fait entendre au bon moment. Une phrase non enregistrée est remplacée par une phrase neutre de Kono, qui ne se fait jamais passer pour Maman.</p>
      ${CLIPS.flatMap(c => c.perChild ? S.profiles.map(p => ({ c, p, key: `${c.id}@${p.id}` })) : [{ c, p: null, key: c.id }]).map(({ c, p, key }) => `<div class="clip" data-id="${esc(key)}"><span class="txt">${p ? `<span class="pill" style="background:var(--${esc(p.couleur)}-soft)">${esc(kidLabel(p))}</span> ` : ''}${esc(c.maman.replace('[prénom]', p ? kidLabel(p) : '…'))}</span>
        <span class="state" style="color:${keys.has(key) ? 'var(--good)' : 'var(--muted)'}">${keys.has(key) ? 'Enregistrée' : 'À enregistrer'}</span>
        <button class="btn sm" data-rec style="--c:var(--maman)">${keys.has(key) ? 'Refaire' : 'Enregistrer'}</button>
        ${keys.has(key) ? `<button class="btn soft sm" data-play>Écouter</button><button class="link" data-del>Effacer</button>` : ''}</div>`).join('')}</div>`;
    pane.querySelectorAll('.clip').forEach(row => {
      const id = row.dataset.id; let rec = null, stream = null, chunks = [];
      const rb = row.querySelector('[data-rec]');
      rb.onclick = async () => {
        if (rec && rec.state === 'recording') { rec.stop(); return; }
        if (!(navigator.mediaDevices && window.MediaRecorder)) { rb.textContent = 'Micro indisponible'; return; }
        try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch (e) { rb.textContent = 'Micro refusé'; return; }
        chunks = []; rec = new MediaRecorder(stream); rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
        rec.onstop = async () => { stream.getTracks().forEach(t => t.stop()); await DB.putClip(id, new Blob(chunks, { type: rec.mimeType || 'audio/webm' })); screenParent('maman'); };
        rec.start(); rb.textContent = 'Arrêter'; rb.style.setProperty('--c', '#a31226');
      };
      const pb = row.querySelector('[data-play]'); if (pb) pb.onclick = async () => { stopSpeech(); const b = await DB.getClip(id); if (b) playFile(URL.createObjectURL(b), false); };
      const db = row.querySelector('[data-del]'); if (db) db.onclick = async () => { await DB.delClip(id); screenParent('maman'); };
    });
  }
  if (tab === 'kono') {
    pane.innerHTML = `<div class="card stack"><h3>Affichage et sons</h3>
      <label class="toggle"><input type="checkbox" id="st-sub" ${S.settings.subtitles ? 'checked' : ''}> Afficher les sous-titres sous Kono</label>
      <p class="small muted" style="margin:0">Par défaut, ils sont cachés : l'enfant écoute au lieu de lire ce qu'on lui dit, et regarde le dessin. Ils s'affichent d'office si la tablette n'a pas de voix française.</p>
      <label class="toggle"><input type="checkbox" id="st-snd" ${S.settings.sounds ? 'checked' : ''}> Petits sons quand l'enfant pose, valide ou trouve</label></div>
      <div class="card stack"><h3>Pour l'enfant</h3>
      <label class="toggle"><input type="checkbox" id="st-gauch" ${S.settings.gaucher ? 'checked' : ''}> Main gauche : le clavier et la flèche à gauche, Kono à droite</label>
      <label class="toggle"><input type="checkbox" id="st-calme" ${S.settings.calme ? 'checked' : ''}> Moins d'animations : Kono reste calme, rien ne clignote ni ne saute</label>
      <label class="toggle"><input type="checkbox" id="st-contr" ${S.settings.contraste ? 'checked' : ''}> Contraste renforcé : texte plus noir, bords plus marqués</label></div>
      <div class="card stack"><h3>La voix de Kono</h3>${voiceControls()}</div>`;
    $('#st-sub').onchange = e => { S.settings.subtitles = e.target.checked; save(); };
    $('#st-snd').onchange = e => { S.settings.sounds = e.target.checked; save(); };
    [['st-gauch', 'gaucher'], ['st-calme', 'calme'], ['st-contr', 'contraste']].forEach(([id, k]) => { $('#' + id).onchange = e => { S.settings[k] = e.target.checked; save(); applySettings(); }; });
    bindVoiceControls();
  }
  if (tab === 'rapport') {
    RECS_CACHE = (await DB.recs()) || [];
    const txt = report();
    pane.innerHTML = `<div class="card stack"><p style="margin:0">Le dimanche : copier le rapport pour l'envoyer, ou l'enregistrer dans un fichier à déposer à l'école, qui en fait un tableau par classe. Son format ne change pas d'une semaine à l'autre, pour pouvoir comparer.</p><textarea id="rep" readonly aria-label="Rapport">${esc(txt)}</textarea><div class="row"><button class="btn" id="copy" style="--c:var(--river)">Copier le rapport</button><button class="btn ghost" id="repfile" style="--c:var(--river)">Enregistrer dans un fichier</button><span id="cp" class="small muted"></span></div></div>`;
    $('#copy').onclick = async () => { try { await navigator.clipboard.writeText(txt); $('#cp').textContent = 'Copié.'; } catch (e) { const t = $('#rep'); t.focus(); t.select(); $('#cp').textContent = 'Sélectionné : utilisez Copier.'; } };
    $('#repfile').onclick = () => { download(`corridor-rapport-${S.ecole && S.ecole.id ? S.ecole.id : 'libre'}-${today()}.json`, JSON.stringify(reportData(txt), null, 1), 'application/json'); $('#cp').textContent = 'Fichier enregistré.'; };
  }
  if (tab === 'reglages') {
    let persisted = null; try { persisted = navigator.storage && navigator.storage.persisted ? await navigator.storage.persisted() : null; } catch (e) {}
    const installed = ['standalone', 'fullscreen', 'minimal-ui'].some(m => matchMedia(`(display-mode: ${m})`).matches);
    pane.innerHTML = `<div class="card stack"><h3>Les enfants</h3>
      ${S.profiles.map(p => `<div class="row" style="justify-content:space-between"><span><b style="color:var(--${esc(p.couleur)})">${esc(kidLabel(p))}</b> <span class="small muted">· ${esc(parcoursLabel(p))}${ageOf(p.dob) != null ? ` · ${ageOf(p.dob)} ans` : ''}</span></span><span class="row"><button class="btn soft sm" data-edit="${esc(p.id)}">Modifier</button><button class="btn soft sm" data-exp="${esc(p.id)}">Exporter</button><button class="link" data-rm="${esc(p.id)}">Supprimer</button></span></div>`).join('') || '<p class="muted small" style="margin:0">Aucun enfant.</p>'}
      <div class="row"><button class="btn" id="addp" style="--c:var(--river)">Ajouter un enfant</button><label class="btn ghost" style="--c:var(--river)">Importer un profil<input type="file" id="impp" accept="application/json,.json" hidden></label></div>
      <p class="small muted" style="margin:0">Exporter un profil : un fichier avec le suivi de l'enfant, ses enregistrements et les phrases de Maman, pour le retrouver sur une autre tablette.</p><p class="small" id="impmsgp"></p></div>
    <div class="card stack"><h3>École</h3><p class="small" style="margin:0">${esc(ecoleLine())}.</p>${accessRequired() && !(S.ecole && S.ecole.id) ? `<div class="row"><input type="text" id="ecode" autocomplete="off" autocapitalize="characters" placeholder="Code d'inscription" style="text-transform:uppercase"><button class="btn sm" id="ecode-go" style="--c:var(--river)">Enregistrer le code</button><span class="small" id="ecode-msg" style="color:var(--try)"></span></div>` : ''}</div>
    <div class="card stack"><p style="margin:0">Code parent et voix de Kono.</p><div><button class="btn" id="setup" style="--c:var(--river)">Modifier</button></div></div>
    <div class="card stack"><h3>Sauvegarder le suivi</h3><p class="small" style="margin:0">Le suivi vit dans la tablette. Une tablette réinitialisée le perd. Sauvegardez-le de temps en temps dans un fichier (il reste chez vous : rien n'est envoyé). Les enregistrements audio ne sont pas dans ce fichier.</p>
      <div class="row"><button class="btn" id="exp" style="--c:var(--river)">Télécharger la sauvegarde</button><label class="btn ghost" style="--c:var(--river)">Restaurer une sauvegarde<input type="file" id="imp" accept="application/json,.json" hidden></label></div><p class="small" id="impmsg"></p></div>
    <div class="card stack"><h3>Mémoire de la tablette</h3><p class="small" style="margin:0">Le suivi est rangé dans ce navigateur, à l'adresse <b>${esc(location.origin)}</b>. Un autre navigateur ou une autre adresse ne le voit pas. Application installée : <b>${installed ? 'oui' : 'non (ouverte dans le navigateur)'}</b>. Mémoire protégée contre l'effacement automatique : <b>${persisted === null ? 'inconnu' : persisted ? 'oui' : 'pas encore'}</b>.</p></div>
    <div class="card stack"><h3>Bloquer la tablette sur l'application</h3><p class="small" style="margin:0">Android : Paramètres › Sécurité › Épinglage d'écran. Ouvrez ${APPNAME}, affichez les applications récentes, touchez l'icône de l'application puis « Épingler ».</p></div>
    <div class="card stack"><h3>Journal</h3><p class="small muted" style="margin:0">${(S.log || []).length ? `${(S.log || []).length} erreur${(S.log || []).length > 1 ? 's' : ''} notée${(S.log || []).length > 1 ? 's' : ''} sur cette tablette. À copier dans un message si l'application se comporte mal.` : 'Aucune erreur notée sur cette tablette.'}</p>
      ${(S.log || []).slice(-5).reverse().map(l => `<p class="small" style="margin:0">${esc(l.ts.slice(0, 16).replace('T', ' '))} · v${esc(l.v)} · ${esc(l.ecran)} · ${esc(l.m)}</p>`).join('')}
      ${(S.log || []).length ? `<div class="row"><button class="btn soft sm" id="logcopy">Copier le journal</button><button class="link" id="logclear">Effacer le journal</button><span class="small muted" id="logmsg"></span></div>` : ''}</div>
    <div class="card stack"><h3>Remettre le suivi à zéro</h3><p class="small muted" style="margin:0">Efface les séances, les records et les mesures (pas les enregistrements de Maman).</p><div class="row"><input type="text" id="conf" placeholder="Tapez EFFACER"><button class="btn ghost" id="wipe">Effacer le suivi</button></div></div>`;
    $('#setup').onclick = screenSetup;
    $('#addp').onclick = () => screenProfile(null);
    pane.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => screenProfile(profileOf(b.dataset.edit)));
    pane.querySelectorAll('[data-rm]').forEach(b => { let armed = false; b.onclick = async () => { if (!armed) { armed = true; b.textContent = 'Confirmer : son suivi et ses enregistrements seront effacés'; return; } await removeProfile(b.dataset.rm); screenParent('reglages'); }; });
    pane.querySelectorAll('[data-exp]').forEach(b => b.onclick = () => exportProfile(profileOf(b.dataset.exp)));
    $('#impp').onchange = async e => {
      const f = e.target.files[0]; if (!f) return;
      try { const n = await importProfile(JSON.parse(await f.text())); $('#impmsgp').textContent = `Profil de ${n} importé.`; screenParent('reglages'); }
      catch (err) { $('#impmsgp').textContent = 'Ce fichier n\'est pas un profil de ' + APPNAME + '.'; }
    };
    const eg = $('#ecode-go'); if (eg) eg.onclick = async () => { const ok = await checkCode($('#ecode').value); if (!ok) { $('#ecode-msg').textContent = 'Code inconnu.'; return; } S.ecole = ok; save(); screenParent('reglages'); };
    const lc = $('#logcopy'); if (lc) lc.onclick = async () => { const txt = (S.log || []).map(l => `${l.ts} · v${l.v} · ${l.ecran} · ${l.m}`).join('\n'); try { await navigator.clipboard.writeText(txt); $('#logmsg').textContent = 'Copié.'; } catch (e) { $('#logmsg').textContent = 'Copie impossible ici.'; } };
    const lx = $('#logclear'); if (lx) lx.onclick = () => { S.log = []; save(); screenParent('reglages'); };
    $('#exp').onclick = () => {
      const data = JSON.stringify({ app: 'corridor-a-la-maison', format: 2, version: VERSION, date: new Date().toISOString(), store: S }, null, 1);
      download(`corridor-suivi-${today()}.json`, data, 'application/json');
      S.lastBackup = new Date().toISOString(); save();
    };
    $('#imp').onchange = async e => {
      const f = e.target.files[0]; if (!f) return;
      try {
        const d = JSON.parse(await f.text());
        if (d.app !== 'corridor-a-la-maison' || !d.store || !(Array.isArray(d.store.profiles) || d.store.progress)) throw new Error('fichier inconnu');
        const b = fromStore(d.store);   /* une sauvegarde de la v0.2 est migrée comme au démarrage */
        Object.keys(S).forEach(k => delete S[k]); Object.assign(S, b); save(); await migrateDB();
        $('#impmsg').textContent = `Sauvegarde du ${String(d.date || '').slice(0, 10)} restaurée : ${S.profiles.length} enfant${S.profiles.length > 1 ? 's' : ''}.`;
      } catch (err) { $('#impmsg').textContent = 'Ce fichier n\'est pas une sauvegarde de ' + APPNAME + '.'; }
    };
    $('#wipe').onclick = () => { if ($('#conf').value.trim().toUpperCase() !== 'EFFACER') return; S.profiles.forEach(p => { p.progress = kid(); }); save(); screenParent('suivi'); };
  }
}
/* Mesure de fluence : le parent écoute, touche les mots mal lus, et au besoin le dernier mot lu. */
function screenMeasure(r) {
  if (!r) return;
  markHeard(r);
  const words = r.passage.join(' ').split(/\s+/);
  const isWord = w => /[\p{L}\p{N}]/u.test(w);
  const err = new Set(); let last = words.length - 1, mode = 'err', secs = r.dur || 60;
  const draw = () => {
    const read = words.slice(0, last + 1).filter(isWord).length, nErr = [...err].filter(k => k <= last).length;
    const wcpm = Math.round((read - nErr) * 60 / Math.max(1, secs));
    app.innerHTML = `<div class="page stack"><div class="row" style="justify-content:space-between"><button class="icon-btn" id="back" aria-label="Retour">${UI.back}</button><h2>Mesurer la lecture</h2></div>
    <div class="card stack"><div class="row"><button class="btn soft" id="play" style="--c:var(--river)">Écouter l'enregistrement</button><label class="f" style="flex-direction:row;align-items:center;gap:8px">Durée (s) <input type="tel" id="secs" value="${secs}" style="width:90px"></label></div>
    <div class="seg"><button data-m="err" class="${mode === 'err' ? 'on' : ''}">Toucher les mots mal lus</button><button data-m="last" class="${mode === 'last' ? 'on' : ''}">Toucher le dernier mot lu</button></div>
    <div class="measure">${words.map((w, k) => isWord(w) ? `<button class="mw ${err.has(k) ? 'err' : ''} ${k > last ? 'out' : ''} ${k === last ? 'last' : ''}" data-w="${k}">${esc(w)}</button>` : `<span class="mw p">${esc(w)}</span>`).join(' ')}</div>
    <p style="margin:0">Mots lus : <b>${read}</b> · erreurs : <b>${nErr}</b> · <b style="font-size:1.3rem">${wcpm} mots par minute</b> <span class="small muted">(repère de fin de CE1 : 70)</span></p>
    <div><button class="btn" id="save" style="--c:var(--river)">Enregistrer la mesure</button></div></div></div>`;
    $('#back').onclick = () => screenParent('suivi');
    $('#play').onclick = () => { stopSpeech(); playFile(URL.createObjectURL(r.blob), false); };
    $('#secs').onchange = e => { secs = Math.max(1, Number(e.target.value) || secs); draw(); };
    app.querySelectorAll('[data-m]').forEach(b => b.onclick = () => { mode = b.dataset.m; draw(); });
    app.querySelectorAll('[data-w]').forEach(b => b.onclick = () => { const k = Number(b.dataset.w); if (mode === 'last') last = k; else if (err.has(k)) err.delete(k); else err.add(k); draw(); });
    $('#save').onclick = () => { (progressOfRec(r) || kid()).measures.push({ type: 'fluence', date: today(), lesson: r.lesson, recId: r.id, read, errors: nErr, secs, wcpm, reread: !!r.reread }); save(); screenParent('suivi'); };
  };
  draw();
}
function screenGrade(r) {
  if (!r) return;
  markHeard(r);
  const chk = new Set();
  const draw = () => {
    app.innerHTML = `<div class="page stack"><div class="row" style="justify-content:space-between"><button class="icon-btn" id="back" aria-label="Retour">${UI.back}</button><h2>Noter le récit</h2></div>
    <div class="card stack"><div><button class="btn soft" id="play" style="--c:var(--river)">Écouter le récit</button></div>
    <p class="small muted" style="margin:0">Cochez ce que l'enfant a dit, même avec ses mots à lui.</p>
    ${RECIT.map((t, k) => `<label class="row" style="gap:10px"><input type="checkbox" data-k="${k}" ${chk.has(k) ? 'checked' : ''} style="width:24px;height:24px"> ${esc(t)}</label>`).join('')}
    <p style="margin:0">Score : <b>${chk.size} sur ${RECIT.length}</b></p><div><button class="btn" id="save" style="--c:var(--river)">Enregistrer la note</button></div></div></div>`;
    $('#back').onclick = () => screenParent('suivi');
    $('#play').onclick = () => { stopSpeech(); playFile(URL.createObjectURL(r.blob), false); };
    app.querySelectorAll('[data-k]').forEach(b => b.onchange = () => { const k = Number(b.dataset.k); if (b.checked) chk.add(k); else chk.delete(k); draw(); });
    $('#save').onclick = () => { (progressOfRec(r) || kid()).measures.push({ type: 'recit', date: today(), lesson: r.lesson, recId: r.id, score: chk.size, items: [...chk] }); save(); screenParent('suivi'); };
  };
  draw();
}

/* ============================ rapport du dimanche ============================ */
/* Format fixe (format 1) : mêmes rubriques, même ordre, chaque semaine. Comparable d'une semaine à l'autre. */
const DAY_MS = 864e5;
function skillStats(p, sinceDays) {
  const since = Date.now() - sinceDays * DAY_MS, pr = p.progress, st = {};
  const add = (code, kind) => { if (!code) return; const s = st[code] || (st[code] = { n: 0, first: 0, after: 0, shown: 0 }); s.n++; s[kind]++; };
  pr.runs.filter(r => r.start >= since).forEach(r => {
    r.items.forEach(it => { if (!it.answers.length) return; add(it.skill || ((LESSONS[r.lesson] || {}).skills || [])[0], it.ok ? (it.first ? 'first' : 'after') : 'shown'); });
    if (r.drill && r.drill.kinds) Object.entries(r.drill.kinds).forEach(([k, v]) => { const code = ((PROG[p.parcours] || {}).drillKinds || {})[k]; for (let i = 0; i < v.n; i++) add(code, i < v.ok ? 'first' : 'shown'); });
  });
  return st;
}
const pc = (a, n) => n ? Math.round(100 * a / n) + ' %' : '—';
function skillTableHTML(p) {
  const st = skillStats(p, 7), codes = Object.keys(st);
  if (!codes.length) return '';
  return `<div><h3 style="font-size:1rem">Compétences, 7 derniers jours</h3><div class="table-wrap"><table class="t"><tr><th>Compétence</th><th>Essais</th><th>1er essai</th><th>Après aide</th><th>Montrée</th></tr>${codes.map(k => `<tr><td>${esc(skillLabel(p.parcours, k))}</td><td>${st[k].n}</td><td>${pc(st[k].first, st[k].n)}</td><td>${pc(st[k].after, st[k].n)}</td><td>${pc(st[k].shown, st[k].n)}</td></tr>`).join('')}</table></div></div>`;
}
/* Maîtrise par compétence, sur 30 jours : part des réponses trouvées, une réponse trouvée après aide comptant moitié.
   Quatre paliers : acquis (80 % et plus), en cours (50 à 79 %), fragile (moins de 50 %), peu travaillé (moins de 3 essais).
   Sert au Suivi, au rapport (rubrique 8) et à la séance de révision, qui vise d'abord les compétences fragiles. */
const MASTERY = { acquis: 'acquis', 'en-cours': 'en cours', fragile: 'fragile', peu: 'peu travaillé' };
function masteryOf(p, days = 30) {
  const st = skillStats(p, days), out = {};
  Object.keys(st).forEach(k => { const s = st[k], score = s.n ? (s.first + 0.5 * s.after) / s.n : 0; out[k] = { n: s.n, score, level: s.n < 3 ? 'peu' : score >= 0.8 ? 'acquis' : score >= 0.5 ? 'en-cours' : 'fragile' }; });
  return out;
}
function masteryTableHTML(p) {
  const m = masteryOf(p), all = ((PROG[p.parcours] || {}).skills || []), seen = all.filter(s => m[s.code]), extra = Object.keys(m).filter(k => !all.some(s => s.code === k));
  const rows = seen.map(s => [s.code, s.label]).concat(extra.map(k => [k, k]));
  if (!rows.length) return '';
  const left = all.length - seen.length;
  return `<div><h3 style="font-size:1rem">Maîtrise par compétence, 30 derniers jours</h3><div class="table-wrap"><table class="t"><tr><th>Compétence</th><th>Palier</th><th>Réussite</th><th>Essais</th></tr>${rows.map(([k, lab]) => `<tr><td>${esc(lab)}</td><td><span class="pill m-${m[k].level}">${MASTERY[m[k].level]}</span></td><td>${Math.round(100 * m[k].score)} %</td><td>${m[k].n}</td></tr>`).join('')}</table></div>${left ? `<p class="small muted" style="margin:4px 0 0">${left} compétence${left > 1 ? 's' : ''} de la progression pas encore travaillée${left > 1 ? 's' : ''}.</p>` : ''}</div>`;
}
let RECS_CACHE = [];
function report() {
  const L = [`${APPNAME.toUpperCase()} · RAPPORT · format 2`, `Date : ${today()} · version ${VERSION}`, ecoleLine()];
  if (!S.profiles.length) L.push('', 'Aucun enfant.');
  S.profiles.forEach(p => {
    const pr = p.progress, since = Date.now() - 7 * DAY_MS, runs = pr.runs.filter(r => r.start >= since), age = ageOf(p.dob);
    L.push('', `== Profil ${p.id} · ${kidLabel(p)} · parcours ${p.parcours} · classe ${p.classe || (parcoursOf(p.parcours) || {}).classe || '?'} · ${age == null ? 'âge inconnu' : age + ' ans'} ==`);
    const mins = runs.reduce((a, r) => a + Math.max(1, Math.round(((r.end || r.start) - r.start) / 60000)), 0);
    L.push(`1. SÉANCES (7 derniers jours) : ${runs.filter(r => r.done).length} terminées · ${runs.filter(r => !r.done).length} arrêtées avant la fin · ${mins} min au total · séances faites depuis le début : ${Object.keys(pr.done).length}`);
    L.push('2. COMPÉTENCES (7 derniers jours) · code | essais | 1er essai | après aide | réponse montrée');
    const st = skillStats(p, 7), codes = Object.keys(st).sort();
    if (!codes.length) L.push('   aucune');
    codes.forEach(k => L.push(`   ${k} | ${st[k].n} | ${pc(st[k].first, st[k].n)} | ${pc(st[k].after, st[k].n)} | ${pc(st[k].shown, st[k].n)}`));
    const recs = Object.entries(pr.records).map(([k, r]) => `${k} ${r.best} (${r.secs} s, ${r.date})`).join(' ; ');
    L.push(`3. AUTOMATISMES : records : ${recs || 'aucun'}`);
    const ms = pr.measures.filter(m => m.type === 'fluence').slice(-4).map(m => `${m.date} ${m.wcpm} mots/min${m.reread ? ' (relecture)' : ''}`).join(' ; ');
    const rc = pr.measures.filter(m => m.type === 'recit').slice(-3).map(m => `${m.date} ${m.score}/${RECIT.length}`).join(' ; ');
    L.push(`4. MESURES : lecture : ${ms || 'aucune'} · récit : ${rc || 'aucun'}`);
    const rr = RECS_CACHE.filter(r => r.profile === p.id), un = rr.filter(r => !r.heard);
    L.push(`5. ENREGISTREMENTS : ${rr.length} au total · ${un.length} pas encore écouté${un.length > 1 ? 's' : ''}${un.length ? ' : ' + un.slice(0, 6).map(r => `${recKind(r)} « ${r.title} » (${new Date(r.ts).toISOString().slice(0, 10)})`).join(' ; ') : ''}`);
    L.push(`6. FILE DE RÉVISION : ${pr.review.map(r => r.id).join(', ') || 'vide'}`);
    L.push('7. DÉTAIL DES SÉANCES (7 derniers jours)');
    if (!runs.length) L.push('   aucune');
    runs.forEach(r => {
      L.push(`   - ${r.date} · ${r.title} · ${Math.max(1, Math.round(((r.end || r.start) - r.start) / 60000))} min · ${r.done ? 'terminée' : 'arrêtée avant la fin'} · enregistrements : ${r.recs || 0}${r.drill ? ` · automatismes ${r.drill.score}/${r.drill.count} en ${r.drill.secs} s${r.drill.record ? ' (record)' : ''}` : ''}`);
      r.items.forEach(it => L.push(`      ${it.ok ? (it.first ? 'OK 1er essai' : 'OK après erreur') : (it.answers.length ? 'MONTRÉE' : 'non fait')} | ${it.skill || '-'} | ${it.q} | réponses : ${it.answers.join(' → ') || '—'} | attendu : ${it.answer}`));
    });
    L.push('8. MAÎTRISE (30 derniers jours) · code | palier | réussite | essais');
    const ma = masteryOf(p), mk = Object.keys(ma).sort();
    if (!mk.length) L.push('   aucune');
    mk.forEach(k => L.push(`   ${k} | ${MASTERY[ma[k].level]} | ${Math.round(100 * ma[k].score)} % | ${ma[k].n}`));
  });
  return L.join('\n');
}

/* Le même rapport, en données : le fichier que la famille dépose à l'école ; tools/tableau_classe.py en fait un tableau par classe.
   Format rapport-2 : les mêmes chiffres que le texte (format 2), et le texte lui-même ; rapport-1 était sans la maîtrise. */
function reportData(txt) {
  const since = Date.now() - 7 * DAY_MS, mins = runs => runs.reduce((a, r) => a + Math.max(1, Math.round(((r.end || r.start) - r.start) / 60000)), 0);
  return { app: 'corridor-a-la-maison', format: 'rapport-2', version: VERSION, date: today(), ecole: ECOLE.ecole || '', inscription: S.ecole && S.ecole.id ? { id: S.ecole.id, classe: S.ecole.classe || '' } : null, acces: ecoleLine(), texte: txt || report(),
    profils: S.profiles.map(p => {
      const pr = p.progress, runs = pr.runs.filter(r => r.start >= since), st = skillStats(p, 7), rr = RECS_CACHE.filter(r => r.profile === p.id), rs = resumeOf(p);
      return { id: p.id, prenom: kidLabel(p), parcours: p.parcours, classe: p.classe || (parcoursOf(p.parcours) || {}).classe || '', age: ageOf(p.dob),
        seances: { terminees: runs.filter(r => r.done).length, arretees: runs.filter(r => !r.done).length, minutes: mins(runs), total: Object.keys(pr.done).length, derniere: pr.runs.length ? pr.runs[pr.runs.length - 1].date : null },
        competences: Object.fromEntries(Object.keys(st).sort().map(k => [k, { libelle: skillLabel(p.parcours, k), essais: st[k].n, premier: st[k].first, apres: st[k].after, montree: st[k].shown }])),
        maitrise: Object.fromEntries(Object.entries(masteryOf(p)).map(([k, v]) => [k, { palier: v.level, reussite: Math.round(100 * v.score), essais: v.n }])),
        records: pr.records, mesures: pr.measures.slice(-8), enregistrements: { total: rr.length, nonEcoutes: rr.filter(r => !r.heard).length },
        revision: pr.review.map(r => r.id), reprise: rs ? { seance: rs.lesson, etape: rs.i + 1, sur: rs.steps.length } : null };
    }) };
}

/* ============================ démarrage ============================ */
/* Après une mise à jour depuis la v0.2 : les enregistrements et les phrases de Maman passent sous l'identifiant du profil. */
async function migrateDB() {
  if (!S.migrate) return;
  const byLeg = {}; S.profiles.forEach(p => { if (p.legacy) byLeg[p.legacy] = p.id; });
  const recs = (await DB.recs()) || [];
  for (const r of recs) if (r.child && !r.profile && byLeg[r.child]) { r.profile = byLeg[r.child]; delete r.child; await DB.putRec(r); }
  const keys = (await DB.clipKeys()) || [];
  for (const k of keys) { const m = /^(bonjour|fin)_(bleu|orange)$/.exec(String(k)); if (m && byLeg[m[2]]) { const b = await DB.getClip(k); if (b) await DB.putClip(`${m[1]}@${byLeg[m[2]]}`, b); await DB.delClip(k); } }
  delete S.migrate; save();
}
async function boot() {
  try { await loadAll(); } catch (e) {
    app.innerHTML = /^schema/.test(String(e && e.message)) ? `<div class="page card"><h2>Leçons dans un format inconnu</h2><p>Les leçons publiées demandent une application plus récente. Ouvrez l'application avec internet pour la mettre à jour.</p></div>`
      : `<div class="page card"><h2>Leçons introuvables</h2><p>Connectez la tablette à internet une fois pour télécharger les leçons, puis rouvrez l'application.</p></div>`;
    return;
  }
  S.profiles.forEach(p => { if (!p.classe) { const pr = parcoursOf(p.parcours); if (pr) p.classe = pr.classe; } });
  await migrateDB();
  /* Demande au navigateur de ne jamais effacer les données du site de lui-même (suivi, voix de Maman). */
  try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {}); } catch (e) {}
  RECS_CACHE = (await DB.recs()) || [];
  applySettings();
  const home = () => { if (!S.setup) screenSetup(); else if (!S.profiles.length) screenProfile(null); else screenHome(); };
  if (accessRequired()) {
    if (!S.ecole) {
      if (S.profiles.length) { S.ecole = { grandfathered: true, date: today() }; save(); }   /* installée avant le contrôle : l'école régularise avec un code */
      else return screenEcole(home);
    } else if (S.ecole.h && !codeStillValid(S.ecole.h)) return screenEcole(home, 'Votre inscription a été retirée par l\'école. Tapez un nouveau code pour continuer.');
  }
  home();
}
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) { try { navigator.serviceWorker.register('sw.js').catch(() => {}); } catch (e) {} }
document.addEventListener('visibilitychange', () => { if (document.hidden) stopSpeech(); });
window.__kono = { keyOf, sentences, S, P: () => P, AUDIO: () => AUDIO, report, reportData, makeRevision, LESSONS: () => LESSONS, profileOf, startLesson, logError, normCode, ECOLE: () => ECOLE, domainIcon,
  unit: { normCode, keyOf, sentences, fill, ageOf, opts3, genItem, verdict, isRight, masteryOf, skillStats, journey, fromStore, fromV02, newId, recapOf, kid, blank, retrievalPool, applySettings, calm, PH: () => PH, PROG: () => PROG } };   /* pour les tests */
boot();
})();
