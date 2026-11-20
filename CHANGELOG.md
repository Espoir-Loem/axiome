# Journal des modifications

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/). Versions : [SemVer](https://semver.org/lang/fr/).

## [Non publié]
### Ajouté (outils de code, M7.7)
- **Génération composée (M7.7)** : `depth` compose jusqu'à N éditions sur des lignes distinctes et `extra_targets` étend la recherche à plusieurs fichiers. Chaque composition forme un patch complet soumis aux tests ; la recherche parcourt les états en largeur et partage un seul budget entre les profondeurs.
- Banc de génération porté à 16 tâches, dont deux éditions sur un fichier et deux éditions réparties sur deux fichiers, avec un budget propre à chaque tâche : `pass@1` 16/16, 0 échec silencieux. Le banc par rejeu reste à 0/3 avec son budget de quatre candidats.
- Une erreur de syntaxe dans un fichier cible lève `CodeSyntaxError`, avec chemin et ligne structurés, comme le reste de la couche `code`.

### Ajouté (outils de code, M7.1 à M7.3)
- **Analyse (M7.1)** : huit règles nommées (`import_inutilise`, `nom_non_utilise`, `code_mort`, `appel_inconnu`, `exception_avalee`, `comparaison_a_none`, `complexite_cyclomatique`, `cycle_import`). Chaque constat porte une règle, une position, la ligne citée et les faits qui le soutiennent. Les règles activées et le seuil de complexité se règlent dans `[tool.axiome.code]`.
- **Revue de diff (M7.1)** : le diff est appliqué en mémoire (le dépôt de l'utilisateur n'est jamais modifié), seuls les diagnostics nouveaux sont retenus, puis passés au `Reviewer` existant via `team.code_review`. Commandes `axiome --analyze CHEMIN` et `axiome --review DIFF`.
- **Bac à sable (M7.2)** : copie temporaire, délai mural, limites `resource` (CPU, mémoire, fichier, cœur), sortie plafonnée, environnement vidé (`AXIOME_*` et secrets absents, `PYTHONHASHSEED=0`, `TZ=UTC`). Le réseau est coupé par `unshare -n` quand c'est possible ; sinon le rapport le dit (`degraded_network`).
- **Génération vérifiée (M7.3, étendue en M7.4)** : recherche bornée et déterministe de petits correctifs (littéraux, booléens, comparaisons, `not`, opérateurs binaires, `and`/`or`, négation de condition et de `if` expression), chaque candidat exécuté par les tests du projet. Un patch n'est accepté que si les tests passent réellement ; budget épuisé → « je n'ai pas trouvé », avec le journal des rejets. Banc porté à 14 tâches : `pass@1` 14/14, 0 échec silencieux.
- Tests des quatre nouvelles familles de mutation, dont la négation d'une `if` expression.
- **Banc par rejeu (M7.5, élargi en M7.6)** : rejeu de vrais commits du dépôt, à l'envers. L'arbre du commit correctif est extrait, ses fichiers source sont ramenés à leur version parente, et ses tests doivent échouer avant toute mutation ; sinon la tâche est rejetée comme erreur d'intégrité. Le patch attendu n'est jamais lu. Corpus de trois tâches, dont une multi-fichiers : `pass@1` **0/3**, ce qui situe le travail restant au lieu de le masquer.
- **Bac à sable : la copie prime sur le paquet installé.** Les tests d'un projet importaient `axiome` depuis l'installation éditable (`-e .`) au lieu de l'arbre copié, ce qui faussait toute mesure sur les tests du projet. `PYTHONPATH` désigne désormais la copie, et un test unitaire le vérifie.
- **Bancs de code** (`evals/code/`) : revue étiquetée notée par règle (précision et rappel) et génération avec tests.
- Faits d'analyse ajoutés : `importe_sous`, `appel_simple`, `retourne`, `complexite`, `except_vide`, `compare_a_none`.
- RFC-0002 passée à « Implémenté ».

### Ajouté (outils de code, M7.0)
- Nouvelle couche `code`, en bibliothèque standard seule : lecture déterministe d'un dépôt (`source.py`), extraction du code en faits Datalog (`facts.py`) et index interrogeable (`index.py`).
- Prédicats `defines`, `references`, `imports`, `calls`, `parametre` et `ligne`. Les noms sont qualifiés par le module et par la définition englobante (`pkg.mod.Cls.method`) ; les positions s'écrivent `chemin:ligne` et sont citables.
- Requêtes `?-` sur l'index : `?- defines(Pos, Nom).`, avec réponses triées de façon canonique. Un fichier qui ne se parse pas est signalé avec sa ligne, jamais ignoré.
- RFC-0002 (jalon M7), 33 tests unitaires et de propriétés. Indexation mesurée : 10 000 lignes (60 fichiers, 45 000 faits) en 303 ms.

### Ajouté (mémoire du projet)
- Dossier `memoires/` : vision, état, architecture, journal des décisions, méthode d'évaluation, leçons, journal de session et feuille de route, pour qu'une autre session reprenne le travail avec le raisonnement suivi.

### Ajouté (suivi de la conversation)
- Axiome suit le fil : une relance courte reprend la dernière question sur un autre sujet (« et le tri rapide ? », « et celle de la recherche linéaire ? », « what about heapsort? »).
- Questions sans sujet résolues sur le sujet en cours : « est-il un mammifère ? », « c'est un animal ? », « et sa complexité ? ».
- « Pourquoi ? » seul explique la dernière réponse (chaîne de déduction, prérequis, propriété).
- Corrections : « non, je voulais dire une file », « I meant a queue ».
- « Développe », « plus de détails », « tell me more » : le dernier sujet, avec tout ce qui est vérifié.
- Traduction des mots connus : « et en anglais ? », « comment dit-on baleine en anglais ? », « and in French? ».
- Calcul enchaîné : « et fois 3 ? » repart du dernier résultat.
- « bien et toi ? » : Axiome répond aussi à la question.
- Banc d'évaluation `context` (24 conversations) et banc réservé (20 conversations) : 5/24 au départ, puis 24/24. Le banc réservé a obtenu 19/20 à sa première mesure ; l'échec venait d'un vrai défaut de motif (« je parlais d'une pile »), corrigé depuis.

