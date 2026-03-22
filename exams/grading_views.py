"""Vues : interface correcteur, enseignants, harmonisation, QR, historique."""

from __future__ import annotations

import io
import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .forms import (
    CorrectorGradeForm,
    CorrectorLoginForm,
    HarmonizationForm,
    TeacherForm,
)
from .models import (
    Exam,
    Harmonization,
    Score,
    ScoreHistory,
    Student,
    Subject,
    SubjectAssignment,
    Teacher,
)
from .services.score_history import log_score_change
from .views import get_active_exam

SESSION_CORRECTION_EXAM_ID = "correction_exam_id"
SESSION_CORRECTION_TEACHER_ID = "correction_teacher_id"
SESSION_CORRECTION_RECENT = "correction_recent_entries"


def _build_absolute_correction_url(request, exam: Exam) -> str:
    path = reverse("exams:corrector_login", kwargs={"exam_code": exam.code})
    return request.build_absolute_uri(path)


def _corrector_session_ok(request, exam: Exam) -> Teacher | None:
    eid = request.session.get(SESSION_CORRECTION_EXAM_ID)
    tid = request.session.get(SESSION_CORRECTION_TEACHER_ID)
    if not eid or not tid or int(eid) != exam.id:
        return None
    try:
        teacher = Teacher.objects.get(pk=int(tid), is_active=True)
    except (Teacher.DoesNotExist, ValueError, TypeError):
        return None
    return teacher


def _append_recent_session(request, matricule: str, value: float) -> None:
    recent = request.session.get(SESSION_CORRECTION_RECENT, [])
    if not isinstance(recent, list):
        recent = []
    recent.insert(0, {"matricule": matricule, "value": value})
    request.session[SESSION_CORRECTION_RECENT] = recent[:10]


def compute_harmonized_value(
    old: float,
    max_score: float,
    adjustment_type: str,
    value: float,
) -> float:
    if adjustment_type == Harmonization.TYPE_ADD:
        out = old + value
    elif adjustment_type == Harmonization.TYPE_MULTIPLY:
        out = old * value
    elif adjustment_type == Harmonization.TYPE_SET_MIN:
        out = max(old, value)
    else:
        out = old
    return max(0.0, min(float(max_score), round(out, 4)))


# ── Interface correcteur (sans login Django) ───────────────────────────────


def corrector_login_view(request, exam_code: str):
    exam = get_object_or_404(Exam, code__iexact=exam_code.strip())
    if exam.is_locked:
        messages.error(request, "Cet examen est verrouillé : correction indisponible.")
        return render(request, "correction/login.html", {"exam": exam, "form": CorrectorLoginForm(), "locked": True})

    teacher = _corrector_session_ok(request, exam)
    if teacher:
        return redirect("exams:corrector_subjects", exam_code=exam.code)

    form = CorrectorLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"].strip()
        try:
            t = Teacher.objects.get(code__iexact=code, is_active=True)
        except Teacher.DoesNotExist:
            messages.error(request, "Identifiant incorrect ou compte inactif.")
        else:
            request.session[SESSION_CORRECTION_EXAM_ID] = exam.id
            request.session[SESSION_CORRECTION_TEACHER_ID] = t.id
            messages.success(request, f"Bienvenue, {t.first_name} {t.last_name}.")
            return redirect("exams:corrector_subjects", exam_code=exam.code)

    return render(request, "correction/login.html", {"exam": exam, "form": form, "locked": False})


def corrector_logout_view(request):
    request.session.pop(SESSION_CORRECTION_EXAM_ID, None)
    request.session.pop(SESSION_CORRECTION_TEACHER_ID, None)
    request.session.pop(SESSION_CORRECTION_RECENT, None)
    messages.info(request, "Vous êtes déconnecté de l’interface correcteur.")
    return redirect("exams:login")


def corrector_subjects_view(request, exam_code: str):
    exam = get_object_or_404(Exam, code__iexact=exam_code.strip())
    teacher = _corrector_session_ok(request, exam)
    if not teacher:
        messages.warning(request, "Veuillez vous identifier.")
        return redirect("exams:corrector_login", exam_code=exam.code)

    assigned_ids = SubjectAssignment.objects.filter(
        teacher=teacher,
        exam=exam,
    ).values_list("subject_id", flat=True)
    subjects = exam.subjects.filter(pk__in=assigned_ids).order_by("name")
    return render(request, "correction/subjects.html", {
        "exam": exam,
        "teacher": teacher,
        "subjects": subjects,
    })


