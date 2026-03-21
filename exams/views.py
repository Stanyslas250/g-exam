import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Avg, Count, Q

from .models import Exam, School, Student, Subject, Score, Room, RoomAssignment
from .forms import (
    ExamForm, SchoolForm, StudentForm, SubjectForm, ScoreForm,
    RoomForm, ExcelImportForm, ExamCodeForm,
)
from .services.calculations import calculate_student_average, get_mention
from .services.rankings import rank_students, rank_schools
from .services.statistics import compute_global_stats, compute_distribution, compute_subject_stats
from .services.room_dispatch import alphabetical_dispatch
from .services.excel_import import parse_excel_file, parse_exam_excel, parse_exam_json
from .services.excel_export import generate_results_excel
from .services.pdf_export import generate_results_pdf, generate_room_dispatch_pdf


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
        avg = calculate_student_average(score_list)
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
            "mention": get_mention(avg, exam.passing_grade) if avg is not None else "",
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
            if meta.get("passing_grade") is not None:
                exam_kwargs["passing_grade"] = meta["passing_grade"]
            if meta.get("is_locked"):
                exam_kwargs["is_locked"] = meta["is_locked"]
        exam = Exam.objects.create(**exam_kwargs)

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
                max_score=s.get("max_score") or 20,
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
    subjects = exam.subjects.all()

    students_data = _build_students_data(exam)
    averages = [s["average"] for s in students_data if s["average"] is not None]

    passed = sum(1 for a in averages if a >= exam.passing_grade)
    failed = sum(1 for a in averages if a < exam.passing_grade)
    absent = students.filter(is_absent=True).count()

    context = {
        "exam": exam,
        "candidates_count": students.count(),
        "subjects_count": subjects.count(),
        "schools_count": School.objects.filter(students__exam=exam).distinct().count(),
        "rooms_count": exam.rooms.count(),
        "passed": passed,
        "failed": failed,
        "absent": absent,
        "pass_rate": round(passed / len(averages) * 100, 1) if averages else 0,
        "overall_average": round(sum(averages) / len(averages), 2) if averages else 0,
        "highest_avg": round(max(averages), 2) if averages else 0,
        "lowest_avg": round(min(averages), 2) if averages else 0,
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
            messages.success(request, f"Examen « {exam.name} » créé avec succès.")
            return redirect("exams:dashboard")
    else:
        from datetime import datetime
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

    students = exam.students.select_related("school").all()

    search = request.GET.get("search", "")
    if search:
        students = students.filter(
            Q(last_name__icontains=search) |
            Q(first_name__icontains=search) |
            Q(candidate_number__icontains=search)
        )

    school_filter = request.GET.get("school")
    if school_filter:
        students = students.filter(school_id=school_filter)

    schools = School.objects.filter(students__exam=exam).distinct()

    return render(request, "exams/students/list.html", {
        "students": students,
        "schools": schools,
        "search": search,
        "school_filter": school_filter,
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
        form = SubjectForm()
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

    subjects = exam.subjects.all()
    return render(request, "exams/scores/index.html", {"subjects": subjects})


@login_required
def scores_by_subject_view(request, subject_id):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    subject = get_object_or_404(Subject, pk=subject_id, exam=exam)
    students = exam.students.select_related("school").order_by("last_name", "first_name")

    if request.method == "POST":
        updated = 0
        for student in students:
            value = request.POST.get(f"score_{student.id}")
            if value is not None and value.strip() != "":
                try:
                    val = float(value)
                    if 0 <= val <= subject.max_score:
                        Score.objects.update_or_create(
                            student=student,
                            subject=subject,
                            defaults={"value": val},
                        )
                        updated += 1
                except (ValueError, TypeError):
                    pass
        messages.success(request, f"{updated} note(s) enregistrée(s) pour « {subject.name} ».")
        return redirect("exams:scores_by_subject", subject_id=subject.id)

    existing_scores = {
        s.student_id: s.value
        for s in Score.objects.filter(subject=subject, student__exam=exam)
    }

    students_with_scores = []
    for student in students:
        students_with_scores.append({
            "student": student,
            "score": existing_scores.get(student.id, ""),
        })

    return render(request, "exams/scores/by_subject.html", {
        "subject": subject,
        "students_with_scores": students_with_scores,
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

    students_data = _build_students_data(exam)
    stats = compute_global_stats(students_data, exam.passing_grade)
    averages = [s["average"] for s in students_data if s["average"] is not None]
    distribution = compute_distribution(averages)

    subjects = exam.subjects.all()
    subject_stats = []
    for subj in subjects:
        scores = list(Score.objects.filter(subject=subj).values("value"))
        ss = compute_subject_stats(scores, subj.max_score)
        ss["name"] = subj.name
        subject_stats.append(ss)

    return render(request, "exams/statistics/index.html", {
        "stats": stats,
        "distribution": json.dumps(distribution),
        "subject_stats": subject_stats,
        "subject_stats_json": json.dumps(subject_stats),
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
    return render(request, "exams/exports/index.html")


@login_required
def export_pdf_view(request, doc_type):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if doc_type == "results":
        students_data = _build_students_data(exam)
        buffer = generate_results_pdf(exam, students_data)
        filename = f"resultats_{exam.code}_{exam.year}.pdf"
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
    else:
        messages.error(request, "Type d'export inconnu.")
        return redirect("exams:exports")

    response = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ──────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────

@login_required
def settings_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")
    return render(request, "exams/settings/index.html", {"exam": exam})
