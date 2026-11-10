# Axiome

> IA **neuro-symbolique**, **déterministe**, **frugale** et **vérifiable**, construite de zéro, sans aucun modèle pré-entraîné.

Axiome raisonne au lieu de deviner. Chaque réponse est accompagnée :
- de sa **preuve**, c'est-à-dire l'arbre de déduction ;
- de son **statut épistémique** : `PROUVÉ`, `VÉRIFIÉ`, `CONFIRMÉ`, `PLAUSIBLE`, `NON VÉRIFIÉ`, `CONTESTÉ` ou `RÉFUTÉ` ;
- de ses **sources**.

Quand Axiome ne sait pas, il le dit. Il ne confond jamais « absence de preuve » et « preuve d'absence ».

```text
axiome> ?- is_a(cat, animal).
Oui  [PROUVÉ]

axiome> is_a(cat, bird).
Noté : is_a(cat, bird)

axiome> ?- is_a(cat, bird).
Non. is_a(cat, bird) est RÉFUTÉ :
  - viole la contrainte « disjoint_classes »
  - incompatible avec : disjoint(mammal, bird), is_a(cat, mammal)

axiome> ?- is_a(X, sorting_algorithm), not has_property(X, stable).
X = heapsort  [PLAUSIBLE]  (monde clos)
X = quicksort  [PLAUSIBLE]  (monde clos)
```

## Installation

Il faut Python ≥ 3.10. Le noyau n'a **aucune dépendance** et tourne sur n'importe quel PC, sans GPU ni connexion Internet.

```bash
pip install -e .
axiome            # REPL
axiome --memory -c "?- is_a(X, creational_pattern)."
axiome --lang en      # interface en anglais (défaut : français, ou $AXIOME_LANG)
```

## État du projet

| Jalon | Contenu | État |
|---|---|---|
| M0 | Fondations : organisation, CI, documentation, `core/` | ✅ |
| M1 | Connaissance + logique : Datalog stratifié, preuves, statuts épistémiques, révision des croyances | ✅ |
| M2 | Réseaux de neurones maison (tokeniseur BPE, intention, entités) | ⏳ |
| M3 | Recherche scientifique multi-échelle (macro, micro, atomique, nano) | ⏳ |
| M4 | Maths et physique : algèbre symbolique, analyse dimensionnelle | ⏳ |
| M5 | Ingénierie logicielle : analyse AST, revue, génération vérifiée | ⏳ |
| M6 | Méta-cognition : profil utilisateur, clarification | ⏳ |

## Documentation

- [Vision](docs/vision.md) : objectifs et non-objectifs
- [Architecture](docs/architecture.md)
- [Épistémologie](docs/epistemologie.md) : spécification normative des statuts de vérité
- [ADR](docs/adr/) : décisions d'architecture · [RFC](docs/rfc/) : documents de conception
- [Contribuer](CONTRIBUTING.md) · [Sécurité](SECURITY.md)

## Développement

```bash
make venv     # environnement + outils
make check    # ruff + mypy --strict + pytest (couverture ≥ 90 %)
```

Licence : Apache-2.0.
