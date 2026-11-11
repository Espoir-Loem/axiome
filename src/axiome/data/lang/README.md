# Paquets de langue

Un dossier par langue (`fr`, `en`). Ce sont uniquement des données, aucun modèle (ADR-0006, ADR-0007).

| Fichier | Contenu |
|---|---|
| `lexicon.json` | Concepts canoniques de la base → mots de la langue : lemme, genre, pluriel irrégulier, niveau de technicité, domaine, définition simple (`gloss`) et propriété sous forme verbale (`pred`). |
| `grammar.json` | Gabarits de phrases. Les spécificateurs `{x:def}`, `{x:indef}`, `{x:of_def}`, etc. sont résolus par la morphologie (`language/morphology.py`). |
| `intents.json` | Schémas d'intention appliqués au texte normalisé (minuscules, sans accents), signaux de niveau, articles, pronoms, mots vides. |
| `style.json` | Tournures interdites (`docs/signes-ia.md`) et demandes qui les lèvent. |

Pour ajouter une langue :
1. créer les quatre fichiers ;
2. écrire une classe de morphologie et l'enregistrer dans `language/pack.py` ;
3. les tests de parité vérifient que les clés, les champs et les concepts sont les mêmes partout.
