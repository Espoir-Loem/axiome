# Architecture

## Vue d'ensemble (niveau C4 « conteneurs »)

```
            ┌──────────────────────────── axiome ────────────────────────────┐
 texte ───► │ cli ──► kernel ──┬──► reasoning (syntaxe, programme, moteur)   │
            │   ▲              ├──► verification (statuts, révision)         │
            │   │              ├──► knowledge (SQLite, graine)               │
            │ response ◄───────┘                                             │
            │                  M2+ : perception · research · engineering ·   │
            │                        tools · metacog                         │
            └────────────────────────────────────────────────────────────────┘
```

## Règles de dépendance
Les couches basses ne connaissent jamais les couches hautes. Un test d'architecture le vérifiera à partir de M2.

```
core  ◄──  reasoning  ◄──  verification  ◄──  knowledge  ◄──  kernel  ◄──  response, cli
```

- `core` : erreurs, configuration, horloge. Ne dépend de rien.
- `reasoning` : logique pure, sans E/S ni horloge.
- `verification` : statuts épistémiques et révision des croyances (utilise `reasoning`).
- `knowledge` : persistance. Ne raisonne pas.
- `kernel` : seule façade publique ; orchestre les couches inférieures.
- `response`, `cli` : présentation uniquement.

## Flux d'une requête (M1)

1. La `cli` reçoit `?- est_un(chat, X).`
2. `kernel.ask` analyse la requête (`reasoning.syntax`).
3. Calcul de `kernel.state`, mis en cache et invalidé à chaque écriture :
   1. `knowledge.store.evidence()` fournit les faits et leurs preuves ;
   2. `verification.epistemic.assess` attribue un statut à chaque fait de base ;
   3. `verification.revision.revise` sature le programme (`reasoning.engine.evaluate`), détecte les violations de contraintes, réfute ou conteste les maillons faibles, puis itère ;
4. `Model.query` produit les réponses, et le statut de chacune est celui de son maillon le plus faible.
5. `response.render` produit un texte déterministe.

## Invariants
| Invariant | Garanti par |
|---|---|
| Terminaison | Datalog sans fonctions (RFC-0001) |
| Modèle unique | Programme sûr et stratifié (`Program.__post_init__`) |
| Déterminisme | Tris canoniques partout, horloge injectée, aucune itération sur un `set` non trié (`tests/determinism`) |
| Traçabilité | Chaque fait dérivé a une `Justification` et un arbre de preuve |
| Honnêteté épistémique | Plafond « monde clos » et plafond « hypothèse » (epistemologie.md §3) |
