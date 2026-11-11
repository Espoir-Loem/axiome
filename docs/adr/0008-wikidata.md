# ADR-0008 : apprendre les concepts et leurs classes depuis Wikidata

- **Statut** : Accepté
- **Date** : 2026-11-11

## Contexte
Axiome raisonne bien, mais seulement sur une centaine de concepts saisis à la main. Hors de ce périmètre, il ne peut que lire des pages web, qui donnent du texte et pas de classification. La question « le lion est-il un oiseau ? » restait donc sans réponse, alors que la déduction (le lion est un mammifère, un mammifère n'est pas un oiseau) est à sa portée.

## Décision
1. **Wikidata comme source de connaissances structurées.** C'est une base libre (CC0) : des données, pas un modèle. Son usage est donc conforme à l'ADR-0006. Seule l'API officielle est appelée (`wbsearchentities`, `wbgetentities`), au travers du cache disque.
2. **Ce qui est appris** pour un concept et ses classes (`knowledge/wikidata.py`, classe `Librarian`) :
   - `is_a` à partir de « sous-classe de » (P279) pour une classe, de « nature de l'élément » (P31) pour une instance, et de « taxon parent » (P171) pour le vivant ;
   - les noms en français et en anglais, avec le genre grammatical tiré de Wikidata Lexemes (P5185) ;
   - la description courte, comme définition, si rien d'autre ne définit déjà le concept.
3. **Prudence sur les données.**
   - Les métaclasses sont écartées : pour une classe, P31 est ignoré.
   - Une classe sans nom dans toutes les langues, ou dont le nom n'a pas été traduit, n'est pas apprise. Cela évite les phrases en deux langues.
   - Une arête qui fermerait un cycle est ignorée.
   - Les éléments d'homonymie ne deviennent jamais des concepts.
   - À orthographe égale, la casse tranche : « baleine » est l'animal, « Baleine » la constellation.
   - Seules les personnes (P31 = humain) s'emploient sans article.
4. **Statut épistémique.** Chaque fait garde Wikidata comme source. Une seule référence rend un fait PLAUSIBLE, pas CONFIRMÉ. La réponse le dit, une seule fois, dans la note de fiabilité.
5. **Deux usages.**
   - **À la demande :** quand une question oui/non porte sur un mot inconnu, ou quand la base ne permet pas de conclure, Axiome apprend les concepts puis cherche un chemin de classification entre les deux. Ce chemin peut remonter jusqu'à 20 niveaux, pour la classification du vivant.
   - **À l'avance :** `axiome --learn "sujet"`, puis réponses hors ligne.
6. **Politesse envers le service.**
   - Les requêtes sont envoyées une par une, espacées d'une demi-seconde.
   - Sur une réponse 429 ou 503, Axiome réessaie en respectant `Retry-After`.
   - Une adresse de contact peut être ajoutée au User-Agent (`AXIOME_CONTACT`), comme le demande Wikimedia. Elle n'est envoyée que si l'utilisateur la fournit.

## Conséquences
- La déduction s'applique à des dizaines de millions d'éléments, sans saisie manuelle.
- Un premier apprentissage prend quelques secondes à quelques dizaines de secondes, selon la profondeur et le débit accordé par Wikimedia. Les fois suivantes sont instantanées (base et cache).
- La qualité dépend de Wikidata. Ses erreurs deviennent des faits PLAUSIBLES : ils sont signalés comme tels et la révision des croyances peut les contester.
- Le schéma de base passe en v3 (genre et nom propre des mots appris). Les bases v2 sont migrées.