def corrector_grade_entry_view(request, exam_code: str, subject_id: int):
    exam = get_object_or_404(Exam, code__iexact=exam_code.strip())
    if exam.is_locked:
        messages.error(request, "Examen verrouillé.")
        return redirect("exams:corrector_login", exam_code=exam.code)

    teacher = _corrector_session_ok(request, exam)
    if not teacher:
        messages.warning(request, "Veuillez vous identifier.")
        return redirect("exams:corrector_login", exam_code=exam.code)

    subject = get_object_or_404(Subject, pk=subject_id, exam=exam)
    if not SubjectAssignment.objects.filter(teacher=teacher, subject=subject, exam=exam).exists():
        messages.error(request, "Vous n’êtes pas assigné à cette épreuve.")
        return redirect("exams:corrector_subjects", exam_code=exam.code)

    form = CorrectorGradeForm(request.POST or None)
    recent = request.session.get(SESSION_CORRECTION_RECENT, [])
    lookup = None

    if request.method == "POST" and form.is_valid():
        matricule = form.cleaned_data["candidate_number"].strip()
        val = float(form.cleaned_data["value"])
        max_sc = float(subject.max_score)
        comment = (form.cleaned_data.get("recorrection_comment") or "").strip()

        student = Student.objects.filter(exam=exam, candidate_number__iexact=matricule).first()
        if student:
            lookup = {
                "candidate_number": student.candidate_number,
                "is_absent": student.is_absent,
            }
        if not student:
            messages.error(request, "Aucun candidat avec ce numéro pour cet examen.")
        elif val < 0 or val > max_sc:
            messages.error(request, f"La note doit être entre 0 et {max_sc}.")
        else:
            score, created = Score.objects.get_or_create(
                student=student,
                subject=subject,
                defaults={"value": val},
            )
            if created:
                log_score_change(
                    score,
                    old_value=None,
                    new_value=val,
                    reason=ScoreHistory.REASON_INITIAL,
                    comment="Saisie correcteur",
                    teacher=teacher,
                )
                messages.success(request, f"Note enregistrée pour le candidat {matricule}.")
                _append_recent_session(request, matricule, val)
                return redirect("exams:corrector_grade", exam_code=exam.code, subject_id=subject.id)

            old_val = float(score.value)
            if old_val == val:
                messages.info(request, "Note identique — aucun changement.")
            else:
                if not comment:
                    messages.error(
                        request,
                        "Une note existe déjà : indiquez un motif de modification (re-correction).",
                    )
                else:
                    score.value = val
                    score.save(update_fields=["value", "updated_at"])
                    log_score_change(
                        score,
                        old_value=old_val,
                        new_value=val,
                        reason=ScoreHistory.REASON_RECORRECTION,
                        comment=comment,
                        teacher=teacher,
                    )
                    messages.success(request, f"Note mise à jour pour le candidat {matricule}.")
                    _append_recent_session(request, matricule, val)
                    return redirect("exams:corrector_grade", exam_code=exam.code, subject_id=subject.id)

    return render(request, "correction/grade_entry.html", {
        "exam": exam,
        "teacher": teacher,
        "subject": subject,
        "form": form,
        "recent": recent if isinstance(recent, list) else [],
        "lookup": lookup,
    })


# ── Enseignants (admin G-Exam) ───────────────────────────────────────────


@login_required
def teachers_list_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    teachers = Teacher.objects.all().order_by("last_name", "first_name")
    assignment_map: dict[int, list[str]] = {}
    for a in SubjectAssignment.objects.filter(exam=exam).select_related("subject"):
        assignment_map.setdefault(a.teacher_id, []).append(a.subject.name)

    rows = []
    for t in teachers:
        names = assignment_map.get(t.id, [])
        rows.append({"teacher": t, "subjects_label": ", ".join(sorted(names)) if names else "—"})

    return render(request, "exams/teachers/list.html", {"rows": rows, "exam": exam})


@login_required
def teacher_create_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    if request.method == "POST":
        form = TeacherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Enseignant créé.")
            return redirect("exams:teachers_list")
    else:
        form = TeacherForm()
    return render(request, "exams/teachers/form.html", {"form": form, "title": "Ajouter un enseignant"})


@login_required
def teacher_edit_view(request, pk: int):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == "POST":
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, "Enseignant mis à jour.")
            return redirect("exams:teachers_list")
    else:
        form = TeacherForm(instance=teacher)
    return render(request, "exams/teachers/form.html", {"form": form, "title": "Modifier l’enseignant"})


