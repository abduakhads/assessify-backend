from rest_framework import serializers
from djoser.serializers import UserCreateSerializer
from drf_spectacular.utils import extend_schema_field

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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context.get("request").user
        if user.role == User.Role.STUDENT:
            representation["students"] = [
                student
                for student in representation["students"]
                if student["id"] == user.id
            ]
        return representation


class AnswerSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        question = attrs.get("question", getattr(self.instance, "question", None))
        text = attrs.get("text", getattr(self.instance, "text", None))
        qs = Answer.objects.filter(question=question, text=text)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {
                    "text": "An answer with this text already exists for the selected question."
                }
            )
        return attrs

    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

    class Meta:
        model = Answer
        fields = ["id", "question", "text", "is_correct"]

    def update(self, instance, validated_data):
        validated_data.pop("question", None)
        return super().update(instance, validated_data)

    def get_fields(self):
        fields = super().get_fields()
        action = self.context.get("view").action if self.context.get("view") else None
        if action in ["update", "partial_update"]:
            fields["question"].read_only = True
        return fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context.get("request").user
        if user.role == User.Role.STUDENT:
            representation = {"text": representation["text"]}
        return representation


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
        extra_kwargs = {
            "order": {"read_only": True},
        }

    def update(self, instance, validated_data):
        validated_data.pop("quiz", None)
        return super().update(instance, validated_data)

    def get_fields(self):
        fields = super().get_fields()
        action = self.context.get("view").action if self.context.get("view") else None
        if action in ["update", "partial_update"]:
            fields["quiz"].read_only = True
        return fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context.get("request").user
        if user.role == User.Role.STUDENT:
            if representation["is_written"] == True:
                representation["answers"] = None
            else:
                representation["answers"] = [
                    answer["text"] for answer in representation["answers"]
                ]
        return representation


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

    def update(self, instance, validated_data):
        validated_data.pop("classroom", None)
        return super().update(instance, validated_data)

    def get_fields(self):
        fields = super().get_fields()
        action = self.context.get("view").action if self.context.get("view") else None
        if action in ["update", "partial_update"]:
            fields["classroom"].read_only = True
        return fields


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ["id", "question_attempt", "text", "is_correct"]
        read_only_fields = ["is_correct"]


class StudentAnswersSubmitSerializer(serializers.Serializer):
    question_attempt = serializers.IntegerField(required=True)
    answers = serializers.ListField(child=serializers.CharField(), allow_empty=False)

    def create(self, validated_data):
        pass

    # def create(self, validated_data):
    #     question_attempt_id = validated_data.pop("question_attempt")
    #     answers_data = validated_data.pop("answers")

    #     student_answers = []

    #     for answer_data in answers_data:
    #         answer = StudentAnswer.objects.create(
    #             question_attempt=question_attempt_id,
    #             text=answer_data
    #         )
    #         student_answers.append(answer)

    # return student_answers


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

    class Meta:
        model = StudentQuizAttempt
        fields = [
            "id",
            "student",
            "quiz",
            "started_at",
            "completed_at",
            "score",
        ]
        extra_kwargs = {
            "student": {"read_only": True},
            "score": {"read_only": True},
            "completed_at": {"read_only": True},
        }


class SQANextQuestionSerializer(serializers.ModelSerializer):
    next_question = serializers.SerializerMethodField()
    question_attempt = serializers.SerializerMethodField()

    class Meta:
        model = StudentQuizAttempt
        fields = [
            "id",
            "question_attempt",
            "next_question",
        ]

    def get_question_and_attempt(self, obj):

        if hasattr(self, "_cached_next_question_data"):
            return self._cached_next_question_data

        question = obj.get_next_question()
        if question:
            attempt, _ = StudentQuestionAttempt.objects.get_or_create(
                quiz_attempt=obj, question=question
            )
            self._cached_next_question_data = (question, attempt)
            return question, attempt
        return None, None

    @extend_schema_field(QuestionSerializer)
    def get_next_question(self, obj):
        question, _ = self.get_question_and_attempt(obj)
        if question:
            return QuestionSerializer(question, context=self.context).data
        return None

    @extend_schema_field(serializers.IntegerField)
    def get_question_attempt(self, obj):
        _, attempt = self.get_question_and_attempt(obj)
        return attempt.id if attempt else None

    # @extend_schema_field(QuestionSerializer)
    # def get_next_question(self, obj):
    #     question = obj.get_next_question()
    #     if question:
    #         StudentQuestionAttempt.objects.get_or_create(quiz_attempt=obj, question=question)
    #         return QuestionSerializer(question, context=self.context).data
    #     return None