### Ajouté (Wikidata)
- Lettres de l'alphabet : après « Tu parles de la lettre « L » ? », une confirmation (« oui », « je parle bien de la lettre l ») obtient une vraie réponse : rang dans l'alphabet, voyelle ou consonne, minuscule.
- **Apprentissage depuis Wikidata** (ADR-0008) : classes (`is_a`), noms FR/EN avec le genre grammatical (Wikidata Lexemes) et définition courte. Les métaclasses, les éléments d'homonymie et les noms non traduits sont écartés. La classification du vivant est suivie (taxon parent).
- Questions oui/non sur des concepts inconnus : Axiome les apprend à la demande, puis cherche un chemin de classification (« le lion est-il un mammifère ? » remonte une dizaine de rangs). Un « pourquoi » sur une longue lignée est résumé (« le lion est un Panthera, lui-même classé 5 rangs sous les mammifères »).
- Option `axiome --learn "sujet"` pour apprendre à l'avance. Variable `AXIOME_CONTACT` (facultative) pour le User-Agent demandé par Wikimedia.
- Requêtes HTTP : nouvelle tentative sur 429 ou 503, en respectant `Retry-After`.
- Pluriel des noms composés appris (« naines jaunes », « patrons de conception »).

### Modifié (Wikidata)
- Un fait PLAUSIBLE n'est plus nuancé dans chaque phrase : une seule note de fiabilité couvre la réponse.
- Une définition apprise (page web ou Wikidata) ouvre la réponse, avant les classes.
- Schéma de base v3 : genre et nom propre des mots appris (migration automatique des bases v2).

### Ajouté (évaluation)
- **Bancs d'évaluation** (`evals/`, `python -m axiome.evaluation`) : 105 cas de travail et 42 cas réservés, en français et en anglais, notés par catégorie, avec un rapport des échecs. Score : 61/105 au départ, puis 105/105 ; banc réservé à 38/42 (90 %) à sa première mesure.
- Calcul exact sur des fractions (« combien font 10 / 4 ? » donne 5/2, soit environ 2,5). Les opérations peuvent être écrites en mots (« fois », « divided by »). La division par zéro est signalée. Aucune exécution de code.
- Date et heure tirées de l'horloge (« quel jour sommes-nous ? », « what time is it? »). Pour la météo, Axiome dit qu'il n'y a pas accès.
- Questions oui/non sur une propriété (« le tri fusion est-il stable ? »). Réponse « Je ne sais pas » quand rien ne permet de l'établir.
- Prérequis (« la recherche dichotomique marche-t-elle sur une liste non triée ? » donne « Non. Elle exige une entrée triée. »).
- « Pourquoi » expliqué par la chaîne de déduction (« parce que le chat est un mammifère et les mammifères sont des vertébrés »). Une prémisse fausse est corrigée.
- Comparaison (« différence entre une pile et une file ») et choix d'un patron de conception d'après le besoin décrit.
- « Qui est… » et « pourquoi… » sur un sujet inconnu lancent une recherche.
- Relances sur le sujet en cours (« ses propriétés », « donne-moi un exemple »).
- Petite conversation : « salut, ça va ? », « t'es qui », « tu es une IA ? », « mdr », « hmm », « comment je m'appelle ? », « tu peux m'aider ? ».
- Le bruit clavier (« asdfghjkl ») et les demandes de code reçoivent une réponse honnête au lieu d'une recherche.
- Un fait appris de l'utilisateur est présenté comme tel (« Oui, d'après ce que tu m'as dit : … »). Les noms propres appris s'emploient sans article.

