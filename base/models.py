from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.utils import timezone

from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"

    role = models.CharField(max_length=10, choices=Role.choices)


class Classroom(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="classrooms",
        limit_choices_to={"role": "teacher"},
    )
    students = models.ManyToManyField(
        User,
        related_name="classes",
        limit_choices_to={"role": "student"},
        blank=True,
    )

    def __str__(self):
        return self.name

    def student_count(self):
        return self.students.count()

    def clean(self):
        super().clean()
        if self.teacher.role != User.Role.TEACHER:
            raise ValidationError("Assigned teacher must have a teacher role.")


class Quiz(models.Model):
    title = models.CharField(max_length=255)
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name="quizzes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    allowed_attempts = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title

    def question_count(self):
        return self.questions.count()

    def clean(self):
        super().clean()
        if self.allowed_attempts < 1:
            raise ValidationError("allowed_attempts must be at least 1.")


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(null=True, blank=True)
    has_multiple_answers = models.BooleanField(default=False)
    is_written = models.BooleanField(default=False)
    time_limit = models.PositiveIntegerField(null=True, blank=True)  # in seconds

    def save(self, *args, **kwargs):
        if self.pk is None and self.order is None:
            max_order = Question.objects.filter(quiz=self.quiz).aggregate(
                models.Max("order")
            )["order__max"]
            self.order = (max_order or 0) + 1
        else:
            self.order = Quiz.objects.get(id=self.quiz.id).questions.count() + 1
        super().save(*args, **kwargs)

    def get_correct_answers(self):
        return self.answers.filter(is_correct=True)

    def __str__(self):
        return f"{self.quiz} - {self.order}. {self.text[:50]}"


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.text:
            self.text = self.text.strip()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "text"], name="unique_answer_per_question"
            )
        ]

    def __str__(self):
        return self.text


class StudentQuizAttempt(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
        limit_choices_to={"role": "student"},
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def get_next_question(self):
        attempted_ids = self.question_attempts.values_list("question_id", flat=True)
        return (
            self.quiz.questions.exclude(id__in=attempted_ids).order_by("order").first()
        )

    def __str__(self):
        return f"{self.student} - {self.quiz}"

    # TODO: IMPLEMET MULPITPLE GRADING SYSTEMS + DECREMENT FOR INCORRECT ANSWERS
    def calculate_score(self):
        answers = StudentAnswer.objects.filter(question_attempt__quiz_attempt=self)
        total = answers.count()
        correct = answers.filter(is_correct=True).count()

        if total:
            percentage = Decimal(correct * 100) / Decimal(total)
            self.score = percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            self.score = Decimal("0.00")

        self.completed_at = timezone.now()
        self.save()

    def clean(self):
        super().clean()
        if self.student.role != User.Role.STUDENT:
            raise ValidationError(
                "Only users with the student role can attempt quizzes."
            )


class StudentQuestionAttempt(models.Model):
    quiz_attempt = models.ForeignKey(
        StudentQuizAttempt, on_delete=models.CASCADE, related_name="question_attempts"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["quiz_attempt", "question"],
                name="unique_StudentQuestionAttempt_per_question",
            )
        ]

    def __str__(self):
        return f"{self.quiz_attempt.student} - {self.question.order}. {self.question.text[:50]}"

    def clean(self):
        super().clean()
        if self.question.quiz != self.quiz_attempt.quiz:
            raise ValidationError(
                "Question does not belong to the quiz being attempted."
            )


class StudentAnswer(models.Model):
    question_attempt = models.ForeignKey(
        StudentQuestionAttempt, on_delete=models.CASCADE, related_name="student_answers"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.text:
            self.text = self.text.strip()

        if (
            self.question_attempt.question.time_limit
            and self.question_attempt.submitted_at - self.question_attempt.started_at
            > timedelta(seconds=self.question_attempt.question.time_limit - 2)
        ):
            self.is_correct = False
        else:
            self.is_correct = (
                self.question_attempt.question.get_correct_answers()
                .filter(text__iexact=self.text)
                .exists()
            )

        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question_attempt", "text"],
                name="unique_StudentAnswer_per_StudentQuestionAttempt",
            )
        ]

    def clean(self):
        if self.question_attempt.question is None:
            raise ValidationError("Question not found in the attempt.")
        if self.question_attempt.submitted_at is None:
            raise ValidationError(
                "Cannot add an answer before the question attempt is submitted."
            )
        super().clean()

    def __str__(self):
        return f"{self.question_attempt.quiz_attempt.student} - {self.question_attempt.question.text[:50]}: {self.text} ({'Correct' if self.is_correct else 'Incorrect'})"
