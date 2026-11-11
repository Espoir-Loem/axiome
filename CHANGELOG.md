# Journal des modifications

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/).

## [Non publié]
### Ajouté
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
