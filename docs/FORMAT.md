# Format d'une séance · Corridor à la maison · v0.3.1

Une séance = un fichier `app/lessons/<id>.json`. Le même fichier sert à la tablette (`app/app.js`), aux fiches imprimées (`tools/build_print.py`) et à la liste des phrases à enregistrer (`tools/build_audio.py`). On ne décrit jamais une séance ailleurs.

## En-tête

```json
{
 "id": "bleu-s1-echange",          // = nom du fichier
 "child": "bleu",                   // ancien routage (bleu = CE1, orange = GS), gardé tant que le moteur route par lui
 "programme": "CE1",                // v0.3.1 : code du programme, défini dans index.json › programmes. C'EST LA CLÉ DE RÉFÉRENCE.
 "order": 1,                        // ordre dans le parcours (0 = S0, puis 1, 2, 3...)
 "week": "S1",
 "day": "mardi",                    // jour prévu (information pour le parent)
 "title": "La dizaine qui se forme",
 "domain": "Nombres",
 "programme_label": "CE1 · numération : échanger 10 unités contre 1 dizaine",
 "objective": "Comprendre pourquoi 29 + 4 fait 33 et pas 213.",
 "skills": ["N.echange", "C.dizaine", "L.fluence", "O.expliquer"],   // codes de app/progression/ce1.json ou gs.json
 "escale": 1,
 "steps": [ ... ],
 "paper": { ... }
}
```

Chaque question peut porter `"skill": "<code>"`. Sinon, elle compte pour le premier code de `skills`.

## Les programmes (v0.3.1)

