# Journal des modifications

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/).

## [Non publié]
### Ajouté (évaluation)
- **Bancs d'évaluation** (`evals/`, `python -m axiome.evaluation`) : 105 cas de travail et 42 cas réservés, en français et en anglais, notés par catégorie, avec un rapport des échecs. Score : 61/105 au départ, puis 105/105 ; banc réservé à 38/42 (90 %) à sa première mesure.
- Calcul exact sur des fractions (« combien font 10 / 4 ? » donne 5/2, soit environ 2,5). Les opérations peuvent être écrites en mots (« fois », « divided by »). La division par zéro est signalée. Aucune exécution de code.
- Date et heure tirées de l'horloge (« quel jour sommes-nous ? », « what time is it? »). Pour la météo, Axiome dit qu'il n'y a pas accès.
- Questions oui/non sur une propriété (« le tri fusion est-il stable ? »). Réponse « Je ne sais pas » quand rien ne permet de l'établir.
- Prérequis (« la recherche dichotomique marche-t-elle sur une liste non triée ? » donne « Non. Elle exige une entrée triée. »).
- « Pourquoi » expliqué par la chaîne de déduction (« parce que le chat est un mammifère et les mammifères sont des vertébrés »). Une prémisse fausse est corrigée.
- Comparaison (« différence entre une pile et une file ») et choix d'un patron de conception d'après le besoin décrit.
- « Qui est… » et « pourquoi… » sur un sujet inconnu lancent une recherche.
- Relances sur le sujet en cours (« ses propriétés », « donne-moi un exemple »).
- Petite conversation : « salut, ça va ? », « t'es qui », « tu es une IA ? », « mdr », « hmm », « comment je m'appelle ? », « tu peux m'aider ? ».
- Le bruit clavier (« asdfghjkl ») et les demandes de code reçoivent une réponse honnête au lieu d'une recherche.
- Un fait appris de l'utilisateur est présenté comme tel (« Oui, d'après ce que tu m'as dit : … »). Les noms propres appris s'emploient sans article.

- Axiome retient qu'il vient de demander le prénom : « Espoir » seul est compris comme la réponse. Nouvelles formulations : « mon nom c'est… », « appelle-moi… », « my name's… ».
- « Quelles sont tes limites ? » : réponse honnête sur ce qu'Axiome ne sait pas faire.
- Pages d'homonymie : si la page qui porte le nom de la question est une page d'homonymie (« Le mot espoir peut désigner : »), Axiome dit que le mot a plusieurs sens et demande lequel. Il ne se rabat plus sur une page voisine sans rapport.

### Modifié
- Une question de définition commence par la définition quand Axiome en a une (« Un algorithme, c'est une suite finie d'instructions… »).
- Réponses mises en forme comme une bonne réponse humaine : phrase de tête qui résume (sujet en gras), détails en liste, une seule ligne de fiabilité, sources numérotées et citées [n]. Plus de « (plausible…) » répété dans chaque phrase.
- Wikipédia : lecture de l'introduction complète des articles. La page qui porte le titre de la question fournit la définition ; les autres pages du même site vont dans « Voir aussi ».

### Ajouté
- Messages incomplets (« h », « ? ») et questions coupées (« c'est quoi l ») : Axiome demande une précision au lieu de lancer une recherche.
- Correction des fautes de frappe sur le vocabulaire connu (« chta » → chat), annoncée dans la réponse.
- Petite conversation : « comment vas-tu », « ça va ? », « tu t'appelles comment », « je m'appelle… » (prénom mémorisé), « ok ». Une phrase qui s'adresse à Axiome ne déclenche jamais de recherche.
- Sources : DuckDuckGo (réponses instantanées), OpenAlex (recherche approfondie), Brave Search (`AXIOME_BRAVE_API_KEY`).
- **Conversation en streaming** (ADR-0007) : texte libre dans la CLI, session à événements (`dialogue/`), équipe interne Analyste, Planificateur, Chercheur, Vérificateur, Rédacteur, Relecteur (`team/`).
- **Paquets de langue FR/EN** (`data/lang/`) : lexique relié aux concepts, morphologie (articles, élisions, pluriels, contractions), gabarits de phrases, schémas d'intention. Les mots appris sont mémorisés (schéma de base v2).
- **Niveau adaptatif** débutant, intermédiaire ou expert, par domaine. Le contenu pour débutant est un sous-ensemble du contenu pour expert.
- **Recherche web** : Wikipédia (sans clé), Google Programmable Search et SearXNG (configurables), cache disque, extraction du texte principal, classement BM25, recoupement par organisation, apprentissage hors ligne.
- Réponse « Non » fondée sur les classes disjointes ; enseignement en langue naturelle (« Félix est un chat. »).
- `docs/signes-ia.md` : aucune tournure ni typographie typique des assistants IA, sauf demande explicite. Règle appliquée par le Relecteur et testée.
- Option `--offline` et variables `AXIOME_OFFLINE`, `AXIOME_GOOGLE_API_KEY`, `AXIOME_GOOGLE_CX`, `AXIOME_SEARXNG_URL`, `AXIOME_CACHE_DIR`.

### Retiré
- Dependabot : aucun bot ni agent IA ne doit apparaître comme contributeur. Les dépendances de développement sont mises à jour manuellement par les mainteneurs.

### Modifié
- Tout le code source est désormais en anglais (ADR-0005) : identifiants, commentaires, docstrings, messages d'erreur, vocabulaire de la base (`is_a`, `part_of`, `has_property`…) et mot-clé de négation `not`.
- Commandes CLI en anglais : `:proof`, `:conflicts`, `:rules`, `:help`, `:quit`, options `--memory` et `--command`.
### Ajouté
- Internationalisation : catalogues `locales/en.json` et `locales/fr.json`, option `--lang` et variable `AXIOME_LANG` (français par défaut).
- Test garantissant que les deux catalogues ont les mêmes clés et paramètres, et que chaque clé utilisée dans le code existe.

## [0.1.0] - 2026-11-10
### Ajouté
- **M0** : organisation du projet, CI multi-OS, porte de qualité (ruff, mypy --strict, couverture ≥ 90 %), ADR 0001 à 0004, vision, architecture.
- **M1** : langage logique AXL (Datalog stratifié, contraintes, règles étiquetées) et son analyseur.
- Moteur de saturation semi-naïf avec preuves canoniques, indépendantes de l'ordre d'insertion.
- Statuts épistémiques (règles E1 à E8) et révision des croyances (maillon faible, plafonds « hypothèse » et « monde clos », réfutation des contradictions).
- Base de connaissances SQLite avec provenance, et graine curée (taxonomie, structures de données, algorithmes, patrons de conception, SOLID, grandeurs SI).
- CLI : REPL et mode commande déterministe.
