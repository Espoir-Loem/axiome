# ADR-0009 : develop comme branche d'intégration

- **Statut** : Accepté
- **Date** : 2026-11-19

## Contexte
Les jalons M7 s'enchaînent et plusieurs changements peuvent être prêts en même temps. Les règles du dépôt imposent une PR relue et une CI verte avant toute fusion, ce qui laisse les PR ouvertes un certain temps. Le travail suivant dépend pourtant des changements déjà vérifiés localement : attendre la fusion dans `main` bloque la suite, alors que pousser directement dans une branche partagée supprimerait la revue.

## Décision
`develop` est la branche d'intégration du projet. Elle a été créée depuis `main` le 2026-11-19.

Toute modification part d'une branche de sujet (`feat/…`, `fix/…`, `docs/…`, `refactor/…`, `test/…`) et fait l'objet d'une PR vers `develop`, relue et fusionnée en squash. `main` ne reçoit que des PR depuis `develop`, après validation de l'intégration. Le garde-fou local refuse les pushes directs vers `main` et vers `develop` ; les PR #30 et #31, ouvertes avant cette décision, ont été réorientées vers `develop`.

## Options écartées
- **Tout envoyer directement dans `main`.** C'était la règle initiale, mais elle impose d'attendre la fusion de chaque PR avant de commencer la suite et elle ne laisse pas d'état d'intégration visible.
- **Pousser directement dans `develop`.** Cela contournerait la revue obligatoire et rendrait l'historique de la branche d'intégration non reproductible.
- **Empiler les branches de fonctionnalités sans intégration.** Les dépendances entre PR deviennent alors invisibles et la revue porte sur des diffs qui incluent le travail des autres.

## Conséquences
- (+) Le travail peut continuer sur une base commune dès qu'une PR est prête, sans attendre la publication dans `main`.
- (+) `main` reste une branche de publication, avec un historique de squash déjà intégré et vérifié.
- (−) Une PR doit préciser sa base : `develop` pour un changement de sujet, la branche de sujet parent pour une PR empilée, `main` uniquement pour promouvoir `develop`.
- (−) Le garde-fou et les règles écrites doivent être mis à jour en même temps que la décision, sinon les outils continuent d'autoriser les pushes directs.
