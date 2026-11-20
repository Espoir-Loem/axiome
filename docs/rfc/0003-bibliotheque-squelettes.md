# RFC-0003 : Bibliothèque de squelettes guidée par les échecs

- **Statut** : En revue
- **Date** : 2026-11-20
- **Jalon** : M7.9 (proposé)
- **Dépend de** : RFC-0002 (M7.8)

## Contexte

Le banc de génération est à 16/16 avec zéro échec silencieux, mais le banc par
rejeu reste à **0/3**. Ce chiffre a été mesuré avec un budget de 4 puis de 16
candidats, avec `depth: 2`, avec les fichiers `.py` supplémentaires des commits et
avec un ordre de candidats guidé par les identifiants du test qui échoue. Aucune de
ces variations ne change le score.

Les trois échecs ont été lus uniquement dans les tests fournis, jamais dans le
patch attendu :

- `generation-families` exige d'**ajouter** quatre familles de mutation à
  `generate.py` ; la version parente ne les contient pas ;
- `incomplete-input` lève `ImportError: cannot import name 'edit_distance'` depuis
  `lexicon.py` ; la fonction n'existe pas ;
- `research-title-preference` exige que `digest` tienne compte du titre du document,
  alors que la version parente ne note que le texte.

La recherche actuelle ne sait que modifier des nœuds existants (littéraux,
opérateurs, conditions). Elle peut réordonner ses candidats, mais elle ne peut pas
insérer une définition, un appel ou un facteur de pondération. Le §4 de RFC-0002
prévoyait une « bibliothèque de squelettes » ; cette RFC en précise le périmètre.

## Constat

L'écart n'est pas budgétaire : à budget 16, les candidats sont épuisés sans
acceptation. Il n'est pas non plus dû à l'ordre : le guidage par les identifiants
du test place la bonne fonction en tête sans changer le verdict. Il vient d'une
capacité absente : produire du code nouveau, et non seulement en modifier.

## Objectif

