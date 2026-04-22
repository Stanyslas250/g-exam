from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Exam,
    School,
    Student,
    Subject,
    Score,
    Room,
    RoomAssignment,
    Teacher,
    SubjectAssignment,
    ScoreHistory,
    Harmonization,
    Plan,
    UserProfile,
)


class SubjectAssignmentInline(admin.TabularInline):
    model = SubjectAssignment
    extra = 0
    fields = ("subject", "is_lead_corrector")
    autocomplete_fields = ("subject",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "year",
        "exam_type",
        "grading_scale",
        "passing_grade",
        "is_locked",
        "created_at",
    )
    list_filter = ("is_locked", "year", "exam_type")
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
    search_fields = ("name",)


class ScoreHistoryInline(admin.TabularInline):
    model = ScoreHistory
    extra = 0
    readonly_fields = (
        "old_value",
        "new_value",
        "reason",
        "comment",
        "changed_by_teacher",
        "changed_by_admin",
        "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "value", "updated_at")
    list_filter = ("subject",)
    inlines = [ScoreHistoryInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "exam")
    list_filter = ("exam",)


@admin.register(RoomAssignment)
class RoomAssignmentAdmin(admin.ModelAdmin):
    list_display = ("student", "room", "seat_number")
    list_filter = ("room",)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "code", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("last_name", "first_name", "code", "email")
    inlines = [SubjectAssignmentInline]


@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "subject", "exam", "is_lead_corrector")
    list_filter = ("exam", "is_lead_corrector")
    search_fields = ("teacher__last_name", "teacher__code", "subject__name")
    autocomplete_fields = ("teacher", "subject", "exam")


@admin.register(ScoreHistory)
class ScoreHistoryAdmin(admin.ModelAdmin):
    list_display = ("score", "old_value", "new_value", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("comment", "score__student__candidate_number")
    readonly_fields = (
        "score",
        "old_value",
        "new_value",
        "reason",
        "comment",
        "changed_by_teacher",
        "changed_by_admin",
        "created_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(Harmonization)
class HarmonizationAdmin(admin.ModelAdmin):
    list_display = ("subject", "exam", "adjustment_type", "value", "is_applied", "applied_at", "applied_by")
    list_filter = ("is_applied", "adjustment_type", "exam")
    readonly_fields = ("applied_at",)


# ── Plans & Profils ──────────────────────────────

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price_fcfa", "billing_period", "max_exams", "is_featured", "is_active", "sort_order")
    list_editable = ("is_featured", "is_active", "sort_order")
    list_filter = ("is_active", "billing_period")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profil & Forfait"
    fk_name = "user"
    fields = ("plan", "organization", "phone", "subscription_start", "subscription_end", "is_subscription_active", "notes")


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "organization", "subscription_start", "subscription_end", "is_subscription_active")
    list_filter = ("plan", "is_subscription_active")
    search_fields = ("user__username", "user__email", "organization")
    autocomplete_fields = ("user", "plan")
