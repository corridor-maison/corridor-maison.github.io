# Corridor à la maison

Séances guidées par la voix de Kono, le martin-pêcheur du fleuve Niger, pour deux parcours :
**Bleu** (CE1) et **Orange** (grande section). Chaque séance fait avancer une pinasse sur le fleuve, de Bamako à Gao.

Adresse : **https://corridor-maison.github.io/** (définitive : les données des enfants sont liées à cette adresse).

## Ce que fait une séance

Quatre temps, toujours dans le même ordre :

1. **Automatismes** : calcul express (Bleu) ou jeu rapide (Orange), contre soi-même. Les calculs ratés reviennent au début de la séance suivante.
2. **Leçon explicite** : Kono montre, on fait ensemble, l'enfant fait seul. L'enfant **manipule** : il pose des jetons dans la boîte de dix, il ferme une dizaine avec dix unités (animation), il fait les sauts sur la ligne des nombres. Chaque erreur typique a son explication, souvent montrée par une animation. Puis la fiche papier, dont l'enfant tape les réponses.
3. **Lecture** (Bleu) : écoute surlignée, puis l'enfant lit et s'enregistre ; un texte sur deux est relu le lendemain (lecture répétée).
   **Histoire** (Orange), à la manière de Narramus : une même histoire travaillée toute la semaine (écoute, mots mimés, questions, images à remettre dans l'ordre, récit avec puis sans images).
4. **Méthode** : l'enfant explique comment il a fait (enregistrement écouté le soir par un parent).

Si aucune nouvelle semaine n'est arrivée, l'application compose seule une **séance de révision** chaque jour : automatismes, défis ratés, rappel espacé de questions déjà vues, relecture ou histoire.

## Principes de conception

- **Une seule source, deux supports.** Une séance = un fichier `app/lessons/<id>.json`. La tablette le joue ; `tools/build_print.py` en tire les fiches et la carte Maman ; `tools/build_audio.py` la liste des phrases à enregistrer. Format : [`docs/FORMAT.md`](docs/FORMAT.md).
- **Pour l'enfant, aucun texte pour naviguer.** Icônes et voix. On touche Kono pour le réentendre. Les sous-titres sont cachés par défaut (l'enfant écoute et regarde le dessin) ; ils s'affichent d'office si la tablette n'a pas de voix française.
- **Calme.** Un seul objet bouge à la fois ; pas de confettis ni de récompenses à chaque réponse ; les poissons dorés récompensent une réponse trouvée après une erreur.
- **Progression écrite.** `app/progression/ce1.json` et `app/progression/gs.json` : compétences codées par période, alignées sur les programmes 2025, à valider avec l'enseignante. Chaque séance déclare ses compétences ; le rapport du dimanche donne un taux de réussite par compétence.
- **Données des enfants sur la tablette.** Prénoms, suivi, enregistrements, voix de Maman : rien ne part sur internet. Le rapport est copié à la main par le parent.
- **Hors ligne.** Dès la première ouverture avec internet, l'application, toutes les séances de l'index, les images et les voix sont gardées sur la tablette.

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `app/` | L'application publiée (site statique, installable, hors ligne) |
| `app/lessons/index.json` | Liste des séances publiées et escales du voyage |
| `app/lessons/<id>.json` | Une séance : voix, étapes, manipulations, erreurs typiques, fiche papier |
| `app/progression/` | Progressions CE1 et grande section (codes de compétences) |
| `app/phrases.json` | Les phrases que le moteur dit lui-même, et les phrases de Maman |
| `app/img/` | Les images (SVG), communes à la tablette et aux fiches |
| `app/audio/` | Voix enregistrées (`rec/`) ou générées (`gen/`) et leur manifeste |
| `tools/build_print.py` | `python3 tools/build_print.py S1` → `print/Fiches_S1.pdf` |
| `tools/build_audio.py` | Phrases à enregistrer, import des enregistrements, génération des voix, manifeste |
| `voix/` | Enregistrements humains (`conteur/`, `kono/`) et registre stable des numéros |
| `docs/FORMAT.md` | Le format des séances et des programmes (référence pour écrire une nouvelle semaine) |
| `tests/` | Test de bout en bout et test hors ligne |
| `.github/workflows/pages.yml` | Publication automatique de `app/` sur GitHub Pages à chaque poussée sur `main` |

## Mise en ligne

Le site est publié par GitHub Pages à l'adresse **https://corridor-maison.github.io/** (en https, obligatoire pour le micro et le mode hors ligne).

