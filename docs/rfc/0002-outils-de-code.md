# RFC-0002 : Outils de code (analyse, revue, génération vérifiée)

- **Statut** : Implémenté (M7.0 à M7.5, 2026-11-18)
- **Jalon** : M7

## Objectif

Donner à Axiome trois capacités, dans cet ordre :

1. **Analyser** un dépôt : quels symboles existent, qui appelle qui, quelles règles de style sont violées.
2. **Revoir** un changement : signaler les défauts d'un diff, chaque constat adossé à un fait du code.
3. **Générer** du code — mais uniquement du code **vérifié par l'exécution** des tests du projet.

Le non-objectif de `docs/vision.md` fait loi : aucun code « créatif » n'est proposé sans passer des tests. Si rien ne passe, Axiome répond « je ne sais pas » (epistemologie.md §3.5), il ne devine pas une rustine.

Contraintes héritées, non négociables :

- **stdlib uniquement**, pas de dépendance nouvelle (ADR-0006) ; le module `ast` de Python suffit pour M7.
- **Déterminisme** : même dépôt, même diff → même sortie, octet pour octet.
- **CPU seul**, hors ligne possible.
- **Aucune exécution de code non fiable hors bac à sable.**

## Portée

**M7.0** Python seulement. Les autres langages passeront par un analyseur externe déclaré (`AXIOME_CODE_ANALYZER`) et seront marqués `PLAUSIBLE` au mieux : sans analyseur, on ne prétend rien savoir du code.

## Architecture

Nouvelle couche `code`, à côté de `research` et non au-dessus :

```
core ◄ reasoning ◄ knowledge ◄ code ◄ team ◄ dialogue ◄ cli
```

