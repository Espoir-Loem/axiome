# État actuel (au 2026-11-11)

Dernier commit : `11789d2`. La branche locale `main` a divergé de `origin/main`. Le push doit être fait par le mainteneur :
`git push --force-with-lease origin main`.

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

## Scores

| Banc | Score | Remarque |
|---|---|---|
| `evals/suites/` (travail, 138 cas) | 138/138 | Ces cas ont servi à corriger : ce score surestime le niveau réel. |
| `evals/heldout/` (réservé, 62 cas) | 62/62 | Mesures honnêtes, prises avant correction : 38/42 (90 %), puis 19/20 (95 %) pour les conversations. |
| Tests | tous verts, couverture 97 % | ruff et mypy strict propres |

L'historique détaillé des scores est dans `evals/README.md`.

## Limites connues

- **Savoir étroit.** Il se limite à une centaine de concepts saisis à la main, plus ce que Wikidata apprend à la demande. Les bases des langues et du bon sens manquent encore : Wiktionary et ConceptNet sont prévus.
- **Wikidata lent au premier contact.** Comptez 10 à 30 s par sujet, à cause du freinage par Wikimedia (HTTP 429). La variable facultative `AXIOME_CONTACT` permettrait d'aller plus vite. Le mainteneur n'a pas encore donné de contact, et il ne faut pas en inventer.
- **Qualité de Wikidata.** Certaines classes sont surprenantes (« l'étoile est un fuseur »). Ces faits restent PLAUSIBLES.
- **Article des noms propres non humains.** « le Soleil » doit être revérifié depuis la restriction du nom propre sans article aux personnes.
- **Suivi du fil limité.** Il couvre les formes de relance prévues. Une tournure inédite peut encore égarer Axiome. Il ne remonte pas au-delà de la dernière question.
- **Pas de génération de code** (M7). La conversation libre reste limitée aux schémas connus (M4 pour l'aisance).
