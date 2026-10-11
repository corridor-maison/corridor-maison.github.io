# Corridor à la maison — repères pour tout agent

Ce fichier est lu par chaque agent qui travaille dans ce dépôt. Il dit ce qui est déjà fait, ce qui est fixé, et comment livrer sans marcher sur le travail d'un autre. `CONTRAT_LECONS.md` prime sur ce fichier pour tout ce qui touche aux leçons.

## Avant toute chose

1. `git fetch origin` puis `git checkout -b <type>/<sujet> origin/main`. **`main` est la seule vérité, et le site publié est `main`.** Jamais de push direct sur `main`, jamais de force push.
2. Lire la section « État » ci-dessous et vérifier qu'elle correspond au dépôt : `git log --oneline -5 origin/main`, `const VERSION` dans `app/app.js`, `const CACHE` dans `app/sw.js`.
3. Regarder les pull requests ouvertes et les branches. **Un fichier touché par deux chantiers ouverts : on s'arrête et on le signale au fondateur.**

## État au 12 octobre 2026 : v0.3.1 (PR « v0.3.1 : semaine S1, manipulations, profils »)

- **Publié** sur https://corridor-maison.github.io/ par `.github/workflows/pages.yml` à chaque push sur `main` : contrôle des leçons, puis publication du dossier `app/` tel quel. Dépôt `corridor-maison/corridor-maison.github.io`.
- **Fait** : renommage « Corridor à la maison » ; hors ligne dès la première ouverture ; profils locaux par enfant ; routage par parcours (`gs`, `ce1`) ; index au schéma 2 ; migration automatique des données v0.2 ; rapport du dimanche par profil (format 1, 7 rubriques) ; `tools/check_lessons.py` ; manipulations (boîte de dix, dizaines et unités avec fermeture animée, sauts sur la ligne des nombres), six dessins de plus, 16 images SVG, histoire avec images à remettre dans l'ordre, lecture répétée, séance de révision composée seule, progressions `app/progression/` et compétences dans le rapport ; semaine S1 complète (4 séances par parcours, les deux S0 en sont les lundis) ; tests `tests/e2e.py`, `tests/offline.py`, `tests/migration.py`.
- **Ouvert** : la table des classes de l'école pour compléter `app/parcours.json` ; l'export d'un profil vers une autre tablette ; les semaines S2 et suivantes (Cowork, selon le contrat) ; les voix à enregistrer ou générer (`print/voix_a_enregistrer.md`, 1 144 phrases, dont les numéros 1145 à 1152 nés de la mise au contrat des phrases « ta fiche ») ; la voix de Kono sur tablette réelle, jamais testée en machine ; la boîte de dix « en ajout » n'est utilisée par aucune séance publiée.
- **Prochaine version** : `0.3.2`, puis `0.4.0` pour un changement de format de données.

## Architecture : ce qui est fixé, à ne pas réinventer

