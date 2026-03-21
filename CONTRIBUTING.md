# Guide de Contribution — G-Exam

Merci de votre intérêt pour contribuer à **G-Exam** ! Ce guide vous aidera à démarrer.

---

## Prérequis

Avant de contribuer, assurez-vous d'avoir installé :

- **Node.js** >= 18
- **pnpm** >= 8
- **Rust** (dernière version stable)
- **Visual Studio Build Tools** (Windows)
- **Git**

---

## Mise en place de l'environnement

```bash
# 1. Forker le dépôt sur GitHub

# 2. Cloner votre fork
git clone https://github.com/<votre-username>/exam-manager.git
cd exam-manager

# 3. Ajouter le dépôt original comme remote
git remote add upstream https://github.com/Stanyslas250/exam-manager.git

# 4. Installer les dépendances
pnpm install

# 5. Générer le client Prisma
pnpm prisma generate

# 6. Appliquer les migrations
pnpm prisma migrate deploy

# 7. Lancer l'application en mode développement
pnpm dev
```

---

## Workflow de contribution

### 1. Créer une branche

```bash
# Mettre à jour la branche principale
git checkout main
git pull upstream main

# Créer une branche pour votre contribution
git checkout -b feat/ma-fonctionnalite
```

### Conventions de nommage des branches

| Préfixe | Usage |
|---|---|
| `feat/` | Nouvelle fonctionnalité |
| `fix/` | Correction de bug |
| `docs/` | Documentation |
| `refactor/` | Refactoring de code |
| `style/` | Mise en forme (pas de changement de logique) |
| `test/` | Ajout ou modification de tests |

### 2. Développer

- Suivez les conventions de code existantes
- Gardez la logique métier dans `src/core/`
- Utilisez les composants shadcn/ui pour l'interface
- Typez tout avec TypeScript (pas de `any`)

### 3. Commit

Utilisez les [Conventional Commits](https://www.conventionalcommits.org/fr/) :

```
feat: ajouter l'export PDF des classements
fix: corriger le calcul de moyenne pondérée
docs: mettre à jour le README
refactor: simplifier la répartition en salles
style: formater les fichiers avec Prettier
```

### 4. Pousser et créer une Pull Request

```bash
git push origin feat/ma-fonctionnalite
```

Puis créez une Pull Request sur GitHub vers la branche `main`.

---

## Conventions de code

### TypeScript
- Typage strict, pas de `any`
- Interfaces préférées aux types pour les objets
- Noms de variables et fonctions en **camelCase**
- Noms de composants en **PascalCase**
- Noms de fichiers de composants en **PascalCase**

### React
- Composants fonctionnels uniquement
- Hooks personnalisés dans `src/hooks/`
- State management via **Zustand** dans `src/stores/`
- Pas de logique métier dans les composants — utiliser `src/core/`

### CSS
- **Tailwind CSS** uniquement (pas de CSS personnalisé sauf exception)
- Utiliser `cn()` pour la composition de classes conditionnelles

### Structure des fichiers

```
src/app/<module>/
├── page.tsx           # Page principale du module
└── components/        # Composants spécifiques au module
```

---

## Pull Requests

### Checklist avant soumission

- [ ] Le code compile sans erreurs (`pnpm build`)
- [ ] Le linting passe (`pnpm lint`)
- [ ] Les fonctionnalités existantes ne sont pas cassées
- [ ] Le code suit les conventions du projet
- [ ] La PR a une description claire de ce qui a été fait

### Revue de code

- Toute PR sera revue avant d'être fusionnée
- Soyez ouvert aux suggestions et commentaires
- Les discussions doivent rester constructives et respectueuses

---

## Signaler un bug

Utilisez les [GitHub Issues](https://github.com/Stanyslas250/exam-manager/issues) avec le template suivant :

1. **Description** — Décrivez le bug
2. **Étapes pour reproduire** — Comment reproduire le problème
3. **Comportement attendu** — Ce qui devrait se passer
4. **Comportement observé** — Ce qui se passe réellement
5. **Captures d'écran** — Si applicable
6. **Environnement** — Version de Windows, version de l'application

---

## Proposer une fonctionnalité

Ouvrez une [GitHub Issue](https://github.com/Stanyslas250/exam-manager/issues) en décrivant :

1. **Le problème** — Quel besoin cette fonctionnalité adresse
2. **La solution proposée** — Comment vous envisagez la solution
3. **Les alternatives** — Autres approches envisagées

---

## Architecture

### Principe fondamental

> La logique métier doit être centralisée dans `src/core/` et ne jamais être écrite directement dans les composants React.

### Couches de l'application

```
Composants React (UI) → Stores Zustand (état) → Core (logique métier) → Services (DB, fichiers)
```

---

## Licence

En contribuant à ce projet, vous acceptez que vos contributions soient sous la même licence [MIT](./LICENSE) que le projet.
