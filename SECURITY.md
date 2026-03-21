# Politique de Sécurité — G-Exam

## Versions supportées

| Version | Supportée |
|---|---|
| 1.x (dernière) | Oui |
| < 1.0 | Non |

---

## Signaler une vulnérabilité

Si vous découvrez une vulnérabilité de sécurité dans G-Exam, veuillez la signaler de manière responsable.

### Comment signaler

1. **Ne créez PAS d'issue publique** pour les vulnérabilités de sécurité
2. Envoyez un e-mail à **stanyslas250@gmail.com** avec :
   - Une description détaillée de la vulnérabilité
   - Les étapes pour reproduire le problème
   - L'impact potentiel
   - Une suggestion de correction si possible

### Délai de réponse

- **Accusé de réception** : sous 48 heures
- **Évaluation initiale** : sous 7 jours
- **Correction** : selon la gravité, entre 7 et 30 jours

---

## Considérations de sécurité

### Architecture

G-Exam est une application **100 % offline**. Elle ne communique avec aucun serveur externe. Toutes les données sont stockées localement dans une base de données SQLite.

### Données locales

- La base de données SQLite est stockée sur le disque local de l'utilisateur
- Le mot de passe administrateur est hashé localement
- Aucune donnée n'est transmise via le réseau

### Bonnes pratiques pour les utilisateurs

- Protégez l'accès physique à la machine exécutant G-Exam
- Effectuez des sauvegardes régulières du fichier de base de données
- Ne partagez pas le mot de passe administrateur
- Verrouillez les notes après validation pour empêcher toute modification

---

## Dépendances

Les dépendances du projet sont régulièrement mises à jour pour intégrer les correctifs de sécurité. Si vous identifiez une dépendance vulnérable, merci de le signaler via le processus décrit ci-dessus.
