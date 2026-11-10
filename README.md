# Axiome

> IA **neuro-symbolique**, **déterministe**, **frugale** et **vérifiable**, construite de zéro, sans aucun modèle pré-entraîné.

Axiome raisonne au lieu de deviner. Chaque réponse est accompagnée :
- de sa **preuve**, c'est-à-dire l'arbre de déduction ;
- de son **statut épistémique** : `PROUVÉ`, `VÉRIFIÉ`, `CONFIRMÉ`, `PLAUSIBLE`, `NON VÉRIFIÉ`, `CONTESTÉ` ou `RÉFUTÉ` ;
- de ses **sources**.

Quand Axiome ne sait pas, il le dit. Il ne confond jamais « absence de preuve » et « preuve d'absence ».

```text
axiome> ?- est_un(chat, animal).
Oui  [PROUVÉ]

axiome> est_un(chat, oiseau).
Noté : est_un(chat, oiseau)

axiome> ?- est_un(chat, oiseau).
Non. est_un(chat, oiseau) est RÉFUTÉ :
  - viole la contrainte « classes_disjointes »
  - incompatible avec : disjoint(mammifère, oiseau), est_un(chat, mammifère)

axiome> ?- est_un(X, algorithme_de_tri), non a_propriete(X, stable).
X = tri_par_tas  [PLAUSIBLE]  (monde clos)
X = tri_rapide  [PLAUSIBLE]  (monde clos)
```

## Installation

Il faut Python ≥ 3.10. Le noyau n'a **aucune dépendance** et tourne sur n'importe quel PC, sans GPU ni connexion Internet.

```bash
pip install -e .
axiome            # REPL
axiome --memoire -c "?- est_un(X, patron_de_création)."
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
