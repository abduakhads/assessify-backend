from django.urls import path, include
from . import views
from rest_framework import routers

from api.views import (
    ClassroomViewSet,
    QuizViewSet,
    QuestionViewSet,
    AnswerViewSet,
    StudentQuizAttemptViewSet,
    StudentAnswerSubmitViewSet,
    EnrollmentCodeViewSet,
    EnrollView,
)

router = routers.DefaultRouter()
router.register(r"enrollment", EnrollmentCodeViewSet)
router.register(r"classrooms", ClassroomViewSet)
router.register(r"quizzes", QuizViewSet)
router.register(r"questions", QuestionViewSet)
router.register(r"answers", AnswerViewSet)
router.register(r"attempts", StudentQuizAttemptViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("answer-submit/", StudentAnswerSubmitViewSet.as_view(), name="answer-submit"),
    path("enroll/", EnrollView.as_view(), name="enroll"),
]
