# ADR-0005 : Tout le code source en anglais, textes via catalogues i18n

- **Statut** : Accepté (supplante ADR-0004)
- **Date** : 2026-11-10

## Contexte
L'ADR-0004 mélangeait les langues : identifiants en anglais, mais docstrings, messages et prédicats en français. Le mainteneur exige un code source entièrement en anglais, conforme aux standards des grands projets open source.

## Décision
1. **Tout le code source est en anglais** : identifiants, commentaires, docstrings, messages d'erreur, noms de règles, vocabulaire canonique de la base (`is_a`, `part_of`, `has_property`…) et mot-clé de négation `not`.
2. **Aucun texte affiché n'est écrit dans le code.** Le code produit des messages `Msg(clé, paramètres)`, rendus au dernier moment par `axiome.i18n` à partir de `src/axiome/locales/{en,fr}.json`. Les erreurs portent une clé, pas une phrase.
3. **Langue d'affichage** : le français par défaut. On la change avec `--lang` ou `AXIOME_LANG`. Les catalogues sont des données, pas du code source.
4. **Documentation et gouvernance** : `docs/`, issues et labels restent en français. Commits et PR sont en anglais.
5. Un test (`tests/unit/test_i18n.py`) garantit que les deux catalogues ont exactement les mêmes clés et les mêmes paramètres, et que chaque clé utilisée dans le code existe.

## Conséquences
- (+) Un code lisible par toute la communauté, un produit localisable. Une même trace de raisonnement peut s'afficher en plusieurs langues.
- (+) Les étiquettes françaises des concepts (« chat » → `cat`) seront un module de lexique, séparé de la logique (M2).
- (−) Ajouter un message demande de toucher deux catalogues ; le test évite les oublis.
