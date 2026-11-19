# État actuel (au 2026-11-19)

Dernier commit sur `origin/main` : `26c777a` (corpus par rejeu, M7.6).

**Flux de travail :** aucun commit direct sur `main` ni sur `develop`. `develop` est
la branche d'intégration créée le 2026-11-19 depuis `main` (ADR-0009) ; `main` ne
reçoit que des PR depuis `develop`. Chaque changement part d'une branche de sujet
(`feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`), puis d'une PR relue et
fusionnée en squash (voir `CONTRIBUTING.md`).

**En attente de revue :** PR #30 (M7.7), #31 (mémoires M7.7), #32 (flux `develop`),
#33 (M7.8, empilée sur la branche de la PR #30), et issue #29. Rien n'a été poussé
directement sur `main` ni sur `develop` ; toutes les branches de sujet sont poussées
sur `origin`.

## Ce qui fonctionne

- **Noyau logique (M1) :** Datalog stratifié (AXL), preuves, statuts épistémiques E1 à E8 (PROUVÉ, VÉRIFIÉ, CONFIRMÉ, PLAUSIBLE, NON VÉRIFIÉ, CONTESTÉ, RÉFUTÉ), révision des croyances.
- **Conversation en streaming :** l'équipe Analyste, Planificateur, Vérificateur, Chercheur, Rédacteur, Relecteur, avec un flux d'événements `Thinking`, `Searching`, `SourceFound`, `Say` et `Done`.
- **Paquets de langue FR/EN :** lexique relié aux concepts, morphologie (articles, élisions, pluriels y compris des noms composés), gabarits, schémas d'intention, règles de style.
- **Niveau adaptatif** par domaine (débutant, intermédiaire, expert).
- **Recherche web sans clé :** Wikipédia (introductions complètes), DuckDuckGo, OpenAlex en mode approfondi. Brave, Google CSE et SearXNG sont pris en charge avec une clé, mais jamais testés en réel faute de clé. Les pages d'homonymie sont détectées.
- **Wikidata (ADR-0008) :** apprentissage des classes, des noms FR/EN et du genre (via les Lexemes). Les chemins de classification sont trouvés à la demande, jusqu'à 20 rangs : « le lion est-il un oiseau ? » donne « Non » par déduction. Option `axiome --learn`.
- **Raisonnement :** oui/non sur les classes et les propriétés, prérequis, « pourquoi » par la chaîne de déduction, prémisses fausses corrigées, comparaison, choix d'un patron de conception.
- **Calcul exact** sur des fractions, enchaîné (« et fois 3 ? »). Date et heure.
- **Suivi du fil :** relances (« et le tri rapide ? »), questions sans sujet (« est-il un mammifère ? »), « pourquoi ? » seul, corrections, « développe », traduction FR↔EN, réponses aux questions qu'Axiome a posées (prénom, « la lettre L ? »).
- **Petite conversation :** salutations, « ça va », prénom mémorisé, limites, rires, hésitations, bruit clavier.
- **Outils de code (M7.0 à M7.8) :** lecture déterministe d'un dépôt, extraction en faits Datalog, index interrogeable (`?- defines(Pos, Nom).`), 10 000 lignes indexées en 303 ms.
  - **Analyse :** 8 règles nommées, chacune adossée à des faits et à une position ; seuil et règles réglés dans `[tool.axiome.code]`.
  - **Revue :** un diff est appliqué en mémoire, seuls les constats nouveaux sont retenus et passent par le `Reviewer` existant. `axiome --analyze` et `axiome --review`.
  - **Bac à sable :** copie temporaire, délai, limites `resource`, sortie plafonnée, environnement vidé, réseau coupé si `unshare -n` est disponible (sinon signalé comme dégradé). `PYTHONPATH` pointe vers la copie (`src` puis racine) : sans cela, les tests d'un projet importaient le paquet installé en editable et la mesure portait sur le dépôt réel.
  - **Génération :** recherche bornée de mutations (littéraux, booléens, comparaisons, `not`, opérateurs binaires, `and`/`or`, négation de condition), chaque candidat jugé par les tests du projet ; `pass@1` 16/16 sur le banc, 0 échec silencieux. M7.7 compose jusqu'à `depth` éditions sur des lignes distinctes et ouvre `extra_targets` : un patch multi-fichiers est assemblé puis soumis aux tests, avec un budget partagé et un parcours en largeur déterministe.
  - **Banc par rejeu :** trois vrais commits (`evals/code/replay/`). L'arbre du commit correctif est extrait, ses fichiers source sont ramenés à leur version parente, ses tests doivent échouer, puis la recherche peut éditer un fichier cible. Le patch attendu n'est jamais lu ; une tâche déjà verte est une erreur d'intégrité. Mesure : **0/3**, dont une tâche multi-fichiers. M7.8 permet au manifeste de régler `depth` et `extra_targets` ; avec `depth: 2`, les fichiers `.py` supplémentaires et un budget porté à 16, le score reste **0/3** (toutes les tâches finissent en `budget_exhausted`).

