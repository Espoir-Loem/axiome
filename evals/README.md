# Bancs d'évaluation

Chaque capacité est mesurée par un banc versionné. Une régression bloque la fusion.

| Banc | Jalon | Métrique |
|---|---|---|
| `intentions/` | M2 | précision du classifieur d'intention |
| `verite/` | M3 | aucune affirmation RÉFUTÉE présentée comme vraie ; taux de « je ne sais pas » justifiés |
| `raisonnement/` | M1+ | exactitude des déductions et des preuves |
| `physique/` | M4 | détection d'incohérences dimensionnelles |
| `code/` | M5 | revue de code et diagnostic de bogues |

`golden/` contient les sorties de référence attendues (tests de non-régression octet pour octet).