@login_required
def teacher_delete_view(request, pk: int):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == "POST":
        teacher.delete()
        messages.success(request, "Enseignant supprimé.")
        return redirect("exams:teachers_list")
    return render(request, "exams/teachers/delete_confirm.html", {"teacher": teacher})


@login_required
def teacher_assign_view(request, pk: int):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    teacher = get_object_or_404(Teacher, pk=pk)
    existing = set(
        SubjectAssignment.objects.filter(teacher=teacher, exam=exam).values_list("subject_id", flat=True),
    )

    if request.method == "POST":
        selected = [int(x) for x in request.POST.getlist("subject_ids") if str(x).isdigit()]
        valid_ids = set(exam.subjects.filter(pk__in=selected).values_list("id", flat=True))
        SubjectAssignment.objects.filter(teacher=teacher, exam=exam).delete()
        bulk = [
            SubjectAssignment(teacher=teacher, subject_id=sid, exam_id=exam.id)
            for sid in valid_ids
        ]
        if bulk:
            SubjectAssignment.objects.bulk_create(bulk)
        messages.success(request, "Assignations mises à jour.")
        return redirect("exams:teachers_list")

    subjects = exam.subjects.order_by("name")
    return render(request, "exams/teachers/assign.html", {
        "teacher": teacher,
        "subjects": subjects,
        "existing": existing,
        "exam": exam,
    })


# ── Harmonisation ─────────────────────────────────────────────────────────


@login_required
def harmonization_view(request, subject_id: int):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    subject = get_object_or_404(Subject, pk=subject_id, exam=exam)
    form = HarmonizationForm(request.POST or None)

    scores_qs = Score.objects.filter(subject=subject, student__exam=exam).select_related("student")
    preview_limit = 25

    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action")
        adj = form.cleaned_data["adjustment_type"]
        val = float(form.cleaned_data["value"])
        comment = form.cleaned_data.get("comment") or ""

        if action == "preview":
            rows = []
            max_sc = float(subject.max_score)
            slice_qs = list(scores_qs[:preview_limit])
            for sc in slice_qs:
                new_v = compute_harmonized_value(float(sc.value), max_sc, adj, val)
                rows.append({
                    "candidate_number": sc.student.candidate_number,
                    "old": sc.value,
                    "new": new_v,
                })
            return render(request, "exams/scores/harmonize.html", {
                "subject": subject,
                "exam": exam,
                "form": form,
                "preview_rows": rows,
                "preview_total_sample": len(rows),
                "total_scores": scores_qs.count(),
            })

        if action == "apply":
            max_sc = float(subject.max_score)
            count = 0
            for sc in scores_qs:
                old_v = float(sc.value)
                new_v = compute_harmonized_value(old_v, max_sc, adj, val)
                if new_v != old_v:
                    sc.value = new_v
                    sc.save(update_fields=["value", "updated_at"])
                    log_score_change(
                        sc,
                        old_value=old_v,
                        new_value=new_v,
                        reason=ScoreHistory.REASON_HARMONIZATION,
                        comment=comment or f"Harmonisation {subject.name}",
                        admin_user=request.user,
                    )
                    count += 1
            Harmonization.objects.create(
                exam=exam,
                subject=subject,
                adjustment_type=adj,
                value=val,
                comment=comment,
                applied_by=request.user,
                applied_at=timezone.now(),
                is_applied=True,
            )
            messages.success(request, f"Harmonisation appliquée : {count} note(s) modifiée(s).")
            return redirect("exams:scores_by_subject", subject_id=subject.id)

    return render(request, "exams/scores/harmonize.html", {
        "subject": subject,
        "exam": exam,
        "form": form,
        "preview_rows": None,
        "total_scores": scores_qs.count(),
    })


# ── Historique d’une note ─────────────────────────────────────────────────


@login_required
def score_history_view(request, score_id: int):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    score = get_object_or_404(
        Score.objects.select_related("student", "subject"),
        pk=score_id,
        subject__exam=exam,
    )
    entries = score.history_entries.all().order_by("-created_at")
    return render(request, "exams/scores/history.html", {
        "score": score,
        "entries": entries,
        "exam": exam,
    })


# ── QR code correction (PNG) ──────────────────────────────────────────────


@login_required
@require_GET
def exam_correction_qr_png_view(request):
    exam = get_active_exam(request)
    if not exam:
        return redirect("exams:select_exam")

    url = _build_absolute_correction_url(request, exam)
    img = qrcode.make(url, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    response = HttpResponse(buf.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="qr_correction_{exam.code}.png"'
    return response
