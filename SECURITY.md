# Politique de sécurité

## Signaler une vulnérabilité
Ne pas ouvrir d'issue publique. Utilisez « Report a vulnerability » (GitHub Security Advisories) sur ce dépôt. Un accusé de réception est envoyé sous 72 h.

## Modèle de menaces

| Actif / surface | Menace | Mesure |
|---|---|---|
| Base de connaissances locale | Empoisonnement par des faits faux | Statuts épistémiques, révision des croyances ; un fait utilisateur n'est jamais au-dessus de NON VÉRIFIÉ |
| Graine (`data/seed`) | Modification malveillante | Revue obligatoire (CODEOWNERS), empreinte SHA-256 enregistrée |
| Connecteurs web (M3) | Contenu hostile, injection, SSRF | Liste blanche de domaines, analyse stricte, aucun contenu exécuté, délais et tailles bornés |
| Exécution de code (M5) | Évasion du bac à sable | Processus isolé, sans réseau, limites CPU, mémoire et temps, système de fichiers temporaire |
| Profil utilisateur (M6) | Fuite de données personnelles | Stockage **local uniquement**, rien n'est envoyé à un service externe |
| Poids de modèles (M2) | Poids altérés | Vérification SHA-256 avant chargement (`models/manifest.json`) |

## Versions prises en charge
Seule la dernière version mineure reçoit des correctifs de sécurité.
