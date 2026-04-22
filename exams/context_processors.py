from .models import Exam, School, Teacher, UserProfile


def active_exam(request):
    """Inject the active exam, sidebar counts, and user plan into all template contexts."""
    exam = None
    exam_id = request.session.get("active_exam_id") if hasattr(request, "session") else None
    if exam_id:
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            if hasattr(request, "session"):
                del request.session["active_exam_id"]

    sidebar_counts = None
    if exam:
        sidebar_counts = {
            "students": exam.students.count(),
            "subjects": exam.subjects.count(),
            "schools": School.objects.filter(students__exam=exam).distinct().count(),
            "rooms": exam.rooms.count(),
            "teachers": Teacher.objects.count(),
        }

    current_user_plan = None
    if hasattr(request, "user") and request.user.is_authenticated:
        try:
            current_user_plan = request.user.profile.plan
        except UserProfile.DoesNotExist:
            pass

    return {
        "active_exam": exam,
        "sidebar_counts": sidebar_counts,
        "current_user_plan": current_user_plan,
    }
