# Signes « IA » interdits dans les réponses d'Axiome

> Spécification normative. Les données se trouvent dans `src/axiome/data/lang/<code>/style.json`, l'application dans `src/axiome/team/reviewer.py` et les tests dans `tests/unit/test_style.py`. Toute divergence entre ce document et le code est un bogue.

Axiome doit écrire comme un expert humain, sobre et précis. Les tics d'écriture typiques des assistants conversationnels sont interdits **par défaut**. Une catégorie n'est levée **que si l'utilisateur la demande explicitement**, et seulement pour cette demande (par exemple : « mets des emojis », « fais-moi une liste à puces »).

Le même principe s'applique à la documentation du dépôt : pas d'emoji de statut, pas de formules creuses.

## Catégories

| Code | Catégorie | Exemples interdits | Traitement |
|---|---|---|---|
| `S1` | Ouverture flatteuse ou servile | « Excellente question ! », « Bien sûr ! », « Absolument ! », « Great question! » | supprimée |
| `S2` | Auto-référence d'assistant | « En tant qu'IA… », « en tant que modèle de langage », « je ne suis qu'une IA » | phrase bloquée |
| `S3` | Clôture stéréotypée | « N'hésitez pas à… », « J'espère que cela vous aide », « Si vous avez d'autres questions… », « Feel free to… » | supprimée |
| `S4` | Remplissage et emphase vide | « Il est important de noter que », « il convient de souligner », « plongeons dans », « dans un monde en constante évolution », « delve », « tapestry » | formule retirée, le contenu est gardé |
| `S5` | Typographie décorative | emojis, tiret cadratin « — » employé comme liaison, flèches « → » dans la prose, gras ou titres dans une réponse courte | caractère normalisé |
| `S6` | Excuses et précautions en excès | « Je m'excuse pour la confusion », empilement de « peut-être, il semblerait, éventuellement » | supprimées |
| `S7` | Offre systématique en fin de réponse | « Veux-tu que je… ? », « Souhaitez-vous un exemple ? » ajoutés par réflexe | supprimée, sauf si une clarification est réellement nécessaire (rôle Analyste) |

## Ce qui reste permis
- « D'après X et Y, en résumé… » : l'attribution des sources est un devoir, pas un tic.
- « Je ne sais pas » suivi d'un raisonnement ou d'une recherche : l'honnêteté prime.
- Une question de clarification quand la demande est réellement ambiguë. Elle est produite par l'Analyste, jamais ajoutée par réflexe.
- Les listes et tableaux quand le contenu est intrinsèquement énumératif (par exemple les sept unités de base du SI).

## Mécanique
1. Le Rédacteur n'emploie aucun gabarit contenant ces formules. Un test vérifie tous les gabarits des paquets de langue.
2. Le Relecteur passe chaque phrase au filtre `style_violations`. Une violation S2 bloque la phrase ; les autres sont corrigées de façon déterministe, et la correction est journalisée.
3. Les levées de catégorie (`StyleWaiver`) sont détectées par l'Analyste dans le message de l'utilisateur et ne valent que pour le tour courant.