- Le workflow `.github/workflows/pages.yml` se lance à chaque poussée sur `main` : il dépose le contenu de `app/` comme artefact Pages et le déploie (index.html se retrouve à la racine du site). Dans Settings › Pages, la source doit rester « GitHub Actions ».
- Il peut aussi être lancé à la main : onglet Actions › « Deploy app/ to GitHub Pages » › Run workflow.
- Aucune donnée d'enfant ne part sur GitHub : le dépôt ne contient que l'application et les séances. S'il est public, les séances sont lisibles par tous, rien d'autre.

## Installer sur une tablette Android

1. Ouvrir **https://corridor-maison.github.io/** dans **Chrome**, avec internet.
2. Menu ⋮ › **Installer l'application** (ou « Ajouter à l'écran d'accueil »). L'icône **Corridor** apparaît.
3. L'ouvrir une première fois avec internet : tout est gardé pour le hors ligne.
4. Voix française hors ligne : Paramètres › Synthèse vocale › Moteur Google › Installer les données vocales › Français (France).
5. Premier lancement : prénoms, garçon ou fille, code parent à 4 chiffres.
6. Voix de Maman : Espace parent › Voix de Maman (8 phrases, avec ses mots à elle).
7. Bloquer la tablette sur l'application : Paramètres › Sécurité › Épinglage d'écran.

Les mises à jour arrivent seules : à la prochaine ouverture avec internet, la tablette prend la nouvelle version, sans perdre le suivi.

## Le cycle de chaque semaine

1. Du lundi au jeudi, une séance par jour.
2. Le soir, un parent écoute l'enregistrement (Espace parent › Suivi). Le suivi signale les enregistrements pas encore écoutés.
3. **Dimanche** : Espace parent › Rapport › Copier, sur chaque tablette. Le rapport a un format fixe (format 1) : séances, compétences, automatismes, mesures, enregistrements non écoutés, file de révision, détail.
4. La semaine suivante est écrite à partir du rapport et de `app/progression/`, au format `docs/FORMAT.md`, puis relue par un adulte (un enseignant pour le pilote).
5. Déposer les fichiers dans `app/lessons/`, mettre à jour `app/lessons/index.json`, lancer `tools/build_print.py` et `tools/build_audio.py`, publier.
6. Imprimer `print/Fiches_<semaine>.pdf`.

Sans nouvelle semaine, la tablette propose une séance de révision : l'habitude ne casse pas.

Sauvegarde : Espace parent › Réglages › Télécharger la sauvegarde (le suivi dans un fichier, gardé par la famille).

## Les voix

`python3 tools/build_audio.py` écrit `print/voix_a_enregistrer.md` (chaque phrase, son numéro, son rôle, son statut) et `app/audio/manifest.json`.

- **Voix humaines** (prioritaires) : une phrase par fichier, nommé par son numéro (`012.m4a`), dans `voix/conteur/` ou `voix/kono/`, puis relancer le script (volume égalisé, silences coupés, mp3).
- **Voix de synthèse** :
  - Google (par défaut) : `GOOGLE_TTS_API_KEY` ; voix `KONO_VOICE` (défaut `fr-FR-Chirp3-HD-Achird`) et `CONTEUR_VOICE` (défaut `fr-FR-Chirp3-HD-Sulafat`). La gamme Chirp 3 HD est gratuite jusqu'à 1 million de caractères par mois ; tout le contenu actuel en fait environ 41 000.
  - ElevenLabs : `KONO_ENGINE=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` (une voix inventée avec « Voice Design », jamais copiée sur une personne réelle).
- **Choisir la voix de Kono avec les enfants** : `python3 tools/build_audio.py essai` produit `print/essai_voix/voix_1.mp3`, `voix_2.mp3`… (mêmes 10 phrases, voix mélangées). Les enfants écoutent et choisissent ; la correspondance est dans `cle.txt`.
- Les phrases qui contiennent le prénom de l'enfant restent dites par la tablette.

## Tester

- Localement : `python3 -m http.server 8765 --directory app`, puis `http://localhost:8765/#test` (le mode `#test` accélère tout).
- `python3 tests/e2e.py 1280x800` (serveur lancé sur le port 8765) : joue toutes les séances publiées et la séance de révision, pour les deux enfants ; échoue à la moindre erreur.
- `python3 tests/offline.py` : une seule ouverture avec réseau, puis coupure réelle (serveur arrêté) ; l'accueil et une séance doivent s'ouvrir.
- La v0.3.1 passe les deux tests, sur 1280×800, 1024×600 et 800×1280 en portrait.

## Limites connues (v0.3.1)

- Les images des histoires sont des dessins simples, en attendant le kit de l'illustrateur.
- Pas de reconnaissance vocale : la lecture à voix haute est enregistrée, un adulte l'écoute et la mesure.
- Le suivi est propre à chaque tablette (d'où la sauvegarde dans un fichier).
- Tant qu'aucune voix n'est générée ou enregistrée, c'est la synthèse d'Android qui parle.
