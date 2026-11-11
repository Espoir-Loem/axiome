# ADR-0007 : assistant conversationnel, équipe interne et paquets de langue

- **Statut** : Accepté
- **Date** : 2026-11-11

## Contexte
Le mainteneur précise le produit : un assistant de conversation, au sens d'un LLM (pas encore un outil de code). Il doit converser librement, dire « je ne sais pas » puis chercher sur le web (Google ou autre) et répondre « d'après X, en résumé… ». Il doit aussi répondre en streaming, adapter son niveau du débutant au professeur selon le domaine, apprendre les langues, et n'afficher aucun signe d'écriture « IA ». Le tout reste 100 % de zéro (ADR-0006) et tourne sur un PC de 8 Go sans GPU.

## Décision
1. **Une équipe interne aux rôles stricts** (`axiome/team/`) : Analyste, Planificateur, Chercheur, Vérificateur, Rédacteur, Relecteur. Chaque rôle est déterministe et suit une liste de contrôle. Le Relecteur est une porte bloquante :
   - R1 : pas de fait sans source ;
   - R2 : nuance obligatoire sous le statut CONFIRMÉ ;
   - R3 : un fait réfuté n'est jamais affirmé ;
   - filtre de style `docs/signes-ia.md`.
2. **Décomposition du macro au nano** : but (macro), aspects (micro), une requête par aspect (atomique), statut épistémique de chaque fait (nano).
3. **Streaming** : un tour de conversation est un générateur d'événements (`Thinking`, `Searching`, `SourceFound`, `Say`, `Done`). Chaque phrase est émise dès qu'elle est validée.
4. **Paquets de langue** (`axiome/data/lang/<code>/`). Ce sont des données, pas des modèles :
   - lexique relié aux concepts ;
   - gabarits de phrases ;
   - schémas d'intention ;
   - règles de style.
   
   La morphologie (articles, élisions, pluriels, contractions) est codée par langue. Les mots appris en conversation ou sur le web sont stockés dans la base (schéma v2).
5. **Niveau adaptatif par domaine** (`dialogue/level.py`), déduit de signaux déterministes et mémorisé localement. Seule la forme change : le contenu donné à un débutant est un sous-ensemble de celui donné à un expert.
6. **Recherche web** derrière une interface `SearchProvider` :
   - Google Programmable Search (clé de l'utilisateur), SearXNG et Wikipédia (sans clé) ;
   - requêtes parallèles sous budget de temps, mais résultats consommés dans l'ordre configuré ;
   - cache disque ;
   - extraits **verbatim** classés par BM25, puis croisés entre organisations pour attribuer un statut (règles E1 à E8) ;
   - ce qui est trouvé est enregistré avec sa provenance : la question suivante est répondue hors ligne.

## Options écartées
- **Aspirer les pages de résultats Google** : interdit par les conditions d'utilisation et bloqué en pratique. L'API officielle est la seule voie.
- **Générer des phrases librement avec un réseau** : impossible à ce stade sans pré-entraînement massif, et cela risquerait des faits inventés. Un petit modèle maison de reformulation viendra en M4, sous contrôle du Relecteur.

## Conséquences
- (+) Chaque phrase affichée est traçable jusqu'à un fait ou une source. Le comportement est testable sans réseau grâce aux réponses enregistrées.
- (+) Ajouter une langue revient à ajouter des données et une classe de morphologie.
- (−) La conversation libre reste limitée aux intentions et au vocabulaire couverts. Elle s'élargira par l'apprentissage et par les paquets construits à partir de Wiktionary.
