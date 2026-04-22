import uuid

from django.conf import settings
from django.db import models


class Exam(models.Model):
    EXAM_TYPE_BAC = "BAC"
    EXAM_TYPE_BEPC = "BEPC"
    EXAM_TYPE_CAP = "CAP"
    EXAM_TYPE_PROBATOIRE = "PROBATOIRE"
    EXAM_TYPE_AUTRE = "AUTRE"

    EXAM_TYPE_CHOICES = [
        (EXAM_TYPE_BAC, "BAC"),
        (EXAM_TYPE_BEPC, "BEPC"),
        (EXAM_TYPE_CAP, "CAP"),
        (EXAM_TYPE_PROBATOIRE, "Probatoire"),
        (EXAM_TYPE_AUTRE, "Autre"),
    ]

    name = models.CharField(max_length=255, verbose_name="Nom de l'examen")
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        default="",
        verbose_name="Code d'accès",
        help_text="Code unique pour accéder à cet examen (ex: BAC2025-CM). Laisser vide pour génération automatique.",
    )
    year = models.IntegerField(verbose_name="Année")
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        default=EXAM_TYPE_AUTRE,
        verbose_name="Type d'examen",
    )
    description = models.TextField(blank=True, default="", verbose_name="Description")
    start_date = models.DateField(blank=True, null=True, verbose_name="Date de début")
    end_date = models.DateField(blank=True, null=True, verbose_name="Date de fin")
    location = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Lieu / centre d'examen",
    )
    grading_scale = models.FloatField(
        default=20.0,
        verbose_name="Barème (note max de référence)",
        help_text="Échelle des moyennes et du seuil (ex. 20 pour le bac, 10 pour un contrôle). Les notes par épreuve restent sur leur propre note max.",
    )
    passing_grade = models.FloatField(default=10.0, verbose_name="Seuil de réussite")
    is_locked = models.BooleanField(default=False, verbose_name="Verrouillé")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Examen"
        verbose_name_plural = "Examens"

    def __str__(self):
        return f"{self.name} ({self.year})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"{self.year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class School(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom")
    code = models.CharField(max_length=50, blank=True, default="", verbose_name="Code")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Établissement"
        verbose_name_plural = "Établissements"

    def __str__(self):
        return self.name


class Student(models.Model):
    GENDER_CHOICES = [
        ("M", "Masculin"),
        ("F", "Féminin"),
    ]

    candidate_number = models.CharField(max_length=20, verbose_name="N° Candidat")
    first_name = models.CharField(max_length=255, verbose_name="Prénom")
    last_name = models.CharField(max_length=255, verbose_name="Nom")
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, default="", verbose_name="Sexe"
    )
    birth_date = models.DateField(blank=True, null=True, verbose_name="Date de naissance")
    is_absent = models.BooleanField(default=False, verbose_name="Absent")
    created_at = models.DateTimeField(auto_now_add=True)

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="students", verbose_name="Examen"
    )
    school = models.ForeignKey(
        School, on_delete=models.PROTECT, related_name="students", verbose_name="Établissement"
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        unique_together = ["exam", "candidate_number"]
        indexes = [
            models.Index(fields=["exam"]),
            models.Index(fields=["school"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.candidate_number})"


class Subject(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom de l'épreuve")
    coefficient = models.FloatField(blank=True, null=True, verbose_name="Coefficient")
    max_score = models.FloatField(default=20.0, verbose_name="Note maximale")
    created_at = models.DateTimeField(auto_now_add=True)

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="subjects", verbose_name="Examen"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Épreuve"
        verbose_name_plural = "Épreuves"
        indexes = [
            models.Index(fields=["exam"]),
        ]

    def __str__(self):
        return self.name


class Score(models.Model):
    value = models.FloatField(verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="scores", verbose_name="Élève"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="scores", verbose_name="Épreuve"
    )

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject"],
                name="unique_score_per_student_subject",
            ),
        ]
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["subject"]),
        ]

    def __str__(self):
        return f"{self.student} - {self.subject}: {self.value}"


