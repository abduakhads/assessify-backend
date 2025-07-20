from rest_framework import permissions, viewsets, status, generics, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django import shortcuts

from base.permissions import IsTeacher, IsStudent
from base import serializers as base_srlzs
from base.models import (
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


@extend_schema(tags=["Classroom"])
class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = base_srlzs.ClassroomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "delete_students":
            return base_srlzs.ClassroomDeleteStudentsSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action not in ["list", "retrieve"]:
            return [IsTeacher()]
        return super().get_permissions()

    def perform_create(self, serializer):
        classroom = serializer.save(teacher=self.request.user)
        EnrollmentCode.generate_for_class(classroom)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == User.Role.TEACHER:
            return qs.filter(teacher=self.request.user)
        elif self.request.user.role == User.Role.STUDENT:
            return qs.filter(students=self.request.user)
        else:
            return qs.none()

    @action(detail=True, methods=["post"], url_path="delete-students")
    def delete_students(self, request, pk=None):
        classroom = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student_ids = serializer.validated_data["student_ids"]
        students = User.objects.filter(id__in=student_ids, role=User.Role.STUDENT)

        if not students.exists():
            return Response(
                {"detail": "No valid students found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        classroom.students.remove(*students)
        return Response(
            {"detail": "Students removed successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


@extend_schema(tags=["Quiz"])
class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = base_srlzs.QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["classroom"]

    def filter_queryset(self, queryset):
        try:
            return super().filter_queryset(queryset)
        except ValidationError as e:
            return queryset.none()

    def get_permissions(self):
        if self.action not in ["list", "retrieve", "quizzes_by_classroom"]:
            return [IsTeacher()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == User.Role.TEACHER:
            classrooms = Classroom.objects.filter(teacher=self.request.user)
        elif self.request.user.role == User.Role.STUDENT:
            classrooms = Classroom.objects.filter(students=self.request.user)
        return qs.filter(classroom__in=classrooms)

    def create(self, request, *args, **kwargs):
        classroom_id = request.data.get("classroom")
        try:
            classroom = Classroom.objects.get(id=classroom_id)
        except Classroom.DoesNotExist:
            return Response(
                {"detail": "Classroom does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if classroom.teacher != request.user:
            return Response(
                {"detail": "You can only create quizzes for your own classrooms."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


@extend_schema(tags=["Question"])
class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = base_srlzs.QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["quiz"]

    def filter_queryset(self, queryset):
        try:
            return super().filter_queryset(queryset)
        except ValidationError as e:
            return queryset.none()

    def get_permissions(self):
        if self.action not in ["retrieve"]:
            return [IsTeacher()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == User.Role.TEACHER:
            classrooms = Classroom.objects.filter(teacher=self.request.user)
        elif self.request.user.role == User.Role.STUDENT:
            classrooms = Classroom.objects.filter(students=self.request.user)
        quizzes = Quiz.objects.filter(classroom__in=classrooms)
        return qs.filter(quiz__in=quizzes)

    def create(self, request, *args, **kwargs):
        quiz_id = request.data.get("quiz")
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quiz.classroom.teacher != request.user:
            return Response(
                {"detail": "You can only create questions for your own quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


@extend_schema(tags=["Answer"])
class AnswerViewSet(viewsets.ModelViewSet):
    queryset = Answer.objects.all()
    serializer_class = base_srlzs.AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["question"]

    def filter_queryset(self, queryset):
        try:
            return super().filter_queryset(queryset)
        except ValidationError as e:
            return queryset.none()

    def get_permissions(self):
        if self.action not in ["retrieve"]:
            return [IsTeacher()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == User.Role.TEACHER:
            classrooms = Classroom.objects.filter(teacher=self.request.user)
        elif self.request.user.role == User.Role.STUDENT:
            classrooms = Classroom.objects.filter(students=self.request.user)
        quizzes = Quiz.objects.filter(classroom__in=classrooms)
        return qs.filter(question__quiz__in=quizzes)

    def create(self, request, *args, **kwargs):
        question_id = request.data.get("question")
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response(
                {"detail": "Question does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if question.quiz.classroom.teacher != request.user:
            return Response(
                {"detail": "You can only create answers for your own questions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


@extend_schema(tags=["Student Quiz Attempt"])
class StudentQuizAttemptViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = StudentQuizAttempt.objects.all()
    serializer_class = base_srlzs.StudentQuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    filterset_fields = ["quiz"]

    def filter_queryset(self, queryset):
        try:
            return super().filter_queryset(queryset)
        except ValidationError as e:
            return queryset.none()

    def get_queryset(self):
        return super().get_queryset().filter(student=self.request.user)

    def create(self, request, *args, **kwargs):
        quiz_id = request.data.get("quiz")
        try:
            quiz = Quiz.objects.get(id=quiz_id, is_active=True)
        except Quiz.DoesNotExist:
            return Response(
                {"detail": "Quiz does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attempts = StudentQuizAttempt.objects.filter(student=request.user, quiz=quiz)

        if attempts.filter(completed_at__isnull=True).exists():
            return Response(
                {"detail": "You already have an active attempt for this quiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quiz.classroom.students.filter(id=request.user.id).exists():
            attempts_count = attempts.count()
            if attempts_count >= quiz.allowed_attempts:
                return Response(
                    {"detail": "You have reached the maximum allowed attempts."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return super().create(request, *args, **kwargs)
        else:
            return Response(
                {"detail": "You are not enrolled in this quiz's classroom."},
                status=status.HTTP_403_FORBIDDEN,
            )

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def get_serializer_class(self):
        if self.action == "next_question":
            return base_srlzs.SQANextQuestionSerializer
        return base_srlzs.StudentQuizAttemptSerializer

    @extend_schema(
        tags=["Student Question Attempt"],
        responses={200: base_srlzs.SQANextQuestionSerializer},
    )
    @action(detail=True, methods=["get"], url_path="next-question")
    def next_question(self, request, pk=None):
        attempt = self.get_object()
        serializer = self.get_serializer(attempt)
        has_next = serializer.data.get("next_question") is not None
        if not has_next and attempt.completed_at is None:
            attempt.completed_at = timezone.now()
            attempt.calculate_score()
            attempt.save()
        return Response(serializer.data)


@extend_schema(tags=["Student Answer Submit"])
class StudentAnswerSubmitViewSet(generics.CreateAPIView):
    queryset = StudentAnswer.objects.all()
    serializer_class = base_srlzs.StudentAnswersSubmitSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def create(self, request, *args, **kwargs):
        question_attempt_id = request.data.get("question_attempt")
        try:
            question_attempt = StudentQuestionAttempt.objects.get(
                id=question_attempt_id
            )
        except StudentQuestionAttempt.DoesNotExist:
            return Response(
                {"detail": "Question attempt does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if question_attempt.quiz_attempt.student != self.request.user:
            return Response(
                {"detail": "You can only submit answers for your own attempts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if question_attempt.submitted_at is not None:
            return Response(
                {"detail": "This question attempt has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (not question_attempt.question.has_multiple_answers) and len(
            request.data.get("answers")
        ) > 1:
            return Response(
                {"detail": "This question allows only one answer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question_attempt.submitted_at = timezone.now()
        question_attempt.save()

        student_answers = [
            StudentAnswer(question_attempt=question_attempt, text=answer)
            for answer in request.data.get("answers")
        ]
        StudentAnswer.objects.bulk_create(student_answers)

        return Response(
            {"detail": "Answers submitted successfully."},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Enrollment"])
class EnrollmentCodeViewSet(
    mixins.UpdateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = EnrollmentCode.objects.all()
    serializer_class = base_srlzs.EnrollmentCodeSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    lookup_field = "classroom__id"

    def get_queryset(self):
        return super().get_queryset().filter(classroom__teacher=self.request.user)

    def get_object(self):
        classroom_id = self.kwargs.get(self.lookup_field)
        return shortcuts.get_object_or_404(
            self.get_queryset(), classroom__id=classroom_id
        )

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return base_srlzs.EnrollmentCodePutSerializer
        return base_srlzs.EnrollmentCodeSerializer


@extend_schema(tags=["Enrollment"])
class EnrollView(generics.CreateAPIView):
    queryset = EnrollmentCode.objects.all()
    serializer_class = base_srlzs.EnrollSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def create(self, request, *args, **kwargs):
        code = request.data.get("code")
        try:
            enrollment_code = EnrollmentCode.objects.get(code=code, is_active=True)
        except EnrollmentCode.DoesNotExist:
            return Response(
                {"detail": "Invalid or inactive enrollment code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if enrollment_code.classroom.students.filter(id=request.user.id).exists():
            return Response(
                {"detail": "You are already enrolled in this classroom."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollment_code.classroom.students.add(request.user)
        return Response(
            {"detail": "Successfully enrolled in the classroom."},
            status=status.HTTP_201_CREATED,
        )
