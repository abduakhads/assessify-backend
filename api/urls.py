from django.urls import path, include
from . import views
from rest_framework import routers

from api import views as api_views

router = routers.DefaultRouter()
router.register(r"enrollment", api_views.EnrollmentCodeViewSet)
router.register(r"classrooms", api_views.ClassroomViewSet)
router.register(r"quizzes", api_views.QuizViewSet)
router.register(r"questions", api_views.QuestionViewSet)
router.register(r"answers", api_views.AnswerViewSet)
router.register(r"attempts", api_views.StudentQuizAttemptViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("enroll/", api_views.EnrollView.as_view(), name="enroll"),
    path(
        "answer-submit/",
        api_views.StudentAnswerSubmitViewSet.as_view(),
        name="answer-submit",
    ),
    path(
        "quiz/<int:id>/stats/",
        api_views.TeacherStudentQuizAttemptsStatsViewSet.as_view({"get": "list"}),
        name="quiz-stats-list",
    ),
    path(
        "quiz/<int:id>/stats/<int:quiz_attempt_id>/",
        api_views.TeacherStudentQuizAttemptsStatsViewSet.as_view(
            {"get": "stats_by_quiz_attempt", "patch": "set_score"}
        ),
        name="quiz-stats-detail",
    ),
]
