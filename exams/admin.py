from django.contrib import admin
from .models import Exam, School, Student, Subject, Score, Room, RoomAssignment


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "year", "passing_grade", "is_locked", "created_at")
    list_filter = ("is_locked", "year")
    search_fields = ("name", "code")


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("candidate_number", "last_name", "first_name", "gender", "exam", "school", "is_absent")
    list_filter = ("exam", "school", "gender", "is_absent")
    search_fields = ("last_name", "first_name", "candidate_number")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "coefficient", "max_score", "exam")
    list_filter = ("exam",)


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "value", "updated_at")
    list_filter = ("subject",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "exam")
    list_filter = ("exam",)


@admin.register(RoomAssignment)
class RoomAssignmentAdmin(admin.ModelAdmin):
    list_display = ("student", "room", "seat_number")
    list_filter = ("room",)
