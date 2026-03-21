<div align="center">

# G-Exam

**Application desktop de gestion d'examens scolaires — 100 % offline**

[![Tauri](https://img.shields.io/badge/Tauri-2.x-blue?logo=tauri&logoColor=white)](https://tauri.app)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Prisma](https://img.shields.io/badge/Prisma-7.x-2D3748?logo=prisma&logoColor=white)](https://www.prisma.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

</div>

---

## À propos

**G-Exam** est une application desktop Windows permettant de centraliser et automatiser la gestion des examens scolaires : import des candidats, saisie des notes, calcul des moyennes, classements, statistiques et répartition en salles.

Destinée aux établissements scolaires, centres d'examen, inspections pédagogiques et secrétariats, elle fonctionne **entièrement hors-ligne** avec une base de données SQLite locale.

---

## Fonctionnalités

| Module | Description |
|---|---|
| **Gestion des examens** | Création, configuration du seuil de réussite, verrouillage |
| **Établissements** | Ajout, modification, suppression, statistiques par école |
| **Élèves** | Import Excel (.xlsx), saisie manuelle, recherche, tri |
| **Épreuves** | Définition des matières, coefficients, note maximale |
| **Saisie des notes** | Saisie par épreuve, validation, sauvegarde automatique |
| **Calculs** | Moyenne simple ou pondérée, taux de réussite |
| **Classements** | Classement des élèves et des établissements, gestion des ex æquo |
| **Statistiques** | Globales, par épreuve, par établissement, distribution des notes |
| **Répartition en salles** | Alphabétique, par établissement ou mixte |
| **Exports** | PDF et Excel : listes, résultats, classements, statistiques |
| **Sécurité** | Mot de passe administrateur, verrouillage définitif des notes |

---

## Stack technique

### Frontend
- **React 19** — Interface utilisateur
- **TypeScript 5.9** — Typage statique
- **Vite** (rolldown-vite) — Build tool
- **Tailwind CSS 4** — Styles utilitaires
- **shadcn/ui** — Composants UI (Radix UI)
- **Zustand** — State management
- **Recharts** — Graphiques et visualisations
- **Lucide React** — Icônes

### Desktop
- **Tauri 2** — Framework desktop natif

### Base de données
- **SQLite** — Stockage local
- **Prisma 7** — ORM

### Utilitaires
- **xlsx** — Import/export Excel
- **jsPDF + AutoTable** — Génération de PDF
- **Sonner** — Notifications toast

---

## Prérequis

- **Node.js** >= 18
- **pnpm** >= 8
- **Rust** (dernière version stable) — requis par Tauri
- **Visual Studio Build Tools** (Windows) — requis par Tauri

---

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/Stanyslas250/exam-manager.git
cd exam-manager

# Installer les dépendances
pnpm install

# Générer le client Prisma
pnpm prisma generate

# Appliquer les migrations
pnpm prisma migrate deploy
```

---

## Développement

```bash
# Lancer en mode développement (web uniquement)
pnpm dev

# Lancer en mode développement (desktop Tauri)
pnpm tauri dev
```

---

## Build de production

```bash
# Build de l'application desktop
pnpm tauri build
```

L'installateur sera généré dans `src-tauri/target/release/bundle/`.

---

## Structure du projet

```
exam-manager/
├── docs/                    # Documentation du projet
├── prisma/                  # Schéma et migrations Prisma
├── public/                  # Assets statiques
├── src/
│   ├── app/                 # Pages de l'application
│   │   ├── admin/           #   Administration
│   │   ├── dashboard/       #   Tableau de bord
│   │   ├── exam-setup/      #   Configuration d'examen
│   │   ├── exports/         #   Exports PDF/Excel
│   │   ├── rankings/        #   Classements
│   │   ├── rooms/           #   Répartition en salles
│   │   ├── schools/         #   Établissements
│   │   ├── scores/          #   Saisie des notes
│   │   ├── settings/        #   Paramètres
│   │   ├── statistics/      #   Statistiques
│   │   ├── students/        #   Élèves
│   │   └── subjects/        #   Épreuves
│   ├── components/          # Composants réutilisables
│   │   ├── common/          #   Composants partagés
│   │   ├── layout/          #   Sidebar, Header, PageContainer
│   │   └── security/        #   Composants de sécurité
│   ├── core/                # Logique métier centralisée
│   │   ├── calculations/    #   Moyennes, coefficients
│   │   ├── rankings/        #   Algorithmes de classement
│   │   └── room-dispatch/   #   Répartition en salles
│   ├── hooks/               # Hooks React personnalisés
│   ├── lib/                 # Utilitaires (export, Prisma, etc.)
│   ├── services/            # Services (DB, Excel, PDF)
│   ├── stores/              # Stores Zustand
│   └── types/               # Types TypeScript
├── src-tauri/               # Code Rust / Tauri
│   ├── src/                 #   Commandes Tauri
│   └── icons/               #   Icônes de l'application
├── package.json
├── prisma.config.ts
├── vite.config.ts
└── tsconfig.json
```

---

## Schéma de la base de données

```
Exam ──────┬── Student ──── Score
           │       │
           │       └── RoomAssignment
           │
           ├── Subject ──── Score
           │
           └── Room ──── RoomAssignment

School ──── Student
```

| Table | Description |
|---|---|
| `Exam` | Session d'examen (nom, année, seuil de réussite) |
| `School` | Établissement scolaire |
| `Student` | Élève / candidat |
| `Subject` | Épreuve / matière (coefficient, note max) |
| `Score` | Note d'un élève pour une épreuve |
| `Room` | Salle d'examen |
| `RoomAssignment` | Assignation d'un élève à une salle |

---

## Scripts disponibles

| Commande | Description |
|---|---|
| `pnpm dev` | Lancer le serveur de développement |
| `pnpm build` | Build de production (frontend) |
| `pnpm lint` | Lancer ESLint |
| `pnpm preview` | Prévisualiser le build |
| `pnpm tauri dev` | Lancer l'app desktop en dev |
| `pnpm tauri build` | Construire l'installateur desktop |
| `pnpm prisma generate` | Générer le client Prisma |
| `pnpm prisma migrate deploy` | Appliquer les migrations |

---

## Contribuer

Les contributions sont les bienvenues ! Consultez le guide [CONTRIBUTING.md](./CONTRIBUTING.md) pour commencer.

Veuillez respecter notre [Code de Conduite](./CODE_OF_CONDUCT.md).

---

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](./LICENSE) pour plus de détails.

---

## Remerciements

- [Tauri](https://tauri.app) — Framework desktop
- [shadcn/ui](https://ui.shadcn.com) — Composants UI
- [Prisma](https://prisma.io) — ORM
- [Recharts](https://recharts.org) — Graphiques
