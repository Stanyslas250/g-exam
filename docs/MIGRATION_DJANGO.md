# Guide de Migration : React/Tauri/Prisma → Django avec Templates

> **Document de référence** pour transformer le projet **Exam Manager** (React 19 + Tauri 2 + Prisma 7 + SQLite) en une application web **Django** avec templates HTML, rendu côté serveur.

---

## Table des matières

1. [Résumé du projet actuel](#1-résumé-du-projet-actuel)
2. [Architecture cible Django](#2-architecture-cible-django)
3. [Tableau de correspondance des technologies](#3-tableau-de-correspondance-des-technologies)
4. [Prérequis](#4-prérequis)
5. [Étape 1 — Initialisation du projet Django](#5-étape-1--initialisation-du-projet-django)
6. [Étape 2 — Modèles Django (ORM)](#6-étape-2--modèles-django-orm)
7. [Étape 3 — Administration Django](#7-étape-3--administration-django)
8. [Étape 4 — Vues et URLs](#8-étape-4--vues-et-urls)
9. [Étape 5 — Templates HTML](#9-étape-5--templates-html)
10. [Étape 6 — Fichiers statiques (CSS/JS)](#10-étape-6--fichiers-statiques-cssjs)
11. [Étape 7 — Logique métier (core)](#11-étape-7--logique-métier-core)
12. [Étape 8 — Authentification et sécurité](#12-étape-8--authentification-et-sécurité)
13. [Étape 9 — Import/Export Excel](#13-étape-9--importexport-excel)
14. [Étape 10 — Export PDF](#14-étape-10--export-pdf)
15. [Étape 11 — Formulaires Django](#15-étape-11--formulaires-django)
16. [Étape 12 — Migration des données existantes](#16-étape-12--migration-des-données-existantes)
17. [Étape 13 — Tests](#17-étape-13--tests)
18. [Étape 14 — Déploiement](#18-étape-14--déploiement)
19. [Mapping détaillé fichier par fichier](#19-mapping-détaillé-fichier-par-fichier)
20. [Commandes Django essentielles](#20-commandes-django-essentielles)
21. [Structure finale du projet Django](#21-structure-finale-du-projet-django)
22. [Ordre de migration recommandé](#22-ordre-de-migration-recommandé)
23. [Pièges à éviter](#23-pièges-à-éviter)

---

## 1. Résumé du projet actuel

### Stack technique actuelle

| Couche | Technologie | Rôle |
|---|---|---|
| **Frontend** | React 19 + TypeScript | Interface utilisateur SPA |
| **Styling** | Tailwind CSS 4 + shadcn/ui (Radix) | Composants et styles |
| **State** | Zustand (localStorage persist) | Gestion d'état client |
| **Desktop** | Tauri 2 (Rust) | Wrapper desktop natif |
| **ORM** | Prisma 7 | Accès base de données |
| **Base de données** | SQLite | Stockage local |
| **PDF** | jsPDF + AutoTable | Génération de documents |
| **Excel** | xlsx (SheetJS) | Import/export fichiers Excel |
| **Icônes** | Lucide React | Icônes SVG |
| **Graphiques** | Recharts | Visualisations statistiques |
| **Notifications** | Sonner | Messages toast |

### Architecture actuelle

```
┌─────────────────────────────────────────────┐
│                 Tauri (Rust)                 │  ← Wrapper desktop
├─────────────────────────────────────────────┤
│            React 19 + TypeScript            │  ← SPA, routing client
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Pages   │  │Components│  │  Stores    │ │
│  │ (12 app) │  │ (UI/layout│  │ (Zustand) │ │
│  └────┬─────┘  └──────────┘  └─────┬─────┘ │
│       │                             │       │
│  ┌────┴─────────────────────────────┴────┐  │
│  │         Services (Prisma Client)      │  │
│  └───────────────────┬───────────────────┘  │
│                      │                      │
│  ┌───────────────────┴───────────────────┐  │
│  │         Core (logique métier)         │  │
│  │  calculations | rankings | statistics │  │
│  │           room-dispatch               │  │
│  └───────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│               SQLite (Prisma)               │  ← Base de données locale
└─────────────────────────────────────────────┘
```

### Pages de l'application (12 pages)

| Page | ID | Description |
|---|---|---|
| Tableau de bord | `dashboard` | Vue d'ensemble de l'examen |
| Configuration | `exam-setup` | Paramètres de l'examen |
| Établissements | `schools` | CRUD établissements |
| Élèves | `students` | CRUD élèves, import Excel |
| Épreuves | `subjects` | CRUD matières, coefficients |
| Notes | `scores` | Saisie des notes par épreuve |
| Classements | `rankings` | Classement élèves et écoles |
| Statistiques | `statistics` | Graphiques et analyses |
| Salles | `rooms` | Répartition en salles |
| Exports | `exports` | Export PDF et Excel |
| Paramètres | `settings` | Mentions, documents, config |
| Administration | `admin` | Sécurité, gestion BD |

### Modèles de données actuels (Prisma)

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

**7 entités** : `Exam`, `School`, `Student`, `Subject`, `Score`, `Room`, `RoomAssignment`

---

## 2. Architecture cible Django

```
┌─────────────────────────────────────────────┐
│              Django (Python)                 │
├─────────────────────────────────────────────┤
│              Templates HTML                 │  ← Rendu côté serveur
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Pages   │  │Partials/ │  │  Statiques│ │
│  │ (templates│  │ includes │  │ (CSS/JS)  │ │
│  └────┬─────┘  └──────────┘  └───────────┘ │
│       │                                     │
│  ┌────┴─────────────────────────────────┐   │
│  │    Views (CBV ou FBV) + URLs         │   │
│  └───────────────────┬──────────────────┘   │
│                      │                      │
│  ┌───────────────────┴──────────────────┐   │
│  │         Forms (Django Forms)         │   │
│  └───────────────────┬──────────────────┘   │
│                      │                      │
│  ┌───────────────────┴──────────────────┐   │
│  │   Services / Utils (logique métier)  │   │
│  │  calculations | rankings | statistics│   │
│  └───────────────────┬──────────────────┘   │
│                      │                      │
│  ┌───────────────────┴──────────────────┐   │
│  │        Models (Django ORM)           │   │
│  └───────────────────┬──────────────────┘   │
├──────────────────────┴──────────────────────┤
│              SQLite (Django DB)              │
└─────────────────────────────────────────────┘
```

---

## 3. Tableau de correspondance des technologies

| Concept actuel | Technologie actuelle | Équivalent Django |
|---|---|---|
| Composants UI | React + shadcn/ui | Django Templates + Bootstrap 5 / Tailwind |
| Routing | Zustand navigationStore | `django.urls` (URLconf) |
| State management | Zustand stores | Vues + sessions Django |
| ORM | Prisma 7 | Django ORM |
| Migrations DB | `prisma migrate` | `python manage.py makemigrations` / `migrate` |
| Validation formulaires | React state + validations manuelles | `django.forms` |
| Authentification | Tauri invoke (verify_admin) | `django.contrib.auth` |
| Sessions | localStorage (Zustand persist) | `django.contrib.sessions` |
| Export PDF | jsPDF + AutoTable | ReportLab ou WeasyPrint |
| Export Excel | xlsx (SheetJS) | openpyxl |
| Import Excel | xlsx (SheetJS) | openpyxl |
| Notifications toast | Sonner | Django messages framework |
| Icônes | Lucide React | Bootstrap Icons / Lucide (CDN) / Font Awesome |
| Graphiques | Recharts | Chart.js (via CDN) |
| Fichiers statiques | Vite (bundler) | `django.contrib.staticfiles` |
| Serveur de développement | `vite dev` | `python manage.py runserver` |
| Variables d'environnement | `.env` + dotenv | `python-dotenv` ou `django-environ` |

---

## 4. Prérequis

### Logiciels à installer

- **Python** >= 3.11 → [python.org](https://www.python.org/downloads/)
- **pip** (inclus avec Python)
- **virtualenv** ou **venv** (inclus avec Python 3)

### Dépendances Python principales

```
Django>=5.1
openpyxl>=3.1       # Import/export Excel
reportlab>=4.0      # Export PDF
django-environ>=0.11 # Variables d'environnement
Pillow>=10.0        # Gestion images (optionnel)
```

---

## 5. Étape 1 — Initialisation du projet Django

### 5.1. Créer l'environnement virtuel

```bash
# Dans un NOUVEAU dossier (ou à la racine du repo existant)
python -m venv venv

# Activer l'environnement (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activer l'environnement (Linux/Mac)
source venv/bin/activate
```

### 5.2. Installer Django

```bash
pip install django
```

### 5.3. Créer le projet Django

```bash
# Crée le projet racine "g-exam"
django-admin startproject g-exam .
```

> **Note :** Le `.` final crée le projet dans le dossier courant (pas de sous-dossier supplémentaire).

Cette commande crée :
```
manage.py
g-exam/
    __init__.py
    settings.py
    urls.py
    asgi.py
    wsgi.py
```

### 5.4. Créer l'application principale

```bash
python manage.py startapp exams
```

Cette commande crée :
```
exams/
    __init__.py
    admin.py
    apps.py
    models.py
    tests.py
    views.py
    migrations/
        __init__.py
```

### 5.5. Enregistrer l'application dans `settings.py`

```python
# g-exam/settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Application personnalisée
    'exams',
]
```

### 5.6. Configurer la base de données SQLite

SQLite est la base **par défaut** dans Django. Rien à changer dans `settings.py` :

```python
# g-exam/settings.py (déjà configuré par défaut)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### 5.7. Configurer la langue et le fuseau horaire

```python
# g-exam/settings.py
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True
```

---

## 6. Étape 2 — Modèles Django (ORM)

### 6.1. Correspondance Prisma → Django ORM

Voici le mapping de chaque modèle Prisma vers un modèle Django.

#### Prisma `Exam` → Django `Exam`

```python
# exams/models.py

from django.db import models


class Exam(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom de l'examen")
    year = models.IntegerField(verbose_name="Année")
    passing_grade = models.FloatField(default=10.0, verbose_name="Seuil de réussite")
    is_locked = models.BooleanField(default=False, verbose_name="Verrouillé")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Examen"
        verbose_name_plural = "Examens"

    def __str__(self):
        return f"{self.name} ({self.year})"
```

**Correspondances de champs :**

| Prisma | Django | Notes |
|---|---|---|
| `@id @default(autoincrement())` | `id` auto (implicite) | Django ajoute un `id` auto par défaut |
| `String` | `CharField(max_length=...)` | Django exige `max_length` |
| `Int` | `IntegerField()` | |
| `Float` | `FloatField()` | |
| `Boolean @default(false)` | `BooleanField(default=False)` | |
| `DateTime @default(now())` | `DateTimeField(auto_now_add=True)` | |
| `DateTime @updatedAt` | `DateTimeField(auto_now=True)` | |

#### Prisma `School` → Django `School`

```python
class School(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom")
    code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Code")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Établissement"
        verbose_name_plural = "Établissements"

    def __str__(self):
        return self.name
```

#### Prisma `Student` → Django `Student`

```python
class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]

    candidate_number = models.CharField(
        max_length=20, unique=True, verbose_name="N° Candidat"
    )
    first_name = models.CharField(max_length=255, verbose_name="Prénom")
    last_name = models.CharField(max_length=255, verbose_name="Nom")
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Sexe"
    )
    birth_date = models.DateField(blank=True, null=True, verbose_name="Date de naissance")
    is_absent = models.BooleanField(default=False, verbose_name="Absent")
    created_at = models.DateTimeField(auto_now_add=True)

    # Relations (ForeignKey = clé étrangère)
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='students', verbose_name="Examen"
    )
    school = models.ForeignKey(
        School, on_delete=models.PROTECT, related_name='students', verbose_name="Établissement"
    )

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        indexes = [
            models.Index(fields=['exam']),
            models.Index(fields=['school']),
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.candidate_number})"
```

**Correspondances des relations :**

| Prisma | Django | Notes |
|---|---|---|
| `@relation(fields: [examId], references: [id], onDelete: Cascade)` | `ForeignKey(Exam, on_delete=models.CASCADE)` | |
| `@relation(fields: [schoolId], references: [id])` | `ForeignKey(School, on_delete=models.PROTECT)` | PROTECT empêche la suppression d'une école ayant des élèves |
| `related_name='students'` | — | Accès inverse : `exam.students.all()` |

#### Prisma `Subject` → Django `Subject`

```python
class Subject(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom de l'épreuve")
    coefficient = models.FloatField(blank=True, null=True, verbose_name="Coefficient")
    max_score = models.FloatField(default=20.0, verbose_name="Note maximale")
    created_at = models.DateTimeField(auto_now_add=True)

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='subjects', verbose_name="Examen"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Épreuve"
        verbose_name_plural = "Épreuves"
        indexes = [
            models.Index(fields=['exam']),
        ]

    def __str__(self):
        return self.name
```

#### Prisma `Score` → Django `Score`

```python
class Score(models.Model):
    value = models.FloatField(verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='scores', verbose_name="Élève"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='scores', verbose_name="Épreuve"
    )

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        # Contrainte unique : un élève ne peut avoir qu'une note par épreuve
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'subject'],
                name='unique_score_per_student_subject'
            ),
        ]
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['subject']),
        ]

    def __str__(self):
        return f"{self.student} - {self.subject}: {self.value}"
```

#### Prisma `Room` → Django `Room`

```python
class Room(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom de la salle")
    capacity = models.IntegerField(verbose_name="Capacité")
    created_at = models.DateTimeField(auto_now_add=True)

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='rooms', verbose_name="Examen"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Salle"
        verbose_name_plural = "Salles"
        indexes = [
            models.Index(fields=['exam']),
        ]

    def __str__(self):
        return self.name
```

#### Prisma `RoomAssignment` → Django `RoomAssignment`

```python
class RoomAssignment(models.Model):
    seat_number = models.IntegerField(blank=True, null=True, verbose_name="N° de place")
    created_at = models.DateTimeField(auto_now_add=True)

    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name='room_assignment',
        verbose_name="Élève"
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='assignments', verbose_name="Salle"
    )

    class Meta:
        verbose_name = "Assignation"
        verbose_name_plural = "Assignations"
        indexes = [
            models.Index(fields=['room']),
        ]

    def __str__(self):
        return f"{self.student} → {self.room}"
```

> **Note :** `OneToOneField` remplace la contrainte `@unique` sur `studentId` dans Prisma. Un élève ne peut être assigné qu'à une seule salle.

### 6.2. Appliquer les migrations

```bash
# Générer les fichiers de migration à partir des modèles
python manage.py makemigrations exams

# Appliquer les migrations (crée les tables dans la base SQLite)
python manage.py migrate
```

**Équivalences Prisma → Django :**

| Prisma | Django |
|---|---|
| `prisma migrate dev` | `python manage.py makemigrations` + `python manage.py migrate` |
| `prisma generate` | Pas nécessaire (Django ORM est dynamique) |
| `prisma db push` | `python manage.py migrate` |
| `prisma studio` | `python manage.py runserver` puis `/admin/` |

---

## 7. Étape 3 — Administration Django

Django offre une interface d'administration **gratuite** et puissante. Elle remplace en grande partie la page **Admin** du projet actuel.

### 7.1. Créer un superutilisateur

```bash
python manage.py createsuperuser
```

> Entrez un nom d'utilisateur, email et mot de passe. Ce compte remplace le `ADMIN_PASSWORD` du `.env` actuel.

### 7.2. Enregistrer les modèles dans l'admin

```python
# exams/admin.py

from django.contrib import admin
from .models import Exam, School, Student, Subject, Score, Room, RoomAssignment


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'passing_grade', 'is_locked', 'created_at')
    list_filter = ('is_locked', 'year')
    search_fields = ('name',)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('candidate_number', 'last_name', 'first_name', 'gender', 'exam', 'school', 'is_absent')
    list_filter = ('exam', 'school', 'gender', 'is_absent')
    search_fields = ('last_name', 'first_name', 'candidate_number')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'coefficient', 'max_score', 'exam')
    list_filter = ('exam',)


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'value', 'updated_at')
    list_filter = ('subject',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'exam')
    list_filter = ('exam',)


@admin.register(RoomAssignment)
class RoomAssignmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'seat_number')
    list_filter = ('room',)
```

Accessible à l'URL : `http://127.0.0.1:8000/admin/`

---

## 8. Étape 4 — Vues et URLs

### 8.1. Correspondance Pages React → Vues Django

Chaque page React devient une **vue Django** avec son **URL** et son **template**.

| Page React | URL Django | Vue Django | Template |
|---|---|---|---|
| `DashboardPage` | `/` | `dashboard_view` | `dashboard.html` |
| `ExamSetupPage` | `/exam/setup/` | `exam_setup_view` | `exam_setup.html` |
| `SchoolsPage` | `/schools/` | `schools_list_view` | `schools/list.html` |
| `StudentsPage` | `/students/` | `students_list_view` | `students/list.html` |
| `SubjectsPage` | `/subjects/` | `subjects_list_view` | `subjects/list.html` |
| `ScoresPage` | `/scores/` | `scores_view` | `scores/index.html` |
| `RankingsPage` | `/rankings/` | `rankings_view` | `rankings/index.html` |
| `StatisticsPage` | `/statistics/` | `statistics_view` | `statistics/index.html` |
| `RoomsPage` | `/rooms/` | `rooms_view` | `rooms/index.html` |
| `ExportsPage` | `/exports/` | `exports_view` | `exports/index.html` |
| `SettingsPage` | `/settings/` | `settings_view` | `settings/index.html` |
| `AdminPage` | `/admin/` | Admin Django natif | Admin Django |

### 8.2. Exemple de vue (Function-Based View)

```python
# exams/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Exam, Student, School, Subject, Score


@login_required
def dashboard_view(request):
    """Tableau de bord — Vue d'ensemble de l'examen actif."""
    # Récupérer l'examen actif (le plus récent non verrouillé)
    exam = Exam.objects.filter(is_locked=False).order_by('-created_at').first()

    context = {
        'exam': exam,
        'candidates_count': 0,
        'subjects_count': 0,
        'passed_count': 0,
        'failed_count': 0,
    }

    if exam:
        students = exam.students.all()
        context['candidates_count'] = students.count()
        context['subjects_count'] = exam.subjects.count()
        # ... calculs des admis/ajournés

    return render(request, 'exams/dashboard.html', context)
```

### 8.3. Configuration des URLs

```python
# exams/urls.py

from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Examen
    path('exam/setup/', views.exam_setup_view, name='exam_setup'),
    path('exam/<int:pk>/lock/', views.exam_lock_view, name='exam_lock'),

    # Établissements
    path('schools/', views.schools_list_view, name='schools_list'),
    path('schools/create/', views.school_create_view, name='school_create'),
    path('schools/<int:pk>/edit/', views.school_edit_view, name='school_edit'),
    path('schools/<int:pk>/delete/', views.school_delete_view, name='school_delete'),

    # Élèves
    path('students/', views.students_list_view, name='students_list'),
    path('students/create/', views.student_create_view, name='student_create'),
    path('students/<int:pk>/edit/', views.student_edit_view, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete_view, name='student_delete'),
    path('students/import/', views.students_import_view, name='students_import'),

    # Épreuves
    path('subjects/', views.subjects_list_view, name='subjects_list'),
    path('subjects/create/', views.subject_create_view, name='subject_create'),
    path('subjects/<int:pk>/edit/', views.subject_edit_view, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete_view, name='subject_delete'),

    # Notes
    path('scores/', views.scores_view, name='scores'),
    path('scores/subject/<int:subject_id>/', views.scores_by_subject_view, name='scores_by_subject'),

    # Classements
    path('rankings/', views.rankings_view, name='rankings'),

    # Statistiques
    path('statistics/', views.statistics_view, name='statistics'),

    # Salles
    path('rooms/', views.rooms_view, name='rooms'),
    path('rooms/dispatch/', views.rooms_dispatch_view, name='rooms_dispatch'),

    # Exports
    path('exports/', views.exports_view, name='exports'),
    path('exports/pdf/<str:doc_type>/', views.export_pdf_view, name='export_pdf'),
    path('exports/excel/<str:doc_type>/', views.export_excel_view, name='export_excel'),

    # Paramètres
    path('settings/', views.settings_view, name='settings'),
]
```

```python
# g-exam/urls.py (fichier racine)

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('exams.urls')),
]
```

---

## 9. Étape 5 — Templates HTML

### 9.1. Configuration des templates

```python
# g-exam/settings.py

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Templates globaux
        'APP_DIRS': True,  # Cherche dans chaque app/templates/
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

### 9.2. Template de base (layout)

Remplace les composants React `Sidebar`, `Header` et le layout de `App.tsx` :

```html
<!-- templates/base.html -->
{% load static %}
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}G-Exam{% endblock %}</title>
    <!-- Tailwind CSS via CDN (ou build local) -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js pour les graphiques (remplace Recharts) -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Lucide Icons via CDN -->
    <script src="https://unpkg.com/lucide@latest"></script>
    {% block extra_head %}{% endblock %}
</head>
<body class="flex h-screen bg-gray-50">

    <!-- Sidebar (remplace le composant React Sidebar) -->
    {% include "partials/sidebar.html" %}

    <!-- Zone principale -->
    <div class="flex-1 flex flex-col min-w-0">
        <!-- Header (remplace le composant React Header) -->
        {% include "partials/header.html" %}

        <!-- Contenu de la page -->
        <main class="flex-1 overflow-auto p-6">
            <!-- Messages Django (remplace Sonner/toast) -->
            {% if messages %}
            <div class="mb-4">
                {% for message in messages %}
                <div class="p-4 rounded-lg mb-2
                    {% if message.tags == 'success' %}bg-green-100 text-green-800
                    {% elif message.tags == 'error' %}bg-red-100 text-red-800
                    {% elif message.tags == 'warning' %}bg-yellow-100 text-yellow-800
                    {% else %}bg-blue-100 text-blue-800{% endif %}">
                    {{ message }}
                </div>
                {% endfor %}
            </div>
            {% endif %}

            {% block content %}{% endblock %}
        </main>
    </div>

</body>
</html>
```

### 9.3. Sidebar (partial)

```html
<!-- templates/partials/sidebar.html -->
<aside class="w-64 bg-white border-r flex flex-col">
    <div class="p-4 border-b">
        <h1 class="text-xl font-bold">G-Exam</h1>
    </div>
    <nav class="flex-1 p-4 space-y-1">
        <a href="{% url 'exams:dashboard' %}"
           class="flex items-center px-3 py-2 rounded-lg hover:bg-gray-100
                  {% if request.resolver_match.url_name == 'dashboard' %}bg-gray-100 font-semibold{% endif %}">
            Tableau de bord
        </a>
        <a href="{% url 'exams:exam_setup' %}"
           class="flex items-center px-3 py-2 rounded-lg hover:bg-gray-100
                  {% if request.resolver_match.url_name == 'exam_setup' %}bg-gray-100 font-semibold{% endif %}">
            Configuration
        </a>
        <!-- ... autres liens -->
    </nav>
</aside>
```

### 9.4. Exemple de page template

```html
<!-- templates/exams/schools/list.html -->
{% extends "base.html" %}

{% block title %}Établissements — G-Exam{% endblock %}

{% block content %}
<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h2 class="text-2xl font-bold">Établissements</h2>
        <a href="{% url 'exams:school_create' %}" class="btn btn-primary">
            + Ajouter
        </a>
    </div>

    <table class="w-full bg-white rounded-lg shadow">
        <thead>
            <tr class="border-b">
                <th class="px-4 py-3 text-left">Nom</th>
                <th class="px-4 py-3 text-left">Code</th>
                <th class="px-4 py-3 text-left">Élèves</th>
                <th class="px-4 py-3 text-right">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for school in schools %}
            <tr class="border-b hover:bg-gray-50">
                <td class="px-4 py-3">{{ school.name }}</td>
                <td class="px-4 py-3">{{ school.code|default:"-" }}</td>
                <td class="px-4 py-3">{{ school.students.count }}</td>
                <td class="px-4 py-3 text-right">
                    <a href="{% url 'exams:school_edit' school.pk %}">Modifier</a>
                    <a href="{% url 'exams:school_delete' school.pk %}">Supprimer</a>
                </td>
            </tr>
            {% empty %}
            <tr>
                <td colspan="4" class="px-4 py-8 text-center text-gray-500">
                    Aucun établissement enregistré.
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

---

## 10. Étape 6 — Fichiers statiques (CSS/JS)

### 10.1. Configuration

```python
# g-exam/settings.py

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### 10.2. Structure des fichiers statiques

```
static/
├── css/
│   └── style.css          # Styles personnalisés
├── js/
│   └── app.js             # JavaScript personnalisé (Chart.js, etc.)
└── img/
    └── logo.png           # Logo G-Exam
```

### 10.3. Collecte des fichiers statiques (production)

```bash
python manage.py collectstatic
```

---

## 11. Étape 7 — Logique métier (core)

Le module `src/core/` contient des fonctions **pures** (sans dépendances UI). Elles se traduisent directement en fonctions Python.

### 11.1. Calcul des moyennes

**Fichier actuel :** `src/core/calculations/average.ts`
**Fichier Django :** `exams/services/calculations.py`

```python
# exams/services/calculations.py

from typing import Optional


def calculate_student_average(
    scores: list[dict],
    target_scale: float = 20.0,
) -> Optional[float]:
    """
    Calcule la moyenne d'un élève.

    Chaque score est un dict : {
        'value': float,
        'coefficient': float | None,
        'max_score': float | None,
    }

    Règles :
    - Si au moins un coefficient est défini → moyenne pondérée
    - Sinon → moyenne simple
    - Si des maxScore différents → normalisation vers target_scale
    """
    valid_scores = [s for s in scores if s.get('value') is not None]
    if not valid_scores:
        return None

    has_coefficients = any(
        s.get('coefficient') is not None and s['coefficient'] > 0
        for s in valid_scores
    )
    has_variable_max = any(
        s.get('max_score') is not None and s['max_score'] > 0
        for s in valid_scores
    )

    if has_variable_max:
        if has_coefficients:
            total_weighted = 0.0
            total_coef = 0.0
            for s in valid_scores:
                coef = s.get('coefficient') or 1.0
                max_score = s.get('max_score') or target_scale
                normalized = (s['value'] / max_score) * target_scale if max_score > 0 else 0
                total_weighted += normalized * coef
                total_coef += coef
            return round(total_weighted / total_coef, 2) if total_coef > 0 else None
        else:
            total_score = sum(s['value'] for s in valid_scores)
            total_max = sum((s.get('max_score') or target_scale) for s in valid_scores)
            return round((total_score / total_max) * target_scale, 2) if total_max > 0 else None
    else:
        if has_coefficients:
            total_weighted = 0.0
            total_coef = 0.0
            for s in valid_scores:
                coef = s.get('coefficient') or 1.0
                total_weighted += s['value'] * coef
                total_coef += coef
            return round(total_weighted / total_coef, 2) if total_coef > 0 else None
        else:
            total = sum(s['value'] for s in valid_scores)
            return round(total / len(valid_scores), 2)
```

### 11.2. Classement des élèves

**Fichier actuel :** `src/core/rankings/studentRanking.ts`
**Fichier Django :** `exams/services/rankings.py`

```python
# exams/services/rankings.py

def rank_students(students: list[dict]) -> list[dict]:
    """
    Classe les élèves par moyenne décroissante avec gestion des ex-aequo.

    Entrée : [{'student_id': int, 'average': float}, ...]
    Sortie : [{'student_id': int, 'average': float, 'rank': int}, ...]
    """
    if not students:
        return []

    sorted_students = sorted(students, key=lambda s: (-s['average'], s['student_id']))

    ranked = []
    current_rank = 1
    for i, student in enumerate(sorted_students):
        if i > 0 and student['average'] != sorted_students[i - 1]['average']:
            current_rank = i + 1
        ranked.append({**student, 'rank': current_rank})

    return ranked
```

### 11.3. Statistiques globales

**Fichier actuel :** `src/core/statistics/globalStats.ts`
**Fichier Django :** `exams/services/statistics.py`

### 11.4. Répartition en salles

**Fichier actuel :** `src/core/room-dispatch/alphabeticalDispatch.ts`
**Fichier Django :** `exams/services/room_dispatch.py`

---

## 12. Étape 8 — Authentification et sécurité

### 12.1. Remplacement du système actuel

| Actuel | Django |
|---|---|
| `ADMIN_PASSWORD` dans `.env` | `django.contrib.auth` (User model) |
| `verifyAdminPassword()` via Tauri invoke | `authenticate()` / `login()` Django |
| `securityStore` (Zustand) | Session Django côté serveur |
| `LockScreen` composant React | Page de login Django |
| Session timeout (30 min) | `SESSION_COOKIE_AGE` dans settings |

### 12.2. Configuration

```python
# g-exam/settings.py

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
SESSION_COOKIE_AGE = 1800  # 30 minutes (comme l'actuel)
```

### 12.3. Vues d'authentification

```python
# exams/urls.py (ajouter)

from django.contrib.auth import views as auth_views

urlpatterns += [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
```

### 12.4. Protection des vues

```python
# Sur chaque vue qui nécessite une authentification
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    ...
```

Ou dans `urls.py` pour les Class-Based Views :
```python
from django.contrib.auth.mixins import LoginRequiredMixin

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'exams/dashboard.html'
```

---

## 13. Étape 9 — Import/Export Excel

### 13.1. Remplacement de la librairie

| Actuel | Django |
|---|---|
| `xlsx` (SheetJS) en JavaScript | `openpyxl` en Python |

### 13.2. Import Excel — Exemple

**Fichier actuel :** `src/lib/excel.ts` (parseExcelFile, colonnes Nom/Prénom/Sexe/Date)
**Fichier Django :** `exams/services/excel_import.py`

```python
# exams/services/excel_import.py

import openpyxl
from datetime import datetime


COLUMN_MAPPINGS = {
    'nom': 'last_name',
    'lastname': 'last_name',
    'prenom': 'first_name',
    'prénom': 'first_name',
    'sexe': 'gender',
    'genre': 'gender',
    'date de naissance': 'birth_date',
    'naissance': 'birth_date',
}


def normalize(text: str) -> str:
    import unicodedata
    return unicodedata.normalize('NFD', text.lower().strip()).encode('ascii', 'ignore').decode()


def parse_excel_file(file) -> dict:
    """
    Parse un fichier Excel uploadé et retourne les données des élèves.
    Retourne : {'success': bool, 'students': list, 'errors': list}
    """
    errors = []
    students = []

    wb = openpyxl.load_workbook(file, read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return {'success': False, 'students': [], 'errors': ['Fichier vide.']}

    # Mapper les colonnes
    headers = rows[0]
    col_map = {}
    for i, h in enumerate(headers):
        if h:
            key = normalize(str(h))
            if key in COLUMN_MAPPINGS:
                col_map[i] = COLUMN_MAPPINGS[key]

    # Vérifier colonnes obligatoires
    mapped_fields = set(col_map.values())
    if 'last_name' not in mapped_fields or 'first_name' not in mapped_fields:
        return {'success': False, 'students': [], 'errors': ['Colonnes Nom/Prénom manquantes.']}

    # Parser les lignes
    for row_num, row in enumerate(rows[1:], start=2):
        student = {}
        for col_idx, field in col_map.items():
            val = row[col_idx] if col_idx < len(row) else None
            if field == 'gender':
                val = parse_gender(val)
            elif field == 'birth_date':
                val = parse_date(val)
            else:
                val = str(val).strip() if val else ''
            student[field] = val

        if not student.get('last_name'):
            errors.append(f"Ligne {row_num}: Nom manquant")
            continue
        if not student.get('first_name'):
            errors.append(f"Ligne {row_num}: Prénom manquant")
            continue

        students.append(student)

    return {'success': len(students) > 0, 'students': students, 'errors': errors}


def parse_gender(value):
    if not value:
        return None
    s = str(value).upper().strip()
    if s in ('M', 'MASCULIN', 'HOMME', 'H'):
        return 'M'
    if s in ('F', 'FEMININ', 'FÉMININ', 'FEMME'):
        return 'F'
    return None


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None
```

### 13.3. Vue d'import

```python
# exams/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .services.excel_import import parse_excel_file
from .models import Student, School, Exam


@login_required
def students_import_view(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        school_id = request.POST.get('school_id')
        exam_id = request.POST.get('exam_id')

        if not file:
            messages.error(request, "Veuillez sélectionner un fichier.")
            return redirect('exams:students_import')

        result = parse_excel_file(file)

        if result['success']:
            exam = Exam.objects.get(pk=exam_id)
            school = School.objects.get(pk=school_id)
            count = 0
            for s in result['students']:
                # Générer le numéro de candidat
                seq = exam.students.count() + count + 1
                candidate_number = f"{exam.year}-{seq:05d}"
                Student.objects.create(
                    candidate_number=candidate_number,
                    first_name=s['first_name'],
                    last_name=s['last_name'],
                    gender=s.get('gender'),
                    birth_date=s.get('birth_date'),
                    exam=exam,
                    school=school,
                )
                count += 1

            messages.success(request, f"{count} élève(s) importé(s) avec succès.")
            for err in result['errors']:
                messages.warning(request, err)
        else:
            for err in result['errors']:
                messages.error(request, err)

        return redirect('exams:students_list')

    # GET : afficher le formulaire d'import
    return render(request, 'exams/students/import.html', {
        'exams': Exam.objects.filter(is_locked=False),
        'schools': School.objects.all(),
    })
```

---

## 14. Étape 10 — Export PDF

### 14.1. Remplacement

| Actuel | Django |
|---|---|
| `jsPDF` + `jspdf-autotable` (JavaScript) | `ReportLab` ou `WeasyPrint` (Python) |

### 14.2. Exemple avec ReportLab

```python
# exams/services/pdf_export.py

from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


def generate_results_pdf(exam, students_data):
    """
    Génère un PDF des résultats d'un examen.
    Retourne un BytesIO contenant le PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()

    # Titre
    elements.append(Paragraph(f"Résultats - {exam.name} ({exam.year})", styles['Title']))

    # Données du tableau
    data = [['N°', 'Nom', 'Prénom', 'Moyenne', 'Rang', 'Mention']]
    for s in students_data:
        data.append([
            s['candidate_number'],
            s['last_name'],
            s['first_name'],
            f"{s['average']:.2f}" if s['average'] else '-',
            s.get('rank', '-'),
            s.get('mention', ''),
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
```

### 14.3. Vue d'export PDF

```python
# exams/views.py

from django.http import HttpResponse
from .services.pdf_export import generate_results_pdf


@login_required
def export_pdf_view(request, doc_type):
    exam = get_active_exam()  # fonction utilitaire
    # ... préparer les données selon doc_type

    buffer = generate_results_pdf(exam, students_data)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultats_{exam.year}.pdf"'
    return response
```

---

## 15. Étape 11 — Formulaires Django

### 15.1. Correspondance

Les formulaires React (gérés par state/onChange) deviennent des `django.forms.ModelForm`.

```python
# exams/forms.py

from django import forms
from .models import Exam, School, Student, Subject, Score, Room


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['name', 'year', 'passing_grade']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': "Nom de l'examen"}),
            'year': forms.NumberInput(attrs={'class': 'form-input'}),
            'passing_grade': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5'}),
        }


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': "Nom de l'établissement"}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Code (optionnel)'}),
        }


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'gender', 'birth_date', 'school', 'is_absent']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'coefficient', 'max_score']


class ScoreForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ['value']
        widgets = {
            'value': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.25', 'min': '0'}),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'capacity']


class ExcelImportForm(forms.Form):
    file = forms.FileField(
        label="Fichier Excel",
        help_text="Formats acceptés : .xlsx, .xls",
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        label="Établissement",
    )
```

### 15.2. Utilisation dans une vue

```python
@login_required
def school_create_view(request):
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Établissement créé avec succès.")
            return redirect('exams:schools_list')
    else:
        form = SchoolForm()

    return render(request, 'exams/schools/form.html', {'form': form, 'title': 'Ajouter'})
```

---

## 16. Étape 12 — Migration des données existantes

Si vous avez des données existantes dans la base SQLite Prisma, voici comment les migrer.

### 16.1. Script de migration

```python
# scripts/migrate_data.py
# À exécuter avec : python manage.py shell < scripts/migrate_data.py

import sqlite3
from exams.models import Exam, School, Student, Subject, Score, Room, RoomAssignment

# Connexion à l'ancienne base Prisma
old_db = sqlite3.connect('exam-manager.db')
old_db.row_factory = sqlite3.Row
cursor = old_db.cursor()

# Migrer les examens
for row in cursor.execute('SELECT * FROM Exam'):
    Exam.objects.create(
        id=row['id'],
        name=row['name'],
        year=row['year'],
        passing_grade=row['passingGrade'],
        is_locked=bool(row['isLocked']),
    )

# Migrer les établissements
for row in cursor.execute('SELECT * FROM School'):
    School.objects.create(id=row['id'], name=row['name'], code=row['code'])

# ... (même logique pour Student, Subject, Score, Room, RoomAssignment)

old_db.close()
print("Migration terminée !")
```

> **Note :** les données peuvent aussi être dans le localStorage (Zustand stores). Dans ce cas, exportez-les en JSON depuis le navigateur avec la fonction `exportAllData()` existante, puis importez-les via un script Django.

---

## 17. Étape 13 — Tests

### 17.1. Commande Django pour les tests

```bash
python manage.py test exams
```

### 17.2. Structure des tests

```python
# exams/tests/test_calculations.py

from django.test import TestCase
from exams.services.calculations import calculate_student_average


class CalculateAverageTest(TestCase):
    def test_simple_average(self):
        scores = [
            {'value': 12, 'coefficient': None, 'max_score': None},
            {'value': 14, 'coefficient': None, 'max_score': None},
        ]
        self.assertEqual(calculate_student_average(scores), 13.0)

    def test_weighted_average(self):
        scores = [
            {'value': 12, 'coefficient': 2, 'max_score': None},
            {'value': 14, 'coefficient': 1, 'max_score': None},
        ]
        self.assertAlmostEqual(calculate_student_average(scores), 12.67, places=2)

    def test_empty_scores(self):
        self.assertIsNone(calculate_student_average([]))
```

```python
# exams/tests/test_views.py

from django.test import TestCase, Client
from django.contrib.auth.models import User


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('admin', password='test123')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_accessible(self):
        self.client.login(username='admin', password='test123')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
```

---

## 18. Étape 14 — Déploiement

### Option A : Serveur local (similaire à Tauri)

```bash
python manage.py runserver 0.0.0.0:8000
```

### Option B : Production avec Gunicorn + Nginx

```bash
pip install gunicorn
gunicorn g-exam.wsgi:application --bind 0.0.0.0:8000
```

### Option C : Packaging avec PyInstaller (si desktop souhaité)

```bash
pip install pyinstaller
pyinstaller --onefile manage.py
```

---

## 19. Mapping détaillé fichier par fichier

### Services DB → Vues/Services Django

| Fichier actuel (TypeScript) | Fichier Django (Python) | Notes |
|---|---|---|
| `services/db/client.ts` | **Supprimé** | Django ORM se connecte automatiquement |
| `services/db/examService.ts` | `exams/views.py` + Django ORM | Queries directes dans les vues |
| `services/db/studentService.ts` | `exams/views.py` + Django ORM | |
| `services/db/subjectService.ts` | `exams/views.py` + Django ORM | |
| `services/db/scoreService.ts` | `exams/views.py` + Django ORM | |
| `services/db/roomService.ts` | `exams/views.py` + Django ORM | |
| `services/db/admin.ts` | `django.contrib.auth` + `django.contrib.admin` | |
| `services/dataExport.ts` | `exams/services/data_export.py` | |

### Stores Zustand → Sessions/Vues Django

| Store actuel | Équivalent Django | Notes |
|---|---|---|
| `examStore.ts` | Session Django + DB | L'examen actif est en base, pas en state client |
| `navigationStore.ts` | URLs Django | Navigation = liens `<a>`, pas de state |
| `schoolsStore.ts` | Django ORM (DB) | Les données sont en base, pas en localStorage |
| `studentsStore.ts` | Django ORM (DB) | |
| `subjectsStore.ts` | Django ORM (DB) | |
| `scoresStore.ts` | Django ORM (DB) | |
| `securityStore.ts` | `django.contrib.auth` | Authentification native |
| `settingsStore.ts` | Modèle `Settings` en DB ou `settings.py` | |

### Core (logique métier) → Services Python

| Fichier actuel | Fichier Django | Notes |
|---|---|---|
| `core/calculations/average.ts` | `exams/services/calculations.py` | Traduction directe TS → Python |
| `core/rankings/studentRanking.ts` | `exams/services/rankings.py` | |
| `core/rankings/schoolRanking.ts` | `exams/services/rankings.py` | |
| `core/statistics/globalStats.ts` | `exams/services/statistics.py` | |
| `core/statistics/subjectStats.ts` | `exams/services/statistics.py` | |
| `core/room-dispatch/alphabeticalDispatch.ts` | `exams/services/room_dispatch.py` | |

### Composants React → Templates Django

| Composant React | Template Django | Notes |
|---|---|---|
| `App.tsx` | `templates/base.html` | Layout principal |
| `components/layout/Sidebar.tsx` | `templates/partials/sidebar.html` | Include |
| `components/layout/Header.tsx` | `templates/partials/header.html` | Include |
| `components/security/LockScreen.tsx` | `templates/registration/login.html` | Page de connexion |
| `components/ui/*` | Tailwind CSS / Bootstrap classes | Pas de composants, juste du HTML/CSS |
| `app/dashboard/` | `templates/exams/dashboard.html` | |
| `app/schools/` | `templates/exams/schools/*.html` | |
| `app/students/` | `templates/exams/students/*.html` | |
| ... | ... | Un template par page |

### Autres fichiers

| Fichier actuel | Fichier Django | Notes |
|---|---|---|
| `lib/excel.ts` | `exams/services/excel_import.py` | openpyxl remplace SheetJS |
| `lib/export.ts` | `exams/services/pdf_export.py` | ReportLab remplace jsPDF |
| `lib/utils.ts` (cn) | **Supprimé** | Plus de utility CSS JS |
| `types/navigation.ts` | `exams/urls.py` | Navigation = URLconf |
| `hooks/*.ts` | **Supprimés** | Plus de React hooks |
| `index.css` | `static/css/style.css` | Tailwind CSS via CDN ou build |
| `prisma/schema.prisma` | `exams/models.py` | Django ORM |
| `.env` | `.env` + `django-environ` | Même fichier, format compatible |
| `src-tauri/` | **Supprimé entièrement** | Plus de desktop Rust |

---

## 20. Commandes Django essentielles

| Action | Commande |
|---|---|
| Créer le projet | `django-admin startproject g-exam .` |
| Créer une application | `python manage.py startapp exams` |
| Générer les migrations | `python manage.py makemigrations` |
| Appliquer les migrations | `python manage.py migrate` |
| Créer un superutilisateur | `python manage.py createsuperuser` |
| Lancer le serveur de dev | `python manage.py runserver` |
| Ouvrir le shell Python | `python manage.py shell` |
| Collecter les fichiers statiques | `python manage.py collectstatic` |
| Lancer les tests | `python manage.py test` |
| Créer un dump de la base | `python manage.py dumpdata > backup.json` |
| Charger un dump | `python manage.py loaddata backup.json` |
| Vérifier le projet | `python manage.py check` |
| Voir les requêtes SQL | `python manage.py sqlmigrate exams 0001` |

---

## 21. Structure finale du projet Django

```
exam-manager-django/
├── manage.py                          # Point d'entrée Django
├── requirements.txt                   # Dépendances Python
├── .env                               # Variables d'environnement
├── db.sqlite3                         # Base de données SQLite
│
├── g-exam/                      # Configuration du projet
│   ├── __init__.py
│   ├── settings.py                    # Paramètres (DB, auth, static, etc.)
│   ├── urls.py                        # URLs racine
│   ├── wsgi.py                        # Déploiement WSGI
│   └── asgi.py                        # Déploiement ASGI
│
├── exams/                             # Application principale
│   ├── __init__.py
│   ├── admin.py                       # Configuration admin Django
│   ├── apps.py                        # Configuration de l'app
│   ├── models.py                      # Modèles (Exam, School, Student, etc.)
│   ├── forms.py                       # Formulaires Django
│   ├── views.py                       # Vues (remplace pages React)
│   ├── urls.py                        # URLs de l'app
│   ├── templatetags/                  # Tags et filtres custom
│   │   ├── __init__.py
│   │   └── exam_extras.py
│   ├── services/                      # Logique métier (remplace core/)
│   │   ├── __init__.py
│   │   ├── calculations.py            # Calcul des moyennes
│   │   ├── rankings.py                # Classements
│   │   ├── statistics.py              # Statistiques globales
│   │   ├── room_dispatch.py           # Répartition en salles
│   │   ├── excel_import.py            # Import Excel
│   │   ├── excel_export.py            # Export Excel
│   │   └── pdf_export.py             # Export PDF
│   ├── migrations/                    # Migrations auto-générées
│   │   └── __init__.py
│   └── tests/                         # Tests
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_views.py
│       ├── test_calculations.py
│       └── test_rankings.py
│
├── templates/                         # Templates HTML globaux
│   ├── base.html                      # Layout principal (Sidebar + Header)
│   ├── registration/
│   │   └── login.html                 # Page de connexion
│   ├── partials/
│   │   ├── sidebar.html               # Barre latérale
│   │   ├── header.html                # En-tête
│   │   ├── pagination.html            # Pagination
│   │   └── confirm_delete.html        # Modal de suppression
│   └── exams/
│       ├── dashboard.html
│       ├── exam_setup.html
│       ├── schools/
│       │   ├── list.html
│       │   └── form.html
│       ├── students/
│       │   ├── list.html
│       │   ├── form.html
│       │   └── import.html
│       ├── subjects/
│       │   ├── list.html
│       │   └── form.html
│       ├── scores/
│       │   └── index.html
│       ├── rankings/
│       │   └── index.html
│       ├── statistics/
│       │   └── index.html
│       ├── rooms/
│       │   └── index.html
│       ├── exports/
│       │   └── index.html
│       └── settings/
│           └── index.html
│
└── static/                            # Fichiers statiques
    ├── css/
    │   └── style.css
    ├── js/
    │   └── app.js
    └── img/
        └── logo.png
```

---

## 22. Ordre de migration recommandé

Voici l'ordre étape par étape pour réaliser la migration. Chaque étape est indépendante et testable.

### Phase 1 : Fondations (Jour 1-2)

1. **Initialiser le projet Django** → `django-admin startproject` + `startapp`
2. **Définir les modèles** → Traduire `schema.prisma` en `models.py`
3. **Appliquer les migrations** → `makemigrations` + `migrate`
4. **Configurer l'admin** → `admin.py` + `createsuperuser`
5. **Tester** → Vérifier CRUD via `/admin/`

### Phase 2 : Authentification (Jour 2)

6. **Page de login** → Template + `django.contrib.auth`
7. **Protection des vues** → `@login_required`

### Phase 3 : Pages de base (Jour 3-5)

8. **Layout de base** → `base.html` + sidebar + header
9. **Dashboard** → Vue + template
10. **Établissements** → CRUD complet (list, create, edit, delete)
11. **Épreuves** → CRUD complet
12. **Élèves** → CRUD complet

### Phase 4 : Fonctionnalités métier (Jour 5-8)

13. **Import Excel** → Service `excel_import.py` + vue + formulaire
14. **Saisie des notes** → Vue + formulaire
15. **Calculs de moyennes** → Service `calculations.py`
16. **Classements** → Service `rankings.py` + vue + template
17. **Statistiques** → Service `statistics.py` + vue + template + Chart.js

### Phase 5 : Fonctionnalités avancées (Jour 8-10)

18. **Répartition en salles** → Service `room_dispatch.py` + vue
19. **Export PDF** → Service `pdf_export.py` + ReportLab
20. **Export Excel** → Service `excel_export.py` + openpyxl
21. **Paramètres** → Modèle `Settings` + vue

### Phase 6 : Finalisation (Jour 10-12)

22. **Tests** → Tests unitaires et d'intégration
23. **Migration des données** → Script de migration depuis l'ancienne base
24. **Déploiement** → Configuration production

---

## 23. Pièges à éviter

### 23.1. Nommage des champs

Prisma utilise le **camelCase** (`passingGrade`, `createdAt`), Django utilise le **snake_case** (`passing_grade`, `created_at`). Attention à la correspondance lors de la migration des données.

### 23.2. Relations `on_delete`

Prisma définit `onDelete: Cascade` explicitement. En Django, **vous devez toujours spécifier** `on_delete` sur les `ForeignKey`. Les options sont :
- `CASCADE` — Supprime les objets liés
- `PROTECT` — Empêche la suppression
- `SET_NULL` — Met la clé étrangère à NULL
- `SET_DEFAULT` — Met la valeur par défaut

### 23.3. Gestion du `passingGrade` (seuil)

Dans le projet actuel, le seuil est stocké à la fois dans le modèle `Exam` et dans le store `examStore`. En Django, **une seule source de vérité** : le modèle `Exam` en base de données.

### 23.4. Navigation client vs serveur

L'application actuelle est une **SPA** : la navigation se fait côté client (Zustand store, pas de rechargement de page). En Django avec templates, **chaque navigation est un rechargement de page** (requête HTTP classique).

Pour une expérience plus dynamique, vous pouvez ajouter **HTMX** (librairie légère) qui permet de charger des fragments HTML via AJAX sans écrire de JavaScript :

```html
<script src="https://unpkg.com/htmx.org"></script>
```

### 23.5. Zustand localStorage → Session Django

Les stores Zustand persistent les données dans `localStorage`. En Django :
- Les **données métier** (examens, élèves, notes) vont en **base de données**
- Les **préférences utilisateur** (thème, config affichage) vont en **session Django** ou dans un modèle `UserPreference`
- L'**état d'authentification** est géré par le **framework de sessions Django** (cookie côté serveur)

### 23.6. Tauri → Suppression

Tout le dossier `src-tauri/` et les dépendances Tauri sont supprimés. Les fonctionnalités Tauri (dialogues fichiers, invocations Rust) sont remplacées par :
- **Upload de fichiers** → `<input type="file">` + `request.FILES` dans Django
- **Téléchargement** → `HttpResponse` avec le bon `Content-Type` et `Content-Disposition`
- **Vérification admin** → `django.contrib.auth`

### 23.7. Graphiques Recharts → Chart.js

Recharts est une librairie React. En Django avec templates, utilisez **Chart.js** via CDN. Les données sont passées au template via le context et injectées dans le JavaScript :

```html
<canvas id="statsChart"></canvas>
<script>
const ctx = document.getElementById('statsChart').getContext('2d');
new Chart(ctx, {
    type: 'bar',
    data: {
        labels: {{ labels|safe }},
        datasets: [{
            label: 'Notes',
            data: {{ data|safe }},
        }]
    }
});
</script>
```

---

## Résumé des fichiers de dépendances

### `requirements.txt`

```
Django>=5.1
openpyxl>=3.1
reportlab>=4.0
django-environ>=0.11
Pillow>=10.0
```

### Installation complète

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows
pip install -r requirements.txt
django-admin startproject g-exam .
python manage.py startapp exams
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

> **Ce document est votre feuille de route complète.** Suivez les étapes dans l'ordre de la [section 22](#22-ordre-de-migration-recommandé) pour une migration progressive et testable à chaque étape.
