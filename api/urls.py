from django.urls import path, include
from . import views
from rest_framework import routers

from api.views import (
    # UserViewSet,
    ClassroomViewSet,
    QuizViewSet,
    QuestionViewSet,
    AnswerViewSet,
    StudentQuizAttemptViewSet,
    StudentQuestionAttemptViewSet,
    StudentAnswerViewSet,
)

router = routers.DefaultRouter()
# router.register(r'users', UserViewSet)
router.register(r"classrooms", ClassroomViewSet)
router.register(r"quizzes", QuizViewSet)
router.register(r"questions", QuestionViewSet)
router.register(r"answers", AnswerViewSet)
router.register(r"attempts", StudentQuizAttemptViewSet)
router.register(r"question-attempts", StudentQuestionAttemptViewSet)
router.register(r"student-answers", StudentAnswerViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
