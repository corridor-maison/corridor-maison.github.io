# Passage de relais — 11 octobre 2026

De : la session application (Claude Code cloud, session `01D5iNfBwuakkotoUw54CW8a`). À : l'agent local qui porte la v0.3.1.
Décision du fondateur : la session cloud s'arrête, l'agent local prend la main. Ce fichier dit où en est le dépôt, ce qui est fixé, ce qui est décidé pour la suite, et ce qui a été appris en route. `CLAUDE.md` reste la référence courte ; `CONTRAT_LECONS.md` prime pour les leçons.

## 1. Où en est le dépôt

| Élément | Valeur |
|---|---|
| Dépôt | `corridor-maison/corridor-maison.github.io` (organisation renommée depuis `Corridor-a-la-Maison`, ancien chemin redirigé) |
| `main` | `9a9188e` — v0.3.0 publiée, `CLAUDE.md` en place |
| Site publié | https://corridor-maison.github.io/ — déployé par `.github/workflows/pages.yml` à chaque push sur `main` (contrôle des leçons, puis publication de `app/`) |
| Version servie | `app.js` : `VERSION = '0.3.0'` ; `sw.js` : `CACHE = 'kono-0.3.0'` ; index `S0-2026-10-11` |
| Pull requests | aucune ouverte. #1 à #5 fusionnées par la session cloud ; #6 (zip v0.3.1, lignée sans profils) fermée par l'agent local |
| Branches | `main` ; `claude/busy-meitner-y45bhh` (session cloud, identique à `main`, peut être supprimée) ; `v0.3.1` au commit `12b4e2f` (archive du zip, à supprimer après fusion des PR v0.3.1) |

Historique de `main`, du plus récent au plus ancien :

| Commit | Contenu |
|---|---|
| `9a9188e` | `CLAUDE.md` : repères pour tout agent |
| `6c843e4` | v0.3.0 : profils locaux par enfant, parcours `gs` et `ce1`, index au schéma 2, migration des données v0.2, rapport par profil, `tools/check_lessons.py`, contrôle des leçons dans le workflow |
| `511314d` | `CONTRAT_LECONS.md` v1 |
| `d6c987e` | Hors ligne : le service worker garde toutes les leçons de l'index dès l'installation |
| `af268a5` | Renommage visible « Corridor à la maison » |
| `3ee4167` | v0.2 livrée par le fondateur (quatre temps, lecture, histoire, carte du voyage, voix) |

## 2. Ce qui est fixé (détail dans `CLAUDE.md`)

- Site statique sans serveur ; seul `app/` est publié ; aucune donnée d'enfant ne quitte la tablette.
- État sous `localStorage['kono-v1']`, `{ schema: 2, setup, pin, voice, profiles }` ; un profil `{ id, name, girl, dob, classe, parcours, couleur, created, progress }`, `id` immuable. Base IndexedDB `kono`, magasins `clips` (phrases de Maman, clé `<phrase>` ou `<phrase>@<profil>`) et `recs` (champ `profile`). Ne jamais renommer la clé ni la base.
- Routage par `parcours` (`app/parcours.json`), index `schema: 2`, escales par parcours, `version` au format `S<n>-AAAA-MM-JJ`. L'application lit encore un index v0.2 le temps d'une mise à jour ; tout autre schéma est refusé avec un message.
- Toute version change `VERSION` dans `app.js` et `CACHE` dans `sw.js`, même numéro. Prochaine : `0.3.1`.
- Listes fermées (étapes, `kinds`, dessins) dans README § 4 et `tools/check_lessons.py`. Un besoin nouveau passe d'abord par l'application et le contrôle.

## 3. Mandat v0.3.1 : les décisions prises par la session application

Réponses aux sept questions posées par l'agent local le 11 octobre.