- `code` ne connaît ni `team`, ni `dialogue` : il expose une API, l'équipe décide quand l'appeler.
- La partie pure (extraction de faits depuis l'AST) ne fait aucune E/S et reste testable sans dépôt.
- `code.source` est le seul module qui lit le disque ; `code.sandbox` (M7.2) sera le seul à exécuter un sous-processus.

```
code/
  source.py    lecture d'un dépôt : liste canonique et triée des fichiers
  facts.py     AST Python → atomes Datalog (aucune E/S)
  index.py     index en mémoire et requêtes ?- (M7.0)
  analyze.py   requêtes de diagnostic sur l'index (M7.1)
  review.py    diff → constats, chacun adossé à des faits (M7.1)
  sandbox.py   exécution confinée (sous-processus, limites, délai) (M7.2)
  generate.py  recherche bornée de correctifs, jugés par les tests (M7.3-M7.4)
```

## 1. Le code comme faits

L'idée directrice du projet — « un réseau propose, la logique dispose » — s'applique telle quelle : le code est **traduit en faits**, les diagnostics sont des **requêtes**, la preuve est l'arbre de déduction.

Prédicats (constantes `str`/`int`, comme AXL aujourd'hui ; une position s'encode `"chemin.py:12"`) :

| Prédicat | Sens |
|---|---|
| `defines(Pos, Nom)` | `Nom` est défini à `Pos` (fonction, classe, méthode, variable de module) |
| `references(Pos, Nom)` | `Nom` est lu à `Pos` |
| `imports(Module, Cible)` | `Module` importe `Cible` |
| `calls(Appelant, Appelé)` | appel ; l'appelant est qualifié, l'appelé reste syntaxique (M7.0), puis résolu par portée lexicale et par import |
| `parametre(Fonction, Rang, Nom)` | paramètres positionnels (positionnels seuls compris) et nommés-seuls ; `*args`/`**kwargs` exclus |
| `retourne(Nom, Pos)` | M7.1 |
| `ligne(Pos, Texte)` | texte source d'une ligne, pour citer |
| `test_de(NomTest, NomCible)` | un test couvre une cible (par convention de nom, puis par couverture observée) |
| `violation(Regle, Pos)` | diagnostic produit par `analyze` |

Les faits de code portent une preuve de type `computation` (l'analyse est un calcul reproductible) : un constat d'analyse est donc `VÉRIFIÉ` au sens E3, jamais `PROUVÉ`. Un fait appris par lecture d'une page web sur le langage reste `PLAUSIBLE`, sans exception.

**Pourquoi des faits et pas des objets Python ?** Parce qu'on obtient gratuitement la traçabilité (chaque diagnostic a un arbre de preuve), les requêtes (`?- violation(Regle, Pos)`), la révision, et le déterminisme (tris canoniques du noyau). Et l'utilisateur peut interroger l'index comme le reste de la base.

Résolution des appels — limite assumée : portée lexicale, `self.`/`cls.`, imports résolus dans le dépôt ; le dispatch dynamique (`getattr`, décorateurs, métaclasses) donne `PLAUSIBLE`, jamais un appel affirmé. En M7.0, `calls` ne porte que le nom syntaxique de l'appelé (identifiant ou attribut) ; la résolution arrive en M7.1.

Nommage : les définitions et les appelants sont qualifiés par le module et par la définition englobante (`pkg.mod.Cls.method`) ; les références et les appelés restent le nom lu dans le source.

## 2. Analyse : règles, pas d'heuristique

`analyze` n'invente pas de « bonnes pratiques ». Chaque règle est (a) un prédicat dérivé, (b) un énoncé en clair, (c) un cas de test.

Premier lot, volontairement petit et vérifiable :

- `import_inutilise`, `nom_non_utilise`, `code_mort` (aucun `references` vers un `defines` non exporté) ;
- `appel_inconnu` (nom appelé absent de l'index et non résolu via import) ;
- `exception_avalee` (`except: pass`), `comparaison_a_none` (`== None`) ;
- `complexite_cyclomatique(Nom, N)` et son seuil, **affiché avec sa formule** (vision, non-objectif « confiance opaque ») ;
- `cycle_import(Module)`.

Un diagnostic est toujours : une règle nommée, une position, la ligne citée. Aucun diagnostic sans position. Les règles activées sont déclarées dans `pyproject.toml` (`[tool.axiome.code]`), donc lisibles et versionnées.

## 3. Revue d'un diff

Entrée : un diff unifié et le dépôt d'origine. Sortie : des constats triés par position.

1. L'index est recalculé sur l'arbre après application du diff (copie temporaire, jamais l'arbre de travail : on ne modifie pas le dépôt de l'utilisateur).
2. Les diagnostics **nouveaux** — présents après, absents avant — sont retenus ; une règle déjà violée ailleurs n'est pas reprochée deux fois.
3. Les constats passent par le `Reviewer` existant : règle R1 (chaque phrase cite un fait), R2 (nuance sous `CONFIRMÉ`), R3 (un fait réfuté n'est énoncé que comme réfuté). Rien ne change dans `team/reviewer.py` : les faits de code sont des faits comme les autres.

Aucune sévérité numérique opaque : `bloquant` / `à corriger` / `remarque`, chacune définie par la règle.

## 4. Génération vérifiée par l'exécution

C'est le cœur du jalon, et le plus risqué. Trois temps :

1. **Cadre.** L'utilisateur fournit une cible (test qui échoue, ou signature attendue). Sans test exécutable, Axiome refuse de générer : il explique ce qui manque.
2. **Proposition.** Recherche bornée et déterministe, sans modèle pré-entraîné :
   - bibliothèque de squelettes (patrons déjà connus de la base, cf. `creational_pattern`) ;
   - mutations guidées par les échecs : renommage, remplacement d'un littéral, ajout d'un cas, inversion de condition, ajout d'un `return` ;
   - ordre de parcours strictement trié, budget de candidats déclaré (`budget = N`, par défaut 50), graine fixe.
   Chaque candidat est un patch unifié, jamais une réécriture complète.
3. **Jugement.** Le patch est appliqué dans le bac à sable, les tests du projet sont exécutés. Le résultat est un fait `passe(Revision, Test)` de type `computation` → `VÉRIFIÉ` (E3). Le patch retenu est le premier, dans l'ordre canonique, qui fait passer **tous** les tests ciblés sans en casser d'autres ; les tests de non-régression sont ceux du projet, pas une sélection d'Axiome.

Si le budget s'épuise : « je n'ai pas trouvé de correctif qui passe les tests », avec le journal des candidats rejetés et leur erreur. C'est une réponse utile, et honnête.

## 5. Bac à sable

`code.sandbox` est le seul module autorisé à exécuter quoi que ce soit. Règles :

- copie temporaire du dépôt, supprimée après usage ; le dépôt de l'utilisateur n'est jamais modifié ;
- sous-processus avec délai mur (`timeout`), limites `resource` (CPU, mémoire, taille de fichier, pas de fork), sortie plafonnée ;
- environnement vidé : ni `AXIOME_*`, ni secrets, ni proxy ; `PYTHONHASHSEED=0`, `TZ=UTC`, graines fixées ;
- réseau coupé (`unshare -n` quand disponible ; sinon, mode dégradé signalé comme tel dans le rapport, car il ne garantit rien) ;
- aucun `sudo`, aucun accès hors du répertoire temporaire.

Une exécution non reproductible (dépendante du temps, du réseau, de l'ordre d'itération) est signalée : deux exécutions doivent donner le même verdict, sinon le fait reste `NON VÉRIFIÉ`.

## Vérification

| Propriété | Test |
|---|---|
| Extraction invariante par ordre des fichiers | `property/test_code_properties.py` |
| Aller-retour position ↔ `chemin:ligne`, y compris chemins non ASCII | `unit/test_code_source.py`, `property/test_code_properties.py` |
| Faits exacts : noms qualifiés, imports relatifs, doublons fusionnés | `unit/test_code_facts.py` |
| Un fichier illisible syntaxiquement est signalé avec sa ligne, jamais ignoré | `unit/test_code_index.py` |
| Chaque règle d'analyse a au moins un cas positif et un cas négatif | `unit/test_code_analyze.py` |
| Aucun diagnostic sans position ni sans fait de support (R1) | `unit/test_code_analyze.py`, `unit/test_code_review.py` |
| Un patch proposé ne modifie jamais l'arbre de travail | `unit/test_code_sandbox.py` |
| Dépassement de délai, de mémoire et de sortie → arrêt propre, rapport explicite | `unit/test_code_sandbox.py` |
| Génération déterministe : même cible, même graine → même premier patch | `unit/test_code_generate.py` |
| Un patch n'est déclaré accepté que si les tests passent réellement | `unit/test_code_generate.py` |

Bancs (`evals/code/`, séparés des bancs de conversation) :

- **revue** : précision et rappel sur un jeu étiqueté à la main, par règle (pas de score global qui masque une règle qui crie au loup) ;
- **génération** : `pass@1` sur de petites tâches avec tests, plus le taux d'échecs *silencieux* (patch annoncé correct à tort), qui doit rester à **zéro** ;
- **déterminisme** : deux exécutions, même empreinte.

Lancement : `python -m pytest tests/integration/test_code_bench.py` (les cas sont dans
`evals/code/review.jsonl` et `evals/code/generation.jsonl`), et
`tests/integration/test_code_heldout.py` pour le rejeu de vrais commits hébergé par
`evals/code/heldout.jsonl` : l'arbre parent est extrait, seuls les tests du commit
correctif sont ajoutés, et le patch attendu n'est jamais lu. Le banc de génération
compte 14 petites tâches (arithmétique, comparaisons, appartenance, booléens,
inversion de condition, index, bornes de `range`) ; chacune échoue avant mutation.
Le banc tenu à l'écart rejoue en plus un commit réel du dépôt, sans révéler son
correctif ; une tâche qui passe déjà est une erreur d'intégrité.

## Implémentation

Pour que chaque règle ait un fait de support, l'extraction ajoute aux prédicats de
M7.0 : `importe_sous` (nom lié et position d'un import), `appel_simple` (appel par
nom, position), `retourne`, `complexite` (1 + points de décision), `except_vide` et
`compare_a_none`. Les règles activées et le seuil de complexité se règlent dans
`[tool.axiome.code]` de `pyproject.toml`.

La CLI expose `axiome --analyze CHEMIN` et `axiome --review DIFF` (code de sortie 1
dès qu'un constat existe). La revue passe les constats au `Reviewer` de l'équipe via
`team/code_review.py` : le paquet `code` continue de ne pas connaître `team`.

M7.4 étend la recherche à quatre familles de plus : opérateurs binaires (`+`, `-`,
`*`, `/`, `//`, `%`), opérateurs booléens (`and`/`or`), négation d'une condition de
`if`/`elif`/`while` et d'une `if` expression. Chaque famille reste une mutation
locale d'un nœud AST ; le verdict vient toujours de l'exécution des tests.

Aucun score n'est publié sans la commande et le commit qui l'ont produit (`evals/README.md`).

## Sécurité

Voir `SECURITY.md`. Un dépôt analysé est une entrée **non fiable** : l'analyse ne fait que lire, la génération n'exécute que dans le bac à sable, et le rapport d'exécution ne contient jamais de variable d'environnement ni de sortie non plafonnée.

## Livraison

| Étape | Contenu | Critère de sortie |
|---|---|---|
| M7.0 | `source.py`, `facts.py`, index, requêtes `?-` sur le code | **fait** : 10 000 lignes (60 fichiers, 45 000 faits) en 303 ms, ordre des fichiers sans effet |
| M7.1 | règles d'analyse + revue de diff intégrée à l'équipe | **fait** : 8 règles, aucun diagnostic sans position ni preuve ; banc de revue étiqueté, précision et rappel 1,0 par règle |
| M7.2 | bac à sable + exécution des tests | **fait** : copie temporaire, délai, limites `resource`, sortie plafonnée, environnement vidé ; isolation réseau annoncée dégradée quand `unshare -n` manque |
| M7.3 | génération bornée sur tâches à tests | **fait** : `pass@1` 2/2 sur le banc, 0 échec silencieux, même graine → même patch |
| M7.4 | plus de patrons de mutation et un banc réaliste | **fait** : opérateurs binaires, `and`/`or`, condition et `if` expression négation ; banc de 14 tâches, `pass@1` 14/14, 0 échec silencieux |
| M7.5 | banc tenu à l'écart sur de vrais commits | **fait** : rejeu de l'arbre parent, tests du commit correctif seuls révélés, patch attendu jamais lu ; `pass@1` 0/1 sur la seule tâche réelle de l'historique ; une tâche déjà verte est rejetée comme erreur d'intégrité |

## Questions ouvertes

1. **Langages hors Python.** Un analyseur externe est-il acceptable au regard de l'ADR-0006 (« de zéro ») ? Proposition : oui pour *lire*, non pour *raisonner* — les faits restent produits par Axiome, l'analyseur ne fournit que l'AST.
2. **Couverture.** `test_de` par convention de nom est fragile ; faut-il mesurer la couverture réelle (`trace`, stdlib) au prix d'une exécution supplémentaire ?
3. **Budget de génération.** 50 candidats est arbitraire ; le rendre adaptatif au nombre de tests ciblés, sans casser le déterminisme.
4. **Réseau dans le bac à sable.** `unshare -n` n'est pas portable (macOS, Windows, conteneurs restreints). Faut-il refuser d'exécuter plutôt que d'exécuter sans garantie ? Position proposée : refuser par défaut, mode dégradé sur demande explicite.
5. **Réutilisation du noyau.** Les faits de code doivent-ils vivre dans la base de connaissances principale ou dans un index séparé ? Un index séparé évite de polluer la révision des croyances ; il prive aussi des requêtes croisées (« ce module utilise-t-il un fait réfuté ? »).
