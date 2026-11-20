# Feuille de route

À mettre à jour à chaque fin de session. État au 2026-11-20.

## Prochaine étape conseillée : des connaissances locales

Un LLM « sait » avant qu'on lui demande. Axiome doit faire pareil avec des bases libres importées en local, sans aller sur le web à chaque question.

| Ordre | Base | Apport | Licence | Taille | État |
|---|---|---|---|---|---|
| 1 | Wiktionary FR et EN (extraction kaikki.org) | Définitions, genre, flexions, traductions, synonymes | CC BY-SA | 1 à 2 Go bruts, à réduire | Attend l'accord du mainteneur |
| 2 | ConceptNet 5 | Sens commun (« sert à », « fait partie de », « peut ») | CC BY-SA | environ 1 Go pour FR et EN filtrés | À faire |
| 3 | OpenStax et constantes CODATA | Bases scientifiques (physique, chimie, biologie) | CC BY, domaine public | petit | À faire |
| 4 | YAGO 4.5 | Taxonomie propre dérivée de Wikidata et schema.org | CC BY-SA | plusieurs Go, prendre un sous-ensemble | À faire |
| — | WordNet et WOLF | Relations entre sens (synonymie, hyperonymie) | libre | petit | Possible |
| — | Lexique 3 | Fréquences et formes du français | CC BY-SA | petit | Possible |
| — | Tatoeba | Phrases parallèles FR et EN, utiles pour M4 | CC BY | moyen | Plus tard |
| — | PubChem | Chimie | domaine public | énorme, faire une sélection | Plus tard |

Règles d'import :
- un outil hors ligne qui produit un fichier compact et versionné par SHA-256 ;
- chaque fait garde sa source ;
- tenir dans 8 Go de RAM : lecture en flux, SQLite et index.

## Ensuite

- **Contexte.** Il ne couvre que les formes prévues et la seule dernière question. Prochaine étape : une pile de sujets et les références à plus de deux tours.
- **Nouveau banc réservé**, sur des domaines non couverts : l'actuel a servi aux corrections.
- **Corpus du banc par rejeu (code).** Le harnais et trois tâches existent (`evals/code/replay/`) : `dc11b2b`, `b2ce7c6`, `1e193e2`, cette dernière multi-fichiers. Chaque nouveau jalon peut en ajouter une (un dossier, un manifeste, les versions parentes, avec `depth` et `extra_targets` en clés facultatives). La mesure avec `depth: 2`, les fichiers `.py` supplémentaires et un budget de 16 donne toujours 0/3 ; l'ordre guidé par les identifiants du test qui échoue ne change pas ce score. L'écart ne vient donc ni du budget, ni de l'absence de composition, ni de l'ordre des candidats : les trois cas demandent d'ajouter du code. RFC-0003 a été écrite et fusionnée dans `develop` (PR #36, `c98a6c9`), mais son statut reste **En revue** : catalogue déterministe de squelettes, budget partagé, règle anti-surapprentissage. Aucune implémentation ne commence avant une acceptation explicite. Ne jamais lire le patch attendu, puis ajouter une tâche quand le score progresse.
- **Article des noms propres non humains** (« le Soleil ») à revérifier.
- **Lenteur de Wikidata sans `AXIOME_CONTACT`.** Ajouter un cache local, puis faire basculer le gros de la taxonomie sur YAGO.
- **M4** : petit modèle de langue maison (NumPy, 20 à 60 M de paramètres, int8). Il reformule et n'invente jamais de fait.
- **M5** maths et physique, **M6** méta-cognition. **M7** outils de code est fait (M7.0 à M7.8, RFC-0002) : analyse, revue de diff, bac à sable et génération vérifiée par les tests. M7.4 a ajouté quatre familles de mutation et un banc de 14 tâches ; M7.7 porte le banc à 16 tâches avec éditions composées et multi-fichiers ; M7.8 mesure ces réglages sur le banc par rejeu et confirme 0/3. Reste à couvrir d'autres langages et à améliorer le score du banc par rejeu.

## Actions du mainteneur en attente

1. Les PR #30, #31, #32, #33, #34, #35 et #36 ont été relues et fusionnées dans `develop` en squash : #32 (`14741e3`), #30 (`546714c`), #31 (`19cab3a`), #33 (`4faa86d`), #35 (`6aff4dd`), #34 (`88122ac`), #36 (`c98a6c9`).
2. Promouvoir `develop` vers `main` par une PR, sans push direct.
3. Accepter ou rejeter explicitement RFC-0003 avant tout travail d'implémentation des squelettes.
4. Accord pour le téléchargement de Wiktionary.
5. Facultatif : définir `AXIOME_CONTACT` (son choix, ne jamais le faire à sa place).

L'ancienne action « `push --force-with-lease origin main` » a été retirée : `main`
n'est pas à réécrire, et `develop` est maintenant la branche d'intégration (ADR-0009).
