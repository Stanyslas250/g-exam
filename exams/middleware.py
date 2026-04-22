from django.shortcuts import redirect


EXEMPT_URLS = [
    "/login/",
    "/logout/",
    "/admin/",
    "/select-exam/",
    "/exam/create/",
    "/exam/import/",
    "/exam/generate-code/",
    "/correction/",
    "/dashboard/",
]

EXEMPT_EXACT = ["/"]


class ExamSelectionMiddleware:
    """Ensures an exam is selected in session before accessing exam-specific pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            if path in EXEMPT_EXACT:
                return self.get_response(request)
            is_exempt = any(path.startswith(url) for url in EXEMPT_URLS)
            if not is_exempt and not request.session.get("active_exam_id"):
                return redirect("exams:select_exam")

        return self.get_response(request)
