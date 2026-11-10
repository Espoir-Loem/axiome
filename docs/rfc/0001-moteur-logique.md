# RFC-0001 : Moteur logique et révision des croyances

- **Statut** : Implémenté (v0.1.0)
- **Jalon** : M1

## Objectif
Fournir un raisonnement **correct, complet, terminant et déterministe**, avec des preuves vérifiables, sur lequel tous les autres modules s'appuieront.

## Langage (AXL)
Sous-ensemble de Datalog, avec :
- négation par l'échec **stratifiée** ;
- contraintes d'intégrité (`! nom :- corps.`) ;
- règles étiquetées (`[nom] tête :- corps.`) ;
- constantes : chaînes et entiers.

La grammaire EBNF figure dans `reasoning/syntax.py`.

**Pourquoi Datalog et non Prolog ?** Prolog n'est pas garanti de terminer : la récursion à gauche ou les symboles de fonction peuvent le faire boucler. Datalog, lui, possède un modèle unique et toujours calculable.

## Évaluation
- **Saturation ascendante semi-naïve, strate par strate.** Au tour *k*, seules les combinaisons de prémisses qui contiennent au moins un fait du delta du tour *k − 1* sont énumérées. La *i*-ème prémisse est prise dans le delta, les précédentes dans l'ancien état, les suivantes dans l'état complet. Chaque combinaison est ainsi énumérée exactement une fois.
- **Justification canonique.** Pour un fait donné, on garde la justification minimale selon (tour, indice de règle, clés des prémisses). Comme le tour d'apparition d'un fait ne dépend que de la profondeur de sa dérivation, cette justification est **indépendante de l'ordre d'insertion**, ce que vérifie un test de propriété.
- **Requêtes.** Conjonctions de littéraux évaluées sur le modèle matérialisé. Le chaînage arrière orienté but (tabulation SLG) est reporté (voir « Questions ouvertes »).

## Vérification
| Propriété | Test |
|---|---|
| Fermeture transitive égale à Floyd-Warshall | `property/test_engine_properties.py` |
| Invariance par permutation des faits (modèle **et** preuves) | idem |
| Toute preuve se termine sur des faits de base | idem |
| Aller-retour entre `str(atome)` et `parse` | idem |
| Programmes non sûrs ou non stratifiables rejetés | `unit/test_program.py` |

## Révision des croyances
Voir `docs/epistemologie.md` §3.

## Questions ouvertes
1. **Distinguer `instance_of` et `subclass_of`.** Aujourd'hui, tout passe par `is_a`.
2. **Chaînage arrière tabulé** pour les grandes bases, afin d'éviter de tout matérialiser.
3. **Statut d'un fait dérivé** calculé sur la meilleure preuve plutôt que sur la preuve canonique (point fixe max-min).
4. **Prédicats intégrés** (comparaisons, arithmétique exacte) pour M4.