- **Site statique, sans serveur, sans dépendance, sans bundler.** HTML, CSS et JS tels quels, pour tourner hors ligne sur une tablette Android. Seul `app/` est publié. Aucune donnée d'enfant ne quitte la tablette.
- **État** : `localStorage`, clé `kono-v1`, forme `{ schema: 2, setup, pin, voice, settings, profiles: [...] }`. Un profil : `{ id, name, girl, dob, classe, parcours, couleur, created, progress }`. **`id` est immuable** (4 caractères, base 32), il nomme les enregistrements et les phrases de Maman. La migration depuis la v0.2 vit dans `fromV02()` (appelée par `loadStore()` et par la restauration d'une sauvegarde) et marque les profils migrés par `legacy` ; `migrateDB()` rattache ensuite les enregistrements et les phrases de Maman aux profils. **Ne jamais renommer la clé `kono-v1` ni la base IndexedDB `kono`** (magasins `clips` et `recs`) : ce serait perdre le suivi des enfants.
- **Enregistrements** (`recs`) : champ `profile` = id du profil, `heard` = écouté par un parent. **Phrases de Maman** (`clips`) : clé `<phrase>` pour les phrases communes, `<phrase>@<profil>` pour celles marquées `perChild` dans `app/phrases.json` (`bonjour`, `fin`).
- **Routage** : `lesson.parcours` est un `id` de `app/parcours.json`. L'index est au `schema: 2`, avec `escales` par parcours et `version` au format `S<n>-AAAA-MM-JJ`. L'application lit encore un index v0.2 le temps d'une mise à jour et refuse tout autre schéma. **L'âge propose la classe, le parent la confirme : la classe tranche.**
- **Thèmes** : `THEMES = bleu, orange, vert, violet` dans `app.js`, variables et sélecteurs `body[data-child="<couleur>"]` dans `styles.css`. La couleur est une préférence du profil, jamais une identité, jamais un critère de routage. La fiche est nommée par l'application d'après la couleur du parcours (`ficheOf`), jamais dans le texte d'une leçon.
- **Service worker** (`app/sw.js`) : cache `kono-<VERSION>` ; les fichiers de base, `parcours.json`, l'index, les progressions, les images et **toutes les leçons de l'index** sont préchargés à l'installation. **Toute nouvelle version change `VERSION` dans `app.js` et `CACHE` dans `sw.js`, avec le même numéro.** Le service worker s'enregistre en HTTPS et sur localhost.
- **Liste fermée** : types d'étapes, sortes d'automatismes (`kinds`), dessins (`show`) et champs sont ceux du README § 4 cité par le contrat et de son annexe A, vérifiés par `tools/check_lessons.py`. Un besoin nouveau se traite d'abord dans l'application et dans le script de contrôle, ensuite dans l'annexe, enfin dans les leçons. Il n'y a pas de `docs/FORMAT.md` : le contrat est le seul document de format.
- **Identifiants** : un identifiant de profil, de leçon, de parcours, d'escale ou de phrase (`voix/registre.json`) ne se renomme jamais et ne se renumérote jamais. Les leçons nouvelles s'appellent `<parcours>-s<n>-<mot>` ; `bleu-s0-dizaine` et `orange-s0-amis10` gardent leur nom.
- **Carte du voyage** : la pinasse avance d'une séance terminée à l'autre (révisions comprises) sur les escales du parcours ; Ségou après 4 séances (voulu : le texte de lecture y arrive).

## Qui écrit quoi (CONTRAT_LECONS.md § 10)

| Fichiers | Qui écrit |
|---|---|
| `app/parcours.json` | L'école, via le fondateur ; la session application l'édite sur sa demande |
| `app/lessons/index.json`, `app/lessons/*.json` | Cowork, selon le contrat, et `tools/check_lessons.py` doit rendre 0 |
| `voix/registre.json`, `print/voix_a_enregistrer.md`, `app/audio/` | `tools/build_audio.py`, lancé par le fondateur seulement |
| `app/*.js`, `app/*.html`, `app/*.css`, `app/img/`, `app/progression/`, `tools/`, `tests/`, workflow, README, contrat, ce fichier | La session application, sur mandat du fondateur |

## Avant de pousser

- `node --check app/app.js && node --check app/sw.js` ; `python3 tools/check_lessons.py` doit rendre `0`.
- `python3 -m http.server 8765 --directory app` puis `python3 tests/e2e.py 1280x800` (deux profils jouent tout, couverture des manipulations, aucune erreur JavaScript) ; `python3 tests/offline.py` (coupure réelle) ; `python3 tests/migration.py` (état v0.2 → deux profils sans perte). Sous Windows : `python -X utf8`.
- Test dans un vrai navigateur, sur HTTPS ou localhost : première installation (réglage parent, puis profil) ; deux profils, chacun ne voyant que son parcours ; une séance arrêtée comptée pour le bon profil ; **hors ligne après une seule ouverture** ; migration d'un état v0.2 si le code du stockage a bougé.
- Une pull request vers `main`, titre préfixé par la version (« v0.3.2 : … »), avec les tests faits et leurs résultats réels. Le workflow doit être vert. **Après la fusion, vérifier le site publié** : fichiers identiques au commit, `VERSION` et cache servis, hors ligne après une ouverture.
- Mettre à jour la section « État » de ce fichier dans la pull request qui change l'état.
