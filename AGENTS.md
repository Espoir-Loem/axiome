# Instructions aux agents

Ce fichier complète [CONTRIBUTING.md](CONTRIBUTING.md), qui fait foi en cas de doute.

## Branches et pull requests

- **Jamais de commit direct sur `main`.** Toute modification part d'une branche :
  `feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`. Après le clone, activer le
  garde-fou local avec `make hooks` : il refuse les pushes directs vers `main`.
- Une branche porte **un seul sujet**, puis une PR vers `main`, fusionnée en
  *squash merge* après revue et CI verte.
- Petites PR : moins de 400 lignes modifiées, hors données et tests.
- Un module majeur part d'une RFC (`docs/rfc/`) ; une décision structurante, d'un ADR
  (`docs/adr/`).

## Commits

- [Conventional Commits](https://www.conventionalcommits.org/), en anglais :
  `feat(reasoning): add stratified negation`.
- **Aucun agent IA ni bot comme contributeur** : pas de ligne `Co-Authored-By`
  d'outil IA, pas de pied de page d'attribution, pas de PR automatique.

## Avant de pousser

```bash
make check   # ruff + format + mypy --strict + pytest --cov (≥ 90 %)
```

Le déterminisme est un invariant : pas d'aléa, pas d'itération sur un `set` non trié,
pas d'horloge directe. Aucune dépendance d'exécution nouvelle sans ADR.

## Mémoires

En fin de session, mettre à jour `memoires/projet/etat-actuel.md` et
`memoires/suite/feuille-de-route.md`, et ajouter une entrée dans `memoires/sessions/`.
