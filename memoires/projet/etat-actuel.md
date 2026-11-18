# État actuel (au 2026-11-18)

Dernier commit sur `origin/main` : `59ddd16` (RFC-0002 à jour, M7.0 à M7.4).

**Flux de travail :** aucun commit direct sur `main`. Chaque changement part d'une
branche (`feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`), puis d'une PR relue et
fusionnée en squash (voir `CONTRIBUTING.md`).

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
- **Outils de code (M7.0 à M7.5) :** lecture déterministe d'un dépôt, extraction en faits Datalog, index interrogeable (`?- defines(Pos, Nom).`), 10 000 lignes indexées en 303 ms.
  - **Analyse :** 8 règles nommées, chacune adossée à des faits et à une position ; seuil et règles réglés dans `[tool.axiome.code]`.
  - **Revue :** un diff est appliqué en mémoire, seuls les constats nouveaux sont retenus et passent par le `Reviewer` existant. `axiome --analyze` et `axiome --review`.
  - **Bac à sable :** copie temporaire, délai, limites `resource`, sortie plafonnée, environnement vidé, réseau coupé si `unshare -n` est disponible (sinon signalé comme dégradé).
  - **Génération :** recherche bornée de mutations (littéraux, booléens, comparaisons, `not`, opérateurs binaires, `and`/`or`, négation de condition), chaque candidat jugé par les tests du projet ; `pass@1` 14/14 sur le banc, 0 échec silencieux.
  - **Banc tenu à l'écart :** rejeu de vrais commits (`evals/code/heldout.jsonl`). La recherche part de l'arbre parent, seuls les tests du commit correctif sont révélés, le patch attendu n'est jamais lu, et une tâche déjà verte est rejetée comme erreur d'intégrité. Mesure : 0/1 — l'historique ne fournit qu'une tâche propre, et la recherche ne sait pas encore traiter un correctif réel.

## Scores

| Banc | Score | Remarque |
|---|---|---|
| `evals/suites/` (travail, 138 cas) | 138/138 | Ces cas ont servi à corriger : ce score surestime le niveau réel. |
| `evals/heldout/` (réservé, 62 cas) | 62/62 | Mesures honnêtes, prises avant correction : 38/42 (90 %), puis 19/20 (95 %) pour les conversations. |
| `evals/code/heldout.jsonl` (rejeu de commits réels) | 0/1 | Une seule tâche propre dans l'historique ; le reste demande du multi-fichiers. |
| Tests | 341 verts, couverture 95,5 % | ruff et mypy strict propres ; couche `code/` de 89 à 100 % |

L'historique détaillé des scores est dans `evals/README.md`.

## Limites connues

- **Savoir étroit.** Il se limite à une centaine de concepts saisis à la main, plus ce que Wikidata apprend à la demande. Les bases des langues et du bon sens manquent encore : Wiktionary et ConceptNet sont prévus.
- **Wikidata lent au premier contact.** Comptez 10 à 30 s par sujet, à cause du freinage par Wikimedia (HTTP 429). La variable facultative `AXIOME_CONTACT` permettrait d'aller plus vite. Le mainteneur n'a pas encore donné de contact, et il ne faut pas en inventer.
- **Qualité de Wikidata.** Certaines classes sont surprenantes (« l'étoile est un fuseur »). Ces faits restent PLAUSIBLES.
- **Article des noms propres non humains.** « le Soleil » doit être revérifié depuis la restriction du nom propre sans article aux personnes.
- **Suivi du fil limité.** Il couvre les formes de relance prévues. Une tournure inédite peut encore égarer Axiome. Il ne remonte pas au-delà de la dernière question.
- **Génération de code volontairement étroite.** Elle ne cherche que de petites mutations déterministes sur **un** fichier cible ; sans test exécutable, elle refuse. Sur un vrai correctif (`dc11b2b`), le banc tenu à l'écart donne 0/1 : le correctif réel demande plusieurs éditions et parfois plusieurs fichiers. Ce n'est pas encore un assistant de programmation généraliste.
- **Isolation réseau non portable.** `unshare -n` n'existe pas partout ; sans lui le rapport dit « réseau non isolé » au lieu de prétendre le contraire.
- **Analyse Python seulement.** Les autres langages demanderont un analyseur externe déclaré (RFC-0002, question ouverte 1).
- **Faux positifs possibles de `code_mort`/`nom_non_utilise`** sur une API publique sans `__all__` ni import interne ; ce sont des remarques, jamais des blocages.
- La conversation libre reste limitée aux schémas connus (M4 pour l'aisance).
