# Vision et contraintes

## Ce que veut le mainteneur

Axiome est un assistant de conversation au sens d'un LLM, à la manière de Fable ou Kimi. Il doit :
- converser comme un expert, en français et en anglais ;
- adapter son niveau du débutant au professeur selon le domaine ;
- être honnête : dire « je ne sais pas », raisonner, chercher, puis répondre « d'après X, en résumé… » ;
- chercher sur tout le web, pas seulement sur Wikipédia ;
- répondre vite et en streaming ;
- travailler comme une équipe aux processus stricts, en décomposant chaque question du macro au nano ;
- suivre le fil de la conversation et comprendre le contexte ;
- connaître les bases : langues humaines, sciences, bon sens ;
- plus tard, coder proprement (jalon M7).

Le mainteneur compare sans cesse Axiome à Fable 5.5 et Kimi. Les réponses doivent avoir une mise en forme et un ton comparables : phrase de tête qui résume, détails en liste, sources numérotées. Pas de réponse « bête » : pas de recherche web sur « h » ou « comment vas-tu ».

## Règles non négociables

| Règle | Source | Conséquence |
|---|---|---|
| 100 % de zéro : aucun modèle pré-entraîné, aucune API de modèle | ADR-0006 | Ne jamais proposer llama.cpp, des poids ouverts ni une API de LLM. Les **données** libres (Wikidata, Wiktionary…) sont permises. |
| Tourne sur un PC de 8 Go de RAM, sans GPU | demande initiale | Bases filtrées et compilées en SQLite, rien de gros en mémoire. |
| Déterministe | ADR-0002 | Horloge injectable, cache web, ordre canonique partout. |
| Code source en anglais | ADR-0005 | Identifiants et commentaires en anglais. Les textes affichés vont dans `src/axiome/locales/*.json` et les paquets `src/axiome/data/lang/<code>/`. La documentation est en français. |
| Aucun agent IA ni bot comme contributeur | demande répétée | Jamais de `Co-Authored-By` IA ni de mention d'IA dans les commits. Dependabot retiré. Commits sous l'identité Git configurée du mainteneur. |
| Zéro signe d'écriture « IA » | `docs/signes-ia.md` | Ni flatterie, ni « en tant qu'IA », ni clôture stéréotypée, ni emoji, ni tiret cadratin de liaison, sauf demande explicite. Vaut aussi pour la documentation. |
| Pas d'aspiration de Google | conditions d'utilisation | Seulement des API officielles (Google CSE, Brave, SearXNG auto-hébergé). |
| Dépôt privé `Espoir-Loem/axiome` | | |

## Ce qui a été dit une fois et ne doit pas être répété

La parité avec un grand modèle de langue est impossible sans pré-entraînement massif. Le mainteneur le sait. On peut le rappeler en une phrase quand c'est utile, sans relancer le débat. Les écarts qui restent sont l'aisance d'écriture et la conversation libre hors des schémas connus. Le jalon M4 (petit modèle de langue maison en NumPy) vise l'aisance.
