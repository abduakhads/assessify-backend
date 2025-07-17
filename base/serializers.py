from rest_framework import serializers
from djoser.serializers import UserCreateSerializer

from base.models import (
    User,
    Classroom,
    Quiz,
    Question,
    Answer,
    StudentQuizAttempt,
    StudentQuestionAttempt,
    StudentAnswer,
)

# class BaseUserSerializer(serializers.HyperlinkedModelSerializer):
#     role = serializers.ChoiceField(choices=User.Role.choices)

#     class Meta:
#         model = User
#         fields = ["url", "username", "password", "role"]
#         extra_kwargs = {"password": {"write_only": True}}

#     def create(self, validated_data):
#         password = validated_data.pop("password")
#         user = User.objects.create(**validated_data)

#         user.set_password(password)
#         user.save()

#         return user


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=User.Role.choices)

    class Meta(UserCreateSerializer.Meta):
        fields = ["id", "username", "email", "password", "role"]


class BaseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]


class ClassroomSerializer(serializers.ModelSerializer):
    teacher = BaseUserSerializer(read_only=True)
    students = BaseUserSerializer(many=True, read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Classroom
        fields = ["id", "name", "teacher", "students", "student_count"]


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())

    class Meta:
        model = Question
        fields = [
            "id",
            "quiz",
            "text",
            "order",
            "has_multiple_answers",
            "is_written",
            "time_limit",
            "answers",
        ]


class QuizSerializer(serializers.ModelSerializer):
    classroom = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all())
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "classroom",
            "created_at",
            "deadline",
            "is_active",
            "allowed_attempts",
            "question_count",
        ]


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ["id", "question_attempt", "text", "is_correct"]
        read_only_fields = ["is_correct"]


class StudentQuestionAttemptSerializer(serializers.ModelSerializer):
    student_answers = StudentAnswerSerializer(many=True, read_only=True)
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = StudentQuestionAttempt
        fields = [
            "id",
            "quiz_attempt",
            "question",
            "started_at",
            "submitted_at",
            "student_answers",
        ]


class StudentQuizAttemptSerializer(serializers.ModelSerializer):
    question_attempts = StudentQuestionAttemptSerializer(many=True, read_only=True)
    student = BaseUserSerializer(read_only=True)
    quiz = QuizSerializer(read_only=True)

    class Meta:
        model = StudentQuizAttempt
        fields = [
            "id",
            "student",
            "quiz",
            "started_at",
            "completed_at",
            "score",
            "question_attempts",
        ]


class AnswerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "question", "text", "is_correct"]


class QuestionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "quiz",
            "text",
            "order",
            "has_multiple_answers",
            "is_written",
            "time_limit",
        ]
