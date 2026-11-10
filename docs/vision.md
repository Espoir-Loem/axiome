# Vision

## Mission
Construire une IA qui **sait pourquoi elle sait** : elle raisonne, vérifie et cite ses sources, tourne sur n'importe quel ordinateur et donne toujours la même réponse à la même question.

## Objectifs
1. **Vérité avant fluidité.** Une réponse vaut par sa justification. Chaque affirmation porte un statut épistémique calculé par des règles explicites (voir [epistemologie.md](epistemologie.md)).
2. **Déterminisme.** À entrée et base de connaissances identiques, la sortie est identique octet pour octet. Un test le vérifie sur plusieurs processus et plusieurs graines de hachage.
3. **Frugalité.** Le CPU suffit, sans GPU. Le noyau tient en quelques Mo et n'a aucune dépendance obligatoire. Il fonctionne hors ligne avec la connaissance déjà acquise.
4. **Démarche scientifique.** Hypothèse, prédiction, test, révision. La recherche est multi-échelle :
   - **macro** : contexte ;
   - **micro** : mécanismes ;
   - **atomique** : faits unitaires ;
   - **nano** : vérification de chaque fait.
5. **Excellence en ingénierie logicielle.** Analyse, conception, revue et diagnostic de code, ainsi que génération de code *vérifiée par l'exécution*.
6. **Apprentissage.** Axiome accumule des faits vérifiés et apprend les types de questions de son utilisateur pour mieux orienter ses recherches.

## Non-objectifs (assumés)
- **Rivaliser avec un LLM en conversation libre ou en rédaction créative.** Axiome rédige des réponses structurées.
- **Générer du code « créatif » sans vérification.** Tout code proposé doit passer des tests.
- **Utiliser un modèle pré-entraîné tiers**, quel qu'il soit.
- **Exprimer une confiance par une probabilité opaque.** Si un calcul numérique est utilisé, sa formule est documentée.

## Principe directeur
> Un réseau de neurones **propose**, la logique **dispose**.

Les réseaux (M2) servent à *percevoir* : comprendre une phrase, reconnaître une entité. Ils ne produisent jamais un fait.
