from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, Mock
from django.urls import reverse
import requests
from ..models import (
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
from ..serializers import (
    CustomUserCreateSerializer,
    BaseUserSerializer,
    ClassroomSerializer,
    ClassroomDeleteStudentsSerializer,
    AnswerSerializer,
    QuestionSerializer,
    QuizSerializer,
    StudentAnswerSerializer,
    StudentAnswersSubmitSerializer,
    StudentQuestionAttemptSerializer,
    StudentQuizAttemptSerializer,
    SQANextQuestionSerializer,
    EnrollmentCodeSerializer,
    EnrollmentCodePutSerializer,
    EnrollSerializer,
    TeacherStudentQuizAttemptStatsSerializer,
    TeacherStudentQuestionAttemptStatsSerializer,
)
from ..permissions import IsTeacher, IsStudent


class CustomUserCreateSerializerTest(TestCase):
    def test_valid_serializer(self):
        """Test valid user creation serializer"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "role": User.Role.TEACHER,
        }
        serializer = CustomUserCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_missing_email(self):
        """Test serializer validation when email is missing"""
        data = {
            "username": "testuser",
            "password": "testpass123",
            "role": User.Role.TEACHER,
        }
        serializer = CustomUserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_invalid_role(self):
        """Test serializer validation with invalid role"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "role": "invalid_role",
        }
        serializer = CustomUserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("role", serializer.errors)

    def test_duplicate_email(self):
        """Test serializer validation with duplicate email"""
        # Create a user first
        User.objects.create_user(
            username="existinguser",
            email="test@example.com",
            password="pass123",
            role=User.Role.TEACHER,
        )

        # Try to create another user with the same email
        data = {
            "username": "newuser",
            "email": "test@example.com",
            "password": "testpass123",
            "role": User.Role.STUDENT,
        }
        serializer = CustomUserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class BaseUserSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role=User.Role.TEACHER,
        )

    def test_serializer_fields(self):
        """Test serializer includes correct fields"""
        serializer = BaseUserSerializer(self.user)
        data = serializer.data

        self.assertIn("id", data)
        self.assertIn("username", data)
        self.assertIn("first_name", data)
        self.assertIn("last_name", data)
        self.assertNotIn("password", data)
        self.assertNotIn("email", data)

    def test_readonly_fields(self):
        """Test that certain fields are read-only"""
        serializer = BaseUserSerializer()
        readonly_fields = serializer.Meta.extra_kwargs

        self.assertTrue(readonly_fields["role"]["read_only"])
        self.assertTrue(readonly_fields["username"]["read_only"])


class ClassroomSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student1 = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.classroom.students.add(self.student1, self.student2)

    def test_serializer_fields(self):
        """Test classroom serializer includes correct fields"""
        request_mock = Mock()
        request_mock.user = self.teacher

        serializer = ClassroomSerializer(
            self.classroom, context={"request": request_mock}
        )
        data = serializer.data

        self.assertEqual(data["name"], "Math")
        self.assertEqual(data["teacher"]["username"], "teacher")
        self.assertEqual(len(data["students"]), 2)
        self.assertEqual(data["student_count"], 2)

    def test_student_view_filters_students(self):
        """Test that students only see themselves in the students list"""
        request_mock = Mock()
        request_mock.user = self.student1

        serializer = ClassroomSerializer(
            self.classroom, context={"request": request_mock}
        )
        data = serializer.data

        self.assertEqual(len(data["students"]), 1)
        self.assertEqual(data["students"][0]["id"], self.student1.id)


