# Architecture : d'une question à une réponse

Les identifiants sont ceux du code (anglais). Pour le détail de référence, voir `docs/architecture.md` et les ADR.

## Le trajet d'un message

```
texte ─► Analyst ─► (niveau) ─► handler par intention ─► Planner ─► Verifier ─► Writer ─► Reviewer ─► événements
            │                        │                                  ▲
            │                        └─► Researcher (web) ──────────────┤
            │                        └─► Librarian (Wikidata) ─► Kernel ┘
            └─ Context (sujet, dernière question, attente, dernier résultat)
```

1. **Analyst** (`team/analyst.py`). Il normalise le texte avec `fold()`, qui retire accents et majuscules sans changer la longueur : les positions restent alignées entre texte replié et texte d'origine. Il détecte ensuite les demandes de niveau, puis les messages reconnus d'un bloc (`_shortcut` : calcul, rire, hésitation) et retire une salutation de tête. Il cherche l'intention dans l'ordre des motifs du paquet de langue (`intents.json`). Certains motifs trop larges sont validés après coup (`_valid`) :
   - `check_property` exige que le mot soit un adjectif connu ;
   - `why_is_a` exige deux concepts connus.

   Enfin, il résout les mentions : lexique, puis correction de fautes (Damerau-Levenshtein), puis pronoms renvoyant au sujet en cours.
2. **Context.** C'est la mémoire de la conversation :
   - `topic` : le sujet en cours ;
   - `last` : la dernière question complète, réutilisée par les relances et les corrections ;
   - `expect` : ce qu'Axiome vient de demander (le prénom, une lettre), valable un seul tour ;
   - `last_result` : le dernier résultat de calcul.

   Une relance (`follow_up`) devient la dernière question appliquée au nouveau sujet (`_continue`).
3. **Session** (`dialogue/session.py`). Une table `_handlers` associe un traitement à chaque intention. C'est voulu : ruff limite la complexité à 12 par fonction, et une table reste lisible. Les réponses sont mises en lot puis relues ensemble (`_flush`), parce que la note de fiabilité couvre toute la réponse.
4. **Planner** (`team/planner.py`). Il décompose : but (MACRO), aspects (MICRO), une requête Datalog par aspect (ATOMIC), vérification de chaque fait (NANO).
5. **Verifier** (`team/verifier.py`). Il donne à chaque fait son statut épistémique et écarte les faits réfutés. Il fournit aussi `is_a_path` (chaîne la plus courte), `disjointness`, `base_facts` et `held`.
6. **Writer** (`team/writer.py`). Il met les faits en phrases selon le niveau. Rôles de phrase : LEAD (le résumé), POINT (liste), NOTE, SEE_ALSO, SOURCE, SOCIAL.
   - Un fait PLAUSIBLE n'est pas nuancé phrase par phrase (`covered=True`) : une seule note de fiabilité couvre la réponse.
   - Les faits plus faibles (NON VÉRIFIÉ, CONTESTÉ) gardent une nuance dans la phrase même.
7. **Reviewer** (`team/reviewer.py`). C'est la porte bloquante :
   - R1 : une phrase factuelle a un support ;
   - R2 : un fait sous CONFIRMÉ est nuancé ou couvert par la note ;
   - R3 : un fait réfuté n'est jamais affirmé ;
   - filtre de style S1 à S7 (`docs/signes-ia.md`), où S2 bloque la phrase.
8. **Researcher** (`team/researcher.py`). Il interroge les fournisseurs en parallèle dans un budget de temps et classe les phrases par BM25. Ensuite `digest()` choisit la page principale : celle qui porte le titre de la question, sauf si c'est une page d'homonymie. La phrase de définition sert de tête. Les autres pages du même site vont dans « Voir aussi », celles d'autres organisations corroborent.
9. **Librarian** (`knowledge/wikidata.py`). Il apprend depuis Wikidata (voir `decisions.md` et l'ADR-0008).
10. **Kernel** (`kernel.py`) et **KnowledgeStore** (`knowledge/store.py`, SQLite, schéma v3). Chaque fait a ses preuves et ses sources. Les mots appris sont stockés avec leur genre et leur caractère de nom propre.

## Pourquoi des règles et des données plutôt qu'un modèle

L'ADR-0006 interdit les modèles pré-entraînés. La justesse vient donc de la logique (déduction vérifiable) et des sources (provenance de chaque fait). L'étendue vient des données libres. La forme vient des gabarits et de la morphologie, qui produisent des phrases correctes par construction. Ce qu'on perd : l'aisance et la conversation hors schéma. Le jalon M4 doit compenser en partie, avec un petit modèle maison qui reformule sans inventer de fait.

## Où ajouter quoi

| Besoin | Endroit |
|---|---|
| Nouvelle tournure comprise | motif dans `data/lang/{fr,en}/intents.json`, à la bonne place dans l'ordre. Une valeur `Intent` et un traitement dans `_handlers` si l'intention est nouvelle. |
| Nouvelle phrase produite | gabarit dans `data/lang/{fr,en}/grammar.json`, jamais en dur dans le code |
| Nouveau mot ou concept curé | `data/lang/{fr,en}/lexicon.json`, et les faits dans `data/seed/facts.json` |
| Nouveau message de la CLI | `locales/{fr,en}.json` |
| Nouvelle source web | `research/providers/`, enregistrée dans `research/setup.py` |
