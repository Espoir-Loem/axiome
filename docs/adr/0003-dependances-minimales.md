# ADR-0003 : Dépendances minimales

- **Statut** : Accepté
- **Date** : 2026-11-10

## Décision
- Le noyau (M0, M1, M3 à M6) n'utilise que la **bibliothèque standard** de Python, SQLite compris.
- Le module `neural` (M2) pourra dépendre de **NumPy uniquement**, en dépendance optionnelle `axiome[neural]`. Le moteur de tenseurs et d'autodifférentiation est écrit dans le projet.
- Les outils de développement (pytest, hypothesis, ruff, mypy) sont dans l'extra `[dev]` et ne sont jamais requis à l'exécution.

## Options écartées
- **PyTorch, TensorFlow** : des centaines de Mo, contraires à la frugalité.
- **spaCy et modèles NLP** : ils embarquent des modèles pré-entraînés, ce que la vision interdit.

## Conséquences
- (+) `pip install axiome` fonctionne partout, en quelques secondes.
- (−) Plus de code à écrire et à tester soi-même.
