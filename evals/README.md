# Bancs d'évaluation

Axiome est évalué comme on évalue un modèle avant sa sortie : des cas fixes, une note par catégorie et un rapport des échecs. Une régression bloque la fusion (le test `tests/integration/test_evaluation.py` exige 100 % sur les deux bancs).

## Lancer

```
python -m axiome.evaluation evals            # banc principal  -> evals/reports/latest.md
python -m axiome.evaluation evals heldout    # banc réservé    -> evals/reports/heldout.md
```

Tout tourne hors ligne et de façon déterministe :
- l'heure est fixée au 11 novembre 2026, 9 h 30 UTC ;
- la recherche web répond à partir de documents enregistrés (`fixtures/web.json`). La clé est la question normalisée, avec un préfixe de langue facultatif (`en:photon`).

## Les deux bancs

| Banc | Rôle |
|---|---|
| `suites/` | Banc de travail : on corrige les échecs en le regardant. |
| `heldout/` | Banc réservé : écrit **avant** de corriger et jamais consulté pendant les corrections. Il mesure si une correction se généralise au lieu de coller aux cas pour lesquels elle a été écrite. |

Un cas est une ligne JSON :

```json
{"id": "smalltalk-fr-001", "category": "smalltalk", "lang": "fr",
 "setup": ["je m'appelle Espoir"], "turn": "salut",
 "expect": {"contains": ["Espoir"], "no_search": true}}
```

Contrôles : `contains`, `not_contains`, `any_of`, `starts_with`, `equals`, `no_search`, `searches`, `max_chars`. Deux contrôles s'appliquent toujours : aucun signe IA (`docs/signes-ia.md`) et aucun plantage.

Catégories : arithmétique, code, contexte (conversations à plusieurs tours), honnêteté, connaissances, niveau, raisonnement, recherche, robustesse, petite conversation, heure et date.

## Historique des scores

| Date | Banc principal | Banc réservé | Changements |
|---|---|---|---|
| 2026-11-11 | 61/105 (58 %) | — | Point de départ. |
| 2026-11-11 | 105/105 | 38/42 (90 %) à la première mesure, 42/42 après | Calcul exact, date et heure, questions oui/non sur une propriété, prérequis, « pourquoi » expliqué par la chaîne de déduction, comparaison, choix d'un patron selon le besoin, « qui est », relances (« ses propriétés », « un exemple »), petite conversation élargie, bruit clavier, apostrophes manquantes. |

| 2026-11-11 | 111/111 | 42/42 | Cas relevés en usage réel : prénom donné en réponse, « mon nom c'est… », limites, pages d'homonymie. |
| 2026-11-11 | 138/138 | 62/62 ; conversations : 19/20 (95 %) à la première mesure | Suivi du fil : relances, questions sans sujet, « pourquoi ? », corrections, « développe », traduction, calcul enchaîné. Banc `context` : 5/24 au départ. |

Le chiffre honnête est celui du banc réservé à sa **première** mesure : 90 %. Une fois ses échecs corrigés, il ne mesure plus la généralisation. Il faut alors écrire un nouveau banc réservé.

## Bancs de code (`evals/code/`)

Séparés des bancs de conversation, ils mesurent les outils de code de la RFC-0002.

```
python -m pytest tests/integration/test_code_bench.py
python -m pytest tests/integration/test_code_replay.py
```

- `review.jsonl` : 5 changements étiquetés à la main. Le score est donné **par règle** (précision et rappel) : une règle qui crie au loup ne peut pas être masquée par une moyenne.
- `generation.jsonl` : petites tâches avec tests, notées en `pass@1`. Le taux d'échecs *silencieux* (patch annoncé correct alors que les tests échouent) doit rester à zéro ; il l'est par construction, puisque l'acceptation dépend de l'exécution réelle.
- `replay/` : rejeu de **vrais commits** de ce dépôt, à l'envers. L'arbre du commit correctif est extrait, les fichiers source qu'il a modifiés sont ramenés à leur version parente, puis ses tests sont lancés : ils doivent échouer. La recherche peut alors modifier un fichier cible et est jugée par ces mêmes tests. Le patch attendu n'est jamais lu ; une tâche déjà verte est une erreur d'intégrité, pas un succès gratuit.

Mesure actuelle : revue 5/5, précision et rappel 1,0 par règle ; génération 16/16, 0 échec silencieux ; rejeu de commits réels **0/3** au budget de quatre candidats. Les tâches `two-constants` et `two-files` portent `depth` et `extra_targets`, avec un budget propre : elles ne passent qu'avec un patch composé soumis aux tests.

Le harnais de rejeu sait aussi lire `depth` et `extra_targets` depuis un manifeste, sans changer les manifestes livrés. Une mesure ad hoc avec `depth: 2` et les fichiers `.py` supplémentaires des commits, aux budgets 4 et 16, donne toujours **0/3** : les trois tâches finissent en `budget_exhausted`, aucun patch n'est accepté. La composition seule ne comble donc pas l'écart entre le banc de génération et de vrais correctifs.

Une deuxième mesure, avec l'ordre des candidats guidé par les identifiants du test qui échoue, donne également **0/3** aux budgets 4 et 16. Les échecs observés demandent tous d'ajouter du code : de nouvelles familles de mutation dans `generate.py`, une fonction `edit_distance` dans `lexicon.py`, un bonus de titre dans `digest`. Le banc distingue ainsi deux limites : l'ordre des candidats, réglé ici, et l'absence de synthèse de code, qui reste entière. Mesure du 2026-11-20 sur l'arbre intégré `6aff4dd` (PR #35), avec `python -m pytest tests/integration/test_code_replay.py` et le script de mesure décrit plus haut. Mesure du 2026-11-19 sur l'arbre intégré `4faa86d` (PR #33) : appel direct à `generate(..., budget=4 ou 16, depth=2, extra_targets=fichiers .py modifiés)` sur les trois cas de `evals/code/replay/`, après vérification que leurs tests échouent avant mutation. Les branches empilées ont été rebasées lors de l'intégration ; ces empreintes désignent les commits squash sur `develop`, au contenu identique.

Les trois tâches sont `dc11b2b` (préférence pour la page homonyme), `b2ce7c6` (familles de mutation) et `1e193e2` (entrée incomplète, cinq fichiers). `0/3` ne dit pas que la recherche est mauvaise : il dit qu'elle ne sait pas encore traiter un correctif réel, qui demande plusieurs éditions et parfois plusieurs fichiers. Ajouter une tâche ne demande aucune ligne de code : un dossier dans `evals/code/replay/`, un `manifest.json` (`id`, `commit`, `target`, `tests`, `changed`, `summary`, plus les facultatifs `depth` et `extra_targets`) et les versions parentes des fichiers reversés.

Attention au sens de lecture : ce banc rejoue des commits **du dépôt courant**, donc il mesure aussi sa propre infrastructure. La première version donnait `0/1` pour une mauvaise raison — le bac à sable laissait `import axiome` résoudre le paquet installé (`-e .`) au lieu de l'arbre copié. `PYTHONPATH` pointe désormais vers la copie, et un test dédié verrouille ce comportement.

## Limites

Ces bancs mesurent ce qu'Axiome sait déjà faire, dans les domaines de sa base (biologie, structures de données, algorithmes, patrons de conception, grandeurs physiques). Ils ne le comparent pas à un grand modèle de langue. La génération de code est volontairement étroite (petites mutations, désormais composables sur plusieurs fichiers, Python seulement), et la conversation libre reste limitée aux schémas connus (jalon M4 pour la fluidité).

`golden/` contient les sorties de référence attendues (tests de non-régression octet pour octet).
