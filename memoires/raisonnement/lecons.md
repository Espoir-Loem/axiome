# Leçons et pièges

Chaque entrée : ce qui s'est passé, la cause, ce qu'il faut faire désormais.

## Outillage

- **ruff reformate le code et casse les remplacements exacts.** Un remplacement de texte préparé avant `ruff format` échoue ensuite : relire (`grep -n`) le texte actuel avant de remplacer.
- **Complexité ruff (C901, limite 12).** Découper en petites fonctions nommées (`_shortcut`, `_classify`, `_detail`, `_continue`, `_drop_ambiguous`) ou utiliser une table de répartition. N'ajoutez pas de `noqa`.
- **Autres règles déjà rencontrées :**
  - N818 : une exception se termine par `Error` ;
  - PLR0917 : paramètres nommés seuls (`*`) au-delà de 5 positionnels ;
  - PLC0415 : pas d'import dans une fonction de test ;
  - RUF007 : `itertools.pairwise`.
- **Chemins.** Les catalogues de la CLI sont dans `src/axiome/locales/`, pas à la racine. Un script `set -e` qui fait `grep` sur un mauvais chemin s'arrête sans message clair.

## Tests et évaluation

- **Un assistant de test qui jouait chaque tour deux fois** faisait passer des cas par accident. Une aide de test doit jouer un tour et rendre exactement ce tour.
- **Le banc réservé trouve de vrais défauts.** Exemple : l'espace en trop après « d' » dans le motif de correction français. On ne l'aurait pas vu sur le banc de travail.
- **Test de migration de schéma.** Il faut charger la graine (`load_seed`) pour que la source « user » existe, et comparer des dictionnaires plutôt que l'ordre des lignes.

## Wikidata

- **HTTP 429.** Espacer les appels (`POLITE_INTERVAL_S = 0.5`), réessayer en respectant `Retry-After` (10 s au plus) et alléger les requêtes de Lexemes (`props=claims`, un identifiant par nom).
- **Métaclasses.** P31 sur une classe renvoie « type d'objet astronomique » : utiliser P279 seul pour les classes.
- **Libellés non traduits.** Un libellé français identique à l'anglais sur plusieurs mots est une copie : il est rejeté (`_translated`).
- **Mauvais sens.** « baleine » donnait la constellation. Préférer le résultat dont la casse est celle de la question, et écarter les pages d'homonymie (Q4167410).
- **Lexeme d'une autre langue.** « naine » donnait un mot estonien. Exiger la langue française et « noun » dans la description.
- **Deux « mammifères ».** Le lion n'était pas relié aux mammifères, parce que Q7377 et Q110551885 portent le même nom. Suivre P171 pour les taxons et accepter un élément de même nom anglais que le but.
- **Qualité inégale.** Certaines classes sont rares ou bizarres (« fuseur »). Le statut reste PLAUSIBLE, jamais CONFIRMÉ.

## Langue

- **Doublons de concepts.** L'apprentissage web créait un nom de concept français et Wikidata un nom anglais pour la même chose. Interroger Wikidata avant le web.
- **Grammaire de « parce que » sur une longue chaîne.** Réécrite en « première relation, puis résumé de lignée » (`MAX_CHAIN = 4`).
- **Article des noms propres.** Seules les personnes n'ont pas d'article. « le Soleil » reste à revérifier.

## Conduite avec le mainteneur

- Il veut la parité avec les meilleurs modèles. On dit une fois, brièvement, ce qui est hors de portée sans modèle pré-entraîné, puis on avance sans y revenir.
- Il pousse lui-même (`git push --force-with-lease origin main`) : ne pas pousser à sa place.
- Aucune attribution IA dans les commits, aucun bot contributeur.
