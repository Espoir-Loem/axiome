# ADR-0006 : 100 % de zéro, pas de parité avec les grands modèles

- **Statut** : Accepté
- **Date** : 2026-11-10

## Contexte
Le mainteneur souhaitait un rendu comparable à Fable 5 ou à Kimi entreprise, sur CPU. Ce niveau exige des milliers de milliards de mots d'entraînement, des milliers de GPU et des centaines de milliards de paramètres. Il est donc hors de portée sans modèle pré-entraîné. Trois options ont été présentées : un hybride avec un modèle à poids ouverts, le 100 % de zéro, ou un noyau maison avec une API optionnelle.

## Décision
**100 % de zéro.** Aucun modèle pré-entraîné, aucune API de modèle tiers, ni maintenant ni en option.

Axiome ne vise **pas** la parité générale avec les grands modèles de langage. Il vise l'excellence là où son architecture l'emporte :
1. **Fiabilité** : zéro affirmation inventée ; « je ne sais pas » plutôt qu'une réponse fausse.
2. **Preuve et traçabilité** de chaque conclusion, et déterminisme.
3. **Domaines ciblés et structurés** : ingénierie logicielle (analyse, revue, conception, diagnostic), maths, physique, vérification de faits.
4. **Frugalité** : sur CPU, hors ligne, en quelques Mo.

## Options écartées
- **Hybride avec un modèle à poids ouverts** : rompt la règle « aucun modèle existant ».
- **API optionnelle** : crée une dépendance externe et un comportement non déterministe.

## Conséquences
- (+) Le projet reste entièrement souverain, auditable et reproductible.
- (−) La rédaction et la génération de code libres resteront bien en dessous des grands modèles. Les bancs d'évaluation (`evals/`) mesurent donc la **fiabilité** et la **justesse vérifiable**, pas la ressemblance avec un grand modèle de langage.
