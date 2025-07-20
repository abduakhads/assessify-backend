from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    User,
    Classroom,
    Quiz,
    Question,
    Answer,
    StudentQuizAttempt,
    StudentQuestionAttempt,
    StudentAnswer,
    EnrollmentCode,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    list_display = ("id", "username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    list_display_links = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "role")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    search_fields = ("username", "email")
    ordering = ("username",)


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "teacher", "student_count")
    list_display_links = ("name",)
    list_filter = ("teacher",)
    search_fields = ("name", "teacher__username")
    filter_horizontal = ("students",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "classroom",
        "is_active",
        "allowed_attempts",
    )
    list_display_links = ("title",)
    list_filter = ("classroom", "is_active")
    search_fields = ("title", "classroom__name")
    readonly_fields = ("created_at",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "text",
        "quiz",
        "has_multiple_answers",
        "is_written",
        "time_limit",
    )
    list_display_links = ("text",)
    list_filter = ("quiz", "has_multiple_answers", "is_written")
    search_fields = ("text",)
    # readonly_fields = ("order",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "question", "is_correct")
    list_display_links = ("text",)
    list_filter = ("question__quiz", "is_correct")
    search_fields = ("text",)


@admin.register(StudentQuizAttempt)
class StudentQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "quiz", "score")
    list_display_links = ("student", "quiz")
    list_filter = ("quiz", "student")
    search_fields = ("student__username", "quiz__title")
    readonly_fields = ("started_at", "completed_at", "score")


@admin.register(StudentQuestionAttempt)
class StudentQuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "quiz_attempt", "time_taken_in_seconds")
    list_display_links = ("question",)
    list_filter = ("quiz_attempt__quiz", "question")
    search_fields = ("quiz_attempt__student__username", "question__text")
    readonly_fields = ("started_at",)  # add completed_at

    def time_taken_in_seconds(self, obj):
        if obj.started_at and obj.submitted_at:
            time_diff = obj.submitted_at - obj.started_at
            return round(time_diff.total_seconds())
        return 0

    time_taken_in_seconds.short_description = "Time Taken (Seconds)"


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "question_attempt", "is_correct")
    list_display_links = ("text",)
    list_filter = ("is_correct",)
    search_fields = ("text", "question_attempt__question__text")
    readonly_fields = ("is_correct",)


@admin.register(EnrollmentCode)
class EnrollmentCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "classroom", "is_active")
    list_display_links = ("code",)
    list_filter = ("classroom", "is_active")
    search_fields = ("code", "classroom__name")
    readonly_fields = ("code",)
