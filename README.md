# Axiome

> IA **neuro-symbolique**, **déterministe**, **frugale** et **vérifiable**, construite de zéro, sans aucun modèle pré-entraîné.

Axiome est un assistant de conversation qui raisonne au lieu de deviner. Il explique un sujet à ton niveau, du débutant au professeur. Il vérifie une affirmation, apprend ce que tu lui enseignes et cherche sur le web quand il ne sait pas. Chaque phrase qu'il affiche repose sur un fait de sa base ou sur une source citée.

```text
axiome> comment vas-tu ?
Ça va bien, merci. Et toi ?
axiome> qu'est-ce qu'un trou noir ?
  Je ne le sais pas encore. Je cherche dans : Wikipedia et DuckDuckGo.
En astrophysique, un **trou noir** est un objet céleste si compact que l'intensité de son champ gravitationnel empêche toute forme de matière ou de rayonnement de s'en échapper. [1]

- De tels objets ne peuvent ni émettre, ni diffuser la lumière et sont donc noirs, ce qui revient à dire qu'ils sont invisibles. [1]
- Toutefois, plusieurs techniques d'observation indirecte dans différentes longueurs d'onde ont été mises au point et permettent d'étudier de nombreux phénomènes qu'ils induisent. [1]

Voir aussi : Le Trou noir et Trou noir supermassif.
Fiabilité : une seule source fiable pour l'instant, à recouper.

Sources :
[1] Wikipedia (fr), « Trou noir » : https://fr.wikipedia.org/wiki/Trou_noir
axiome> le chat est-il un oiseau ?
Non. Le chat est un mammifère, et rien ne peut être à la fois un mammifère et un oiseau.
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

Recherche web, sans clé : Wikipédia et DuckDuckGo, plus OpenAlex (articles scientifiques) en recherche approfondie (« fais des recherches sur… » ou niveau expert).

Pour chercher dans tout le web, il faut ajouter un moteur :
- Brave Search : `AXIOME_BRAVE_API_KEY`. C'est un index indépendant de tout le web, avec une offre gratuite ;
- Google : `AXIOME_GOOGLE_API_KEY` et `AXIOME_GOOGLE_CX` (Programmable Search, l'API officielle) ;
- SearXNG auto-hébergé : `AXIOME_SEARXNG_URL`. Il agrège Google, Bing, DuckDuckGo et d'autres. Par exemple : `docker run -p 8888:8080 searxng/searxng`, puis activer le format JSON dans sa configuration.

Avec un moteur web, Axiome lit les pages trouvées. Il recoupe ce qu'elles disent entre organisations différentes : une information devient « confirmée » quand des sources indépendantes la confirment.

Les réponses web sont mises en cache dans `$XDG_CACHE_HOME/axiome/web`.

### Connaissances apprises depuis Wikidata

Quand une question oui/non porte sur un concept inconnu, Axiome l'apprend sur Wikidata : ses classes, ses noms en français et en anglais, le genre des noms. Il raisonne ensuite dessus :

```
axiome> le lion est-il un oiseau ?
  Je ne connais pas encore lion. Je l'apprends sur Wikidata.
Non. Le lion est un mammifère, et rien ne peut être à la fois un mammifère et un oiseau.

Fiabilité : une seule source fiable pour l'instant, à recouper.
```

On peut aussi apprendre à l'avance, puis répondre hors ligne :

```bash
axiome --learn "trou noir" --learn "étoile"
```

Wikimedia limite le débit des clients qui ne donnent pas de contact. Pour un apprentissage plus rapide, ajoutez une adresse ou une URL de contact au User-Agent : `AXIOME_CONTACT="vous@exemple.org"`. Rien n'est envoyé si la variable est vide. Détails : [ADR-0008](docs/adr/0008-wikidata.md).

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
| M7 | Outils de code : analyse, revue, génération vérifiée | fait (M7.0 à M7.3) |

## Documentation

- [Vision](docs/vision.md) : objectifs et non-objectifs
- [Architecture](docs/architecture.md)
- [Épistémologie](docs/epistemologie.md) : spécification normative des statuts de vérité
- [ADR](docs/adr/) : décisions d'architecture · [RFC](docs/rfc/) : documents de conception
- [Mémoires](memoires/README.md) : état, décisions et raisonnement, pour reprendre le travail d'une session à l'autre
- [Contribuer](CONTRIBUTING.md) · [Sécurité](SECURITY.md)

## Développement

```bash
make venv     # environnement + outils
make check    # ruff + mypy --strict + pytest (couverture ≥ 90 %)
```

Licence : Apache-2.0.
