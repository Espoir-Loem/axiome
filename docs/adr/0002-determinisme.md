# ADR-0002 : Déterminisme comme exigence de premier rang

- **Statut** : Accepté
- **Date** : 2026-11-10

## Décision
1. Aucune source d'aléa à l'exécution. Les entraînements (M2) utilisent une graine fixe, et leurs poids sont versionnés avec une empreinte SHA-256.
2. Tout parcours de collection passe par un **ordre canonique** (`Atom.sort_key`) ; on n'itère jamais sur un `set` ou un `dict` dont l'ordre dépend de l'historique.
3. Le temps n'est lu qu'à travers `core.clock.Clock`. Les horodatages sont des métadonnées et n'interviennent jamais dans un raisonnement.
4. Pas de flottants dans la logique, car leur arithmétique varie selon la plateforme. Les constantes sont des chaînes ou des entiers. La physique (M4) utilisera `fractions.Fraction` et l'arithmétique d'intervalles.
5. Le test `tests/determinism` exécute un scénario dans plusieurs processus avec des `PYTHONHASHSEED` différents et exige une sortie identique.

## Conséquences
- (+) Reproductibilité scientifique, débogage trivial, tests « golden » possibles.
- (−) Légère perte de performance due aux tris systématiques, acceptable à l'échelle visée.
