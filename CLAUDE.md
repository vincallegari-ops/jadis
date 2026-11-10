# Jadis : reprise dans Claude Code

Appli mobile d'histoire pour les curieux. Une histoire à la fois (environ 400 mots, avec une anecdote), sur tous les continents et toutes les époques, jusqu'en 1914. À la fin d'un texte : deux indices au choix (lieu et date, couleur de l'époque) ou une Surprise.

## Règles produit (ne pas casser)
- Une seule histoire à l'écran. Jamais un article déjà lu : le choix des deux indices et de la Surprise ne puise que dans les non lus.
- Deux indices aux continents et époques différents, avec préférence pour les continents et époques les moins visités.
- L'interface n'affiche ni sources, ni quiz, ni « vérifié ». La vérification se fait en amont (corpus).
- Accueil, marque-page « Garder », Bibliothèque (histoires gardées), retour accueil depuis l'histoire.
- Lecture audio : voix du navigateur pour l'instant (Web Speech API, fr-FR).
- Bornes des époques : Antiquité -3500 à 476 ; Moyen Âge 477 à 1492 ; Renaissance 1492 à 1600 ; Révolutions 1601 à 1789 ; Ère industrielle 1790 à 1914.

## Design « Papier déchiré »
Fond dégradé aux couleurs de l'époque, pièces de papier déchiré (fonction `torn(seed, steps, amp)` qui renvoie un `clip-path: polygon(...)`, ombre portée sur le conteneur), une police par époque.
- Antiquité #2A5D9F, Marcellus ; Moyen Âge #C23A22, Grenze Gotisch ; Renaissance #1F7A6E, Cormorant Garamond ; Révolutions #A3214B, Libre Baskerville ; Ère industrielle #E3B505 (texte sombre), Alfa Slab One.
- Texte : Literata. Interface : Bricolage Grotesque. Logo : Fraunces 900.
- Maquette : `design/` (fichiers `.dc.html` et `canvas.json` du canevas Design ; écran 7 « Dechire » = accueil et papier déchiré).

## Code
- `app/index.html` : application complète (HTML, CSS et JS vanilla, aucun build). Elle charge `data/articles.json` (92 articles du corpus validé, issu de `articles-runtime.json`). Serveur local : `node .claude/serve.js` (PORT=5173 par défaut).
- PWA : `app/manifest.webmanifest`, `app/sw.js` (cache de l’appli, des données et des polices Google, stratégie cache d’abord ; changer `VERSION` dans sw.js à chaque livraison), `app/icons/`. Retour du téléphone géré par `pushIfHome`/`goHome`/`popstate`.
- État du lecteur : `localStorage`, clé `jadis.v1` (`{ read: [], saved: [] }`). Une histoire est « lue » quand le repère `#endmark` entre dans l'écran (IntersectionObserver).
- Fonctions clés : `pickN(currentId, n)` (choix des indices), `surprisePick`, `chooseHook` (écran de transition date et lieu), `runSplash` (animation d'ouverture), `toggleSpeech`.
- `app/articles.json` : 150 articles dans la version publiée (champs : id, titre, hook, epoque, continent, annee, lat, lon, lieu, theme, date{pre,big,post}, paragraphes[], anecdote, mots).
- Publié : https://claude.ai/artifact/FfQbzNemmwYcZ52Ft8xqhM (deux fichiers : index.html et articles.json).

## Corpus et vérification
Chaîne de production : fiche de faits (chaque fait étiqueté établi, source unique ou contesté, avec ses sources) → article écrit uniquement à partir de la fiche → relecture indépendante qui rouvre les sources → statut `validé` / `à_recouper` / `rejeté`.
- `corpus/INSTRUCTIONS.md` : consignes du rédacteur. `corpus/REVIEW_INSTRUCTIONS.md` : consignes du relecteur.
- `corpus/topics.py` : 500 sujets-graines (100 par époque, répartition par continent fixée). `corpus/mk_lot2.py` : tirage d'un lot.
- `corpus/data/jadis_articles_lots_1_et_2.json` : 49 articles du lot 1 relus (24 validés, 25 à recouper) et 25 articles du lot 2 écrits, pas encore relus. Chaque fichier garde ses faits, sources, divergences et le champ `revue`.
- Constats de relecture : les rédacteurs durcissent les chiffres, ajoutent des détails absents des sources, et beaucoup de faits « établis » reposent sur Wikipédia et ses miroirs. La relecture indépendante est indispensable.
- Attention : le fichier `articles.json` publié (150 articles) ne vient pas uniquement de ces lots. Vérifier d'où viennent ses articles et leur statut de vérification avant de le considérer comme validé.

## Style éditorial (skill `journaliste-historien`)
Reportage d'historien : attaque concrète, pivot qui dit pourquoi c'est important, démarche racontée étape par étape, fin sans morale. Peu de « selon X » dans le texte (les attributions vivent dans la fiche), peu de chiffres, rythme varié, lu à voix haute. Un raccourci populaire n'est jamais repris comme un fait. Détail : voir le skill dans le compte claude.ai.

## À faire
1. PWA : fait (manifeste, icônes, service worker, hors ligne). Reste : hébergement HTTPS sur un domaine à soi (dossier `app/` tel quel).
2. Audio français : comparer des voix neuronales, lexique de prononciation (noms propres), fichiers pré-générés pour les articles validés seulement.
3. Algorithme de préférence : signaux supplémentaires (temps passé, articles gardés, écoute), en gardant la règle « jamais un article lu ».
4. Corpus : terminer la relecture des lots, réécrire les textes sous 380 mots, trancher les moai (étiquette « Vers 1250 » non étayée), brancher seulement les articles validés.
5. Tests : l'ancien script Playwright ciblait une version antérieure de l'appli (boutons `data-go`) ; en écrire un nouveau (boutons `data-hook`).
