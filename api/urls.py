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
)

router = routers.DefaultRouter()
router.register(r"classrooms", ClassroomViewSet)
router.register(r"quizzes", QuizViewSet)
router.register(r"questions", QuestionViewSet)
router.register(r"answers", AnswerViewSet)
router.register(r"attempts", StudentQuizAttemptViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("answer-submit/", StudentAnswerSubmitViewSet.as_view(), name="answer-submit"),
]
