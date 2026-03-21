from django import forms
from .models import Exam, School, Student, Subject, Score, Room


INPUT_CSS = "input input-bordered w-full"
SELECT_CSS = "select select-bordered w-full"
TEXTAREA_CSS = "textarea textarea-bordered w-full"


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ["name", "code", "year", "passing_grade"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Nom de l'examen"}),
            "code": forms.TextInput(attrs={"class": INPUT_CSS, "placeholder": "Ex: BAC2025-CM"}),
            "year": forms.NumberInput(attrs={"class": INPUT_CSS}),
            "passing_grade": forms.NumberInput(attrs={"class": INPUT_CSS, "step": "0.5"}),
        }


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
