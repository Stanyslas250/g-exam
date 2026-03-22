import json
import statistics
import uuid
from collections import defaultdict
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Avg, Count, Q
from django.views.decorators.http import require_POST
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

from .models import Exam, School, Student, Subject, Score, Room, RoomAssignment, ScoreHistory
from .forms import (
    ExamForm, SchoolForm, StudentForm, SubjectForm, ScoreForm,
    RoomForm, ExcelImportForm, ExamCodeForm,
)
from .services.score_history import log_score_change
from .services.calculations import calculate_student_average, get_mention
from .services.rankings import rank_students, rank_schools
from .services.statistics import compute_global_stats, compute_distribution, compute_subject_stats
from .services.room_dispatch import alphabetical_dispatch
from .services.excel_import import parse_excel_file, parse_exam_excel, parse_exam_json
from .services.backup import build_exam_backup_dict
from .services.excel_export import generate_results_by_school_excel, generate_results_excel
from .services.pdf_export import (
    generate_results_pdf,
    generate_room_dispatch_pdf,
    generate_transcripts_pdf,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def get_active_exam(request):
    exam_id = request.session.get("active_exam_id")
    if exam_id:
        try:
            return Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            del request.session["active_exam_id"]
    return None


def _parse_score_post_value(value):
    """Parse une note depuis un champ formulaire (virgule ou point décimal)."""
    if value is None:
        return None
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _safe_grading_scale(exam: Exam) -> float:
    """Barème de l'examen pour normalisation des moyennes (toujours > 0)."""
    try:
        g = float(exam.grading_scale)
    except (TypeError, ValueError):
        return 20.0
    return g if g > 0 else 20.0


def _build_students_data(exam):
    """Build enriched student data with averages, ranks, mentions."""
    students = exam.students.select_related("school").all()
    subjects = list(exam.subjects.all())

    students_data = []
    for student in students:
        scores = Score.objects.filter(student=student, subject__exam=exam).select_related("subject")
        score_list = [
            {
                "value": s.value,
                "coefficient": s.subject.coefficient,
                "max_score": s.subject.max_score,
            }
            for s in scores
        ]
        scale = _safe_grading_scale(exam)
        avg = calculate_student_average(score_list, target_scale=scale)
        students_data.append({
            "student_id": student.id,
            "candidate_number": student.candidate_number,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "gender": student.gender,
            "school": student.school,
            "school_name": student.school.name,
            "is_absent": student.is_absent,
            "average": avg,
            "mention": get_mention(avg, exam.passing_grade, scale) if avg is not None else "",
            "scores_count": scores.count(),
            "total_subjects": len(subjects),
        })

    ranked = rank_students(students_data)
    return ranked


# ──────────────────────────────────────────────
# Exam Selection
# ──────────────────────────────────────────────

@login_required
def select_exam_view(request):
    exams = Exam.objects.all()
    form = ExamCodeForm()
    error = None

    if request.method == "POST":
        form = ExamCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            try:
                exam = Exam.objects.get(code__iexact=code)
                request.session["active_exam_id"] = exam.id
                messages.success(request, f"Examen « {exam.name} » sélectionné.")
                return redirect("exams:dashboard")
            except Exam.DoesNotExist:
                error = "Aucun examen trouvé avec ce code."

    return render(request, "exams/select_exam.html", {
        "exams": exams,
        "form": form,
        "error": error,
    })


@login_required
def switch_exam_view(request):
    if request.method == "POST":
        exam_id = request.POST.get("exam_id")
        if exam_id:
            try:
                exam = Exam.objects.get(pk=exam_id)
                request.session["active_exam_id"] = exam.id
                messages.success(request, f"Examen « {exam.name} » sélectionné.")
            except Exam.DoesNotExist:
                messages.error(request, "Examen introuvable.")
    return redirect("exams:dashboard")


def _exam_type_code_prefix(exam_type: str) -> str:
    return {
        Exam.EXAM_TYPE_BAC: "BAC",
        Exam.EXAM_TYPE_BEPC: "BEPC",
        Exam.EXAM_TYPE_CAP: "CAP",
        Exam.EXAM_TYPE_PROBATOIRE: "PROB",
        Exam.EXAM_TYPE_AUTRE: "EX",
    }.get(exam_type, "EX")


def generate_unique_exam_code(year: int, exam_type: str) -> str:
    prefix = _exam_type_code_prefix(exam_type)
    for _ in range(50):
        candidate = f"{prefix}{year}-{uuid.uuid4().hex[:6].upper()}"
        if not Exam.objects.filter(code__iexact=candidate).exists():
            return candidate
    return f"{prefix}{year}-{uuid.uuid4().hex[:8].upper()}"


@login_required
@require_POST
def generate_exam_code_view(request):
    """Génère un code d'accès unique (AJAX)."""
    year_raw = request.POST.get("year", "").strip()
    exam_type = request.POST.get("exam_type", Exam.EXAM_TYPE_AUTRE)
    if exam_type not in dict(Exam.EXAM_TYPE_CHOICES):
        exam_type = Exam.EXAM_TYPE_AUTRE
    try:
        year = int(year_raw) if year_raw else datetime.now().year
    except ValueError:
        year = datetime.now().year
    code = generate_unique_exam_code(year, exam_type)
    return JsonResponse({"code": code})


@login_required
def exam_import_view(request):
    """Importe un examen complet depuis un fichier Excel ou JSON (y compris backup ancienne app)."""
    if request.method == "POST":
        file = request.FILES.get("file")
        exam_name = request.POST.get("exam_name", "").strip()
        exam_code = request.POST.get("exam_code", "").strip()
        exam_year = request.POST.get("exam_year", "").strip()

        if not file:
            messages.error(request, "Veuillez sélectionner un fichier (Excel ou JSON).")
            return redirect("exams:exam_import")

        filename = file.name.lower()
        if filename.endswith(".json"):
            result = parse_exam_json(file)
        elif filename.endswith((".xlsx", ".xls")):
            result = parse_exam_excel(file)
        else:
            messages.error(request, "Format non supporté. Utilisez un fichier .xlsx ou .json.")
            return redirect("exams:exam_import")

        if not result["success"]:
            for err in result["errors"]:
                messages.error(request, err)
            return redirect("exams:exam_import")

        # Utiliser les métadonnées du backup si disponibles
        meta = result.get("exam_meta")
        if not exam_name and meta:
            exam_name = meta.get("name", "")
        if not exam_year and meta and meta.get("year"):
            exam_year = str(meta["year"])

        if not exam_name or not exam_code:
            messages.error(request, "Le nom et le code de l'examen sont obligatoires.")
            return redirect("exams:exam_import")

        # Créer l'examen
        exam_kwargs = {
            "name": exam_name,
            "code": exam_code,
            "year": int(exam_year) if exam_year.isdigit() else 2025,
        }
        if meta:
            if meta.get("grading_scale") is not None:
                try:
                    exam_kwargs["grading_scale"] = float(meta["grading_scale"])
                except (TypeError, ValueError):
                    pass
            elif meta.get("max_grade") is not None:
                try:
                    exam_kwargs["grading_scale"] = float(meta["max_grade"])
                except (TypeError, ValueError):
                    pass
            if meta.get("passing_grade") is not None:
                exam_kwargs["passing_grade"] = meta["passing_grade"]
            if meta.get("is_locked"):
                exam_kwargs["is_locked"] = meta["is_locked"]
            if meta.get("exam_type") in dict(Exam.EXAM_TYPE_CHOICES):
                exam_kwargs["exam_type"] = meta["exam_type"]
            if meta.get("description"):
                exam_kwargs["description"] = str(meta["description"])[:5000]
            if meta.get("location"):
                exam_kwargs["location"] = str(meta["location"])[:255]
            if meta.get("start_date"):
                exam_kwargs["start_date"] = meta["start_date"]
            if meta.get("end_date"):
                exam_kwargs["end_date"] = meta["end_date"]
        exam = Exam.objects.create(**exam_kwargs)
        default_subject_max = _safe_grading_scale(exam)

        # Créer les établissements
        school_map = {}
        for s in result["schools"]:
            school_obj, _ = School.objects.get_or_create(
                name=s["name"],
                defaults={"code": s.get("code", "")},
            )
            school_map[s["name"].lower()] = school_obj

        # Créer les épreuves
        for s in result["subjects"]:
            Subject.objects.create(
                name=s["name"],
                coefficient=s.get("coefficient") or 1,
                max_score=s.get("max_score") if s.get("max_score") is not None else default_subject_max,
                exam=exam,
            )

        # Créer les élèves
        student_count = 0
        for s in result["students"]:
            school_name = s.get("school_name", "").lower()
            school_obj = school_map.get(school_name)
            if not school_obj:
                if s.get("school_name"):
                    school_obj, _ = School.objects.get_or_create(name=s["school_name"])
                    school_map[school_name] = school_obj
                else:
                    school_obj = School.objects.first()
                    if not school_obj:
                        school_obj = School.objects.create(name="Non défini")
                        school_map["non défini"] = school_obj

            # Utiliser le numéro de candidat du backup s'il existe
            candidate_number = s.get("candidate_number", "").strip()
            if not candidate_number:
                seq = exam.students.count() + 1
                candidate_number = f"{exam.year}-{seq:05d}"

            Student.objects.create(
                candidate_number=candidate_number,
                first_name=s["first_name"],
                last_name=s["last_name"],
                gender=s.get("gender", ""),
                birth_date=s.get("birth_date"),
                is_absent=s.get("is_absent", False),
                exam=exam,
                school=school_obj,
            )
            student_count += 1

        # Activer l'examen
        request.session["active_exam_id"] = exam.id
        request.session["show_new_exam_code"] = exam.code
        request.session["show_new_exam_name"] = exam.name

        summary = []
        if result["schools"]:
            summary.append(f"{len(result['schools'])} établissement(s)")
        if result["subjects"]:
            summary.append(f"{len(result['subjects'])} épreuve(s)")
        if student_count:
            summary.append(f"{student_count} élève(s)")
        messages.success(request, f"Examen « {exam.name} » importé : {', '.join(summary)}.")

        for err in result["errors"]:
            messages.warning(request, err)

        return redirect("exams:dashboard")

    return render(request, "exams/exam_import.html")


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

@login_required
def dashboard_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    students = exam.students.all()
    subjects = exam.subjects.order_by("name")
    students_count = students.count()
    subjects_count = subjects.count()

    students_data = _build_students_data(exam)
    averages = [s["average"] for s in students_data if s["average"] is not None]

    passed = sum(1 for a in averages if a >= exam.passing_grade)
    failed = sum(1 for a in averages if a < exam.passing_grade)
    absent = students.filter(is_absent=True).count()

    schools_count = School.objects.filter(students__exam=exam).distinct().count()
    scores_entered = Score.objects.filter(student__exam=exam).count()
    slots_total = students_count * subjects_count if subjects_count else 0
    scores_progress_pct = round(scores_entered / slots_total * 100, 1) if slots_total else 0.0

    subject_score_progress = []
    for subj in subjects:
        entered = Score.objects.filter(subject=subj).count()
        total = students_count
        pct = round(entered / total * 100, 1) if total else 0.0
        subject_score_progress.append({
            "subject": subj,
            "entered": entered,
            "total": total,
            "pct": pct,
        })

    step_exam = True
    step_schools = schools_count > 0
    step_students = students_count > 0
    step_subjects = subjects_count > 0
    step_scores = scores_entered > 0
    step_complete = bool(slots_total and scores_entered >= slots_total)

    pending_avg = sum(
        1 for s in students_data
        if not s["is_absent"] and s["average"] is None
    )
    donut_labels = json.dumps(["Admis", "Ajournés", "Absents", "En attente"])
    donut_data = json.dumps([passed, failed, absent, pending_avg])
    donut_colors = json.dumps([
        "rgba(34, 197, 94, 0.85)",
        "rgba(239, 68, 68, 0.85)",
        "rgba(148, 163, 184, 0.85)",
        "rgba(59, 130, 246, 0.85)",
    ])

    show_created_code = request.session.pop("show_new_exam_code", None)
    show_created_name = request.session.pop("show_new_exam_name", None)

    context = {
        "exam": exam,
        "candidates_count": students_count,
        "subjects_count": subjects_count,
        "schools_count": schools_count,
        "rooms_count": exam.rooms.count(),
        "passed": passed,
        "failed": failed,
        "absent": absent,
        "pending_avg": pending_avg,
        "pass_rate": round(passed / len(averages) * 100, 1) if averages else 0,
        "overall_average": round(sum(averages) / len(averages), 2) if averages else 0,
        "highest_avg": round(max(averages), 2) if averages else 0,
        "lowest_avg": round(min(averages), 2) if averages else 0,
        "show_created_code": show_created_code,
        "show_created_name": show_created_name,
        "scores_entered": scores_entered,
        "slots_total": slots_total,
        "scores_progress_pct": scores_progress_pct,
        "subject_score_progress": subject_score_progress,
        "step_exam": step_exam,
        "step_schools": step_schools,
        "step_students": step_students,
        "step_subjects": step_subjects,
        "step_scores": step_scores,
        "step_complete": step_complete,
        "donut_labels": donut_labels,
        "donut_data": donut_data,
        "donut_colors": donut_colors,
    }
    return render(request, "exams/dashboard.html", context)


# ──────────────────────────────────────────────
# Exam Setup
# ──────────────────────────────────────────────

@login_required
def exam_setup_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuration de l'examen mise à jour.")
            return redirect("exams:exam_setup")
    else:
        form = ExamForm(instance=exam)

    return render(request, "exams/exam_setup.html", {"form": form, "exam": exam})


@login_required
def exam_create_view(request):
    if request.method == "POST":
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            request.session["active_exam_id"] = exam.id
            request.session["show_new_exam_code"] = exam.code
            request.session["show_new_exam_name"] = exam.name
            messages.success(request, f"Examen « {exam.name} » créé avec succès.")
            return redirect("exams:dashboard")
    else:
        form = ExamForm(initial={"year": datetime.now().year})

    return render(request, "exams/exam_create.html", {"form": form})


@login_required
def exam_edit_view(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, "Examen mis à jour.")
            return redirect("exams:select_exam")
    else:
        form = ExamForm(instance=exam)
    return render(request, "exams/exam_create.html", {"form": form, "exam": exam})


@login_required
def exam_lock_view(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == "POST":
        exam.is_locked = not exam.is_locked
        exam.save()
        status = "verrouillé" if exam.is_locked else "déverrouillé"
        messages.success(request, f"Examen {status}.")
    return redirect("exams:exam_setup")


# ──────────────────────────────────────────────
# Schools
# ──────────────────────────────────────────────

@login_required
def schools_list_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    schools = School.objects.annotate(
        student_count=Count("students", filter=Q(students__exam=exam))
    )
    return render(request, "exams/schools/list.html", {"schools": schools})


@login_required
def school_create_view(request):
    if request.method == "POST":
        form = SchoolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Établissement créé avec succès.")
            return redirect("exams:schools_list")
    else:
        form = SchoolForm()
    return render(request, "exams/schools/form.html", {"form": form, "title": "Ajouter un établissement"})


@login_required
def school_edit_view(request, pk):
    school = get_object_or_404(School, pk=pk)
    if request.method == "POST":
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Établissement mis à jour.")
            return redirect("exams:schools_list")
    else:
        form = SchoolForm(instance=school)
    return render(request, "exams/schools/form.html", {"form": form, "title": "Modifier l'établissement"})


@login_required
def school_delete_view(request, pk):
    school = get_object_or_404(School, pk=pk)
    if request.method == "POST":
        try:
            school.delete()
            messages.success(request, "Établissement supprimé.")
        except Exception:
            messages.error(request, "Impossible de supprimer cet établissement (des élèves y sont rattachés).")
    return redirect("exams:schools_list")


# ──────────────────────────────────────────────
# Students
# ──────────────────────────────────────────────

@login_required
def students_list_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    subjects_count = exam.subjects.count()

    if request.method == "POST":
        action = request.POST.get("bulk_action")
        raw_ids = request.POST.getlist("student_ids")
        ids = []
        for x in raw_ids:
            if str(x).isdigit():
                ids.append(int(x))
        if ids:
            qs = Student.objects.filter(exam=exam, pk__in=ids)
            if action == "mark_absent":
                qs.update(is_absent=True)
                messages.success(request, f"{len(ids)} élève(s) marqué(s) absent(s).")
            elif action == "mark_present":
                qs.update(is_absent=False)
                messages.success(request, f"{len(ids)} élève(s) marqué(s) présent(s).")
            elif action == "delete":
                n = qs.count()
                qs.delete()
                messages.success(request, f"{n} élève(s) supprimé(s).")
            else:
                messages.warning(request, "Action groupée non reconnue.")
        else:
            messages.warning(request, "Sélectionnez au moins un élève.")
        from urllib.parse import urlencode

        return redirect(f"{request.path}?{urlencode(request.GET)}")

    students = exam.students.select_related("school").annotate(
        scores_filled=Count("scores", filter=Q(scores__subject__exam=exam), distinct=True),
    )

    search = request.GET.get("search", "")
    if search:
        students = students.filter(
            Q(last_name__icontains=search)
            | Q(first_name__icontains=search)
            | Q(candidate_number__icontains=search),
        )

    school_filter = request.GET.get("school")
    if school_filter:
        students = students.filter(school_id=school_filter)

    schools = School.objects.filter(students__exam=exam).distinct()

    paginator = Paginator(students.order_by("last_name", "first_name"), 20)
    page_param = request.GET.get("page")
    try:
        page_obj = paginator.page(page_param)
    except (PageNotAnInteger, TypeError, ValueError):
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, "exams/students/list.html", {
        "page_obj": page_obj,
        "paginator": paginator,
        "schools": schools,
        "search": search,
        "school_filter": school_filter,
        "subjects_count": subjects_count,
        "students_total": paginator.count,
    })


@login_required
def student_create_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.exam = exam
            seq = exam.students.count() + 1
            student.candidate_number = f"{exam.year}-{seq:05d}"
            student.save()
            messages.success(request, "Élève ajouté avec succès.")
            return redirect("exams:students_list")
    else:
        form = StudentForm()

    return render(request, "exams/students/form.html", {"form": form, "title": "Ajouter un élève"})


@login_required
def student_edit_view(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Élève mis à jour.")
            return redirect("exams:students_list")
    else:
        form = StudentForm(instance=student)
    return render(request, "exams/students/form.html", {"form": form, "title": "Modifier l'élève"})


@login_required
def student_delete_view(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        student.delete()
        messages.success(request, "Élève supprimé.")
    return redirect("exams:students_list")


@login_required
def students_import_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        form = ExcelImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            school = form.cleaned_data["school"]
            result = parse_excel_file(file)

            if result["success"]:
                count = 0
                for s in result["students"]:
                    seq = exam.students.count() + 1
                    candidate_number = f"{exam.year}-{seq:05d}"
                    Student.objects.create(
                        candidate_number=candidate_number,
                        first_name=s["first_name"],
                        last_name=s["last_name"],
                        gender=s.get("gender", ""),
                        birth_date=s.get("birth_date"),
                        exam=exam,
                        school=school,
                    )
                    count += 1
                messages.success(request, f"{count} élève(s) importé(s) avec succès.")
                for err in result["errors"]:
                    messages.warning(request, err)
            else:
                for err in result["errors"]:
                    messages.error(request, err)

            return redirect("exams:students_list")
    else:
        form = ExcelImportForm()

    return render(request, "exams/students/import.html", {"form": form})


# ──────────────────────────────────────────────
# Subjects
# ──────────────────────────────────────────────

@login_required
def subjects_list_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    subjects = exam.subjects.annotate(scores_count=Count("scores"))
    return render(request, "exams/subjects/list.html", {"subjects": subjects})


@login_required
def subject_create_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.exam = exam
            subject.save()
            messages.success(request, "Épreuve ajoutée avec succès.")
            return redirect("exams:subjects_list")
    else:
        form = SubjectForm(initial={"max_score": _safe_grading_scale(exam)})
    return render(request, "exams/subjects/form.html", {"form": form, "title": "Ajouter une épreuve"})


@login_required
def subject_edit_view(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, "Épreuve mise à jour.")
            return redirect("exams:subjects_list")
    else:
        form = SubjectForm(instance=subject)
    return render(request, "exams/subjects/form.html", {"form": form, "title": "Modifier l'épreuve"})


@login_required
def subject_delete_view(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        subject.delete()
        messages.success(request, "Épreuve supprimée.")
    return redirect("exams:subjects_list")


# ──────────────────────────────────────────────
# Scores
# ──────────────────────────────────────────────

@login_required
def scores_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    students_count = exam.students.count()
    subjects = exam.subjects.order_by("name")
    subjects_cards = []
    for subj in subjects:
        scores_qs = Score.objects.filter(subject=subj)
        entered = scores_qs.count()
        vals = list(scores_qs.values_list("value", flat=True))
        if students_count and entered >= students_count:
            status = "complete"
        elif entered:
            status = "partial"
        else:
            status = "empty"
        subjects_cards.append({
            "subject": subj,
            "entered": entered,
            "total": students_count,
            "pct": round(entered / students_count * 100, 1) if students_count else 0.0,
            "avg": round(sum(vals) / len(vals), 2) if vals else None,
            "min_s": min(vals) if vals else None,
            "max_s": max(vals) if vals else None,
            "status": status,
        })

    subjects_count = subjects.count()
    slots_total = students_count * subjects_count if subjects_count else 0
    scores_entered = Score.objects.filter(student__exam=exam).count() if slots_total else 0
    global_pct = round(scores_entered / slots_total * 100, 1) if slots_total else 0.0
    first_student = exam.students.order_by("last_name", "first_name").first()

    return render(request, "exams/scores/index.html", {
        "subjects_cards": subjects_cards,
        "scores_entered": scores_entered,
        "slots_total": slots_total,
        "global_pct": global_pct,
        "first_student": first_student,
        "students_count": students_count,
    })


@login_required
def scores_by_subject_view(request, subject_id):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    subject = get_object_or_404(Subject, pk=subject_id, exam=exam)

    subject_ids = list(exam.subjects.order_by("name").values_list("id", flat=True))
    try:
        idx = subject_ids.index(subject.id)
    except ValueError:
        idx = 0
    prev_subject_id = subject_ids[idx - 1] if idx > 0 else None
    next_subject_id = subject_ids[idx + 1] if idx + 1 < len(subject_ids) else None

    q = (request.GET.get("q") or request.POST.get("q") or "").strip()
    school_raw = request.GET.get("school") or request.POST.get("school") or ""
    empty_only = (request.GET.get("empty_only") or request.POST.get("empty_only") or "") == "1"

    students = exam.students.select_related("school").order_by("last_name", "first_name")
    if q:
        students = students.filter(
            Q(last_name__icontains=q)
            | Q(first_name__icontains=q)
            | Q(candidate_number__icontains=q),
        )
    if school_raw.isdigit():
        students = students.filter(school_id=int(school_raw))

    score_rows = list(Score.objects.filter(subject=subject, student__exam=exam))
    existing_scores = {s.student_id: s.value for s in score_rows}
    score_obj_by_student = {s.student_id: s for s in score_rows}

    if empty_only:
        students = students.exclude(id__in=list(existing_scores.keys()))

    students_count_all = exam.students.count()
    entered_all = len(existing_scores)
    all_vals = list(existing_scores.values())
    toolbar_stats = None
    if all_vals:
        toolbar_stats = {
            "avg": round(sum(all_vals) / len(all_vals), 2),
            "min": min(all_vals),
            "max": max(all_vals),
        }

    paginator = Paginator(students, 50)
    page_param = request.POST.get("page") if request.method == "POST" else request.GET.get("page")
    try:
        page_obj = paginator.page(page_param)
    except (PageNotAnInteger, TypeError, ValueError):
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    if request.method == "POST":
        updated = 0
        max_sc = float(subject.max_score)
        for student in page_obj.object_list:
            raw = request.POST.get(f"score_{student.id}")
            val = _parse_score_post_value(raw)
            if val is not None and 0 <= val <= max_sc:
                prev = Score.objects.filter(student=student, subject=subject).first()
                old_val = float(prev.value) if prev else None
                obj, created = Score.objects.update_or_create(
                    student=student,
                    subject=subject,
                    defaults={"value": val},
                )
                if created:
                    log_score_change(
                        obj,
                        old_value=None,
                        new_value=val,
                        reason=ScoreHistory.REASON_INITIAL,
                        comment="Saisie administrateur (tableau)",
                        admin_user=request.user,
                    )
                elif old_val is not None and old_val != val:
                    log_score_change(
                        obj,
                        old_value=old_val,
                        new_value=val,
                        reason=ScoreHistory.REASON_CORRECTION,
                        comment="Modification administrateur (tableau)",
                        admin_user=request.user,
                    )
                updated += 1
        messages.success(request, f"{updated} note(s) enregistrée(s) pour « {subject.name} » (page {page_obj.number}).")
        from urllib.parse import urlencode

        query = {"page": str(page_obj.number)}
        if q:
            query["q"] = q
        if school_raw.isdigit():
            query["school"] = school_raw
        if empty_only:
            query["empty_only"] = "1"
        return redirect(f"{request.path}?{urlencode(query)}")

    students_with_scores = []
    for student in page_obj.object_list:
        sco = score_obj_by_student.get(student.id)
        students_with_scores.append({
            "student": student,
            "score": existing_scores.get(student.id, ""),
            "score_obj": sco,
        })

    schools = School.objects.filter(students__exam=exam).distinct().order_by("name")
    absent_students_no_score = exam.students.filter(is_absent=True).exclude(
        id__in=list(existing_scores.keys()),
    ).count()

    gscale = _safe_grading_scale(exam)
    scaled_passing_threshold = round(
        exam.passing_grade * (float(subject.max_score) / gscale), 4,
    )

    return render(request, "exams/scores/by_subject.html", {
        "subject": subject,
        "students_with_scores": students_with_scores,
        "page_obj": page_obj,
        "paginator": paginator,
        "q": q,
        "school_filter": school_raw,
        "empty_only": empty_only,
        "schools": schools,
        "prev_subject_id": prev_subject_id,
        "next_subject_id": next_subject_id,
        "toolbar_stats": toolbar_stats,
        "students_count_all": students_count_all,
        "entered_all": entered_all,
        "passing_grade": exam.passing_grade,
        "grading_scale": gscale,
        "scaled_passing_threshold": scaled_passing_threshold,
        "absent_students_no_score": absent_students_no_score,
    })


@login_required
def scores_by_student_view(request, student_id):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    student = get_object_or_404(Student, pk=student_id, exam=exam)
    subjects = exam.subjects.order_by("name")

    ordered_ids = list(exam.students.order_by("last_name", "first_name").values_list("id", flat=True))
    try:
        ix = ordered_ids.index(student.id)
    except ValueError:
        ix = 0
    prev_student_id = ordered_ids[ix - 1] if ix > 0 else None
    next_student_id = ordered_ids[ix + 1] if ix + 1 < len(ordered_ids) else None

    if request.method == "POST":
        updated = 0
        for subj in subjects:
            raw = request.POST.get(f"score_subj_{subj.id}")
            val = _parse_score_post_value(raw)
            max_sc = float(subj.max_score)
            if val is not None and 0 <= val <= max_sc:
                prev = Score.objects.filter(student=student, subject=subj).first()
                old_val = float(prev.value) if prev else None
                obj, created = Score.objects.update_or_create(
                    student=student,
                    subject=subj,
                    defaults={"value": val},
                )
                if created:
                    log_score_change(
                        obj,
                        old_value=None,
                        new_value=val,
                        reason=ScoreHistory.REASON_INITIAL,
                        comment="Saisie administrateur (par élève)",
                        admin_user=request.user,
                    )
                elif old_val is not None and old_val != val:
                    log_score_change(
                        obj,
                        old_value=old_val,
                        new_value=val,
                        reason=ScoreHistory.REASON_CORRECTION,
                        comment="Modification administrateur (par élève)",
                        admin_user=request.user,
                    )
                updated += 1
        messages.success(request, f"{updated} note(s) enregistrée(s) pour {student.last_name} {student.first_name}.")
        return redirect("exams:scores_by_student", student_id=student.id)

    score_by_subject = {
        s.subject_id: s
        for s in Score.objects.filter(student=student, subject__exam=exam).select_related("subject")
    }
    scores_map = {sid: s.value for sid, s in score_by_subject.items()}

    gscale = _safe_grading_scale(exam)
    subjects_rows = []
    for subj in subjects:
        sco = score_by_subject.get(subj.id)
        subjects_rows.append({
            "subject": subj,
            "score": scores_map.get(subj.id, ""),
            "score_obj": sco,
            "scaled_passing_threshold": round(
                exam.passing_grade * (float(subj.max_score) / gscale), 4,
            ),
        })

    subjects_meta_json = json.dumps([
        {
            "id": s.id,
            "name": s.name,
            "max_score": float(s.max_score),
            "coefficient": float(s.coefficient) if s.coefficient is not None else None,
        }
        for s in subjects
    ])

    return render(request, "exams/scores/by_student.html", {
        "student": student,
        "subjects_rows": subjects_rows,
        "prev_student_id": prev_student_id,
        "next_student_id": next_student_id,
        "passing_grade": exam.passing_grade,
        "grading_scale": gscale,
        "subjects_meta_json": subjects_meta_json,
    })


# ──────────────────────────────────────────────
# Rankings
# ──────────────────────────────────────────────

@login_required
def rankings_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    tab = request.GET.get("tab", "students")
    students_data = _build_students_data(exam)

    if tab == "schools":
        school_map = {}
        for s in students_data:
            sid = s["school"].id
            if sid not in school_map:
                school_map[sid] = {
                    "school_id": sid,
                    "school_name": s["school_name"],
                    "averages": [],
                    "total_students": 0,
                    "passed": 0,
                }
            school_map[sid]["total_students"] += 1
            if s["average"] is not None:
                school_map[sid]["averages"].append(s["average"])
                if s["average"] >= exam.passing_grade:
                    school_map[sid]["passed"] += 1

        schools_data = []
        for data in school_map.values():
            avg = round(sum(data["averages"]) / len(data["averages"]), 2) if data["averages"] else 0
            schools_data.append({
                "school_id": data["school_id"],
                "school_name": data["school_name"],
                "average": avg,
                "total_students": data["total_students"],
                "passed": data["passed"],
                "pass_rate": round(data["passed"] / len(data["averages"]) * 100, 1) if data["averages"] else 0,
            })
        ranked_schools = rank_schools(schools_data)
        return render(request, "exams/rankings/index.html", {
            "tab": tab,
            "ranked_schools": ranked_schools,
        })

    return render(request, "exams/rankings/index.html", {
        "tab": tab,
        "students_data": students_data,
    })


# ──────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────

@login_required
def statistics_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    school_filter = (request.GET.get("school") or "").strip()

    students_data = _build_students_data(exam)
    if school_filter.isdigit():
        sid = int(school_filter)
        students_data = [s for s in students_data if s["school"].id == sid]

    stats = compute_global_stats(students_data, exam.passing_grade)
    averages = [s["average"] for s in students_data if s["average"] is not None]
    median_avg = round(statistics.median(averages), 2) if averages else 0.0
    stdev_avg = round(statistics.pstdev(averages), 2) if len(averages) > 1 else 0.0
    gscale = _safe_grading_scale(exam)
    distribution = compute_distribution(averages, max_val=gscale)

    mention_counts: dict[str, int] = {}
    for s in students_data:
        m = (s.get("mention") or "").strip()
        if m:
            mention_counts[m] = mention_counts.get(m, 0) + 1

    full_data = _build_students_data(exam)
    school_avgs: dict[str, list[float]] = defaultdict(list)
    for s in full_data:
        if s["average"] is not None:
            school_avgs[s["school_name"]].append(s["average"])
    school_chart = [
        {"name": name, "average": round(sum(vals) / len(vals), 2)}
        for name, vals in sorted(school_avgs.items(), key=lambda x: -sum(x[1]) / len(x[1]))
    ]

    subjects = exam.subjects.all()
    subject_stats = []
    for subj in subjects:
        scores = list(Score.objects.filter(subject=subj).values("value"))
        ss = compute_subject_stats(scores, subj.max_score)
        ss["name"] = subj.name
        subject_stats.append(ss)

    schools = School.objects.filter(students__exam=exam).distinct().order_by("name")
    gender_stats_json = json.dumps(stats.get("gender_stats") or {})

    subj_chart_max = gscale
    if subject_stats:
        subj_chart_max = max(
            gscale,
            max((float(ss["highest"]) for ss in subject_stats), default=0),
        )

    return render(request, "exams/statistics/index.html", {
        "stats": stats,
        "distribution": json.dumps(distribution),
        "subject_stats": subject_stats,
        "subject_stats_json": json.dumps(subject_stats),
        "median_avg": median_avg,
        "stdev_avg": stdev_avg,
        "mention_labels": json.dumps(list(mention_counts.keys())),
        "mention_data": json.dumps(list(mention_counts.values())),
        "school_chart_json": json.dumps(school_chart),
        "gender_stats_json": gender_stats_json,
        "schools": schools,
        "school_filter": school_filter,
        "grading_scale": gscale,
        "subject_chart_y_max": round(subj_chart_max + 0.5, 1) if subj_chart_max else gscale,
    })


# ──────────────────────────────────────────────
# Rooms
# ──────────────────────────────────────────────

@login_required
def rooms_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    rooms = exam.rooms.annotate(assigned_count=Count("assignments"))
    total_capacity = sum(r.capacity for r in rooms)
    total_students = exam.students.count()

    return render(request, "exams/rooms/index.html", {
        "rooms": rooms,
        "total_capacity": total_capacity,
        "total_students": total_students,
    })


@login_required
def room_create_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.exam = exam
            room.save()
            messages.success(request, "Salle ajoutée avec succès.")
            return redirect("exams:rooms")
    else:
        form = RoomForm()
    return render(request, "exams/rooms/form.html", {"form": form, "title": "Ajouter une salle"})


@login_required
def room_delete_view(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == "POST":
        room.delete()
        messages.success(request, "Salle supprimée.")
    return redirect("exams:rooms")


@login_required
def rooms_dispatch_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        RoomAssignment.objects.filter(student__exam=exam).delete()

        students = list(exam.students.values("id", "last_name", "first_name"))
        rooms = list(exam.rooms.values("id", "name", "capacity"))

        try:
            assignments = alphabetical_dispatch(students, rooms)
            for a in assignments:
                RoomAssignment.objects.create(
                    student_id=a["student_id"],
                    room_id=a["room_id"],
                    seat_number=a["seat_number"],
                )
            messages.success(request, f"{len(assignments)} élève(s) réparti(s) dans les salles.")
        except ValueError as e:
            messages.error(request, str(e))

    return redirect("exams:rooms")


# ──────────────────────────────────────────────
# Exports
# ──────────────────────────────────────────────

@login_required
def exports_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    students_count = exam.students.count()
    subjects_count = exam.subjects.count()
    slots = students_count * subjects_count if subjects_count else 0
    scores_count = Score.objects.filter(student__exam=exam).count() if slots else 0
    scores_complete = bool(slots and scores_count >= slots)
    export_warning = None
    if slots and not scores_complete:
        export_warning = (
            f"Saisie incomplète : {scores_count}/{slots} notes enregistrées. "
            "Les exports reflètent l’état actuel des données."
        )

    return render(request, "exams/exports/index.html", {
        "students_count": students_count,
        "subjects_count": subjects_count,
        "scores_count": scores_count,
        "slots_total": slots,
        "scores_complete": scores_complete,
        "export_warning": export_warning,
    })


@login_required
def export_pdf_view(request, doc_type):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if doc_type == "results":
        students_data = _build_students_data(exam)
        buffer = generate_results_pdf(exam, students_data)
        filename = f"resultats_{exam.code}_{exam.year}.pdf"
    elif doc_type == "transcripts":
        buffer = generate_transcripts_pdf(exam)
        filename = f"releves_notes_{exam.code}_{exam.year}.pdf"
    elif doc_type == "rooms":
        rooms = exam.rooms.prefetch_related("assignments__student").all()
        rooms_data = []
        for room in rooms:
            assigns = room.assignments.select_related("student").order_by("seat_number")
            rooms_data.append({
                "room_name": room.name,
                "assignments": [
                    {
                        "seat": a.seat_number,
                        "candidate_number": a.student.candidate_number,
                        "name": f"{a.student.last_name} {a.student.first_name}",
                    }
                    for a in assigns
                ],
            })
        buffer = generate_room_dispatch_pdf(exam, rooms_data)
        filename = f"repartition_salles_{exam.code}_{exam.year}.pdf"
    else:
        messages.error(request, "Type d'export inconnu.")
        return redirect("exams:exports")

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_excel_view(request, doc_type):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if doc_type == "results":
        students_data = _build_students_data(exam)
        buffer = generate_results_excel(exam, students_data)
        filename = f"resultats_{exam.code}_{exam.year}.xlsx"
    elif doc_type == "by_school":
        students_data = _build_students_data(exam)
        buffer = generate_results_by_school_excel(exam, students_data)
        filename = f"resultats_par_etablissement_{exam.code}_{exam.year}.xlsx"
    else:
        messages.error(request, "Type d'export inconnu.")
        return redirect("exams:exports")

    response = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_json_view(request, doc_type):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if doc_type != "backup":
        messages.error(request, "Type d'export inconnu.")
        return redirect("exams:exports")

    payload = build_exam_backup_dict(exam)
    body = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="backup_{exam.code}_{exam.year}.json"'
    )
    return response


# ──────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────

@login_required
def settings_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "clear_scores":
            n = Score.objects.filter(student__exam=exam).count()
            Score.objects.filter(student__exam=exam).delete()
            messages.warning(request, f"{n} note(s) supprimée(s) pour cet examen.")
            return redirect("exams:settings")
        if action == "clear_room_assignments":
            n = RoomAssignment.objects.filter(student__exam=exam).count()
            RoomAssignment.objects.filter(student__exam=exam).delete()
            messages.warning(request, f"{n} assignation(s) de salle supprimée(s).")
            return redirect("exams:settings")

    students_count = exam.students.count()
    subjects_count = exam.subjects.count()
    slots = students_count * subjects_count if subjects_count else 0
    scores_count = Score.objects.filter(student__exam=exam).count() if slots else 0
    completion_pct = round(scores_count / slots * 100, 1) if slots else 0.0

    return render(request, "exams/settings/index.html", {
        "exam": exam,
        "students_count": students_count,
        "subjects_count": subjects_count,
        "schools_count": School.objects.filter(students__exam=exam).distinct().count(),
        "scores_count": scores_count,
        "slots_total": slots,
        "completion_pct": completion_pct,
    })
