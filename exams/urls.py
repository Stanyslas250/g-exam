from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import grading_views

app_name = "exams"

urlpatterns = [
    # Landing page publique (page d'accueil)
    path("", views.landing_view, name="landing"),

    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Interface correcteur (hors session examen admin)
    path("correction/logout/", grading_views.corrector_logout_view, name="corrector_logout"),
    path("correction/<str:exam_code>/", grading_views.corrector_login_view, name="corrector_login"),
    path("correction/<str:exam_code>/subjects/", grading_views.corrector_subjects_view, name="corrector_subjects"),
    path(
        "correction/<str:exam_code>/subject/<int:subject_id>/",
        grading_views.corrector_grade_entry_view,
        name="corrector_grade",
    ),

    # Exam selection
    path("select-exam/", views.select_exam_view, name="select_exam"),
    path("switch-exam/", views.switch_exam_view, name="switch_exam"),

    # Dashboard
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # Exam setup
    path("exam/setup/", views.exam_setup_view, name="exam_setup"),
    path("exam/create/", views.exam_create_view, name="exam_create"),
    path("exam/generate-code/", views.generate_exam_code_view, name="generate_exam_code"),
    path("exam/import/", views.exam_import_view, name="exam_import"),
    path("exam/<int:pk>/edit/", views.exam_edit_view, name="exam_edit"),
    path("exam/<int:pk>/lock/", views.exam_lock_view, name="exam_lock"),

    # Schools
    path("schools/", views.schools_list_view, name="schools_list"),
    path("schools/create/", views.school_create_view, name="school_create"),
    path("schools/<int:pk>/edit/", views.school_edit_view, name="school_edit"),
    path("schools/<int:pk>/delete/", views.school_delete_view, name="school_delete"),

    # Students
    path("students/", views.students_list_view, name="students_list"),
    path("students/create/", views.student_create_view, name="student_create"),
    path("students/<int:pk>/edit/", views.student_edit_view, name="student_edit"),
    path("students/<int:pk>/delete/", views.student_delete_view, name="student_delete"),
    path("students/import/", views.students_import_view, name="students_import"),

    # Subjects
    path("subjects/", views.subjects_list_view, name="subjects_list"),
    path("subjects/create/", views.subject_create_view, name="subject_create"),
    path("subjects/<int:pk>/edit/", views.subject_edit_view, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete_view, name="subject_delete"),

    # Scores
    path("scores/", views.scores_view, name="scores"),
    path("scores/student/<int:student_id>/", views.scores_by_student_view, name="scores_by_student"),
    path("scores/subject/<int:subject_id>/", views.scores_by_subject_view, name="scores_by_subject"),
    path("scores/subject/<int:subject_id>/harmonize/", grading_views.harmonization_view, name="scores_harmonize"),
    path("scores/<int:score_id>/history/", grading_views.score_history_view, name="score_history"),
    path("scores/qr-correction.png", grading_views.exam_correction_qr_png_view, name="exam_correction_qr_png"),

    # Enseignants / correcteurs
    path("teachers/", grading_views.teachers_list_view, name="teachers_list"),
    path("teachers/create/", grading_views.teacher_create_view, name="teacher_create"),
    path("teachers/<int:pk>/edit/", grading_views.teacher_edit_view, name="teacher_edit"),
    path("teachers/<int:pk>/delete/", grading_views.teacher_delete_view, name="teacher_delete"),
    path("teachers/<int:pk>/assign/", grading_views.teacher_assign_view, name="teacher_assign"),

    # Rankings
    path("rankings/", views.rankings_view, name="rankings"),

    # Statistics
    path("statistics/", views.statistics_view, name="statistics"),

    # Rooms
    path("rooms/", views.rooms_view, name="rooms"),
    path("rooms/create/", views.room_create_view, name="room_create"),
    path("rooms/<int:pk>/delete/", views.room_delete_view, name="room_delete"),
    path("rooms/dispatch/", views.rooms_dispatch_view, name="rooms_dispatch"),

    # Exports
    path("exports/", views.exports_view, name="exports"),
    path("exports/pdf/<str:doc_type>/", views.export_pdf_view, name="export_pdf"),
    path("exports/excel/<str:doc_type>/", views.export_excel_view, name="export_excel"),
    path("exports/json/<str:doc_type>/", views.export_json_view, name="export_json"),

    # Settings
    path("settings/", views.settings_view, name="settings"),
]
