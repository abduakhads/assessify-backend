from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import (
    User,
    Classroom,
    Quiz,
    Question,
    Answer,
    StudentQuizAttempt,
    StudentQuestionAttempt,
    StudentAnswer,
)


class UserModelTest(TestCase):
    def test_create_teacher_and_student(self):
        teacher = User.objects.create_user(
            username="teacher1", password="pass", role=User.Role.TEACHER
        )
        student = User.objects.create_user(
            username="student1", password="pass", role=User.Role.STUDENT
        )
        self.assertEqual(teacher.role, User.Role.TEACHER)
        self.assertEqual(student.role, User.Role.STUDENT)


class ClassroomModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role=User.Role.TEACHER
        )
        self.student = User.objects.create_user(
            username="student", password="pass", role=User.Role.STUDENT
        )

    def test_create_classroom(self):
        classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        classroom.students.add(self.student)
        self.assertEqual(classroom.teacher, self.teacher)
        self.assertIn(self.student, classroom.students.all())
        self.assertEqual(classroom.student_count(), 1)

    def test_invalid_teacher_role(self):
        student = User.objects.create_user(
            username="student2", password="pass", role=User.Role.STUDENT
        )
        classroom = Classroom(name="Science", teacher=student)
        with self.assertRaises(ValidationError):
            classroom.clean()


class QuizModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role=User.Role.TEACHER
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)

    def test_create_quiz(self):
        quiz = Quiz.objects.create(
            title="Quiz 1", classroom=self.classroom, teacher=self.teacher
        )
        self.assertEqual(str(quiz), "Quiz 1")
        self.assertEqual(quiz.question_count(), 0)

    def test_allowed_attempts_validation(self):
        quiz = Quiz(
            title="Quiz 2",
            classroom=self.classroom,
            teacher=self.teacher,
            allowed_attempts=0,
        )
        with self.assertRaises(ValidationError):
            quiz.clean()


class QuestionModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role=User.Role.TEACHER
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(
            title="Quiz 1", classroom=self.classroom, teacher=self.teacher
        )

    def test_create_question_and_order(self):
        q1 = Question.objects.create(quiz=self.quiz, text="Q1")
        q2 = Question.objects.create(quiz=self.quiz, text="Q2")
        self.assertEqual(q1.order, 1)
        self.assertEqual(q2.order, 2)

    def test_get_correct_answers(self):
        question = Question.objects.create(quiz=self.quiz, text="Q1")
        a1 = Answer.objects.create(question=question, text="A1", is_correct=True)
        a2 = Answer.objects.create(question=question, text="A2", is_correct=False)
        correct = question.get_correct_answers()
        self.assertIn(a1, correct)
        self.assertNotIn(a2, correct)


class AnswerModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role=User.Role.TEACHER
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(
            title="Quiz 1", classroom=self.classroom, teacher=self.teacher
        )
        self.question = Question.objects.create(quiz=self.quiz, text="Q1")

    def test_unique_answer_per_question(self):
        Answer.objects.create(question=self.question, text="A1")
        with self.assertRaises(Exception):
            Answer.objects.create(question=self.question, text="A1")


class StudentQuizAttemptModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role=User.Role.TEACHER
        )
        self.student = User.objects.create_user(
            username="student", password="pass", role=User.Role.STUDENT
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(
            title="Quiz 1", classroom=self.classroom, teacher=self.teacher
        )
        self.question = Question.objects.create(quiz=self.quiz, text="Q1")
        self.quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

    def test_get_next_question(self):
        next_q = self.quiz_attempt.get_next_question()
        self.assertEqual(next_q, self.question)

    def test_calculate_score(self):
        # Add a correct answer for the question
        Answer.objects.create(question=self.question, text="A1", is_correct=True)
        question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )
        question_attempt.submitted_at = timezone.now()
        question_attempt.save()
        StudentAnswer.objects.create(
            question_attempt=question_attempt, text="A1", is_correct=True
        )
        self.quiz_attempt.calculate_score()
        self.assertEqual(self.quiz_attempt.score, Decimal("100.00"))

    def test_invalid_student_role(self):
        quiz_attempt = StudentQuizAttempt(student=self.teacher, quiz=self.quiz)
        with self.assertRaises(ValidationError):
            quiz_attempt.clean()


class StudentQuestionAttemptModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role=User.Role.TEACHER
        )
        self.student = User.objects.create_user(
            username="student", password="pass", role=User.Role.STUDENT
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(
            title="Quiz 1", classroom=self.classroom, teacher=self.teacher
        )
        self.question = Question.objects.create(quiz=self.quiz, text="Q1")
        self.quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

    def test_unique_question_attempt(self):
        StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )
        with self.assertRaises(Exception):
            StudentQuestionAttempt.objects.create(
                quiz_attempt=self.quiz_attempt, question=self.question
            )

    def test_invalid_question_quiz(self):
        other_quiz = Quiz.objects.create(
            title="Quiz 2", classroom=self.classroom, teacher=self.teacher
        )
        other_question = Question.objects.create(quiz=other_quiz, text="Q2")
        attempt = StudentQuestionAttempt(
            quiz_attempt=self.quiz_attempt, question=other_question
        )
        with self.assertRaises(ValidationError):
            attempt.clean()


class StudentAnswerModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role=User.Role.TEACHER
        )
        self.student = User.objects.create_user(
            username="student", password="pass", role=User.Role.STUDENT
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(
            title="Quiz 1", classroom=self.classroom, teacher=self.teacher
        )
        self.question = Question.objects.create(
            quiz=self.quiz, text="Q1", time_limit=60
        )
        self.quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )
        self.question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()
        Answer.objects.create(question=self.question, text="A1", is_correct=True)

    def test_unique_student_answer(self):
        StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="A1", is_correct=True
        )
        with self.assertRaises(Exception):
            StudentAnswer.objects.create(
                question_attempt=self.question_attempt, text="A1", is_correct=True
            )

    def test_clean_methods(self):
        answer = StudentAnswer(
            question_attempt=self.question_attempt, text="A1", is_correct=True
        )
        answer.question_attempt.submitted_at = None
        with self.assertRaises(ValidationError):
            answer.clean()

    def test_is_correct_logic(self):
        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="A1"
        )
        self.assertTrue(answer.is_correct)
        answer2 = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="wrong"
        )
        self.assertFalse(answer2.is_correct)