## Scores

| Banc | Score | Remarque |
|---|---|---|
| `evals/suites/` (travail, 138 cas) | 138/138 | Ces cas ont servi à corriger : ce score surestime le niveau réel. |
| `evals/heldout/` (réservé, 62 cas) | 62/62 | Mesures honnêtes, prises avant correction : 38/42 (90 %), puis 19/20 (95 %) pour les conversations. |
| `evals/code/generation.jsonl` (banc de génération) | 16/16 | Dont deux éditions sur un fichier et deux éditions sur deux fichiers ; 0 échec silencieux. |
| `evals/code/replay/` (rejeu de commits réels) | 0/3 | Correctifs réels, dont un multi-fichiers : 0/3 aux budgets 4 et 16, même avec `depth: 2` et les fichiers supplémentaires. |
| Tests | 353 verts, couverture 95,66 % | ruff et mypy strict propres ; `make check` vert sur la branche de la PR #33 |

L'historique détaillé des scores est dans `evals/README.md`.

## Limites connues

- **Savoir étroit.** Il se limite à une centaine de concepts saisis à la main, plus ce que Wikidata apprend à la demande. Les bases des langues et du bon sens manquent encore : Wiktionary et ConceptNet sont prévus.
- **Wikidata lent au premier contact.** Comptez 10 à 30 s par sujet, à cause du freinage par Wikimedia (HTTP 429). La variable facultative `AXIOME_CONTACT` permettrait d'aller plus vite. Le mainteneur n'a pas encore donné de contact, et il ne faut pas en inventer.
- **Qualité de Wikidata.** Certaines classes sont surprenantes (« l'étoile est un fuseur »). Ces faits restent PLAUSIBLES.
- **Article des noms propres non humains.** « le Soleil » doit être revérifié depuis la restriction du nom propre sans article aux personnes.
- **Suivi du fil limité.** Il couvre les formes de relance prévues. Une tournure inédite peut encore égarer Axiome. Il ne remonte pas au-delà de la dernière question.
- **Génération de code volontairement étroite.** Elle ne cherche que de petites mutations déterministes, désormais composables sur plusieurs fichiers ; sans test exécutable, elle refuse. Le parcours en largeur dépense d'abord le budget dans les éditions simples : une composition profonde n'est atteinte que s'il reste des tentatives. Sur trois correctifs réels, le banc par rejeu donne toujours 0/3, y compris à seize candidats avec une profondeur de deux et les fichiers supplémentaires. Ce n'est pas encore un assistant de programmation généraliste.
- **Isolation réseau non portable.** `unshare -n` n'existe pas partout ; sans lui le rapport dit « réseau non isolé » au lieu de prétendre le contraire.
- **Analyse Python seulement.** Les autres langages demanderont un analyseur externe déclaré (RFC-0002, question ouverte 1).
- **Faux positifs possibles de `code_mort`/`nom_non_utilise`** sur une API publique sans `__all__` ni import interne ; ce sont des remarques, jamais des blocages.
- La conversation libre reste limitée aux schémas connus (M4 pour l'aisance).
