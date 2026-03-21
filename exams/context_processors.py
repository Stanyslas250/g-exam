from .models import Exam


def active_exam(request):
    """Inject the active exam into all template contexts."""
    exam = None
    exam_id = request.session.get("active_exam_id") if hasattr(request, "session") else None
    if exam_id:
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            if hasattr(request, "session"):
                del request.session["active_exam_id"]
    return {"active_exam": exam}
