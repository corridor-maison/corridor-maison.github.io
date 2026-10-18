# Corridor à la maison

Séances guidées par la voix de Kono, le martin-pêcheur du fleuve Niger, pour les parcours de l'école (`app/parcours.json`) :
**CE1** et **grande section**. Chaque séance fait avancer une pinasse sur le fleuve, de Bamako à Gao.

Adresse : **https://corridor-maison.github.io/** (définitive : les données des enfants sont liées à cette adresse).

## Ce que fait une séance

Quatre temps, toujours dans le même ordre :

1. **Automatismes** : calcul express (CE1) ou jeu rapide (grande section), contre soi-même. Les calculs ratés reviennent au début de la séance suivante.
2. **Leçon explicite** : Kono montre, on fait ensemble, l'enfant fait seul. L'enfant **manipule** : il pose des jetons dans la boîte de dix, il ferme une dizaine avec dix unités (animation), il fait les sauts sur la ligne des nombres. Chaque erreur typique a son explication, souvent montrée par une animation. Puis la fiche papier, dont l'enfant tape les réponses.
3. **Lecture** (CE1) : écoute surlignée, puis l'enfant lit et s'enregistre ; un texte sur deux est relu le lendemain (lecture répétée).
   **Histoire** (grande section), à la manière de Narramus : une même histoire travaillée toute la semaine (écoute, mots mimés, questions, images à remettre dans l'ordre, récit avec puis sans images).
4. **Méthode** : l'enfant explique comment il a fait (enregistrement écouté le soir par un parent).

Si aucune nouvelle semaine n'est arrivée, l'application compose seule une **séance de révision** chaque jour : automatismes, défis ratés, rappel espacé de questions déjà vues, relecture ou histoire.

Une séance interrompue (bouton Arrêter, tablette en veille, application fermée) **reprend là où l'enfant s'est arrêté** : même étape, réponses et poissons déjà gagnés conservés. À l'ouverture de son espace, **Kono rappelle le niveau** : ce que l'enfant a fait la dernière fois, ce qu'il réussit bien, ce qu'on va revoir, et la séance du jour.

Dans son espace, l'enfant n'a **rien à lire pour choisir** : chaque séance est un billet avec une image (nombres, problèmes, langage, lecture, révision) ; il touche un billet, Kono nomme la séance, et la pinasse, seul bouton, la lance.

## Principes de conception

- **Une seule source, deux supports.** Une séance = un fichier `app/lessons/<id>.json`. La tablette le joue ; `tools/build_print.py` en tire les fiches et la carte Maman ; `tools/build_audio.py` la liste des phrases à enregistrer. Le format est fixé par [`CONTRAT_LECONS.md`](CONTRAT_LECONS.md) et son annexe A, et vérifié par `tools/check_lessons.py`.
- **Accès autorisé par l'école.** L'école remet à chaque famille un code d'inscription (`python3 tools/codes.py nouveau 20 CE1`) ; sans code valide, l'application ne s'ouvre pas. Le dépôt ne contient que les empreintes des codes (`app/ecole.json`), jamais les codes ni un nom d'enfant ; les codes sont dans un fichier remis à l'école, jamais commité. Un code se retire (`retirer C-0007`), et la tablette le refuse à sa prochaine ouverture avec internet. **Remise sans saisie** : `tools/fiches_codes.py` imprime une fiche par famille (QR code) et prépare un message WhatsApp ; le QR code ou le lien ouvre l'application avec le code (`#code=…`, jamais envoyé au serveur, effacé de l'adresse dès sa lecture), qui est vérifié tout seul. Les tablettes installées avant ce contrôle gardent leur accès ; l'école les régularise avec un code depuis l'espace parent.
- **Un profil par enfant.** Prénom, garçon ou fille, date de naissance, classe proposée d'après l'âge et confirmée par le parent, couleur choisie par l'enfant. L'application route par **parcours** (`gs`, `ce1`), jamais par couleur ni par prénom. Une tablette venue de la v0.2 est migrée au premier lancement, sans perte.
- **Pour l'enfant, aucun texte pour naviguer.** Icônes et voix : une image par domaine sur chaque billet de séance, Kono nomme la séance touchée, un seul bouton (la pinasse) la lance. **L'ordre des séances est tenu** : la séance du jour est la première non faite ; celles d'après sont verrouillées (cadenas), et si l'enfant en touche une, Kono dit laquelle vient d'abord ; les séances faites se refont librement. **Chaque escale de la carte est un bouton** : elle montre les séances de l'étape (faites, du jour, à venir) et Kono les compte. On touche Kono pour le réentendre. Les sous-titres sont cachés par défaut (l'enfant écoute et regarde le dessin) ; ils s'affichent d'office si la tablette n'a pas de voix française.
- **Calme.** Un seul objet bouge à la fois ; pas de confettis ni de récompenses à chaque réponse ; les poissons dorés récompensent une réponse trouvée après une erreur. Une seule fête, à la fin de la séance : quelques points qui s'envolent derrière « Séance terminée » (rien en mode « moins d'animations »).
- **Clair.** Fond presque blanc et chaud, le sable seulement en accent (carte, plateaux) ; ombres douces, jamais de relief dur ; pas de pointillés ni de bandeau ; la séance remplit l'écran, Kono est grand et change d'expression (content, étonné, pensif, à l'écoute) ; la pinasse tangue sur la carte. `tests/ecrans.py` refuse tout pointillé ou relief dur sur les écrans de l'enfant.
- **Accessible.** Focus visible partout au clavier ; trois réglages pour l'enfant dans l'espace parent (Voix et affichage) : main gauche (clavier et flèche à gauche, Kono à droite), moins d'animations (Kono immobile, rien ne clignote ; suit aussi le réglage du système), contraste renforcé (texte noir, bords marqués). Chaque bouton, champ et image a un nom pour un lecteur d'écran ; la ligne des nombres et le plateau de blocs se jouent aussi au clavier. Mise en page dédiée au téléphone (360 px) : rien de tronqué, cibles de 44 px au moins.
- **Programme lisible.** Espace parent › Programme : le voyage (escales, séances prévues et publiées), chaque semaine publiée (jour, séance, ce qu'elle travaille, compétences, état pour chaque enfant) et la progression de l'année par période.
- **Progression écrite.** `app/progression/ce1.json` et `app/progression/gs.json` : compétences codées par période, alignées sur les programmes 2025, à valider avec l'enseignante. Chaque séance déclare ses compétences ; le rapport du dimanche donne un taux de réussite par compétence (7 jours) et une **maîtrise** sur 30 jours en quatre paliers (acquis, en cours, fragile, peu travaillé) ; la séance de révision vise d'abord les compétences fragiles.
- **Données des enfants sur la tablette.** Prénoms, suivi, enregistrements, voix de Maman : rien ne part sur internet. Le rapport est copié, ou enregistré dans un fichier que le parent dépose à l'école : rien ne part tout seul. L'application demande au navigateur de ne jamais effacer ces données de lui-même ; l'espace parent (Réglages › Mémoire de la tablette) montre l'adresse, le mode d'installation et l'état de cette protection.
- **Hors ligne.** Dès la première ouverture avec internet, l'application, les parcours, toutes les séances de l'index, les images et les voix sont gardées sur la tablette. Une nouvelle version est vue à la première ouverture avec internet, sans rien vider : le moteur, les styles, les séances et les index sont toujours revalidés auprès du serveur, puis gardés pour le hors ligne.

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `app/` | L'application publiée (site statique, installable, hors ligne) |
| `app/parcours.json` | Les parcours de l'école : classe, âges proposés, couleur par défaut |
| `app/ecole.json` | Mode d'accès et empreintes des codes d'inscription (jamais les codes) |
| `tools/codes.py` | Crée, retire et vérifie les codes d'inscription ; écrit les codes pour l'école dans `print/codes-<date>.csv` (non commité) |
| `tools/fiches_codes.py` | `python3 tools/fiches_codes.py print/codes-<date>.csv --classe CE1 --pdf` → fiches d'inscription à imprimer (4 par page A4, QR code, code en grand, trois consignes) et messages WhatsApp prêts à copier, un par famille ; jamais commités. Demande `segno` (`pip install segno`) |
| `app/lessons/index.json` | Liste des séances publiées (schéma 2) et escales du voyage, par parcours |
| `app/lessons/<id>.json` | Une séance : voix, étapes, manipulations, erreurs typiques, fiche papier |
| `app/progression/` | Progressions CE1 et grande section (codes de compétences) |
| `app/phrases.json` | Les phrases que le moteur dit lui-même, et les phrases de Maman |
| `app/img/` | Les images (SVG), communes à la tablette et aux fiches |
| `app/audio/` | Voix enregistrées (`rec/`) ou générées (`gen/`) et leur manifeste |
| `tools/check_lessons.py` | Contrôle des séances selon le contrat ; rend 0 si tout est conforme ; lancé par le workflow avant toute publication |
| `tools/build_print.py` | `python3 tools/build_print.py S1` → `print/Fiches_S1.pdf` |
| `tools/build_review.py` | `python3 tools/build_review.py S1` → `print/Relecture_S1.html` : relecture d'une semaine avant publication (tout ce que l'enfant entend, voit et répond, fiche, carte Maman, contrôles) |
| `tools/build_icons.py` | Icônes du site (`app/icons/`, usages « any » et « maskable »), de l'enveloppe Android (`--android <res>`) et de la fiche Play (`--play <dossier>`), rendues par Chromium depuis le dessin de Kono d'`app.js` |
| `tools/tableau_classe.py` | `python3 tools/tableau_classe.py <dossier>` → tableau par classe pour l'enseignante, à partir des rapports (`rapport-1`) déposés par les familles |
| `tools/build_audio.py` | Phrases à enregistrer, import des enregistrements, génération des voix, manifeste |
| `voix/` | Enregistrements humains (`conteur/`, `kono/`) et registre stable des numéros |
| `tests/` | Bout en bout (profils, séances, révision), hors ligne, migration depuis la v0.2, outils, unitaires (juge, moteur), écrans (téléphone, réglages, lecteur d'écran) |
| `CONTRAT_LECONS.md` | Le contrat des séances : format, listes fermées (annexe A), qui écrit quoi |
| `CLAUDE.md` | Repères pour tout agent qui travaille dans ce dépôt |
| `.github/workflows/pages.yml` | Contrôle des séances, puis publication de `app/` sur GitHub Pages à chaque poussée sur `main` |

## Mise en ligne

Le site est publié par GitHub Pages à l'adresse **https://corridor-maison.github.io/** (en https, obligatoire pour le micro et le mode hors ligne).

- Le workflow `.github/workflows/pages.yml` se lance à chaque poussée sur `main` : il lance `tools/check_lessons.py`, puis dépose le contenu de `app/` comme artefact Pages et le déploie (index.html se retrouve à la racine du site). Dans Settings › Pages, la source doit rester « GitHub Actions ».
- Il peut aussi être lancé à la main : onglet Actions › « Deploy app/ to GitHub Pages » › Run workflow.
- Aucune donnée d'enfant ne part sur GitHub : le dépôt ne contient que l'application et les séances. S'il est public, les séances sont lisibles par tous, rien d'autre.

## Installer sur une tablette Android

1. Ouvrir **https://corridor-maison.github.io/** dans **Chrome**, avec internet.
2. Menu ⋮ › **Installer l'application** (ou « Ajouter à l'écran d'accueil »). L'icône **Corridor** (Kono sur fond sable) apparaît.
3. L'ouvrir une première fois avec internet : tout est gardé pour le hors ligne.
4. Voix française hors ligne : Paramètres › Synthèse vocale › Moteur Google › Installer les données vocales › Français (France).
5. Premier lancement : code d'inscription remis par l'école (viser le QR code de la fiche ou toucher le lien du message WhatsApp : le code est vérifié sans rien taper ; sinon le taper), code parent à 4 chiffres, puis un profil par enfant (prénom, garçon ou fille, date de naissance, classe confirmée, couleur). Un enfant de plus s'ajoute depuis l'accueil, avec le code parent.
6. Voix de Maman : Espace parent › Voix de Maman (avec ses mots à elle ; « bonjour » et « fin » se font une fois par enfant).
7. Bloquer la tablette sur l'application : Paramètres › Sécurité › Épinglage d'écran.

Les mises à jour arrivent seules : à la prochaine ouverture avec internet, la tablette prend la nouvelle version, sans perdre le suivi.

À l'ouverture, l'écran est clair avec Kono dès le premier instant, avant même que le moteur soit chargé : jamais d'écran blanc. L'application du Play Store (enveloppe Android) montre le même Kono sur le même sable comme icône et comme écran de lancement.

Toujours ouvrir l'application de la même façon, par l'icône installée : un autre navigateur (Samsung Internet, Firefox), la navigation privée ou une autre adresse ont chacun leur propre mémoire et ne voient pas le suivi.

## Le cycle de chaque semaine

1. Du lundi au jeudi, une séance par jour.
2. Le soir, un parent écoute l'enregistrement (Espace parent › Suivi). Le suivi signale les enregistrements pas encore écoutés.
3. **Dimanche** : Espace parent › Rapport, sur chaque tablette : Copier (pour l'envoyer) ou **Enregistrer dans un fichier** (format `rapport-1`, à déposer à l'école). Le rapport a un format fixe (format 2), par profil : séances, compétences, automatismes, mesures, enregistrements non écoutés, file de révision, détail, maîtrise sur 30 jours. Le fichier est au format `rapport-2` (le tableau par classe lit aussi `rapport-1`). À l'école, `python3 tools/tableau_classe.py <dossier des fichiers>` fait un tableau par classe (séances, compétences, défis à revoir) pour l'enseignante.
4. La semaine suivante est écrite à partir du rapport et de `app/progression/`, selon `CONTRAT_LECONS.md`, puis **relue par un adulte** (un enseignant pour le pilote) sur `python3 tools/build_review.py S2` → `print/Relecture_S2.html` : chaque séance dans l'ordre de la tablette, ce que Kono dit, ce que l'enfant voit et répond, les erreurs expliquées, la fiche, la carte Maman, et les contrôles (compétences inconnues, images absentes, questions sans erreur expliquée, voix manquantes).
5. Déposer les fichiers dans `app/lessons/`, mettre à jour `app/lessons/index.json`, vérifier avec `python3 tools/check_lessons.py` (doit rendre 0), lancer `tools/build_print.py` et `tools/build_audio.py`, publier.
6. Imprimer `print/Fiches_<semaine>.pdf`.

Sans nouvelle semaine, la tablette propose une séance de révision : l'habitude ne casse pas.

Sauvegarde : Espace parent › Réglages › Télécharger la sauvegarde (le suivi dans un fichier, gardé par la famille ; une sauvegarde de la v0.2 se restaure aussi). Le Suivi rappelle de sauvegarder après sept jours sans sauvegarde. Un enfant seul se déplace vers une autre tablette : Réglages › Exporter (suivi, enregistrements, phrases de Maman) puis Importer un profil sur l'autre tablette. Réglages › Journal garde les dernières erreurs de l'application, à copier dans un message en cas de problème.

## 4. Format d'une séance (référence citée par le contrat comme « README § 4 »)

Étapes possibles, dans l'ordre de l'enseignement explicite. Les listes sont fermées : `tools/check_lessons.py` les vérifie, avec l'annexe A du contrat qui ajoute les étapes `manip` et `order`, les champs `pass`, `skipVocab`, `order`, `noImages`, `reread`, `max`, `fill` et `optionKind`, les erreurs objets et six dessins.

| `type` | Ce que fait la tablette |
|---|---|
| `maman` | Joue la phrase enregistrée par Maman (`clip` : `bonjour`, `bravo_effort`, `fiche`, `explique`, `fin`, `bravo_escale`). Sinon, Kono dit une phrase neutre. |
| `say` | Kono parle (`say` pour la voix, `text` pour la bulle) et affiche `show`. |
| `part` | Annonce un des quatre temps (`n`, `title`, `text`). L'en-tête de la séance montre le temps en cours. |
| `review` | Rejoue jusqu'à `max` défis ratés les jours précédents (2 par défaut), sinon `fallback`. |
| `demo` | « Je te montre » : une suite de `lines`, chacune avec sa voix et son dessin. |
| `number` / `choice` | Question avec clavier ou choix. `errors` = explication propre à chaque mauvaise réponse typique ; `hints` = indices ; `sol` = solution expliquée ; `after` = dessin affiché une fois trouvé ; `options` et `optionKind` pour `choice`. |
| `manip` | L'enfant manipule puis valide : boîte de dix, dizaines et unités, sauts sur la ligne des nombres (annexe A du contrat). |
| `order` | Remettre les images d'une histoire dans l'ordre (annexe A du contrat). |
| `paper` | Envoie l'enfant sur sa fiche, puis vérifie les réponses tapées. Les exercices viennent de la section `paper` du même fichier. |
| `record` | L'enfant s'enregistre pour expliquer sa méthode ou raconter l'histoire. Le parent écoute le soir. |
| `drill` | Automatismes : `count` questions en `seconds` secondes, `kinds` pondérés (`complement10`, `complement-next-ten`, `through10`, `double`, `table`, `tf-complement`, `count-tf`, `decomp`), `input` = `keypad` ou `choice`. Record gardé par enfant. |
| `reading` | Lecture répétée : `passage` = liste de phrases. Écoute surlignée, puis enregistrement de l'enfant ; `reread` pour une relecture. |
| `story` | Histoire : `sentences`, `vocab` (mot + explication à mimer), `questions` (étapes `choice`), `scenes` (images), `retell` (consigne pour raconter), et les champs de l'annexe A. |
| `end` | Bilan de la séance et phrase de fin de Maman (`clip` : `fin`). |

Dessins disponibles dans `show` : `title`, `expr`, `text`, `numberline` (from, to, marks, jumps), `split` (whole, parts), `tenframe` (filled, highlightEmpty), `fingers` (up), `part`, `word`, `listen`, `scenes`, plus les six de l'annexe A (`blocks`, `bar`, `items`, `hidden`, `icon`, `syllables`).
Jetons de texte : `{prenom}` (prénom de l'enfant), `{e}` (accord au féminin). Aucune couleur comme identité dans un texte : c'est l'application qui nomme la fiche.

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
- `python3 tests/e2e.py 1280x800` (serveur lancé sur le port 8765) : deux profils, CE1 et grande section, jouent toutes les séances publiées de leur parcours puis la séance de révision ; vérifie qu'il n'y a aucune erreur JavaScript, que chaque mode de manipulation, la remise en ordre de l'histoire et une erreur animée ont été joués, qu'une séance arrêtée puis fermée reprend à la bonne étape avec ses réponses, que le rappel du niveau est dit à l'ouverture, que Kono nomme chaque billet touché avant que la pinasse ne le lance, qu'un billet verrouillé ne change pas la sélection et que Kono dit quelle séance vient d'abord, qu'une escale touchée liste les séances de l'étape, que l'onglet Programme montre le voyage, la semaine et la progression, qu'un code d'inscription faux est refusé, que l'export puis l'import d'un profil ne perdent rien, et que le rapport s'enregistre en fichier `rapport-1` avec les mêmes chiffres que le texte.
- `python3 tests/outils.py` : `check_lessons.py` et `codes.py verifier` rendent 0 ; `build_review.py` produit la relecture de la semaine avec chaque séance ; `tableau_classe.py` fait un tableau par classe à partir d'un rapport d'exemple et du rapport exporté par le test de bout en bout.
- `python3 tests/maj.py` : mise à jour sans vider le cache. Une copie de l'application en version 0.0.1 est servie et installée hors ligne ; la vraie version la remplace sur le même serveur ; à la première ouverture en ligne, la vraie version doit s'afficher en bas de l'accueil, son cache doit être le seul restant, et elle doit encore marcher sans réseau.
- `python3 tests/unite.py` : 34 contrôles unitaires dans le vrai moteur (Chromium), sans jouer de séance : la liste exacte des escales (Bamako, Ségou, Mopti, Tombouctou, Gao), codes d'inscription, clés et phrases, prénom et accord, âge, ordre des séances (verrou) et séances par escale, automatismes (invariants sur 300 tirages par sorte), verdict du juge (3 essais, erreur typique, aide, réponse montrée), statistiques et maîtrise par compétence, carte du voyage, lecture d'un état, rappel du niveau, révision ciblée.
- `python3 tests/ecrans.py` : lancement (fond clair, Kono et le nom avant même les styles et le moteur), icônes du manifeste (tailles, usages « any » et « maskable », fond sable, Kono dedans et dans la zone sûre), téléphone 360 × 640 (pas de débordement, compteur visible, Kono au quart de l'écran au plus, cibles ≥ 44 px, ni pointillés ni relief dur, captures), séance sur tablette (le dessin remplit au moins la moitié de la hauteur, Kono au moins le tiers), carte (le Bani dessiné, Djenné en losange et non en escale, noms des fleuves lisibles), billets dont le titre tient sur trois lignes au plus, réglages main gauche / moins d'animations / contraste posés depuis l'espace parent et gardés, et sur chaque écran visité, chaque bouton, champ et image a un nom pour un lecteur d'écran. Le test de bout en bout refait cet audit à chaque capture.
- `python3 tests/offline.py` : une seule ouverture avec réseau, puis coupure réelle (serveur arrêté) ; l'accueil et une séance doivent s'ouvrir.
- `python3 tests/migration.py` : un état de la v0.2 (`tests/etat-v0.2.json`) devient deux profils sans perte ; écrit la comparaison avant/après.
- Les tests demandent Playwright (Chromium) et Pillow (`tests/ecrans.py` lit les icônes).
- Sous Windows, lancer Python avec `-X utf8`.

## Limites connues (v0.3.5)

- Les images des histoires et des objets sont des dessins simples, en attendant le kit de l'illustrateur : quatre scènes d'histoire (`marche`, `vent`, `pecheur`, `merci`, SVG au format 240 × 160) et seize images d'objets carrées, à déposer dans `app/img/` ; le moteur les prend telles quelles.
- Pas de reconnaissance vocale : la lecture à voix haute est enregistrée, un adulte l'écoute et la mesure.
- Le suivi est propre à chaque tablette : sauvegarde dans un fichier, export d'un profil vers une autre tablette, rapport déposé à l'école en fichier. Pas de remontée automatique vers un dépôt central : c'est une décision de politique de données à prendre avec l'école.
- Tant qu'aucune voix n'est générée ou enregistrée, c'est la synthèse d'Android qui parle.
- L'interface est en français seulement (une deuxième langue se décide avec l'école).
- La difficulté s'adapte par la file de révision et la maîtrise par compétence (défis de rappel ciblés) ; les automatismes pondèrent déjà les sortes ratées. Pas d'adaptation du contenu des leçons elles-mêmes, qui restent celles de la semaine.
- Les séances S1 n'utilisent pas la boîte de dix « en ajout » (`goal: add`) ; le moteur la gère et le test la contrôle sur une étape injectée.
