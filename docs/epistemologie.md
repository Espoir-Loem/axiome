# Épistémologie d'Axiome (spécification normative)

> Ce document fait foi. L'implémentation se trouve dans `src/axiome/verification/` et les tests dans `tests/unit/test_epistemic.py` et `test_revision.py`. Toute divergence entre le code et ce document est un bogue.

## 1. Statuts (du plus fort au plus faible)

| Statut | Signification |
|---|---|
| `PROUVÉ` | Découle d'axiomes ou d'une démonstration. Vrai *relativement aux axiomes du système*. |
| `VÉRIFIÉ` | Établi par un calcul ou une exécution reproductible. |
| `CONFIRMÉ` | Au moins 2 sources fiables **indépendantes** (d'organisations différentes). |
| `PLAUSIBLE` | Une source fiable, ou au moins 2 sources moyennes indépendantes. |
| `NON VÉRIFIÉ` | Simplement affirmé, ou aucune preuve. |
| `CONTESTÉ` | Des preuves contradictoires de force comparable. |
| `RÉFUTÉ` | Contredit par une preuve décisive, par plusieurs sources fiables, ou par la logique (§3). |

## 2. Statut d'un fait de base : règles E1 à E8, appliquées dans l'ordre

Les preuves sont typées par la nature de leur source (`axiom`, `proof`, `computation`, `reference`, `publication`, `user`, `other`), par sa fiabilité (`HIGH`, `MEDIUM`, `LOW`) et par leur position (`supports` ou `contradicts`). Les sources *décisives* sont `axiom`, `proof` et `computation`.

- **E1.** Si au moins une source décisive contredit le fait, il est `RÉFUTÉ`.
- **E2.** Si un axiome ou une preuve le soutient, il est `PROUVÉ`.
- **E3.** Si un calcul le soutient, il est `VÉRIFIÉ`.
- **E4.** Si une source fiable le contredit et qu'au moins une source le soutient, il est `CONTESTÉ`.
- **E5.** Si au moins 2 organisations fiables le contredisent, il est `RÉFUTÉ`.
- **E6.** Si au moins 2 organisations fiables le soutiennent, il est `CONFIRMÉ`.
- **E7.** S'il est soutenu par 1 organisation fiable, ou par au moins 2 organisations de fiabilité moyenne ou plus, il est `PLAUSIBLE`.
- **E8.** S'il est contredit, il est `CONTESTÉ` lorsqu'il est aussi soutenu, et `NON VÉRIFIÉ` sinon. Dans tous les autres cas, il est `NON VÉRIFIÉ`.

L'indépendance se mesure par **organisation** : deux pages d'un même site ne comptent qu'une fois.

## 3. Faits dérivés et révision des croyances

1. **Maillon le plus faible.** Un fait déduit prend le statut le plus faible parmi ses prémisses (preuve canonique).
2. **Plafond « hypothèse ».** Une règle ajoutée par l'utilisateur plafonne ses conclusions à `NON VÉRIFIÉ`.
3. **Plafond « monde clos ».** Une conclusion qui utilise `not` (l'absence d'un fait) plafonne à `PLAUSIBLE`. Ne pas trouver un fait ne prouve pas qu'il est faux.
4. **Contradictions.** Pour chaque violation d'une contrainte d'intégrité, on remonte aux faits de base qui la supportent.
   - S'il existe un **unique** fait le plus faible et que **tous les autres** sont au moins `CONFIRMÉ`s, ce fait est `RÉFUTÉ` : il est retiré et l'on recommence.
   - Sinon, les faits les plus faibles deviennent `CONTESTÉ`s et le conflit est signalé comme non résolu. On ne tranche pas arbitrairement.
5. **Inconnu.** Une requête sans réponse donne « je ne sais pas », jamais « faux ».

## 4. Limites connues (M1)
- Le statut d'un fait dérivé se calcule sur sa preuve *canonique*, la plus courte, et non sur la meilleure de toutes ses preuves. Une preuve alternative plus solide est ignorée. Ce point sera corrigé par un calcul de point fixe en M3.
- La combinaison quantitative des indices (Dempster-Shafer) arrive en M3, en complément des règles, jamais à leur place.
