# Méthode d'évaluation

Le mainteneur a demandé de tester Axiome « comme on teste le dernier modèle de Gemini, Anthropic ou Kimi ». Voici la méthode retenue.

## Principe

- **Cas fixes, notés par catégorie, avec un rapport des échecs.** Ils sont dans `evals/suites/*.jsonl` (banc de travail) et `evals/heldout/*.jsonl` (banc réservé).
- **Exécution déterministe et hors ligne.** L'heure est fixée au 2026-11-11 à 9 h 30 UTC (`EVAL_TIME`). Le web est remplacé par `evals/fixtures/web.json`, avec des clés « question normalisée » et un préfixe de langue facultatif (`en:photon`).
- **Deux contrôles toujours actifs :** aucun signe IA et aucun plantage.
- `tests/integration/test_evaluation.py` exige 100 % sur les deux bancs : une régression casse la CI.

## Ne pas se tromper soi-même

1. **Mesurer avant de corriger.** On écrit le banc réservé avant de corriger, puis on le mesure une fois. Ce chiffre-là est le chiffre honnête.
2. **Ne pas corriger en regardant le banc réservé.** Une fois ses échecs corrigés, il ne mesure plus la généralisation : il faut en écrire un nouveau pour la passe suivante.
3. **Distinguer défaut d'Axiome et défaut du test.** Exemple : « tu sers à quoi » répondait bien (« j'explique… »), mais le test cherchait « expliquer ». On corrige alors le test, et on le note.
4. **Regarder les vraies réponses.** Un test vert ne garantit pas un bon texte. La passe sur les vraies réponses a révélé « Oui. » isolé suivi d'une puce, et « Oui, d'après ce que tu m'as dit. Parce que… ».
5. **Tester en réel ce qui touche au web.** Wikipédia et Wikidata réels ont révélé des défauts qu'aucune donnée enregistrée ne montrait : homonymies, métaclasses, libellés non traduits, HTTP 429.

## Commandes

```
.venv/bin/python -m axiome.evaluation evals           # rapport : evals/reports/latest.md
.venv/bin/python -m axiome.evaluation evals heldout   # rapport : evals/reports/heldout.md
```

Pour voir des réponses rendues sans réseau, utiliser un petit script : une `Session` avec `Kernel.in_memory(FixedClock(EVAL_TIME))`, puis `answer_text()`. Les sessions précédentes en gardaient un dans leur dossier temporaire ; il faut le recréer au besoin.

## Historique

| Étape | Travail | Réservé (1re mesure) |
|---|---|---|
| Départ | 61/105 (58 %) | — |
| Raisonnement, calcul, heure | 105/105 | 38/42 (90 %) |
| Usage réel (prénom, limites, homonymies) | 111/111 | — |
| Lettres | 114/114 | — |
| Suivi du fil | 138/138 (contexte : 5/24 au départ) | 19/20 (95 %) |
