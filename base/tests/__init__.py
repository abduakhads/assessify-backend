# Import all test classes to make them discoverable by Django's test runner
from .test_models import (
    UserModelTest,
    ClassroomModelTest,
    QuizModelTest,
    QuestionModelTest,
    AnswerModelTest,
    StudentQuizAttemptModelTest,
    StudentQuestionAttemptModelTest,
    StudentAnswerModelTest,
    EnrollmentCodeModelTest,
)

from .test_serializers import (
    CustomUserCreateSerializerTest,
    BaseUserSerializerTest,
    ClassroomSerializerTest,
    ClassroomDeleteStudentsSerializerTest,
    AnswerSerializerTest,
    QuestionSerializerTest,
    QuizSerializerTest,
    StudentAnswerSerializerTest,
    StudentAnswersSubmitSerializerTest,
    StudentQuestionAttemptSerializerTest,
    StudentQuizAttemptSerializerTest,
    SQANextQuestionSerializerTest,
    EnrollmentCodeSerializerTest,
    EnrollmentCodePutSerializerTest,
    EnrollSerializerTest,
    TeacherStatsSerializersTest,
    ActivateUserViewTest,
    PermissionTests,
)
