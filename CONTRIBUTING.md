# Contribuer à Axiome

## Flux de travail
1. **Une issue d'abord.** Tout changement non trivial part d'une issue. Un module majeur part d'une **RFC** (`docs/rfc/`) et une décision structurante d'un **ADR** (`docs/adr/`).
2. **Une branche par changement** : `feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`. On ne pousse jamais directement sur `main`.
3. **Petites PR** : moins de 400 lignes modifiées, hors données et tests, et un seul sujet par PR.
4. **Revue obligatoire** et CI verte avant toute fusion. On fusionne en *squash merge*.
5. **Mémoires à jour.** En fin de session, on met à jour `memoires/projet/etat-actuel.md` et `memoires/suite/feuille-de-route.md`, et on ajoute une entrée dans `memoires/sessions/` (voir `memoires/README.md`).

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
- Les phrases d'Axiome viennent des paquets `src/axiome/data/lang/<code>/`. Tout gabarit doit exister dans chaque langue (un test le vérifie) et ne contenir aucun signe IA ([docs/signes-ia.md](docs/signes-ia.md)). La même règle vaut pour la documentation : pas d'emoji de statut, pas de formules creuses.
- Commits et PR en anglais. **Aucun agent IA ni bot comme contributeur** : pas de ligne `Co-Authored-By` d'outil IA, pas de PR automatiques (Dependabot, Renovate…).
- Typage complet, `mypy --strict`.
- Fonctions pures dès que possible ; les E/S restent aux bords (`knowledge`, `cli`).
- Toute affirmation ajoutée à la graine cite sa source (voir `src/axiome/data/seed/README.md`).