- Axiome retient qu'il vient de demander le prénom : « Espoir » seul est compris comme la réponse. Nouvelles formulations : « mon nom c'est… », « appelle-moi… », « my name's… ».
- « Quelles sont tes limites ? » : réponse honnête sur ce qu'Axiome ne sait pas faire.
- Pages d'homonymie : si la page qui porte le nom de la question est une page d'homonymie (« Le mot espoir peut désigner : »), Axiome dit que le mot a plusieurs sens et demande lequel. Il ne se rabat plus sur une page voisine sans rapport.

### Modifié
- Une question de définition commence par la définition quand Axiome en a une (« Un algorithme, c'est une suite finie d'instructions… »).
- Réponses mises en forme comme une bonne réponse humaine : phrase de tête qui résume (sujet en gras), détails en liste, une seule ligne de fiabilité, sources numérotées et citées [n]. Plus de « (plausible…) » répété dans chaque phrase.
- Wikipédia : lecture de l'introduction complète des articles. La page qui porte le titre de la question fournit la définition ; les autres pages du même site vont dans « Voir aussi ».

### Ajouté
- Messages incomplets (« h », « ? ») et questions coupées (« c'est quoi l ») : Axiome demande une précision au lieu de lancer une recherche.
- Correction des fautes de frappe sur le vocabulaire connu (« chta » → chat), annoncée dans la réponse.
- Petite conversation : « comment vas-tu », « ça va ? », « tu t'appelles comment », « je m'appelle… » (prénom mémorisé), « ok ». Une phrase qui s'adresse à Axiome ne déclenche jamais de recherche.
- Sources : DuckDuckGo (réponses instantanées), OpenAlex (recherche approfondie), Brave Search (`AXIOME_BRAVE_API_KEY`).
- **Conversation en streaming** (ADR-0007) : texte libre dans la CLI, session à événements (`dialogue/`), équipe interne Analyste, Planificateur, Chercheur, Vérificateur, Rédacteur, Relecteur (`team/`).
- **Paquets de langue FR/EN** (`data/lang/`) : lexique relié aux concepts, morphologie (articles, élisions, pluriels, contractions), gabarits de phrases, schémas d'intention. Les mots appris sont mémorisés (schéma de base v2).
- **Niveau adaptatif** débutant, intermédiaire ou expert, par domaine. Le contenu pour débutant est un sous-ensemble du contenu pour expert.
- **Recherche web** : Wikipédia (sans clé), Google Programmable Search et SearXNG (configurables), cache disque, extraction du texte principal, classement BM25, recoupement par organisation, apprentissage hors ligne.
- Réponse « Non » fondée sur les classes disjointes ; enseignement en langue naturelle (« Félix est un chat. »).
- `docs/signes-ia.md` : aucune tournure ni typographie typique des assistants IA, sauf demande explicite. Règle appliquée par le Relecteur et testée.
- Option `--offline` et variables `AXIOME_OFFLINE`, `AXIOME_GOOGLE_API_KEY`, `AXIOME_GOOGLE_CX`, `AXIOME_SEARXNG_URL`, `AXIOME_CACHE_DIR`.

### Retiré
- Dependabot : aucun bot ni agent IA ne doit apparaître comme contributeur. Les dépendances de développement sont mises à jour manuellement par les mainteneurs.

### Modifié
- Tout le code source est désormais en anglais (ADR-0005) : identifiants, commentaires, docstrings, messages d'erreur, vocabulaire de la base (`is_a`, `part_of`, `has_property`…) et mot-clé de négation `not`.
- Commandes CLI en anglais : `:proof`, `:conflicts`, `:rules`, `:help`, `:quit`, options `--memory` et `--command`.
### Ajouté
- Internationalisation : catalogues `locales/en.json` et `locales/fr.json`, option `--lang` et variable `AXIOME_LANG` (français par défaut).
- Test garantissant que les deux catalogues ont les mêmes clés et paramètres, et que chaque clé utilisée dans le code existe.

## [0.1.0] - 2026-11-10
### Ajouté
- **M0** : organisation du projet, CI multi-OS, porte de qualité (ruff, mypy --strict, couverture ≥ 90 %), ADR 0001 à 0004, vision, architecture.
- **M1** : langage logique AXL (Datalog stratifié, contraintes, règles étiquetées) et son analyseur.
- Moteur de saturation semi-naïf avec preuves canoniques, indépendantes de l'ordre d'insertion.
- Statuts épistémiques (règles E1 à E8) et révision des croyances (maillon faible, plafonds « hypothèse » et « monde clos », réfutation des contradictions).
- Base de connaissances SQLite avec provenance, et graine curée (taxonomie, structures de données, algorithmes, patrons de conception, SOLID, grandeurs SI).
- CLI : REPL et mode commande déterministe.