class Teacher(models.Model):
    """Enseignant / correcteur (connexion par code, sans compte Django)."""

    first_name = models.CharField(max_length=255, verbose_name="Prénom")
    last_name = models.CharField(max_length=255, verbose_name="Nom")
    code = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Code correcteur",
        help_text="Identifiant unique pour la connexion à l’interface correction.",
    )
    email = models.EmailField(blank=True, default="", verbose_name="E-mail")
    phone = models.CharField(max_length=32, blank=True, default="", verbose_name="Téléphone")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Enseignant"
        verbose_name_plural = "Enseignants"

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.code})"


class SubjectAssignment(models.Model):
    """Assignation d’un correcteur à une épreuve."""

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="subject_assignments",
        verbose_name="Enseignant",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
        verbose_name="Épreuve",
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="subject_assignments",
        verbose_name="Examen",
    )
    is_lead_corrector = models.BooleanField(
        default=False,
        verbose_name="Correcteur principal",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Assignation épreuve"
        verbose_name_plural = "Assignations épreuves"
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "subject"],
                name="unique_teacher_subject_assignment",
            ),
        ]
        indexes = [
            models.Index(fields=["exam"]),
            models.Index(fields=["teacher"]),
            models.Index(fields=["subject"]),
        ]

    def save(self, *args, **kwargs):
        if self.subject_id:
            self.exam_id = Subject.objects.values_list("exam_id", flat=True).get(pk=self.subject_id)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.teacher} → {self.subject}"


class ScoreHistory(models.Model):
    """Historique des modifications d’une note."""

    REASON_INITIAL = "INITIAL"
    REASON_CORRECTION = "CORRECTION"
    REASON_RECORRECTION = "RECORRECTION"
    REASON_HARMONIZATION = "HARMONIZATION"

    REASON_CHOICES = [
        (REASON_INITIAL, "Saisie initiale"),
        (REASON_CORRECTION, "Correction"),
        (REASON_RECORRECTION, "Re-correction"),
        (REASON_HARMONIZATION, "Harmonisation"),
    ]

    score = models.ForeignKey(
        Score,
        on_delete=models.CASCADE,
        related_name="history_entries",
        verbose_name="Note",
    )
    old_value = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Ancienne note",
        help_text="Vide pour la première saisie.",
    )
    new_value = models.FloatField(verbose_name="Nouvelle note")
    reason = models.CharField(
        max_length=32,
        choices=REASON_CHOICES,
        verbose_name="Motif",
    )
    comment = models.TextField(blank=True, default="", verbose_name="Commentaire")
    changed_by_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="score_history_entries",
        verbose_name="Correcteur",
    )
    changed_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="score_history_entries",
        verbose_name="Administrateur",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Historique de note"
        verbose_name_plural = "Historiques de notes"
        indexes = [
            models.Index(fields=["score"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.score_id}: {self.old_value} → {self.new_value} ({self.reason})"


class Harmonization(models.Model):
    """Trace d’une opération d’harmonisation sur une épreuve."""

    TYPE_ADD = "ADD"
    TYPE_MULTIPLY = "MULTIPLY"
    TYPE_SET_MIN = "SET_MIN"

    ADJUSTMENT_TYPE_CHOICES = [
        (TYPE_ADD, "Ajout de points"),
        (TYPE_MULTIPLY, "Coefficient multiplicateur"),
        (TYPE_SET_MIN, "Note plancher"),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="harmonizations",
        verbose_name="Examen",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="harmonizations",
        verbose_name="Épreuve",
    )
    adjustment_type = models.CharField(
        max_length=16,
        choices=ADJUSTMENT_TYPE_CHOICES,
        verbose_name="Type d’ajustement",
    )
    value = models.FloatField(verbose_name="Valeur (points, coefficient ou plancher)")
    comment = models.TextField(blank=True, default="", verbose_name="Commentaire")
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="harmonizations_applied",
        verbose_name="Appliqué par",
    )
    applied_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date d’application",
    )
    is_applied = models.BooleanField(default=False, verbose_name="Appliqué")

    class Meta:
        ordering = ["-applied_at", "-id"]
        verbose_name = "Harmonisation"
        verbose_name_plural = "Harmonisations"
        indexes = [
            models.Index(fields=["exam", "subject"]),
        ]

    def __str__(self):
        return f"{self.subject} — {self.get_adjustment_type_display()} ({self.value})"


