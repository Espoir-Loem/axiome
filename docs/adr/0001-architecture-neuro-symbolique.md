# ADR-0001 : Architecture neuro-symbolique

- **Statut** : Accepté
- **Date** : 2026-11-10

## Contexte
Axiome doit être déterministe, frugal, vérifiable, et ne doit dépendre d'aucun modèle pré-entraîné. Il doit pourtant comprendre du texte et raisonner.

## Décision
- Un **noyau symbolique**, Datalog stratifié avec preuves, porte toute affirmation de fait et tout raisonnement.
- De **petits réseaux de neurones entraînés de zéro** (M2) ne servent qu'à la *perception* : intention, entités, similarité. Leur sortie est une *proposition* que le noyau valide ou rejette.
- Un fait ne peut **jamais** provenir directement d'un réseau.

## Options écartées
- **LLM local** (pré-entraîné) : interdit par la vision, gourmand, non vérifiable.
- **Grand modèle entraîné de zéro** : hors de portée en calcul et en données, et non déterministe en génération.
- **Symbolique pur** : trop fragile face au langage naturel. Les réseaux légers comblent ce manque.

## Conséquences
- (+) Chaque réponse est explicable et auditable.
- (+) Tourne sur CPU.
- (−) Rédaction moins fluide qu'un LLM, ce qui est assumé (voir vision.md, non-objectifs).
- À surveiller : la qualité de la perception (M2) conditionne l'expérience utilisateur.