`app/lessons/index.json` déclare la liste des programmes, et chaque séance (dans l'index et dans son fichier) porte son code :

```json
"programmes": [
 { "code": "GS",  "label": "Grande section", "progression": "progression/gs.json",  "theme": "orange" },
 { "code": "CE1", "label": "CE1",            "progression": "progression/ce1.json", "theme": "bleu" }
],
"lessons": [ { "id": "bleu-s1-echange", "child": "bleu", "programme": "CE1", ... } ]
```

- `programme` est la clé de référence d'une séance. `child` disparaîtra quand l'application aura des profils d'enfants (un profil choisit un programme).
- Ajouter un programme = ajouter une ligne dans `programmes`, son fichier de progression, et ses séances. Aucun code à changer.
- `theme` n'est qu'une couleur d'affichage : il ne décide de rien.

## Règles d'écriture

- `text` est ce que le parent peut lire en sous-titre. `say` est ce que la voix dit. Si les deux sont identiques, on ne met que `text`.
- Dans `say`, les nombres sont écrits **en lettres** (« trente-huit plus sept »), pour que toutes les voix les lisent bien.
- `{prenom}` = prénom de l'enfant (la phrase reste alors dite par la tablette, pas enregistrable). `{e}` = accord au féminin (« tout{e} seul{e} »).
- Pas de nombre calculé dans les phrases du moteur : tout ce qui est dit est écrit en entier dans le fichier.
- Phrases courtes. Une idée par phrase. Vocabulaire d'un enfant de l'âge visé.
- Chaque erreur typique a son explication : elle dit **ce que l'enfant a fait** puis **comment corriger**, sans jugement.
- Les identifiants (`id`) des questions sont uniques dans la séance. Ils servent à la file de révision.

## Les types d'étapes

| `type` | Ce que fait la tablette | Champs |
|---|---|---|
| `maman` | Joue la phrase enregistrée par Maman, sinon une phrase neutre de Kono | `clip` : bonjour_bleu, bonjour_orange, bravo_effort, fiche, explique, fin_bleu, fin_orange, bravo_escale |
| `say` | Kono parle et montre `show` | `text`, `say`, `show` |
| `part` | Annonce un des quatre temps | `n` (1 à 4), `title`, `text` |
| `review` | Rejoue jusqu'à `max` (2 par défaut) défis ratés les jours précédents, sinon `fallback` | `fallback` : liste d'étapes, `max` |
| `demo` | « Je te montre » : une suite de lignes, chacune avec voix et dessin | `lines` : [{`text`, `say`, `show`}] |
| `number` | Question à réponse nombre, clavier | `id`, `text`, `say`, `show`, `answer`, `errors`, `hints`, `sol`, `after` |
| `choice` | Question à choix | idem + `options` ; `optionKind`: `"text"` (défaut), `"icon"` (options = noms d'images), `"dots"` (options = nombres affichés en points) |
| `manip` | **v0.3** L'enfant manipule (voir plus bas) | `id`, `mode`, ... |
| `order` | **v0.3** Remettre les images d'une histoire dans l'ordre | `id`, `text`, `say`, `scenes` (dans le bon ordre), `hints` |
| `drill` | Automatismes chronométrés contre soi-même | `id`, `title`, `text`, `seconds`, `count`, `input` (`keypad`/`choice`), `kinds` |
| `paper` | Envoie l'enfant sur sa fiche puis vérifie les réponses tapées | `text`, `say` |
| `reading` | Lecture répétée : écoute surlignée puis l'enfant lit et s'enregistre | `id`, `title`, `passage` (liste de phrases), `reread` (**v0.3**, true = relecture d'un texte déjà lu) |
| `story` | Histoire façon Narramus | `id`, `title`, `sentences`, `vocab` [{`word`, `say`}], `questions` (étapes choice), `scenes`, `retell`, **v0.3** : `pass` (2, 3... = nouvelle séance sur la même histoire), `skipListen`, `skipVocab`, `order` (true = ajoute l'étape de remise en ordre), `noImages` (true = le récit final se fait sans images) |
| `record` | L'enfant s'enregistre | `kind` (methode, recit), `text`, `say`, `clip`, `show` |
| `end` | Bilan et phrase de fin | `clip` : fin_bleu ou fin_orange |

### `errors` (v0.3)

La valeur peut être une phrase, ou un objet avec un dessin animé qui montre l'erreur :

```json
"errors": {
  "213": { "text": "Tu as écrit 13 à côté du 2. Mais 13, c'est une dizaine et 3 unités. Regarde : la dizaine rejoint les deux autres.",
           "show": [ { "kind": "blocks", "t": 2, "u": 13, "regroup": true } ] },
  "23": "Tu as oublié une dizaine."
}
```

### `manip` (v0.3)

Toutes les variantes ont `id`, `text`, `say`, `answer`, `errors`, `hints`, `sol`, `skill`.

**Boîte de dix** : l'enfant touche les cases pour poser ou enlever des jetons, puis valide.

```json
{ "type": "manip", "mode": "tenframe", "id": "pose-3", "start": 7, "goal": "add", "answer": 3,
  "text": "Il y a 7 jetons. Pose les jetons qui manquent pour faire 10.", "say": "..." }
```
`goal` : `add` (on compte les jetons ajoutés) ou `total` (on compte tous les jetons). `item` : `jeton` (défaut) ou `mangue`.

**Dizaines et unités** : la planche montre `t` dizaines et `u` unités (et `h` centaines). Le plateau contient `add` unités à poser (ou `addTens` dizaines). L'enfant les pose une à une ; quand il y a 10 unités, elles brillent et l'enfant les touche pour **fermer la dizaine** (animation). Ensuite le clavier demande le résultat.

```json
{ "type": "manip", "mode": "blocks", "id": "b-27-5", "t": 2, "u": 7, "add": 5, "answer": 32,
  "hundreds": false, "text": "27 + 5. Pose les 5 unités, une par une.", "say": "...",
  "ask": "Combien maintenant ?", "errors": { "212": { "text": "...", "show": [ ... ] } } }
```
Avec `"hundreds": true`, la colonne des centaines apparaît et 10 dizaines se ferment en une centaine.

**Ligne des nombres** : l'enfant touche la ligne pour faire des sauts depuis `start`.

```json
{ "type": "manip", "mode": "jumps", "id": "saut-38-7", "from": 30, "to": 50, "start": 38, "answer": 45, "via": 40,
  "text": "38 + 7. Fais un saut jusqu'à 40, puis le reste.", "say": "...",
  "errors": { "44": "...", "via": "Arrête-toi d'abord à 40 : c'est le nombre tout rond." } }
```
`via` (facultatif) : arrêt obligatoire. L'erreur `via` est dite si l'enfant n'y est pas passé. La ligne couvre au plus 20 nombres.

## Les dessins (`show`)

| `kind` | Champs |
|---|---|
| `title` | `text` |
| `expr` | `text` (calcul en grand) |
| `text` | `text` |
| `numberline` | `from`, `to`, `marks`, `jumps` [[a, b, "+2"]] |
| `split` | `whole`, `parts` [a, b] (null = « ? ») |
| `tenframe` | `filled`, `highlightEmpty`, `small` |
| `fingers` | `up` |
| `scenes` | `scenes` |
| `blocks` | **v0.3** `h`, `t`, `u` ; `regroup: true` = anime la fermeture de la dizaine (ou de la centaine) |
| `bar` | **v0.3** modèle en barres : `parts` [nombres ou null], `whole` (nombre ou null), `labels` [textes sous chaque partie], `unit` (ex. « F ») |
| `items` | **v0.3** une collection d'objets à compter : `n`, `item` (nom d'image) |
| `hidden` | **v0.3** `total`, `visible`, `item` : des objets, dont une partie cachée sous une calebasse |
| `icon` | **v0.3** `name`, `label` (facultatif, mot écrit sous l'image) |
| `syllables` | **v0.3** `name` (image), `n` (nombre de syllabes) : l'image et n ronds qui s'allument un par un |

Images disponibles (`item`, `name`, options `icon`) : `mangue`, `jeton`, `poisson`, `chat`, `sac`, `bol`, `bateau`, `ballon`, `lapin`, `soleil`, `velo`, `ananas`, `baobab`, `domino`, `calebasse`, `panier`.

Syllabes à l'oral (pas de e muet final) : chat, sac, bol (1) ; poisson, bateau, ballon, lapin, soleil, vélo, panier (2) ; ananas, baobab, domino (3).

Scènes d'histoire disponibles : `marche`, `vent`, `pecheur`, `merci` (Le panier de Bintou).

## Les automatismes (`drill`)

`kinds` : `complement10`, `complement-next-ten`, `through10`, `double` (`min`, `max`), `table` (`n`), `tf-complement`, `count-tf`, `decomp` (`n`). Garder le **même `id`** d'une séance à l'autre (`calcul-express-bleu`, `jeu-rapide-orange`) : le record de l'enfant se suit sur toute l'année.

## La fiche (`paper`)

```json
"paper": {
 "title": "...", "model": "Ce que Kono m'a montré, en une ligne",
 "model_visual": { "kind": "blocks", "t": 3, "u": 13 },     // v0.3 : numberline | tenframe | blocks | bar | items | none
 "levels": [ { "stars": 1, "ins": "Consigne", "who": "seul" | "maman", "items": [ ... ] } ],
 "maman": [ "notes pour l'adulte" ]
}
```

Exercices possibles :

| Champs | Rendu |
|---|---|
| `q` court avec `?` (« 9 + ? = 10 ») | calcul à trous |
| `q` court sans `?` (« 38 + 9 ») | calcul + case réponse |
| `q` + `line` [a, b] | calcul + ligne des nombres à dessiner |
| `q` + `tenframe` n | boîte de dix + case réponse (`answer`) ou boîte vide à colorier (sans `answer`) |
| `q` + `blocks` {`h`, `t`, `u`} | **v0.3** dessin de dizaines et unités + case réponse |
| `q` + `draw` {`n`, `item`} | **v0.3** « dessine n mangues » : grand cadre vide (sans `answer`) |
| `q` + `syll` {`name`} + `answer` | **v0.3** image + 3 ronds à colorier (un par syllabe) |
| `q` long | problème : texte + lignes (`lines`) + case réponse si `answer` |

`answer` absent = réponse libre (non tapée sur la tablette). `errors` : comme pour les questions. `short` : intitulé court pour la tablette.
