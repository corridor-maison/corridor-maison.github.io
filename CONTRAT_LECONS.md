# Contrat des leçons — Corridor à la maison

**Version 1 · 11 octobre 2026 · décision du fondateur : profils locaux, sans serveur.**

**Version 1.3 · 15 octobre 2026 · § 5 : le rapport existe aussi en fichier `rapport-1` ; § 7 : relecture d'une semaine avec `tools/build_review.py` avant publication. Le format des leçons est inchangé.**

**Version 1.2 · 15 octobre 2026 · § 10 : `app/ecole.json` (codes d'inscription délivrés par l'école), même propriétaire que `parcours.json`.**

**Version 1.1 · 12 octobre 2026 · annexe A : le catalogue de la v0.3.1 (manipulations, histoire, erreurs objets, dessins), à la demande du fondateur. Le reste est inchangé.**

Ce contrat lie deux parties : l'application (dossier `app/`, dépôt `corridor-maison/corridor-maison.github.io`) et le générateur de leçons (Cowork, ou tout autre modèle). Il s'applique à toute leçon produite à partir de maintenant. Les deux leçons S0 existantes seront mises à ce format par la livraison « profils » de l'application, pas par Cowork.

## 1. Principes

1. **Une seule source.** Chaque leçon est un fichier `app/lessons/<id>.json`. La tablette et les fiches papier en dérivent. Rien n'est écrit deux fois.
2. **L'application route par `parcours`.** Jamais par âge, par couleur ni par prénom. Le parcours d'un enfant est choisi à la création de son profil, à partir de sa classe.
3. **Tout identifiant est immuable.** Identifiant de leçon, identifiant de parcours, numéro de phrase dans `voix/registre.json` : on ajoute, on ne renomme jamais, on ne renumérote jamais.
4. **Aucune donnée d'enfant dans le dépôt.** Pas de prénom, pas d'âge, pas de suivi. Tout cela reste dans la tablette.
5. **Liste fermée.** Une leçon n'utilise que ce que l'application sait exécuter : les types d'étapes, les sortes d'automatismes (`kinds`) et les dessins (`show`) du README § 4, complétés par l'annexe A. Un besoin nouveau se traite d'abord dans l'application, ensuite dans la leçon. Jamais l'inverse.

## 2. Les parcours : `app/parcours.json`

Ce fichier appartient à l'école, via le fondateur. Cowork le lit, ne le modifie jamais, et n'invente aucun parcours.

```json
{
  "schema": 1,
  "parcours": [
    { "id": "gs",  "label": "Grande section", "classe": "GS",  "age_min": 5, "age_max": 6, "couleur": "orange" },
    { "id": "ce1", "label": "CE1",            "classe": "CE1", "age_min": 7, "age_max": 8, "couleur": "bleu" }
  ]
}
```

- `id` : minuscules ASCII, chiffres et tirets, immuable. C'est la clé que portent les leçons.
- `age_min`, `age_max` : une proposition. L'application calcule l'âge depuis la date de naissance, propose la classe, et le parent ou l'enseignant confirme. La classe tranche, pas l'âge.
- `couleur` : le thème par défaut du profil. Une préférence, plus une identité.
- La liste des classes de l'école sera fournie par la promotrice. Les deux parcours ci-dessus sont ceux des leçons S0.

## 3. L'index : `app/lessons/index.json`

```json
{
  "schema": 2,
  "version": "S1-2026-10-18",
  "escales": {
    "gs":  [ { "n": 1, "name": "Bamako", "sessions": 28 }, { "n": 2, "name": "Ségou", "sessions": 28 } ],
    "ce1": [ { "n": 1, "name": "Bamako", "sessions": 28 }, { "n": 2, "name": "Ségou", "sessions": 28 } ]
  },
  "lessons": [
    { "id": "ce1-s1-dizaine-2", "parcours": "ce1", "order": 1, "week": "S1", "title": "Passer par la dizaine, suite", "escale": 1 }
  ]
}
```

- `schema` : `2` pour ce contrat. L'application refuse un index d'un autre schéma, avec un message clair, plutôt que de se tromper en silence.
- `version` : une chaîne unique par publication, au format `S<n>-AAAA-MM-JJ`. L'application l'affiche dans l'espace parent.
- `escales` : la carte du voyage, par parcours. Les numéros `n` ne changent jamais.
- `lessons` : une entrée par leçon, dans l'ordre de lecture. Les champs `id`, `parcours`, `order`, `week`, `title`, `escale` sont obligatoires. La clé `child` disparaît.

## 4. La leçon : `app/lessons/<id>.json`

Clés obligatoires à la racine : `id`, `parcours`, `order`, `week`, `title`, `domain`, `programme`, `objective`, `escale`, `steps`, `paper`.