class ClassroomDeleteStudentsSerializerTest(TestCase):
    def test_valid_data(self):
        """Test valid student deletion data"""
        data = {"student_ids": [1, 2, 3]}
        serializer = ClassroomDeleteStudentsSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_empty_list(self):
        """Test empty student_ids list is invalid"""
        data = {"student_ids": []}
        serializer = ClassroomDeleteStudentsSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_missing_field(self):
        """Test missing student_ids field"""
        data = {}
        serializer = ClassroomDeleteStudentsSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class AnswerSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)
        self.question = Question.objects.create(quiz=self.quiz, text="Test Question")

    def test_valid_answer_creation(self):
        """Test creating valid answer"""
        data = {
            "question": self.question.id,
            "text": "Test Answer",
            "is_correct": True,
        }
        serializer = AnswerSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_duplicate_answer_validation(self):
        """Test validation prevents duplicate answers for same question"""
        Answer.objects.create(question=self.question, text="Duplicate", is_correct=True)

        data = {
            "question": self.question.id,
            "text": "Duplicate",
            "is_correct": False,
        }
        serializer = AnswerSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertTrue(
            "text" in serializer.errors or "non_field_errors" in serializer.errors
        )

    def test_student_view_hides_correctness(self):
        """Test student view only shows answer text"""
        answer = Answer.objects.create(
            question=self.question, text="Test Answer", is_correct=True
        )

        request_mock = Mock()
        request_mock.user = self.student

        serializer = AnswerSerializer(answer, context={"request": request_mock})
        data = serializer.data

        self.assertEqual(data, {"text": "Test Answer"})

    def test_update_cannot_change_question(self):
        """Test that question cannot be changed on update"""
        answer = Answer.objects.create(
            question=self.question, text="Test Answer", is_correct=True
        )

        view_mock = Mock()
        view_mock.action = "update"

        serializer = AnswerSerializer(
            answer,
            data={"text": "Updated Answer"},
            partial=True,
            context={"view": view_mock},
        )

        fields = serializer.get_fields()
        self.assertTrue(fields["question"].read_only)

    def test_duplicate_answer_validation_with_instance(self):
        """Test validation prevents duplicate answers when updating existing instance"""
        answer = Answer.objects.create(
            question=self.question, text="Original Answer", is_correct=True
        )

        Answer.objects.create(
            question=self.question, text="Conflicting Answer", is_correct=False
        )

        # Try to update original answer to conflicting text - this should hit the self.instance condition
        data = {
            "text": "Conflicting Answer",
            "is_correct": True,
        }
        # Pass instance to trigger the self.instance condition in validate()
        serializer = AnswerSerializer(answer, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertTrue(
            "text" in serializer.errors or "non_field_errors" in serializer.errors
        )

    def test_get_fields_update_action(self):
        """Test get_fields method for update actions"""
        answer = Answer.objects.create(
            question=self.question, text="Test Answer", is_correct=True
        )

        view_mock = Mock()
        view_mock.action = "update"  # Exact match for condition

        serializer = AnswerSerializer(answer, context={"view": view_mock})

        # lines 84 and 85
        fields = serializer.get_fields()
        self.assertTrue(fields["question"].read_only)

    def test_get_fields_partial_update_action(self):
        """Test get_fields method for partial_update actions"""
        answer = Answer.objects.create(
            question=self.question, text="Test Answer", is_correct=True
        )

        view_mock = Mock()
        view_mock.action = "partial_update"

        serializer = AnswerSerializer(answer, context={"view": view_mock})

        # lines 84 and 85
        fields = serializer.get_fields()
        self.assertTrue(fields["question"].read_only)

    def test_get_fields_no_view_context(self):
        """Test get_fields method when no view context is provided"""
        answer = Answer.objects.create(
            question=self.question, text="Test Answer", is_correct=True
        )

        serializer = AnswerSerializer(answer, context={})

        # Should not make question field read-only
        fields = serializer.get_fields()
        self.assertFalse(fields["question"].read_only)


class QuestionSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)

    def test_question_with_answers(self):
        """Test question serializer includes answers"""
        question = Question.objects.create(quiz=self.quiz, text="Test Question")
        Answer.objects.create(question=question, text="Answer 1", is_correct=True)
        Answer.objects.create(question=question, text="Answer 2", is_correct=False)

        request_mock = Mock()
        request_mock.user = self.teacher

        serializer = QuestionSerializer(question, context={"request": request_mock})
        data = serializer.data

        self.assertEqual(data["text"], "Test Question")
        self.assertEqual(len(data["answers"]), 2)
        self.assertTrue(data["answers"][0]["is_correct"])

    def test_student_view_hides_correctness_for_mcq(self):
        """Test student view hides answer correctness for MCQ"""
        question = Question.objects.create(
            quiz=self.quiz, text="Test Question", is_written=False
        )
        Answer.objects.create(question=question, text="Answer 1", is_correct=True)
        Answer.objects.create(question=question, text="Answer 2", is_correct=False)

        request_mock = Mock()
        request_mock.user = self.student

        serializer = QuestionSerializer(question, context={"request": request_mock})
        data = serializer.data

        self.assertEqual(data["answers"], ["Answer 1", "Answer 2"])

    def test_student_view_hides_answers_for_written(self):
        """Test student view hides answers for written questions"""
        question = Question.objects.create(
            quiz=self.quiz, text="Test Question", is_written=True
        )
        Answer.objects.create(question=question, text="Answer 1", is_correct=True)

        request_mock = Mock()
        request_mock.user = self.student

        serializer = QuestionSerializer(question, context={"request": request_mock})
        data = serializer.data

        self.assertIsNone(data["answers"])

    def test_order_field_readonly(self):
        """Test that order field is read-only"""
        serializer = QuestionSerializer()
        fields = serializer.get_fields()
        self.assertTrue(fields["order"].read_only)

    def test_get_fields_update_action(self):
        """Test get_fields method for update actions"""
        question = Question.objects.create(quiz=self.quiz, text="Test Question")

        view_mock = Mock()
        view_mock.action = "update"

        serializer = QuestionSerializer(question, context={"view": view_mock})

        # lines 123 and 124
        fields = serializer.get_fields()
        self.assertTrue(fields["quiz"].read_only)

    def test_get_fields_partial_update_action(self):
        """Test get_fields method for partial_update actions"""
        question = Question.objects.create(quiz=self.quiz, text="Test Question")

        view_mock = Mock()
        view_mock.action = "partial_update"

        serializer = QuestionSerializer(question, context={"view": view_mock})

        # lines 123 and 124
        fields = serializer.get_fields()
        self.assertTrue(fields["quiz"].read_only)

    def test_get_fields_no_view_context(self):
        """Test get_fields method when no view context is provided"""
        question = Question.objects.create(quiz=self.quiz, text="Test Question")

        serializer = QuestionSerializer(question, context={})

        # Should not make quiz field read-only
        fields = serializer.get_fields()
        self.assertFalse(fields["quiz"].read_only)

    def test_student_view_written_question_true_condition(self):
        """Test student view for written question with is_written == True"""
        question = Question.objects.create(
            quiz=self.quiz, text="Test Question", is_written=True
        )
        Answer.objects.create(question=question, text="Answer 1", is_correct=True)

        request_mock = Mock()
        request_mock.user = self.student

        serializer = QuestionSerializer(question, context={"request": request_mock})
        data = serializer.data

        # condition: if representation["is_written"] == True:
        self.assertTrue(data["is_written"])
        self.assertIsNone(data["answers"])


class QuizSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)

    def test_quiz_serialization(self):
        """Test quiz serialization includes all fields"""
        quiz = Quiz.objects.create(
            title="Test Quiz",
            classroom=self.classroom,
            allowed_attempts=3,
        )
        Question.objects.create(quiz=quiz, text="Q1")
        Question.objects.create(quiz=quiz, text="Q2")

        serializer = QuizSerializer(quiz)
        data = serializer.data

        self.assertEqual(data["title"], "Test Quiz")
        self.assertEqual(data["classroom"], self.classroom.id)
        self.assertEqual(data["allowed_attempts"], 3)
        self.assertEqual(data["question_count"], 2)

    def test_classroom_readonly_on_update(self):
        """Test classroom field is read-only on update"""
        quiz = Quiz.objects.create(title="Test Quiz", classroom=self.classroom)

        view_mock = Mock()
        view_mock.action = "update"

        serializer = QuizSerializer(context={"view": view_mock})
        fields = serializer.get_fields()
        self.assertTrue(fields["classroom"].read_only)

    def test_get_fields_partial_update_action(self):
        """Test get_fields method for partial_update actions"""
        quiz = Quiz.objects.create(title="Test Quiz", classroom=self.classroom)

        view_mock = Mock()
        view_mock.action = "partial_update"

        serializer = QuizSerializer(quiz, context={"view": view_mock})

        # lines 164 and 165
        fields = serializer.get_fields()
        self.assertTrue(fields["classroom"].read_only)

    def test_get_fields_update_action_with_instance(self):
        """Test get_fields method for update actions with instance"""
        quiz = Quiz.objects.create(title="Test Quiz", classroom=self.classroom)

        view_mock = Mock()
        view_mock.action = "update"

        serializer = QuizSerializer(quiz, context={"view": view_mock})

        # lines 164 and 165
        fields = serializer.get_fields()
        self.assertTrue(fields["classroom"].read_only)

    def test_get_fields_no_view_context(self):
        """Test get_fields method when no view context is provided"""
        quiz = Quiz.objects.create(title="Test Quiz", classroom=self.classroom)

        serializer = QuizSerializer(quiz, context={})

        # Should not make classroom field read-only
        fields = serializer.get_fields()
        self.assertFalse(fields["classroom"].read_only)


class StudentAnswerSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)
        self.question = Question.objects.create(quiz=self.quiz, text="Test Question")
        self.quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )
        self.question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )

    def test_serializer_fields(self):
        """Test student answer serializer fields"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt,
            text="Test Answer",
        )

        serializer = StudentAnswerSerializer(answer)
        data = serializer.data

        self.assertIn("id", data)
        self.assertIn("question_attempt", data)
        self.assertIn("text", data)
        self.assertIn("is_correct", data)

    def test_is_correct_readonly(self):
        """Test that is_correct field is read-only"""
        serializer = StudentAnswerSerializer()
        self.assertIn("is_correct", serializer.Meta.read_only_fields)


class StudentAnswersSubmitSerializerTest(TestCase):
    def test_valid_data(self):
        """Test valid answer submission data"""
        data = {
            "question_attempt": 1,
            "answers": ["Answer 1", "Answer 2"],
        }
        serializer = StudentAnswersSubmitSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_empty_answers(self):
        """Test empty answers list is invalid"""
        data = {
            "question_attempt": 1,
            "answers": [],
        }
        serializer = StudentAnswersSubmitSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_missing_question_attempt(self):
        """Test missing question_attempt field"""
        data = {"answers": ["Answer 1"]}
        serializer = StudentAnswersSubmitSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_create_method(self):
        """Test create method returns None (placeholder implementation)"""
        data = {
            "question_attempt": 1,
            "answers": ["Answer 1", "Answer 2"],
        }
        serializer = StudentAnswersSubmitSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # The create method currently just contains 'pass', so it returns None
        result = serializer.create(serializer.validated_data)
        self.assertIsNone(result)


class StudentQuestionAttemptSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)
        self.question = Question.objects.create(quiz=self.quiz, text="Test Question")
        self.quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

    def test_serializer_includes_nested_data(self):
        """Test serializer includes question and student answers"""
        question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )
        question_attempt.submitted_at = timezone.now()
        question_attempt.save()

        StudentAnswer.objects.create(
            question_attempt=question_attempt, text="Test Answer"
        )

        request_mock = Mock()
        request_mock.user = self.teacher

        serializer = StudentQuestionAttemptSerializer(
            question_attempt, context={"request": request_mock}
        )
        data = serializer.data

        self.assertIn("question", data)
        self.assertIn("student_answers", data)
        self.assertEqual(len(data["student_answers"]), 1)


class StudentQuizAttemptSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)

    def test_readonly_fields(self):
        """Test that certain fields are read-only"""
        serializer = StudentQuizAttemptSerializer()
        readonly_fields = serializer.Meta.extra_kwargs

        self.assertTrue(readonly_fields["student"]["read_only"])
        self.assertTrue(readonly_fields["score"]["read_only"])
        self.assertTrue(readonly_fields["completed_at"]["read_only"])

    def test_serialization(self):
        """Test quiz attempt serialization"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz, score=Decimal("85.50")
        )

        serializer = StudentQuizAttemptSerializer(attempt)
        data = serializer.data

        self.assertEqual(data["student"], self.student.id)
        self.assertEqual(data["quiz"], self.quiz.id)
        self.assertEqual(float(data["score"]), 85.50)


class SQANextQuestionSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)
        self.question1 = Question.objects.create(quiz=self.quiz, text="Question 1")
        self.question2 = Question.objects.create(quiz=self.quiz, text="Question 2")

    def test_next_question_serialization(self):
        """Test serialization of next question"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        request_mock = Mock()
        request_mock.user = self.student

        serializer = SQANextQuestionSerializer(
            attempt, context={"request": request_mock}
        )
        data = serializer.data

        self.assertIn("next_question", data)
        self.assertIn("question_attempt", data)
        self.assertIsNotNone(data["next_question"])
        self.assertIsNotNone(data["question_attempt"])

    def test_no_next_question(self):
        """Test when no next question is available"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        # Complete all questions
        for question in [self.question1, self.question2]:
            question_attempt = StudentQuestionAttempt.objects.create(
                quiz_attempt=attempt, question=question
            )
            question_attempt.submitted_at = timezone.now()
            question_attempt.save()

        serializer = SQANextQuestionSerializer(attempt)
        data = serializer.data

        self.assertIsNone(data["next_question"])
        self.assertIsNone(data["question_attempt"])


class EnrollmentCodeSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)

    def test_serializer_readonly_fields(self):
        """Test that code and classroom are read-only"""
        code = EnrollmentCode.objects.create(code="TEST1234", classroom=self.classroom)

        serializer = EnrollmentCodeSerializer(code)
        fields = serializer.get_fields()

        self.assertTrue(fields["code"].read_only)
        self.assertTrue(fields["classroom"].read_only)

    def test_serialization(self):
        """Test enrollment code serialization"""
        code = EnrollmentCode.objects.create(
            code="TEST1234", classroom=self.classroom, is_active=True
        )

        serializer = EnrollmentCodeSerializer(code)
        data = serializer.data

        self.assertEqual(data["code"], "TEST1234")
        self.assertEqual(data["classroom"], self.classroom.id)
        self.assertTrue(data["is_active"])


class EnrollmentCodePutSerializerTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)

    def test_all_fields_readonly(self):
        """Test that all fields are read-only"""
        serializer = EnrollmentCodePutSerializer()
        readonly_fields = serializer.Meta.extra_kwargs

        self.assertTrue(readonly_fields["code"]["read_only"])
        self.assertTrue(readonly_fields["classroom"]["read_only"])
        self.assertTrue(readonly_fields["is_active"]["read_only"])

    def test_save_method(self):
        """Test custom save method generates new code and sets active"""
        code = EnrollmentCode.objects.create(
            code="OLD1234", classroom=self.classroom, is_active=False
        )
        original_code_text = code.code

        serializer = EnrollmentCodePutSerializer(code, data={})
        self.assertTrue(serializer.is_valid())

        saved_instance = serializer.save()

        # Verify that the instance was updated with new code and set to active
        self.assertEqual(saved_instance.classroom, self.classroom)
        self.assertTrue(saved_instance.is_active)
        self.assertEqual(len(saved_instance.code), 8)

        # Verify that the generate_for_class was called by checking the database
        updated_code = EnrollmentCode.objects.get(id=code.id)
        self.assertTrue(updated_code.is_active)

    def test_save_method_generates_new_code(self):
        """Test that save method calls generate_for_class and sets instance correctly"""
        code = EnrollmentCode.objects.create(
            code="INITIAL1", classroom=self.classroom, is_active=False
        )

        serializer = EnrollmentCodePutSerializer(code, data={})
        self.assertTrue(serializer.is_valid())

        # Mock the generate_for_class method to verify it's called
        with patch.object(EnrollmentCode, "generate_for_class") as mock_generate:
            mock_generate.return_value = code  # Return the same instance for simplicity

            # Call save
            result = serializer.save()

            # Verify generate_for_class was called with correct classroom
            mock_generate.assert_called_once_with(self.classroom)

            # Verify instance is_active was set to True
            self.assertTrue(serializer.instance.is_active)


