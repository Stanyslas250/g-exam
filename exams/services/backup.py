"""
Export JSON complet d'un examen (sauvegarde / migration).
"""
from __future__ import annotations

from typing import Any


def build_exam_backup_dict(exam) -> dict[str, Any]:
    from ..models import RoomAssignment, Score

    school_ids = set(exam.students.values_list("school_id", flat=True))
    from ..models import School

    schools_qs = School.objects.filter(pk__in=school_ids).order_by("name")
    schools = [{"id": s.id, "name": s.name, "code": s.code} for s in schools_qs]

    students = []
    for st in exam.students.select_related("school").order_by("last_name", "first_name"):
        students.append({
            "id": st.id,
            "candidate_number": st.candidate_number,
            "first_name": st.first_name,
            "last_name": st.last_name,
            "gender": st.gender,
            "birth_date": st.birth_date.isoformat() if st.birth_date else None,
            "is_absent": st.is_absent,
            "school_id": st.school_id,
        })

    subjects = []
    for sub in exam.subjects.order_by("name"):
        subjects.append({
            "id": sub.id,
            "name": sub.name,
            "coefficient": sub.coefficient,
            "max_score": float(sub.max_score),
        })

    scores = []
    for sc in Score.objects.filter(student__exam=exam).select_related("student", "subject"):
        scores.append({
            "student_id": sc.student_id,
            "subject_id": sc.subject_id,
            "value": float(sc.value),
        })

    rooms = []
    for rm in exam.rooms.order_by("name"):
        rooms.append({
            "id": rm.id,
            "name": rm.name,
            "capacity": rm.capacity,
        })

    assignments = []
    for ra in RoomAssignment.objects.filter(student__exam=exam).select_related("student", "room"):
        assignments.append({
            "student_id": ra.student_id,
            "room_id": ra.room_id,
            "seat_number": ra.seat_number,
        })

    return {
        "format": "g-exam-backup",
        "version": 1,
        "exam": {
            "id": exam.id,
            "name": exam.name,
            "code": exam.code,
            "year": exam.year,
            "exam_type": exam.exam_type,
            "description": exam.description,
            "start_date": exam.start_date.isoformat() if exam.start_date else None,
            "end_date": exam.end_date.isoformat() if exam.end_date else None,
            "location": exam.location,
            "grading_scale": float(exam.grading_scale),
            "passing_grade": float(exam.passing_grade),
            "is_locked": exam.is_locked,
        },
        "schools": schools,
        "subjects": subjects,
        "students": students,
        "scores": scores,
        "rooms": rooms,
        "room_assignments": assignments,
    }