1. **Identifiants S1** : ceux du contrat : `ce1-s1-echange`, `ce1-s1-centaine`, `ce1-s1-marche`, `gs-s1-cache`, `gs-s1-collection`, `gs-s1-syllabes`. Aucune couleur dans les identifiants d'étapes ni de phrases.
2. **Bloc `programmes`** : supprimé. `app/parcours.json` est la seule source des classes et couleurs. Les progressions vivent dans `app/progression/<id de parcours>.json`, par convention de nom. Le champ `programme` des leçons reste le texte libre du programme officiel.
3. **Escales** : le plan du zip (Bamako 4, Ségou 32, Djenné et Mopti 36, Tombouctou 40) remplace les 28 uniformes, par parcours. **`Gao : 0` est un bug** : dans `journey()`, une escale à 0 séance est tamponnée d'office. Mettre 28 pour Gao en attendant le vrai chiffre, et faire refuser par `check_lessons.py` toute escale sous 1 séance.
4. **Leçons S0** : elles restent en semaine `S0`, `order` 0, identifiants inchangés ; les enfants les ont déjà faites. Champs `skills` et `day` acceptés comme optionnels. Pour S1 seulement, trois leçons nouvelles par parcours sont admises, S0 ayant servi de lundi ; l'exception s'écrit dans la PR. Dès S2 : quatre par semaine.
5. **Registre des voix** : celui du zip est accepté avec preuve dans la PR : les 264 premières entrées de `voix/registre.json` identiques à `main`, aucun numéro réutilisé. Le fondateur relance ensuite `tools/build_audio.py`, qui doit ne rien changer.
6. **Branches** : noms sans barre oblique, `v0.3.1-moteur` puis `s1-semaine-1`. `origin/v0.3.1` reste intacte jusqu'à la fusion des deux PR, puis se supprime.
7. **Deux pull requests, dans l'ordre** :
   - **A — « v0.3.1 : moteur »**. Portage fonction par fonction sur l'`app.js` de `main` : étape `manip` (tenframe, jumps, blocks), six dessins (bar, blocks, hidden, icon, items, syllables), 16 images `app/img/*.svg`, chargement des progressions, rapport avec taux de réussite par compétence sous l'en-tête de profil du contrat, histoire à remettre dans l'ordre, lecture répétée, séance de révision quand aucune semaine n'est arrivée (par profil et par parcours). `VERSION` et `CACHE` à `0.3.1`. `sw.js` : logique d'installation de `main` conservée, `img/*` et `progression/*` ajoutés au préchargement. `check_lessons.py` étendu : étape `manip`, six dessins, escales à 1 séance au moins, chaque image citée existe et est préchargée, chaque code `skills` existe dans la progression du parcours. `tests/e2e.py` et `tests/offline.py` adaptés au parcours réglage parent puis profil. README § 4, `CONTRAT_LECONS.md` en version 1.1 avec journal des changements en tête, `CLAUDE.md` section « État ». Les deux leçons S0 seules dans l'index. Déployable seule.
   - **B — « S1 : semaine 1 (gs, ce1) »**. Contenu seulement : les six leçons, l'index `S1-AAAA-MM-JJ`, le registre des voix avec sa preuve, `Fiches_S1.pdf`. Rien dans `app/*.js`. S'ouvre après la fusion de A.
   - Pas de `docs/FORMAT.md` : une seule vérité, README § 4 et le contrat.

**Ce que le portage doit garder de `main`** : profils, `clipKey` et phrases par enfant, `kono-v1`, base `kono`, `THEMES`, `migrateDB`, lecture d'un index v0.2, `parcoursOf` et `escalesOf`, en-tête de rapport par profil.

## 4. Comment la session application testait (à reproduire dans `tests/`)

Navigateur Chromium sans écran piloté par le protocole DevTools, serveur HTTPS local avec certificat de test (le service worker ne s'enregistre qu'en HTTPS), un profil navigateur neuf par scénario.

