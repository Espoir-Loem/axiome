# Graine de connaissance

- `regles.axl` : programme logique de référence (règles **axiomatiques**).
- `faits.json` : faits curés, chacun rattaché à une source.

Règles de contribution :
1. N'ajouter que des faits **définitionnels ou universellement établis**. Tout fait sujet à débat passe par le pipeline de recherche (M3) et non par la graine.
2. Chaque groupe cite sa source (`source`). Une nouvelle source nécessite une revue.
3. `est_un` mélange volontairement instance et sous-classe dans M1 ; la distinction `instance_de` / `sous_classe_de` est prévue (cf. RFC-0001, « Questions ouvertes »).
4. Pas d'héritage de propriétés à exceptions (ex. « les oiseaux volent ») : la règle `heritage_propriete` est monotone.
