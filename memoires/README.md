# Mémoires du projet

Ce dossier sert à transmettre le contexte d'une session de travail à la suivante, qu'elle soit menée par une personne ou par un modèle. On y trouve ce que le code et l'historique Git ne disent pas : pourquoi les choses sont faites ainsi, les pistes écartées, les erreurs déjà rencontrées et ce qui reste à faire.

## Par où commencer

1. [projet/vision-et-contraintes.md](projet/vision-et-contraintes.md) : ce que veut le mainteneur et les règles qui ne se discutent pas.
2. [projet/etat-actuel.md](projet/etat-actuel.md) : ce qui marche, les scores, les limites connues.
3. [guide/travailler-sur-axiome.md](guide/travailler-sur-axiome.md) : commandes, conventions, porte de qualité, règles de commit.
4. [suite/feuille-de-route.md](suite/feuille-de-route.md) : prochaines étapes et actions en attente.

Pour comprendre le raisonnement :
- [raisonnement/architecture.md](raisonnement/architecture.md) : comment une question devient une réponse, et pourquoi chaque pièce existe ;
- [raisonnement/decisions.md](raisonnement/decisions.md) : journal des décisions, avec les alternatives écartées ;
- [raisonnement/methode-evaluation.md](raisonnement/methode-evaluation.md) : comment on mesure les progrès sans se tromper soi-même ;
- [raisonnement/lecons.md](raisonnement/lecons.md) : pièges déjà rencontrés, pour ne pas les refaire.

Journal chronologique : [sessions/](sessions/), un fichier par jour de travail.

## Règles de tenue

- **Fin de session :** mettre à jour `projet/etat-actuel.md` et `suite/feuille-de-route.md`, puis ajouter une entrée dans `sessions/AAAA-MM-JJ.md`.
- **Décision structurante :** une ligne dans `raisonnement/decisions.md`. Si elle engage l'architecture, un ADR dans `docs/adr/`.
- **Contenu :** écrire des faits vérifiables (fichiers, commandes, scores, commits), pas des impressions. Les dates sont absolues.
- **Rédaction :** en français. Le code cité reste en anglais. Pas d'emoji ni de formules creuses (voir `docs/signes-ia.md`).
- **Ce qu'on ne met pas ici :** les données personnelles et les secrets (clés d'API, adresses électroniques).
