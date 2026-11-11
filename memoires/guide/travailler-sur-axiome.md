# Travailler sur Axiome

## Commandes

```
cd /home/espoir-loemba/work/dev/axiome
.venv/bin/ruff check src tests
.venv/bin/ruff format src tests
.venv/bin/python -m mypy                     # src seulement, strict
.venv/bin/python -m pytest --cov=axiome      # couverture exigée : 90 % (actuelle : 97 %)
.venv/bin/python -m axiome.evaluation evals          # banc de travail
.venv/bin/python -m axiome.evaluation evals heldout  # banc réservé
.venv/bin/axiome                  # conversation en streaming
.venv/bin/axiome --offline        # sans web
.venv/bin/axiome --learn lion     # importer un concept depuis Wikidata
```

La porte de qualité à passer avant chaque commit : ruff check, ruff format, mypy, pytest. Les deux bancs doivent être à 100 % (`tests/integration/test_evaluation.py`).

## Conventions

- Code, identifiants et messages de commit en anglais. Documentation et `memoires/` en français.
- Aucun texte affiché en dur dans le code :
  - phrases d'Axiome : `src/axiome/data/lang/{fr,en}/grammar.json` ;
  - compréhension : `intents.json` ;
  - mots : `lexicon.json` ;
  - CLI : `src/axiome/locales/{fr,en}.json`.
- Toujours modifier les deux langues ensemble.
- Commits sous l'identité git configurée. Jamais de `Co-Authored-By` ni de mention d'IA.
- Ne pas pousser : le mainteneur pousse lui-même.
- Style : relire `docs/signes-ia.md` avant d'écrire du texte, y compris dans la doc.
- Réseau : seulement les API officielles. Pas d'aspiration de Google. Aucune donnée personnelle dans les requêtes.

## Méthode de travail qui a fait ses preuves

1. Reproduire l'échec signalé par le mainteneur dans un cas de banc ou un test.
2. Pour une nouvelle capacité, écrire d'abord des cas réservés et les mesurer une fois.
3. Corriger dans les données (motifs, gabarits) avant le code quand c'est possible.
4. Lire les vraies réponses, pas seulement le score.
5. Essayer en réel ce qui touche au web, avec un script dans le dossier temporaire de la session.
6. Mettre à jour `memoires/` (état, feuille de route, journal de session), le CHANGELOG et, si une décision d'architecture est prise, un ADR.
