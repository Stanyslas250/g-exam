from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Exam,
    School,
    Student,
    Subject,
    Score,
    Room,
    Teacher,
    SubjectAssignment,
    Harmonization,
)


INPUT_CSS = "input input-bordered w-full"
SELECT_CSS = "select select-bordered w-full"
TEXTAREA_CSS = "textarea textarea-bordered w-full"


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            "name",
            "code",
            "year",
            "exam_type",
            "description",
            "start_date",
            "end_date",
            "location",
            "grading_scale",
            "passing_grade",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nom de l'examen"}),
            "code": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Ex: BAC2025-CM"}),
            "year": forms.NumberInput(attrs={"class": INPUT_CSS}),
            "exam_type": forms.Select(attrs={"class": SELECT_CSS}),
            "description": forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 3, "placeholder": "Description (optionnelle)"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CSS}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CSS}),
            "location": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Lieu ou centre d'examen"}),
            "grading_scale": forms.NumberInput(attrs={
                "class": INPUT_CSS,
                "step": "0.5",
                "min": "0.5",
                "placeholder": "Ex. 20, 10, 50…",
            }),
            "passing_grade": forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.5"}),
        }

    def clean_grading_scale(self):
        scale = self.cleaned_data.get("grading_scale")
        if scale is not None and scale <= 0:
            raise ValidationError("Le barème doit être strictement positif.")
        return scale

    def clean(self):
        cleaned = super().clean()
        scale = cleaned.get("grading_scale")
        pg = cleaned.get("passing_grade")
        if scale is not None and pg is not None:
            if pg < 0:
                self.add_error("passing_grade", "Le seuil ne peut pas être négatif.")
            elif pg > scale:
                self.add_error(
                    "passing_grade",
                    f"Le seuil ne peut pas dépasser le barème ({scale}).",
                )
        return cleaned


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "code"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nom de l'établissement"}),
            "code": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Code (optionnel)"}),
        }


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["first_name", "last_name", "gender", "birth_date", "school", "is_absent"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CSS}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CSS}),
            "gender": forms.Select(attrs={"class": SELECT_CSS}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": INPUT_CSS}),
            "school": forms.Select(attrs={"class": SELECT_CSS}),
            "is_absent": forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "coefficient", "max_score"]
        help_texts = {
            "max_score": "Plafond de la note pour cette épreuve (peut différer du barème global de l’examen).",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nom de l'épreuve"}),
            "coefficient": forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.5", "placeholder": "Optionnel"}),
            "max_score": forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.5"}),
        }


class ScoreForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ["value"]
        widgets = {
            "value": forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.25", "min": "0"}),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["name", "capacity"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nom de la salle"}),
            "capacity": forms.NumberInput(attrs={"class": INPUT_CSS, "min": "1"}),
        }


class ExcelImportForm(forms.Form):
    file = forms.FileField(
        label="Fichier Excel",
        help_text="Formats acceptés : .xlsx, .xls",
        widget=forms.FileInput(attrs={"class": "file-input file-input-bordered w-full", "accept": ".xlsx,.xls"}),
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        label="Établissement",
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )


class ExamCodeForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        label="Code de l'examen",
        widget=forms.TextInput(attrs={
            "class": INPUT_CSS,
            "placeholder": "Entrez le code de l'examen",
            "autofocus": True,
        }),
    )


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ["first_name", "last_name", "code", "email", "phone", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Prénom"}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nom"}),
            "code": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Code unique de connexion"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CSS, "placeholder": "optionnel"}),
            "phone": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "optionnel"}),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
        }


class SubjectAssignmentForm(forms.ModelForm):
    class Meta:
        model = SubjectAssignment
        fields = ["subject", "is_lead_corrector"]
        widgets = {
            "subject": forms.Select(attrs={"class": SELECT_CSS}),
            "is_lead_corrector": forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
        }

    def __init__(self, *args, exam=None, **kwargs):
        super().__init__(*args, **kwargs)
        if exam is not None:
            self.fields["subject"].queryset = Subject.objects.filter(exam=exam).order_by("name")


class CorrectorLoginForm(forms.Form):
    code = forms.CharField(
        max_length=64,
        label="Identifiant correcteur",
        widget=forms.TextInput(attrs={
            "class": INPUT_CSS,
            "placeholder": "Votre code correcteur",
            "autocomplete": "username",
            "autofocus": True,
        }),
    )


class CorrectorGradeForm(forms.Form):
    candidate_number = forms.CharField(
        max_length=20,
        label="N° candidat (matricule)",
        widget=forms.TextInput(attrs={
            "class": INPUT_CSS,
            "placeholder": "Matricule",
            "autocomplete": "off",
        }),
    )
    value = forms.FloatField(
        label="Note",
        widget=forms.NumberInput(attrs={
            "class": INPUT_CSS,
            "step": "0.25",
            "min": "0",
            "autocomplete": "off",
        }),
    )
    recorrection_comment = forms.CharField(
        label="Motif de la modification",
        required=False,
        widget=forms.Textarea(attrs={
            "class": TEXTAREA_CSS,
            "rows": 2,
            "placeholder": "Obligatoire si une note existe déjà",
        }),
    )


class HarmonizationForm(forms.Form):
    adjustment_type = forms.ChoiceField(
        label="Type d’ajustement",
        choices=Harmonization.ADJUSTMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": SELECT_CSS}),
    )
    value = forms.FloatField(
        label="Valeur",
        help_text="Points à ajouter, coefficient (ex. 1.05), ou note plancher selon le type.",
        widget=forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.01"}),
    )
    comment = forms.CharField(
        label="Commentaire",
        required=False,
        widget=forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 2}),
    )


class RecorrectionForm(forms.Form):
    """Formulaire court pour motif de re-correction (interface admin)."""

    comment = forms.CharField(
        label="Motif de la modification",
        widget=forms.Textarea(attrs={"class": TEXTAREA_CSS, "rows": 2}),
    )