class EnrollSerializerTest(TestCase):
    def test_valid_code(self):
        """Test valid enrollment code"""
        data = {"code": "VALID123"}
        serializer = EnrollSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_missing_code(self):
        """Test missing code field"""
        data = {}
        serializer = EnrollSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)


class TeacherStatsSerializersTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            first_name="John",
            last_name="Doe",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)
        self.question = Question.objects.create(quiz=self.quiz, text="Test Question")

    def test_teacher_student_quiz_attempt_stats(self):
        """Test teacher quiz attempt stats serializer"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz, score=Decimal("92.5")
        )

        serializer = TeacherStudentQuizAttemptStatsSerializer(attempt)
        data = serializer.data

        self.assertEqual(data["student"]["username"], "student")
        self.assertEqual(data["student"]["first_name"], "John")
        self.assertEqual(data["student"]["last_name"], "Doe")
        self.assertEqual(float(data["score"]), 92.5)

    def test_teacher_student_question_attempt_stats(self):
        """Test teacher question attempt stats serializer"""
        quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )
        question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=quiz_attempt, question=self.question
        )
        question_attempt.submitted_at = timezone.now()
        question_attempt.save()

        StudentAnswer.objects.create(
            question_attempt=question_attempt, text="Test Answer"
        )

        request_mock = Mock()
        request_mock.user = self.teacher

        serializer = TeacherStudentQuestionAttemptStatsSerializer(
            question_attempt, context={"request": request_mock}
        )
        data = serializer.data

        self.assertIn("question", data)
        self.assertIn("student_answers", data)
        self.assertEqual(len(data["student_answers"]), 1)
        self.assertIn("started_at", data)
        self.assertIn("submitted_at", data)


# ======================== VIEW TESTS ========================


class ActivateUserViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse(
            "activate_user", kwargs={"uidb64": "test_uid", "token": "test_token"}
        )

    @patch("base.views.requests.post")
    def test_successful_activation(self, mock_post):
        """Test successful user activation"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "User activated successfilly")

    @patch("base.views.requests.post")
    def test_activation_failure_with_json_response(self, mock_post):
        """Test activation failure with JSON error response"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid token"}
        mock_post.return_value = mock_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    @patch("base.views.requests.post")
    def test_activation_failure_without_json_response(self, mock_post):
        """Test activation failure without JSON response"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = ValueError("No JSON")
        mock_post.return_value = mock_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    @patch("base.views.requests.post")
    def test_request_exception(self, mock_post):
        """Test handling of request exceptions"""
        mock_post.side_effect = requests.RequestException("Network error")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Network error")


# ======================== PERMISSION TESTS ========================


class PermissionTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.anonymous_user = Mock()
        self.anonymous_user.is_authenticated = False

    def test_is_teacher_permission_with_teacher(self):
        """Test IsTeacher permission with teacher user"""
        permission = IsTeacher()
        request = Mock()
        request.user = self.teacher

        self.assertTrue(permission.has_permission(request, None))

    def test_is_teacher_permission_with_student(self):
        """Test IsTeacher permission with student user"""
        permission = IsTeacher()
        request = Mock()
        request.user = self.student

        self.assertFalse(permission.has_permission(request, None))

    def test_is_teacher_permission_with_anonymous(self):
        """Test IsTeacher permission with anonymous user"""
        permission = IsTeacher()
        request = Mock()
        request.user = self.anonymous_user

        self.assertFalse(permission.has_permission(request, None))

    def test_is_student_permission_with_student(self):
        """Test IsStudent permission with student user"""
        permission = IsStudent()
        request = Mock()
        request.user = self.student

        self.assertTrue(permission.has_permission(request, None))

    def test_is_student_permission_with_teacher(self):
        """Test IsStudent permission with teacher user"""
        permission = IsStudent()
        request = Mock()
        request.user = self.teacher

        self.assertFalse(permission.has_permission(request, None))

    def test_is_student_permission_with_anonymous(self):
        """Test IsStudent permission with anonymous user"""
        permission = IsStudent()
        request = Mock()
        request.user = self.anonymous_user

        self.assertFalse(permission.has_permission(request, None))
