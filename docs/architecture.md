# Architecture

## Vue d'ensemble (niveau C4 « conteneurs »)

```
            ┌──────────────────────────────── axiome ────────────────────────────────┐
 texte ───► │ cli ──► dialogue.session ──► team : analyst ► planner ► verifier       │
            │  │         │  (événements)          researcher (web) ► writer ► reviewer│
            │  │         │                                                          │
            │  │         ├──► language (paquets FR/EN : lexique, morphologie, gabarits)
            │  │         ├──► perception (normalisation)                            │
            │  │         └──► research (fournisseurs, cache, extraction, BM25)      │
            │  └── logique ?- ──► kernel ──┬──► reasoning · verification · knowledge │
            └────────────────────────────────────────────────────────────────────────┘
```

## Règles de dépendance
Les couches basses ne connaissent jamais les couches hautes.

```
core ◄ reasoning ◄ verification ◄ knowledge ◄ kernel ◄ team ◄ dialogue ◄ cli
                  perception ◄ language ◄ team          research ◄ team
```

- `core` : erreurs, configuration, horloge. Ne dépend de rien.
- `reasoning` : logique pure, sans E/S ni horloge.
- `verification` : statuts épistémiques et révision des croyances (utilise `reasoning`).
- `knowledge` : persistance (faits, preuves, règles, mots appris, niveaux). Ne raisonne pas.
- `kernel` : façade du noyau logique.
- `perception`, `language` : texte → formes normalisées, mots ↔ concepts, concepts → phrases.
- `research` : accès web (stdlib uniquement), aucun raisonnement.
- `team` : les six rôles ; `dialogue` : session, niveau, événements.
- `response`, `cli` : présentation uniquement.

## Flux d'un tour de conversation (M2)

1. `Analyst` détecte les demandes de niveau, les levées de style, l'intention et les mentions (pronoms et suites de conversation compris).
2. Le profil de niveau du domaine est mis à jour.
3. `make_plan` décompose : macro (but), micro (aspects), atomique (requêtes), nano (statut de chaque fait).
4. `verify` exécute les requêtes sur l'état de croyance du noyau et écarte tout fait réfuté.
5. Sans connaissance locale, `Researcher` interroge les fournisseurs en parallèle. `digest` choisit l'extrait le mieux classé et compte les organisations qui le confirment. Le résultat est enregistré avec sa provenance.
6. `Writer` rédige au niveau voulu ; `Reviewer` bloque ou corrige chaque phrase ; chaque phrase validée est émise aussitôt.

## Flux d'une requête (M1)

1. La `cli` reçoit `?- is_a(cat, X).`
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
| Traçabilité | Chaque fait dérivé a une `Justification` et un arbre de preuve ; chaque phrase affichée cite ses faits ou ses sources (règle R1) |
| Honnêteté en conversation | Nuance obligatoire sous le statut CONFIRMÉ (R2), aucun signe IA (`docs/signes-ia.md`) |
| Honnêteté épistémique | Plafond « monde clos » et plafond « hypothèse » (epistemologie.md §3) |
