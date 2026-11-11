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

Catégories : arithmétique, code, honnêteté, connaissances, niveau, raisonnement, recherche, robustesse, petite conversation, heure et date.

## Historique des scores

| Date | Banc principal | Banc réservé | Changements |
|---|---|---|---|
| 2026-11-11 | 61/105 (58 %) | — | Point de départ. |
| 2026-11-11 | 105/105 | 38/42 (90 %) à la première mesure, 42/42 après | Calcul exact, date et heure, questions oui/non sur une propriété, prérequis, « pourquoi » expliqué par la chaîne de déduction, comparaison, choix d'un patron selon le besoin, « qui est », relances (« ses propriétés », « un exemple »), petite conversation élargie, bruit clavier, apostrophes manquantes. |

| 2026-11-11 | 111/111 | 42/42 | Cas relevés en usage réel : prénom donné en réponse, « mon nom c'est… », limites, pages d'homonymie. |

Le chiffre honnête est celui du banc réservé à sa **première** mesure : 90 %. Une fois ses échecs corrigés, il ne mesure plus la généralisation. Il faut alors écrire un nouveau banc réservé.

## Limites

Ces bancs mesurent ce qu'Axiome sait déjà faire, dans les domaines de sa base (biologie, structures de données, algorithmes, patrons de conception, grandeurs physiques). Ils ne le comparent pas à un grand modèle de langue. Axiome ne génère pas encore de code (jalon M7), et sa conversation libre reste limitée aux schémas connus (jalon M4 pour la fluidité).

`golden/` contient les sorties de référence attendues (tests de non-régression octet pour octet).
