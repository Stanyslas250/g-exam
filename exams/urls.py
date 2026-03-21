from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "exams"

urlpatterns = [
    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Exam selection
    path("select-exam/", views.select_exam_view, name="select_exam"),
    path("switch-exam/", views.switch_exam_view, name="switch_exam"),

    # Dashboard
    path("", views.dashboard_view, name="dashboard"),

    # Exam setup
    path("exam/setup/", views.exam_setup_view, name="exam_setup"),
    path("exam/create/", views.exam_create_view, name="exam_create"),
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
    path("scores/subject/<int:subject_id>/", views.scores_by_subject_view, name="scores_by_subject"),

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

    # Settings
    path("settings/", views.settings_view, name="settings"),
]
