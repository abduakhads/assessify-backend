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
    EnrollmentCode,
)


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=User.Role.choices)

    class Meta(UserCreateSerializer.Meta):
        fields = ["id", "username", "email", "password", "role"]


class BaseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role"]
        extra_kwargs = {
            "role": {"read_only": True},
            "username": {"read_only": True},
        }


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


class ClassroomDeleteStudentsSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True, allow_empty=False
    )

    class Meta:
        fields = ["student_ids"]


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

    def validate_text(self, value):
        if value:
            value = value.strip()

        # Get the question from the request data
        request = self.context.get("request")
        if request and hasattr(request, "data"):
            question_id = request.data.get("question")
            if question_id:
                try:
                    question = Question.objects.get(pk=question_id)

                    qs = Answer.objects.filter(question=question, text=value)
                    if self.instance:
                        qs = qs.exclude(pk=self.instance.pk)

                    if qs.exists():
                        raise serializers.ValidationError(
                            "An answer with this text already exists for the selected question."
                        )
                except Question.DoesNotExist:
                    pass

        return value

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

    #     return student_answers


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


class EnrollmentCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnrollmentCode
        fields = ["code", "classroom", "is_active"]
        extra_kwargs = {
            "code": {"read_only": True},
            "classroom": {"read_only": True},
        }


class EnrollmentCodePutSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnrollmentCode
        fields = ["code", "classroom", "is_active"]
        extra_kwargs = {
            "code": {"read_only": True},
            "classroom": {"read_only": True},
            "is_active": {"read_only": True},
        }

    def save(self, **kwargs):
        self.instance = EnrollmentCode.generate_for_class(self.instance.classroom)
        self.instance.is_active = True
        return super().save(**kwargs)


class EnrollSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)


class TeacherStudentQuizAttemptStatsSerializer(serializers.ModelSerializer):
    student = BaseUserSerializer(read_only=True)

    class Meta:
        model = StudentQuizAttempt
        fields = ["id", "student", "started_at", "completed_at", "score"]
        read_only_fields = ["id", "student", "started_at", "completed_at"]


class TeacherStudentQuestionAttemptStatsSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    student_answers = StudentAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = StudentQuestionAttempt
        fields = [
            "id",
            "question",
            "started_at",
            "submitted_at",
            "student_answers",
        ]
        read_only_fields = ["id", "started_at", "submitted_at"]
