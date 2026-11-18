# Journal des décisions

Format : date, décision, raison, alternatives écartées. Les décisions d'architecture ont aussi un ADR dans `docs/adr/`.

| Date | Décision | Raison | Écarté |
|---|---|---|---|
| 2026-11 | 100 % de zéro (ADR-0006) | Exigence du mainteneur | Poids ouverts, llama.cpp, API de LLM : ne plus jamais les proposer |
| 2026-11 | Assistant conversationnel à équipe interne (ADR-0007) | Le produit est un « LLM » honnête, pas encore un outil de code | Un générateur de texte unique sans relecture |
| 2026-11 | Textes affichés dans les paquets de langue et les catalogues, code en anglais (ADR-0005) | Ajouter une langue sans toucher au code | Chaînes françaises dans le code |
| 2026-11 | Mise en forme « à la Claude » autorisée dans `signes-ia.md` | Le mainteneur veut le résumé et la structure de Fable et Kimi. La décoration et le remplissage restent interdits. | Prose brute sans structure |
| 2026-11 | Une seule note de fiabilité par réponse | « (plausible : …) » répété dans chaque phrase était illisible | Une nuance par phrase. Elle reste pour NON VÉRIFIÉ et CONTESTÉ, plus graves. |
| 2026-11 | Message sans mot de 2 lettres → demande de précision ; une lettre seule → « tu parles de la lettre ? » | Le mainteneur a vu une recherche web lancée sur « h » | Chercher quand même |
| 2026-11 | Phrase adressée à Axiome (marqueurs personnels) non comprise → réponse de conversation, jamais de recherche | « comment vas tu » avait renvoyé la chanson « Si Tú Te Vas » | — |
| 2026-11-11 | Bancs d'évaluation : un banc de travail et un banc réservé | Mesurer la généralisation, pas l'ajustement aux cas | Un seul banc, corrigé en le regardant |
| 2026-11-11 | Calcul par AST et fractions, sans `eval` | Exactitude (10/4 = 5/2) et sécurité | `eval`, flottants |
| 2026-11-11 | Heure affichée dans le fuseau local (`Session(timezone=...)`), UTC dans les bancs | L'horloge stocke de l'UTC, l'utilisateur pense en heure locale | Afficher l'UTC |
| 2026-11-11 | Un fait appris de l'utilisateur seul donne « Oui, d'après ce que tu m'as dit : … » | Honnête et utile, alors qu'un « Non vérifié » sec agaçait | Refuser le oui |
| 2026-11-11 | Page d'homonymie titrée comme la question → « a plusieurs sens, lequel ? » | « espoir » avait renvoyé un parti politique | Prendre la page suivante |
| 2026-11-11 | Wikidata comme source structurée (ADR-0008), via l'API officielle seulement | Étendre la déduction sans saisie manuelle | Dumps complets (trop gros pour la première étape), aspiration de pages |
| 2026-11-11 | Wikidata : pour une classe, P279 seul ; P31 seulement pour les instances ; P171 pour les taxons | P31 sur une classe donne des métaclasses (« type d'objet astronomique ») | Prendre P31 et P279 ensemble |
| 2026-11-11 | Genre français tiré des Lexemes de Wikidata ; repli sur les terminaisons seulement à défaut | « un étoile » est inacceptable | Masculin par défaut |
| 2026-11-11 | Nom propre sans article seulement pour les personnes (P31 = Q5) | « le Soleil », « la Lune » prennent un article | Toute étiquette avec majuscule |
| 2026-11-11 | Une classe sans nom dans toutes les langues, ou au nom copié non traduit, n'est pas apprise | Éviter les phrases bilingues (« massive compact halo object ») | Garder le nom anglais |
| 2026-11-11 | Lien de classification cherché à la demande ; un élément portant le même nom anglais que le but compte comme le but | Wikidata sépare le taxon « mammifères » et la classe « mammifère » | Exiger l'identifiant exact |
| 2026-11-11 | `AXIOME_CONTACT` facultatif dans le User-Agent | Wikimedia le demande, mais aucune donnée personnelle ne part sans accord | Mettre l'adresse du mainteneur d'office |
| 2026-11-11 | Mémoire de conversation (`Context.last`, `expect`, `last_result`) | Le mainteneur veut qu'Axiome suive le fil | Analyse de chaque message isolément |
| 2026-11-11 | Prochaine étape conseillée : bases de connaissances locales (Wiktionary, puis ConceptNet, OpenStax, YAGO) | Savoir les bases à l'avance, comme un LLM, au lieu d'interroger le web à chaque question | Continuer seulement en ligne |
| 2026-11-18 | Le code est indexé comme des faits Datalog (`defines`, `references`, `calls`…), pas comme des objets Python | Les diagnostics héritent des preuves, de la révision et du déterminisme du noyau, et deviennent des requêtes | Un index ad hoc, invisible du raisonneur |
| 2026-11-18 | M7 avance dans l'ordre index (M7.0) → analyse et revue (M7.1) → bac à sable (M7.2) → génération (M7.3) | Aucune génération de code ne doit être annoncée avant que l'exécution puisse la vérifier | Générer d'abord, vérifier ensuite |
| 2026-11-18 | Un diagnostic d'analyse est `VÉRIFIÉ` (E3), avec position, ligne citée et faits de support ; sévérité fixée par la règle | Reproductible et citable, sans score opaque | Une heuristique avec un « score de qualité » |
| 2026-11-18 | La revue applique le diff en mémoire, pas dans une copie sur disque | Même résultat, et l'arbre de l'utilisateur ne peut pas être modifié par accident | Copie temporaire à chaque revue |
| 2026-11-18 | `import_inutilise` ignore les `__init__.py` | Un ré-export public n'est pas un import mort | Signaler les ré-exports |
| 2026-11-18 | `exception_avalee` ne vise que `except: pass` sans type | Un `except ResearchError: pass` avec repli volontaire n'est pas une erreur avalée | Signaler tout handler contenant `pass` |
| 2026-11-18 | Le réseau du bac à sable est coupé par `unshare -n` si possible, sinon le rapport le dit | Refuser d'exécuter partout serait impraticable ; mentir sur l'isolation serait pire | Supposer l'isolation toujours présente |
| 2026-11-18 | Génération = mutations déterministes bornées, jugées par les tests du projet ; jamais de réécriture complète | On peut montrer le patch et son verdict ; le budget épuisé est une réponse honnête | Générer du texte « plausible » sans exécution |
