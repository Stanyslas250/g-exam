import uuid
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