- `id` : `<parcours>-s<n>-<mot>`, par exemple `ce1-s1-dizaine-2`. ASCII minuscule, au plus 32 caractères, unique pour toujours. Le fichier porte le même nom.
- `parcours` : un `id` de `parcours.json`. Remplace `child`, qui est interdit.
- `order` : entier, unique dans un parcours, croissant avec les semaines. L'application joue la première leçon non terminée dans cet ordre.
- `week` : `S<n>`. Quatre leçons par semaine et par parcours, du lundi au jeudi.
- `programme` : la référence au programme officiel, en texte libre, comme aujourd'hui. Ce n'est pas la clé de routage.
- `escale` : un `n` présent dans `escales[parcours]`.
- `steps` et `paper` : le format du README § 4, inchangé. Chaque fiche a au moins un niveau `who: "seul"`. Chaque exercice porte `answer` et `errors`, les clés de `errors` étant la réponse fausse exactement telle que l'enfant la tape.
- Texte : les jetons `{prenom}` et `{e}` sont permis. Aucune couleur comme identité (« ta fiche bleue ») : c'est l'application qui nomme la fiche. Aucun prénom en dur.
- Voix : toute phrase nouvelle reçoit son numéro par `tools/build_audio.py`, dans `voix/registre.json`. Les numéros existants ne bougent jamais.

## 5. Le rapport du dimanche

C'est l'entrée de Cowork. Avec la livraison « profils », il sera émis par profil et commencera ainsi :

```
== Profil k7f2 · Awa · parcours ce1 · classe CE1 · 7 ans ==
```

Suivent, inchangés : les séances, les réponses item par item, les mesures, les automatismes par sorte, la file de révision. Cowork génère la semaine suivante à partir du `parcours` et de ces lignes, jamais à partir du prénom. Jusqu'à cette livraison, `BLEU` vaut `ce1` et `ORANGE` vaut `gs`.

Depuis la v0.3.4, le même rapport s'enregistre aussi en fichier (`rapport-1`, JSON : mêmes chiffres, et le texte lui-même) que la famille dépose à l'école ; `tools/tableau_classe.py` en fait un tableau par classe pour l'enseignante. Cowork continue de lire le texte.

## 6. Une publication, c'est tout ou rien

Une publication contient, pour chaque parcours actif, les quatre leçons de la semaine et l'index mis à jour. Jamais une semaine partielle : un lundi sans leçon est une panne pour l'enfant. Tant qu'une semaine n'est pas complète, elle reste sur une branche.

## 7. Acceptation

Une leçon est acceptée quand `python3 tools/check_lessons.py` rend `0` et qu'un adulte a lu la relecture de la semaine, `python3 tools/build_review.py S<n>` → `print/Relecture_S<n>.html` (ce que Kono dit, ce que l'enfant voit et répond, les erreurs expliquées, la fiche, la carte Maman, et les avertissements : compétence absente de la progression, image absente, question sans erreur expliquée, voix manquantes). Ce script arrive avec la livraison « profils ». Il vérifie : le schéma de l'index, l'existence de chaque fichier de leçon et l'inverse, les clés obligatoires, `parcours` connu, `escale` connu, `order` unique par parcours, l'absence de `child`, l'absence de couleur et de prénom en dur dans les textes, les types d'étapes, les `kinds`, les dessins et les champs de l'annexe A dans la liste fermée, les erreurs objets bien formées, et au moins un niveau `seul` par fiche. En attendant le script, cette liste est la revue manuelle.

## 8. Ordre de mise en service

1. L'application « profils » est mise en ligne : elle lit le schéma 2, crée les profils, migre le suivi des deux enfants actuels, et met les deux leçons S0 au nouveau format.
2. Seulement ensuite, la première publication au schéma 2 est poussée sur `main`.

**Un index au schéma 2 poussé sur `main` avant cette mise en ligne casse l'application actuelle**, qui lit encore `child`. Cowork prépare donc S1 sur une branche et attend le feu vert.

## 9. Interdits

- Renommer ou renuméroter un identifiant de leçon, de parcours, d'escale ou de phrase.
- Ajouter un parcours, un type d'étape, une sorte d'automatisme ou un dessin.
- Écrire un prénom, un âge ou une couleur dans une leçon.
- Publier une semaine incomplète, ou un index au schéma 2 avant l'application qui le lit.
- Modifier `parcours.json`, `app.js`, `sw.js` ou tout fichier hors de `app/lessons/` et de `print/`.

## 10. Qui possède quoi

| Fichier | Propriétaire | Qui écrit |
|---|---|---|
| `app/parcours.json`, `app/ecole.json` | L'école, via le fondateur | La session application (`tools/codes.py` pour `ecole.json` ; jamais un code en clair ni un nom d'enfant) |
| `app/lessons/index.json` et `app/lessons/*.json` | Le contenu | Cowork |
| `voix/registre.json` | La chaîne des voix | `tools/build_audio.py`, lancé par le fondateur |
| `app/*.js`, `app/*.html`, `app/*.css`, `app/sw.js` | L'application | La session application |
| Ce contrat | Le fondateur | Modifié par une nouvelle version numérotée, jamais en place |