class Room(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom de la salle")
    capacity = models.IntegerField(verbose_name="Capacité")
    created_at = models.DateTimeField(auto_now_add=True)

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="rooms", verbose_name="Examen"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Salle"
        verbose_name_plural = "Salles"
        indexes = [
            models.Index(fields=["exam"]),
        ]

    def __str__(self):
        return self.name


class RoomAssignment(models.Model):
    seat_number = models.IntegerField(blank=True, null=True, verbose_name="N° de place")
    created_at = models.DateTimeField(auto_now_add=True)

    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="room_assignment",
        verbose_name="Élève",
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="assignments", verbose_name="Salle"
    )

    class Meta:
        verbose_name = "Assignation"
        verbose_name_plural = "Assignations"
        indexes = [
            models.Index(fields=["room"]),
        ]

    def __str__(self):
        return f"{self.student} → {self.room}"


class Plan(models.Model):
    BILLING_FREE = "FREE"
    BILLING_MONTHLY = "MONTHLY"
    BILLING_YEARLY = "YEARLY"
    BILLING_CUSTOM = "CUSTOM"

    BILLING_CHOICES = [
        (BILLING_FREE, "Gratuit"),
        (BILLING_MONTHLY, "Par mois"),
        (BILLING_YEARLY, "Par an"),
        (BILLING_CUSTOM, "Sur devis"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Nom du forfait")
    slug = models.SlugField(max_length=100, unique=True)
    tagline = models.CharField(max_length=200, blank=True, default="", verbose_name="Accroche")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    price_fcfa = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Prix (FCFA)",
        help_text="Laisser vide pour gratuit ou sur devis.",
    )
    billing_period = models.CharField(
        max_length=16, choices=BILLING_CHOICES, default=BILLING_MONTHLY, verbose_name="Période de facturation",
    )
    max_exams = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Nb max d'examens",
        help_text="Vide = illimité.",
    )
    max_students_per_exam = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Nb max de candidats / examen",
        help_text="Vide = illimité.",
    )
    max_teachers = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Nb max de correcteurs",
        help_text="Vide = illimité.",
    )
    features = models.JSONField(
        default=list, blank=True, verbose_name="Fonctionnalités incluses",
        help_text="Liste de chaînes affichées sur la page tarifs.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_featured = models.BooleanField(default=False, verbose_name="Mis en avant")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        ordering = ["sort_order", "price_fcfa"]
        verbose_name = "Forfait"
        verbose_name_plural = "Forfaits"

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile", verbose_name="Utilisateur",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscribers", verbose_name="Forfait",
    )
    organization = models.CharField(max_length=255, blank=True, default="", verbose_name="Organisation")
    phone = models.CharField(max_length=32, blank=True, default="", verbose_name="Téléphone")
    subscription_start = models.DateField(null=True, blank=True, verbose_name="Début abonnement")
    subscription_end = models.DateField(null=True, blank=True, verbose_name="Fin abonnement")
    is_subscription_active = models.BooleanField(default=True, verbose_name="Abonnement actif")
    notes = models.TextField(blank=True, default="", verbose_name="Notes")

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        plan_name = self.plan.name if self.plan else "Aucun forfait"
        return f"{self.user.username} — {plan_name}"