Permettre à la recherche d'insérer un petit nombre de **squelettes paramétrés**,
déclenchés par des signaux présents dans la sortie des tests (nom manquant, forme
d'un appel, mot du test), puis jugés exactement comme les mutations locales : par
l'exécution des tests dans le bac à sable.

Contraintes héritées, non négociables :

- stdlib seule, aucun modèle pré-entraîné, aucun appel réseau (ADR-0006) ;
- déterminisme : même arbre, même diagnostics, même ordre, même patch ;
- le patch attendu du commit n'est jamais lu ;
- aucune exécution hors bac à sable, sortie plafonnée, environnement vidé ;
- un patch n'est accepté que si les tests passent réellement.

## Non-objectifs

- Pas de synthèse de programme arbitraire : les squelettes sont déclarés, versionnés
  et limités.
- Pas de correctif écrit pour un commit du banc de rejeu.
- Pas de déduction de la valeur attendue en lisant les assertions du test : ce
  serait un surapprentissage du banc, pas une capacité de réparation.
- Pas d'extension à d'autres langages dans cette RFC (Python seulement, comme
  RFC-0002).

## Architecture proposée

Nouveau module `code/squelettes.py`, à côté de `generate.py` ; la couche `code`
continue de ne pas connaître `team` ni `dialogue`.

```text
code/
  generate.py     recherche bornée existante, inchangée dans son verdict
  squelettes.py   catalogue immuable et moteur d'insertion (nouveau)
```

Un squelette est une valeur de données, pas du texte libre :

```python
@dataclass(frozen=True, slots=True)
class Squelette:
    id: str              # identifiant stable, triable
    declencheur: str     # motif sur les diagnostics, jamais sur le patch attendu
    inscription: str     # "module" | "avant" | "apres"
    raison: str          # pourquoi ce squelette est utile hors du banc de rejeu
```

Le corps de chaque squelette est une fonction Python du module, courte et
testée séparément. Le catalogue est trié par `id` : l'ordre ne dépend jamais de
l'ordre d'un dictionnaire ni du système de fichiers.

### Déclenchement

Les diagnostics sont déjà transmis à `generate()` depuis M7.8. Le moteur cherche
les motifs déclarés dans la sortie des tests :

- `cannot import name 'X'` → chercher un squelette de définition pour `X` ;
- un appel `X(...)` dans le test qui échoue → chercher un squelette de fonction
  paramétré par le nom `X` ;
- un mot du test qui échoue → chercher un squelette de pondération portant ce mot.

Un squelette non déclenché ne produit aucun candidat. Un déclenchement ne produit
jamais plus de `k` candidats, avec `k` petit et déclaré (proposition : 2).

### Insertion

L'insertion se fait sur l'AST de la copie, jamais sur l'arbre de travail :

- `module` : ajout en fin de module, après les imports ;
- `avant` / `apres` : insertion autour de la fonction dont le nom apparaît dans
  les diagnostics, retrouvée par `ast.walk` puis triée par position.

Chaque insertion forme un patch complet, ajouté à la même file d'attente que les
mutations locales. Le budget reste unique entre les deux familles. Une insertion
n'est pas « acceptée » parce qu'elle ressemble au correctif : elle ne l'est que si
les tests passent.

### Catalogue initial proposé

Trois familles sont proposées pour la revue, avec une règle d'admission stricte :
un squelette n'entre dans le catalogue que si sa raison est valable **hors** des
trois tâches du banc de rejeu, et s'il a ses propres tests unitaires.

1. `definition_locale` — insère une fonction minimale quand un test importe un nom
   absent du module cible. Le corps est choisi parmi un petit ensemble de formes
   générales (constante, identité, longueur), jamais déduit de la valeur attendue
   du test.
2. `distance_d_edition` — insère une fonction de distance d'édition standard quand
   un diagnostic cite un nom de similarité ou de distance entre chaînes. Algorithme
   unique, documenté, avec ses propres tests ; aucun paramètre lié à un commit.
3. `bonus_de_correspondance` — insère un facteur de correspondance entre la
   requête et un champ nommé du document (`title`, `name`) dans une expression de
   score existante. Le champ est le paramètre, pas le libellé d'un test.

Si la revue estime qu'une entrée ne satisfait pas la règle d'admission, elle est
retirée : mieux vaut un catalogue de deux squelettes honnêtes que trois adaptés
au banc.

## Mesure et honnêteté

- Le banc de génération doit rester à 16/16 avec zéro échec silencieux.
- Le banc par rejeu est rejoué avant et après, avec la même commande, le même
  budget et la même empreinte. Un score publié sans ces éléments n'est pas publié.
- Si un cas du banc par rejeu passe uniquement parce qu'un squelette a été écrit
  pour lui, il est compté comme **surapprentissage**, pas comme une réussite, et
  le squelette est retiré.
- Le corpus peut recevoir de nouvelles tâches uniquement comme données : un
  dossier, un manifeste, les versions parentes ; jamais une modification du moteur
  pour une tâche donnée.

## Vérification

| Propriété | Test prévu |
|---|---|
| Catalogue trié et immuable, sans itération sur un `set` non trié | `unit/test_code_squelettes.py` |
| Chaque squelette a un déclencheur, une raison et un test unitaire | `unit/test_code_squelettes.py` |
| Insertion dans une copie, jamais dans l'arbre de travail | `unit/test_code_squelettes.py` |
| Un squelette non déclenché ne consomme pas de budget | `unit/test_code_generate.py` |
| Budget partagé entre mutations et insertions | `unit/test_code_generate.py` |
| Même diagnostic, même graine → même patch | `property/test_code_properties.py` |
| Acceptation uniquement si les tests passent | `unit/test_code_generate.py` |
| Banc de génération 16/16, rejeu mesuré avant/après | `integration/test_code_bench.py`, `integration/test_code_replay.py` |

## Livraison proposée

| Étape | Contenu | Critère de sortie |
|---|---|---|
| M7.9.1 | Module `squelettes.py`, catalogue et tests unitaires | Un squelette non déclenché ne produit aucun candidat ; insertion dans une copie |
| M7.9.2 | Intégration dans `generate()` et `run_replay()` | Budget partagé, ordre déterministe, verdict toujours par exécution |
| M7.9.3 | Mesure avant/après et documentation | 16/16 sur la génération, rejeu publié avec commande et commit, surapprentissage exclu |

## Options écartées

- **Copier le patch du commit.** Interdit par le protocole du banc par rejeu.
- **Augmenter le budget.** Déjà mesuré à 16 : 0/3.
- **Lire les assertions pour en extraire la réponse.** Donnerait l'impression d'une
  réussite sans capacité générale ; c'est un surapprentissage du banc.
- **Appeler un modèle pré-entraîné.** Contradiction directe avec ADR-0006.
- **Écrire un correctif par tâche de rejeu.** Le banc mesurerait alors la mémoire
  du harnais, pas la réparation.

## Questions ouvertes

1. Faut-il un budget séparé pour les squelettes, ou le budget unique actuel suffit-il
   pour garder la mesure comparable ? Position proposée : budget unique.
2. Quel critère objectif décide qu'un squelette est « général » ? Proposition :
   au moins un test unitaire indépendant du banc de rejeu et une raison formulée
   sans référence aux commits rejoués.
3. Les insertions doivent-elles être essaysées avant ou après les mutations locales
   de même profondeur ? Proposition : après, pour ne pas déplacer le comportement
   déjà vérifié sur le banc de génération.
4. Faut-il exposer un squelette personnalisé via la configuration utilisateur ?
   Position proposée : non dans un premier temps, pour garder le déterminisme et
   la surface d'attaque réduite.