- **Première installation** : écran réglage parent (code + voix, sans case enfant) → profil (prénom, date de naissance `2019-04-10` → classe CE1 proposée et présélectionnée) → accueil avec un enfant et le bouton « Ajouter ». Deuxième profil via le code parent, `2021-02-01` → Grande section, couleur choisie respectée.
- **Routage et isolation** : chaque enfant ne voit que les leçons de son parcours ; une séance démarrée puis arrêtée compte pour lui seul (`profiles[i].progress.runs`).
- **Espace parent** : rapport avec l'en-tête `== Profil <id> · <prénom> · parcours <id> · classe <classe> · <âge> ans ==` ; phrases de Maman `bonjour@<id>` et `fin@<id>` par enfant ; mesure de lecture enregistrée sur le bon profil.
- **Migration v0.2** : état `kono-v1` v0.2 injecté (prénom Bleu, une séance faite, une révision), plus un enregistrement `child: 'bleu'` et une phrase `bonjour_bleu` en IndexedDB → un seul profil créé, suivi conservé, enregistrement et phrase rattachés au profil, état v2 enregistré.
- **Hors ligne** : une seule ouverture avec réseau, puis réseau coupé → l'application s'ouvre, cache `kono-0.3.0` avec `parcours.json` et toutes les leçons.
- **Contrôle des leçons** : dépôt accepté, treize mutations refusées (clé `child`, parcours inconnu, `order` en double, fichier manquant ou hors index, couleur comme identité, schéma 1, version hors format, fiche sans niveau « seul », type d'étape ou `kind` inconnu, escale inconnue, identifiant invalide).
- **Après fusion** : les onze vérifications sur le site publié : code 200 pour `/`, `/app.js`, `/sw.js`, `/phrases.json`, `/audio/manifest.json`, `/lessons/index.json`, `/lessons/bleu-s0-dizaine.json`, `/lessons/orange-s0-amis10.json`, chaque fichier identique au commit ; `app.js` contient la `VERSION` attendue ; l'index contient la `version` attendue ; `sw.js` contient le nom de cache attendu. Puis le test hors ligne après une seule ouverture sur le site publié.

## 5. Ouvert, hors du mandat v0.3.1

- **Table des classes de l'école** : demandée à la promotrice par le fondateur (classes, âges au 1er octobre, programme suivi, manuels ; sections multiples ; nombre d'enfants par classe et de tablettes ; qui confirme la classe). À l'arrivée : compléter `app/parcours.json`, rien d'autre à coder.
- **Export d'un profil vers une autre tablette** (fichier ou QR code) : non commencé.
- **PDF des fiches** : `tools/build_print.py S0` génère le HTML avec les libellés des parcours ; la conversion PDF demande Playwright.
- **Voix de Kono et micro sur tablette réelle** : jamais testés en machine.
- **README** : encore « Ouvrir l'application une première fois avec internet » et quelques formulations v0.2 dans la section 3.

## 6. Pièges rencontrés, pour ne pas les repayer

- **Pages** : une organisation GitHub a trois noms ; seul l'identifiant (celui de l'adresse) fabrique `https://<id>.github.io/`. Le renommage de l'organisation ne republie pas le site : relancer le workflow (`workflow_dispatch`).
- **Service worker** : à la toute première ouverture, la page n'est pas contrôlée ; tout ce que l'application demande elle-même avant le `claim` n'est pas en cache. D'où le préchargement des leçons à l'installation (`d6c987e`), que le zip v0.3.1 a reproduit indépendamment.
- **Données** : le suivi, les enregistrements et la voix de Maman sont liés à l'adresse du site. Changer d'adresse après installation sur une tablette, c'est repartir de zéro.
- **Actions** : un compte GitHub verrouillé pour facturation refuse tout job, même sur un dépôt public, avec le message « The job was not started because your account is locked due to a billing issue ».
- **Dans le zip v0.3.1** : index de lignée `child` avec bloc `programmes`, S0 déplacées au lundi de S1, `Gao : 0`. Tout cela est tranché en § 3.