## Annexe A · Catalogue de la v0.3.1

Liste fermée au sens du § 1.5, en plus des types d'étapes, des `kinds` et des dessins du README § 4. `tools/check_lessons.py` vérifie exactement ce catalogue, ni plus ni moins. Les champs ici décrits s'ajoutent au format existant ; aucun champ existant ne change de sens.

### A.1 Deux étapes de plus

| `type` | Ce que fait la tablette | Champs |
|---|---|---|
| `manip` | L'enfant manipule, puis valide. Trois modes (ci-dessous). Jugée comme une question : 3 essais, chaque erreur typique expliquée, puis la réponse montrée. | `id`, `mode`, `text`, `say`, `answer`, `errors`, `hints`, `sol`, `skill`, et les champs du mode |
| `order` | Remettre les images d'une histoire dans l'ordre. Trois erreurs sur une même image : l'image est placée et l'on continue. | `id`, `text`, `say`, `scenes` (dans le bon ordre), `hints` |

- `manip`, mode `tenframe` (boîte de dix) : `start` (jetons déjà posés), `goal` (`add` : on compte les jetons posés par l'enfant ; `total` : on compte tous les jetons), `item` (`jeton` par défaut, ou `mangue`).
- `manip`, mode `blocks` (dizaines et unités) : `t`, `u`, `h`, `hundreds` (vrai : colonne des centaines), `add` (unités à poser) ou `addTens` (dizaines à poser), `ask` (question du clavier). Quand 10 unités brillent, l'enfant les touche pour fermer la dizaine (animation) ; avec `hundreds`, 10 dizaines se ferment en une centaine. Puis le clavier demande le résultat.
- `manip`, mode `jumps` (ligne des nombres) : `from`, `to`, `start`, `via` (arrêt obligatoire ; l'erreur `via` est dite si l'enfant n'y est pas passé). La ligne couvre au plus 20 nombres.

### A.2 Champs nouveaux sur des étapes existantes

| Étape | Champ | Sens |
|---|---|---|
| `story` | `pass` | 2, 3… : nouvelle séance sur la même histoire (l'étape d'ordre reçoit un identifiant distinct par passage) |
| `story` | `skipVocab` | vrai : pas de mots mimés |
| `story` | `order` | vrai : ajoute l'étape de remise en ordre des images après les questions |
| `story` | `noImages` | vrai : le récit final se fait sans images |
| `reading` | `reread` | vrai : relecture d'un texte déjà lu (annoncée comme telle, mesurée à part) |
| `review` | `max` | nombre de défis rejoués (2 par défaut) |
| `review` | `fill` | vrai : complète avec `fallback` jusqu'à `max` |
| `choice` | `optionKind` | `text` (défaut), `icon` (les options sont des noms d'images), `dots` (les options sont des nombres montrés en points) |

Pour information, hors liste fermée : `skills` à la racine et `skill` sur une question sont des codes de `app/progression/<parcours>.json` ; sans `skill`, une question compte pour le premier code de `skills`. Le rapport du dimanche en tire la rubrique 2.

### A.3 Les erreurs objets

La valeur d'une clé de `errors` (question, manipulation ou exercice de la fiche) est une phrase, ou un objet `{ "text": "…", "show": [ … ] }` dont le dessin est joué pour montrer l'erreur, par exemple `{ "kind": "blocks", "t": 2, "u": 13, "regroup": true }` pour 213 au lieu de 33. Aucune autre clé n'est admise dans cet objet.

### A.4 Six dessins de plus (`show`)

| `kind` | Champs |
|---|---|
| `blocks` | `h`, `t`, `u` ; `regroup: true` = anime la fermeture de la dizaine (ou de la centaine) |
| `bar` | modèle en barres : `parts` (nombres ou `null` pour « ? »), `whole` (nombre ou `null`), `labels`, `unit` (ex. « F ») |
| `items` | une collection à compter : `n`, `item` (nom d'image) |
| `hidden` | `total`, `visible`, `item` : des objets dont une partie est cachée sous une calebasse |
| `icon` | `name`, `label` (facultatif, mot écrit sous l'image) |
| `syllables` | `name` (image), `n` (nombre de syllabes) : l'image et n ronds qui s'allument un par un |

Images disponibles (`item`, `name`, options `icon`) : `mangue`, `jeton`, `poisson`, `chat`, `sac`, `bol`, `bateau`, `ballon`, `lapin`, `soleil`, `velo`, `ananas`, `baobab`, `domino`, `calebasse`, `panier`. Scènes d'histoire : `marche`, `vent`, `pecheur`, `merci`.

### A.5 Les phrases de Maman (`clip`)

`bonjour`, `bravo_effort`, `fiche`, `explique`, `fin`, `bravo_escale`. `bonjour` et `fin` sont enregistrées une fois par enfant ; l'application les range sous `<phrase>@<profil>`.
