# Axiome

> IA **neuro-symbolique**, **déterministe**, **frugale** et **vérifiable**, construite de zéro, sans aucun modèle pré-entraîné.

Axiome est un assistant de conversation qui raisonne au lieu de deviner. Il explique un sujet à ton niveau, du débutant au professeur. Il vérifie une affirmation, apprend ce que tu lui enseignes et cherche sur le web quand il ne sait pas. Chaque phrase qu'il affiche repose sur un fait de sa base ou sur une source citée.

```text
axiome> qu'est-ce qu'un graphe ?
Le graphe est une structure de données. Exemples de graphes : l'arbre.
axiome> explique plus simplement
D'accord, je reprends plus simplement. Un graphe, c'est un ensemble de points reliés par des liens. Le graphe est une structure de données. Une structure de données, c'est une façon d'organiser des données en mémoire pour les retrouver et les modifier efficacement. Exemples de graphes : l'arbre.
axiome> le chat est-il un oiseau ?
Non. Le chat est un mammifère, et rien ne peut être à la fois un mammifère et un oiseau.
axiome> qu'est-ce qu'un photon ?
  Je ne le sais pas encore. Je cherche dans : Wikipedia.
  Je recoupe 1 source(s).
D'après Wikipedia (fr), en résumé : Le photon est … (plausible : une seule source fiable). Source : Wikipedia (fr) https://fr.wikipedia.org/wiki/Photon
```

Sous la conversation, le noyau logique reste accessible. Chaque réponse y est accompagnée :
- de sa **preuve**, c'est-à-dire l'arbre de déduction ;
- de son **statut épistémique** : `PROUVÉ`, `VÉRIFIÉ`, `CONFIRMÉ`, `PLAUSIBLE`, `NON VÉRIFIÉ`, `CONTESTÉ` ou `RÉFUTÉ` ;
- de ses **sources**.

Quand Axiome ne sait pas, il le dit. Il ne confond jamais « absence de preuve » et « preuve d'absence ». Il n'emploie aucune tournure typique des assistants IA ([docs/signes-ia.md](docs/signes-ia.md)).

```text
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
axiome --offline      # sans réseau : répond uniquement avec ce qu'il sait
```

Recherche web : Wikipédia est toujours disponible, sans clé. On peut ajouter d'autres moteurs par variables d'environnement :
- Google : `AXIOME_GOOGLE_API_KEY` et `AXIOME_GOOGLE_CX` (Programmable Search, l'API officielle) ;
- SearXNG auto-hébergé : `AXIOME_SEARXNG_URL`.

Les réponses web sont mises en cache dans `$XDG_CACHE_HOME/axiome/web`.

## État du projet

| Jalon | Contenu | État |
|---|---|---|
| M0 | Fondations : organisation, CI, documentation, `core/` | fait |
| M1 | Connaissance et logique : Datalog stratifié, preuves, statuts épistémiques, révision des croyances | fait |
| M2 | Conversation en streaming, paquets de langue FR/EN, niveau adaptatif, équipe interne | en cours |
| M3 | Équipe de recherche : Google, SearXNG, Wikipédia, Wikidata, arXiv, OpenAlex ; recoupement et apprentissage | socle fait |
| M4 | Réseaux maison (NumPy) : tokeniseur BPE, plongements, petit modèle de reformulation | à venir |
| M5 | Maths et physique : algèbre symbolique, analyse dimensionnelle | à venir |
| M6 | Méta-cognition : profil des types de questions, pré-recherche | à venir |
| M7 | Outils de code : analyse, revue, génération vérifiée | à venir |

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
