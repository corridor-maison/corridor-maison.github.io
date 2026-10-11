# Corridor à la maison — repères pour tout agent

Ce fichier est lu par chaque agent qui travaille dans ce dépôt. Il dit ce qui est déjà fait, ce qui est fixé, et comment livrer sans marcher sur le travail d'un autre. `CONTRAT_LECONS.md` prime sur ce fichier pour tout ce qui touche aux leçons.

## Avant toute chose

1. `git fetch origin` puis `git checkout -b <type>/<sujet> origin/main`. **`main` est la seule vérité, et le site publié est `main`.** Jamais de push direct sur `main`, jamais de force push.
2. Lire la section « État » ci-dessous et vérifier qu'elle correspond au dépôt : `git log --oneline -5 origin/main`, `const VERSION` dans `app/app.js`, `const CACHE` dans `app/sw.js`.
3. Regarder les pull requests ouvertes et les branches. **Un fichier touché par deux chantiers ouverts : on s'arrête et on le signale au fondateur.**

## État au 11 octobre 2026 : v0.3.0, commit `6c843e4`

- **Publié** sur https://corridor-maison.github.io/ par `.github/workflows/pages.yml` à chaque push sur `main` : contrôle des leçons, puis publication du dossier `app/` tel quel. Dépôt `corridor-maison/corridor-maison.github.io`.
- **Fait** : renommage « Corridor à la maison » ; hors ligne dès la première ouverture ; profils locaux par enfant ; routage par parcours (`gs`, `ce1`) ; index au schéma 2 ; migration automatique des données v0.2 ; rapport du dimanche par profil ; `tools/check_lessons.py` ; `tools/build_print.py` lit les parcours.
- **Ouvert** : la table des classes de l'école pour compléter `app/parcours.json` ; l'export d'un profil vers une autre tablette ; les semaines S1 et suivantes (Cowork, selon le contrat) ; le PDF des fiches à régénérer (`python3 tools/build_print.py S0`, Playwright requis) ; la voix de Kono sur tablette réelle, jamais testée en machine.
- **Prochaine version** : `0.3.1`, puis `0.4.0` pour un changement de format de données.

## Architecture : ce qui est fixé, à ne pas réinventer

- **Site statique, sans serveur, sans dépendance, sans bundler.** HTML, CSS et JS tels quels, pour tourner hors ligne sur une tablette Android. Seul `app/` est publié. Aucune donnée d'enfant ne quitte la tablette.
- **État** : `localStorage`, clé `kono-v1`, forme `{ schema: 2, setup, pin, voice, profiles: [...] }`. Un profil : `{ id, name, girl, dob, classe, parcours, couleur, created, progress }`. **`id` est immuable** (4 caractères, base 32), il nomme les enregistrements et les phrases de Maman. La migration depuis la v0.2 vit dans `loadStore()` et marque les profils migrés par `legacy`. **Ne jamais renommer la clé `kono-v1` ni la base IndexedDB `kono`** (magasins `clips` et `recs`) : ce serait perdre le suivi des enfants.
- **Enregistrements** (`recs`) : champ `profile` = id du profil. **Phrases de Maman** (`clips`) : clé `<phrase>` pour les phrases communes, `<phrase>@<profil>` pour celles marquées `perChild` dans `app/phrases.json` (`bonjour`, `fin`).
- **Routage** : `lesson.parcours` est un `id` de `app/parcours.json`. L'index est au `schema: 2`, avec `escales` par parcours et `version` au format `S<n>-AAAA-MM-JJ`. L'application lit encore un index v0.2 le temps d'une mise à jour et refuse tout autre schéma. **L'âge propose la classe, le parent la confirme : la classe tranche.**
- **Thèmes** : `THEMES = bleu, orange, vert, violet` dans `app.js`, variables et sélecteurs `body[data-child="<couleur>"]` dans `styles.css`. La couleur est une préférence du profil, jamais une identité, jamais un critère de routage.
- **Service worker** (`app/sw.js`) : cache `kono-<VERSION>` ; les fichiers de base, `parcours.json`, l'index et **toutes les leçons de l'index** sont préchargés à l'installation. **Toute nouvelle version change `VERSION` dans `app.js` et `CACHE` dans `sw.js`, avec le même numéro.** Le service worker ne s'enregistre qu'en HTTPS.
- **Liste fermée** : types d'étapes, sortes d'automatismes (`kinds`) et dessins (`show`) sont ceux du README § 4 et de `tools/check_lessons.py`. Un besoin nouveau se traite d'abord dans l'application et dans le script de contrôle, ensuite dans les leçons.
- **Identifiants** : un identifiant de profil, de leçon, de parcours, d'escale ou de phrase (`voix/registre.json`) ne se renomme jamais et ne se renumérote jamais.

## Qui écrit quoi (CONTRAT_LECONS.md § 10)

| Fichiers | Qui écrit |
|---|---|
| `app/parcours.json` | L'école, via le fondateur ; la session application l'édite sur sa demande |
| `app/lessons/index.json`, `app/lessons/*.json` | Cowork, selon le contrat, et `tools/check_lessons.py` doit rendre 0 |
| `voix/registre.json`, `app/audio/` | `tools/build_audio.py`, lancé par le fondateur seulement |
| `app/*.js`, `app/*.html`, `app/*.css`, `tools/`, workflow, README, contrat, ce fichier | La session application, sur mandat du fondateur |

## Avant de pousser

- `node --check app/app.js && node --check app/sw.js` ; `python3 tools/check_lessons.py` doit rendre `0`.
- Test dans un vrai navigateur, sur HTTPS ou localhost : première installation (réglage parent, puis profil) ; deux profils, chacun ne voyant que son parcours ; une séance arrêtée comptée pour le bon profil ; **hors ligne après une seule ouverture** ; migration d'un état v0.2 si le code du stockage a bougé.
- Une pull request vers `main`, titre préfixé par la version (« v0.3.1 : … »), avec les tests faits et leurs résultats réels. Le workflow doit être vert. **Après la fusion, vérifier le site publié** : fichiers identiques au commit, `VERSION` et cache servis, hors ligne après une ouverture.
- Mettre à jour la section « État » de ce fichier dans la pull request qui change l'état.
