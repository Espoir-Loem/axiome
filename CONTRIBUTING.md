# Contribuer à Axiome

## Flux de travail
1. **Une issue d'abord.** Tout changement non trivial part d'une issue. Un module majeur part d'une **RFC** (`docs/rfc/`) et une décision structurante d'un **ADR** (`docs/adr/`).
2. **Une branche par changement** : `feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`. On ne pousse jamais directement sur `main`.
3. **Petites PR** : moins de 400 lignes modifiées, hors données et tests, et un seul sujet par PR.
4. **Revue obligatoire** et CI verte avant toute fusion. On fusionne en *squash merge*.

## Commits
[Conventional Commits](https://www.conventionalcommits.org/), in English:
```
feat(reasoning): add stratified negation
fix(store): make evidence insertion idempotent
```

## Porte de qualité (identique à la CI)
```bash
make check   # ruff + format + mypy --strict + pytest --cov (≥ 90 %)
```

## Exigences pour toute PR
- [ ] Tests ajoutés : unitaires, plus tests de propriétés si le changement touche un invariant.
- [ ] Déterminisme préservé : pas d'aléa, pas d'itération sur un `set` non trié, pas d'horloge directe.
- [ ] Aucune nouvelle dépendance d'exécution sans ADR (voir ADR-0003).
- [ ] `docs/epistemologie.md` mis à jour si `verification/` change.
- [ ] `CHANGELOG.md` mis à jour (section « Non publié »).

## Style
- **Tout le code source est en anglais** : identifiants, commentaires, docstrings, messages d'erreur et vocabulaire de la base (ADR-0005).
- Aucun texte affiché dans le code : passer par `axiome.i18n` (`t()` / `msg()`) et ajouter la clé dans **les deux** catalogues `src/axiome/locales/{en,fr}.json` (un test le vérifie).
- Commits et PR en anglais. **Aucun agent IA comme co-auteur** : pas de ligne `Co-Authored-By` d'outil IA.
- Typage complet, `mypy --strict`.
- Fonctions pures dès que possible ; les E/S restent aux bords (`knowledge`, `cli`).
- Toute affirmation ajoutée à la graine cite sa source (voir `src/axiome/data/seed/README.md`).
