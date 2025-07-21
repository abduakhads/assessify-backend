from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

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


class BaseAPITestCase(APITestCase):
    """Base test case class with common setup methods."""

    def setUp(self):
        # Create test users
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

        self.teacher2 = User.objects.create_user(
            username="teacher2",
            email="teacher2@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        # Create test classroom
        self.classroom = Classroom.objects.create(
            name="Test Classroom", teacher=self.teacher
        )
        self.classroom.students.add(self.student)

        # Create test quiz
        self.quiz = Quiz.objects.create(
            title="Test Quiz",
            classroom=self.classroom,
            is_active=True,
            allowed_attempts=2,
        )

        # Create test questions
        self.question1 = Question.objects.create(
            quiz=self.quiz,
            text="What is 2+2?",
            has_multiple_answers=False,
            is_written=False,
            time_limit=30,
            order=1,
        )

        self.question2 = Question.objects.create(
            quiz=self.quiz,
            text="Select all prime numbers",
            has_multiple_answers=True,
            is_written=False,
            order=2,
        )

        # Create test answers
        self.answer1 = Answer.objects.create(
            question=self.question1, text="4", is_correct=True
        )

        self.answer2 = Answer.objects.create(
            question=self.question1, text="3", is_correct=False
        )

        self.answer3 = Answer.objects.create(
            question=self.question2, text="2", is_correct=True
        )

        self.answer4 = Answer.objects.create(
            question=self.question2, text="3", is_correct=True
        )

        self.answer5 = Answer.objects.create(
            question=self.question2, text="4", is_correct=False
        )


class ClassroomViewSetTests(BaseAPITestCase):
    """Tests for ClassroomViewSet."""

    def test_teacher_can_create_classroom(self):
        """Test that teachers can create classrooms."""
        self.client.force_authenticate(user=self.teacher)
        data = {"name": "New Classroom"}

        response = self.client.post("/api/classrooms/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Classroom")
        self.assertEqual(response.data["teacher"]["id"], self.teacher.id)

        # Check that enrollment code was created
        classroom_id = response.data["id"]
        self.assertTrue(
            EnrollmentCode.objects.filter(classroom_id=classroom_id).exists()
        )

    def test_student_cannot_create_classroom(self):
        """Test that students cannot create classrooms."""
        self.client.force_authenticate(user=self.student)
        data = {"name": "New Classroom"}

        response = self.client.post("/api/classrooms/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_list_own_classrooms(self):
        """Test that teachers can list their own classrooms."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get("/api/classrooms/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.classroom.id)

    def test_student_can_list_enrolled_classrooms(self):
        """Test that students can list classrooms they're enrolled in."""
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/classrooms/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.classroom.id)
        # students should only see themselves in the students list
        self.assertEqual(len(response.data[0]["students"]), 1)
        self.assertEqual(response.data[0]["students"][0]["id"], self.student.id)

    def test_teacher_can_retrieve_classroom(self):
        """Test that teachers can retrieve their classroom."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/classrooms/{self.classroom.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.classroom.id)

    def test_teacher_cannot_retrieve_other_teacher_classroom(self):
        """Test that teachers cannot retrieve other teacher's classroom."""
        other_classroom = Classroom.objects.create(
            name="Other Classroom", teacher=self.teacher2
        )

        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/classrooms/{other_classroom.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_can_update_classroom(self):
        """Test that teachers can update their classroom."""
        self.client.force_authenticate(user=self.teacher)
        data = {"name": "Updated Classroom Name"}

        response = self.client.patch(f"/api/classrooms/{self.classroom.id}/", data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Classroom Name")

    def test_teacher_can_delete_students(self):
        """Test that teachers can remove students from classroom."""
        self.classroom.students.add(self.student2)
        self.client.force_authenticate(user=self.teacher)
        data = {"student_ids": [self.student.id, self.student2.id]}

        response = self.client.post(
            f"/api/classrooms/{self.classroom.id}/delete-students/", data
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.classroom.students.count(), 0)

    def test_delete_students_with_invalid_ids(self):
        """Test removing students with invalid IDs."""
        self.client.force_authenticate(user=self.teacher)
        data = {"student_ids": [999]}

        response = self.client.post(
            f"/api/classrooms/{self.classroom.id}/delete-students/", data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No valid students found", response.data["detail"])

    def test_unauthenticated_user_cannot_access_classrooms(self):
        """Test that unauthenticated users cannot access classrooms."""
        response = self.client.get("/api/classrooms/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class QuizViewSetTests(BaseAPITestCase):
    """Tests for QuizViewSet."""

    def test_teacher_can_create_quiz(self):
        """Test that teachers can create quizzes."""
        self.client.force_authenticate(user=self.teacher)
        data = {
            "title": "New Quiz",
            "classroom": self.classroom.id,
            "allowed_attempts": 3,
        }

        response = self.client.post("/api/quizzes/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Quiz")
        self.assertEqual(response.data["classroom"], self.classroom.id)

    def test_teacher_cannot_create_quiz_for_other_classroom(self):
        """Test that teachers cannot create quizzes for other teachers' classrooms."""
        other_classroom = Classroom.objects.create(
            name="Other Classroom", teacher=self.teacher2
        )

        self.client.force_authenticate(user=self.teacher)
        data = {"title": "New Quiz", "classroom": other_classroom.id}

        response = self.client.post("/api/quizzes/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Classroom does not exist", response.data["detail"])

    def test_teacher_can_create_quiz_for_nonexistent_classroom(self):
        """Test creating quiz for nonexistent classroom."""
        self.client.force_authenticate(user=self.teacher)
        data = {"title": "New Quiz", "classroom": 999}

        response = self.client.post("/api/quizzes/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Classroom does not exist", response.data["detail"])

    def test_student_cannot_create_quiz(self):
        """Test that students cannot create quizzes."""
        self.client.force_authenticate(user=self.student)
        data = {"title": "New Quiz", "classroom": self.classroom.id}

        response = self.client.post("/api/quizzes/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_list_own_quizzes(self):
        """Test that teachers can list quizzes in their classrooms."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get("/api/quizzes/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.quiz.id)

    def test_student_can_list_accessible_quizzes(self):
        """Test that students can list quizzes in their enrolled classrooms."""
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/quizzes/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.quiz.id)

    def test_filter_quizzes_by_classroom(self):
        """Test filtering quizzes by classroom."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/quizzes/?classroom={self.classroom.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["classroom"], self.classroom.id)

    def test_invalid_classroom_filter_returns_empty(self):
        """Test filtering with invalid classroom ID returns empty queryset."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get("/api/quizzes/?classroom=invalid")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class QuestionViewSetTests(BaseAPITestCase):
    """Tests for QuestionViewSet."""

    def test_teacher_can_create_question(self):
        """Test that teachers can create questions."""
        self.client.force_authenticate(user=self.teacher)
        data = {
            "quiz": self.quiz.id,
            "text": "What is 3+3?",
            "has_multiple_answers": False,
            "time_limit": 60,
        }

        response = self.client.post("/api/questions/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["text"], "What is 3+3?")
        self.assertEqual(response.data["quiz"], self.quiz.id)

    def test_teacher_cannot_create_question_for_other_quiz(self):
        """Test that teachers cannot create questions for other teachers' quizzes."""
        other_classroom = Classroom.objects.create(
            name="Other Classroom", teacher=self.teacher2
        )
        other_quiz = Quiz.objects.create(title="Other Quiz", classroom=other_classroom)

        self.client.force_authenticate(user=self.teacher)
        data = {"quiz": other_quiz.id, "text": "What is 3+3?"}

        response = self.client.post("/api/questions/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Quiz does not exist", response.data["detail"])

    def test_teacher_cannot_create_question_for_nonexistent_quiz(self):
        """Test creating question for nonexistent quiz."""
        self.client.force_authenticate(user=self.teacher)
        data = {"quiz": 999, "text": "What is 3+3?"}

        response = self.client.post("/api/questions/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Quiz does not exist", response.data["detail"])

    def test_student_cannot_create_question(self):
        """Test that students cannot create questions."""
        self.client.force_authenticate(user=self.student)
        data = {"quiz": self.quiz.id, "text": "What is 3+3?"}

        response = self.client.post("/api/questions/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_list_questions(self):
        """Test that teachers can list questions from their quizzes."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get("/api/questions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # question1 and question2

    def test_filter_questions_by_quiz(self):
        """Test filtering questions by quiz."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/questions/?quiz={self.quiz.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for question in response.data:
            self.assertEqual(question["quiz"], self.quiz.id)

    def test_invalid_quiz_filter_returns_empty(self):
        """Test filtering with invalid quiz ID returns empty queryset."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get("/api/questions/?quiz=invalid")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class AnswerViewSetTests(BaseAPITestCase):
    """Tests for AnswerViewSet."""

    def test_teacher_can_create_answer(self):
        """Test that teachers can create answers."""
        self.client.force_authenticate(user=self.teacher)
        data = {"question": self.question1.id, "text": "5", "is_correct": False}

        response = self.client.post("/api/answers/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["text"], "5")
        self.assertEqual(response.data["question"], self.question1.id)

    def test_teacher_cannot_create_answer_for_other_question(self):
        """Test that teachers cannot create answers for other teachers' questions."""
        other_classroom = Classroom.objects.create(
            name="Other Classroom", teacher=self.teacher2
        )
        other_quiz = Quiz.objects.create(title="Other Quiz", classroom=other_classroom)
        other_question = Question.objects.create(
            quiz=other_quiz, text="Other question?"
        )

        self.client.force_authenticate(user=self.teacher)
        data = {"question": other_question.id, "text": "Answer"}

        response = self.client.post("/api/answers/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Question does not exist", response.data["detail"])

    def test_teacher_cannot_create_answer_for_nonexistent_question(self):
        """Test creating answer for nonexistent question."""
        self.client.force_authenticate(user=self.teacher)
        data = {"question": 999, "text": "Answer"}

        response = self.client.post("/api/answers/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Question does not exist", response.data["detail"])

    def test_student_cannot_create_answer(self):
        """Test that students cannot create answers."""
        self.client.force_authenticate(user=self.student)
        data = {"question": self.question1.id, "text": "5"}

        response = self.client.post("/api/answers/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_list_answers(self):
        """Test that teachers can list answers from their questions."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get("/api/answers/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)  # answer1-5

    def test_student_cannot_list_answers(self):
        """Test that students cannot list answers (teacher only)."""
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/answers/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_answers_by_question(self):
        """Test filtering answers by question."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/answers/?question={self.question1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # answer1 and answer2
        for answer in response.data:
            self.assertEqual(answer["question"], self.question1.id)

    def test_empty_filter_answers_by_question(self):
        """Test filtering answers by question for invalid query."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/answers/?question={999}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class StudentQuizAttemptViewSetTests(BaseAPITestCase):
    """Tests for StudentQuizAttemptViewSet."""

    def test_student_can_create_quiz_attempt(self):
        """Test that students can create quiz attempts."""
        self.client.force_authenticate(user=self.student)
        data = {"quiz": self.quiz.id}

        response = self.client.post("/api/attempts/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quiz"], self.quiz.id)
        self.assertEqual(response.data["student"], self.student.id)

    def test_student_cannot_create_attempt_for_inactive_quiz(self):
        """Test that students cannot create attempts for inactive quizzes."""
        self.quiz.is_active = False
        self.quiz.save()

        self.client.force_authenticate(user=self.student)
        data = {"quiz": self.quiz.id}

        response = self.client.post("/api/attempts/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Quiz does not exist", response.data["detail"])

    def test_student_cannot_create_attempt_for_nonexistent_quiz(self):
        """Test creating attempt for nonexistent quiz."""
        self.client.force_authenticate(user=self.student)
        data = {"quiz": 999}

        response = self.client.post("/api/attempts/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Quiz does not exist", response.data["detail"])

    def test_student_cannot_create_multiple_active_attempts(self):
        """Test that students cannot have multiple active attempts."""
        # Create first attempt
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.client.force_authenticate(user=self.student)
        data = {"quiz": self.quiz.id}

        response = self.client.post("/api/attempts/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already have an active attempt", response.data["detail"])

    def test_student_cannot_exceed_allowed_attempts(self):
        """Test that students cannot exceed allowed attempts."""
        # Create maximum allowed attempts
        for i in range(self.quiz.allowed_attempts):
            attempt = StudentQuizAttempt.objects.create(
                student=self.student, quiz=self.quiz, completed_at=timezone.now()
            )

        self.client.force_authenticate(user=self.student)
        data = {"quiz": self.quiz.id}

        response = self.client.post("/api/attempts/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reached the maximum allowed attempts", response.data["detail"])

    def test_student_cannot_attempt_quiz_not_enrolled(self):
        """Test that students cannot attempt quizzes they're not enrolled for."""
        other_classroom = Classroom.objects.create(
            name="Other Classroom", teacher=self.teacher2
        )
        other_quiz = Quiz.objects.create(
            title="Other Quiz", classroom=other_classroom, is_active=True
        )

        self.client.force_authenticate(user=self.student)
        data = {"quiz": other_quiz.id}

        response = self.client.post("/api/attempts/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not enrolled in this quiz", response.data["detail"])

    def test_teacher_cannot_create_quiz_attempt(self):
        """Test that teachers cannot create quiz attempts."""
        self.client.force_authenticate(user=self.teacher)
        data = {"quiz": self.quiz.id}

        response = self.client.post("/api/attempts/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_list_own_attempts(self):
        """Test that students can list their own attempts."""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/attempts/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], attempt.id)

    def test_student_cannot_see_other_students_attempts(self):
        """Test that students cannot see other students' attempts."""
        self.classroom.students.add(self.student2)
        other_attempt = StudentQuizAttempt.objects.create(
            student=self.student2, quiz=self.quiz
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/attempts/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 0
        )  # should not see other student's attempt

    def test_filter_attempts_by_quiz(self):
        """Test filtering quiz attempts bu quiz."""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f"/api/attempts/?quiz={self.quiz.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], attempt.id)

    def test_empty_filter_attempts_by_quiz(self):
        """Test filtering quiz attempts bu quiz for invalid query."""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f"/api/attempts/?quiz={999}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_next_question_action(self):
        """Test the next question action."""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f"/api/attempts/{attempt.id}/next-question/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["next_question"])
        self.assertEqual(response.data["next_question"]["id"], self.question1.id)

    def test_next_question_completes_attempt_when_no_more_questions(self):
        """Test that attempt is completed when no more questions available."""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        # Create question attempts for all questions
        for question in self.quiz.questions.all():
            StudentQuestionAttempt.objects.create(
                quiz_attempt=attempt, question=question, submitted_at=timezone.now()
            )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f"/api/attempts/{attempt.id}/next-question/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["next_question"])

        # Check that attempt is now completed
        attempt.refresh_from_db()
        self.assertIsNotNone(attempt.completed_at)

    def test_archived_attempts(self):
        """Test getting archived attempts (student no longer in classroom)."""
        # Create attempt
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        # Remove student from classroom
        self.classroom.students.remove(self.student)

        self.client.force_authenticate(user=self.student)

        response = self.client.get("/api/attempts/archived/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], attempt.id)


class StudentAnswerSubmitViewSetTests(BaseAPITestCase):
    """Tests for StudentAnswerSubmitViewSet."""

    def setUp(self):
        super().setUp()
        # Create a quiz attempt and question attempt for testing
        self.attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )
        self.question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.attempt, question=self.question1
        )

    def test_student_can_submit_answer(self):
        """Test that students can submit answers."""
        self.client.force_authenticate(user=self.student)
        data = {"question_attempt": self.question_attempt.id, "answers": ["4"]}

        response = self.client.post("/api/answer-submit/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Answers submitted successfully", response.data["detail"])

        # Check that question attempt is marked as submitted
        self.question_attempt.refresh_from_db()
        self.assertIsNotNone(self.question_attempt.submitted_at)

    def test_student_cannot_submit_answer_for_nonexistent_attempt(self):
        """Test submitting answer for nonexistent question attempt."""
        self.client.force_authenticate(user=self.student)
        data = {"question_attempt": 999, "answers": ["4"]}

        response = self.client.post("/api/answer-submit/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Question attempt does not exist", response.data["detail"])

    def test_student_cannot_submit_answer_for_other_students_attempt(self):
        """Test that students cannot submit answers for other students' attempts."""
        other_attempt = StudentQuizAttempt.objects.create(
            student=self.student2, quiz=self.quiz
        )
        other_question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=other_attempt, question=self.question1
        )

        self.client.force_authenticate(user=self.student)
        data = {"question_attempt": other_question_attempt.id, "answers": ["4"]}

        response = self.client.post("/api/answer-submit/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Question attempt does not exist", response.data["detail"])

    def test_student_cannot_resubmit_answer(self):
        """Test that students cannot resubmit answers."""
        # Mark question attempt as already submitted
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        self.client.force_authenticate(user=self.student)
        data = {"question_attempt": self.question_attempt.id, "answers": ["4"]}

        response = self.client.post("/api/answer-submit/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been completed", response.data["detail"])

    def test_student_cannot_submit_multiple_answers_for_single_answer_question(self):
        """Test validation for single answer questions."""
        self.client.force_authenticate(user=self.student)
        data = {
            "question_attempt": self.question_attempt.id,
            "answers": ["4", "3"],  # multiple answers for single-answer question
        }

        response = self.client.post("/api/answer-submit/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("allows only one answer", response.data["detail"])

    def test_student_can_submit_multiple_answers_for_multiple_answer_question(self):
        """Test submitting multiple answers for multiple answer questions."""
        multiple_question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.attempt,
            question=self.question2,  # has_multiple_answers=True
        )

        self.client.force_authenticate(user=self.student)
        data = {"question_attempt": multiple_question_attempt.id, "answers": ["2", "3"]}

        response = self.client.post("/api/answer-submit/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Answers submitted successfully", response.data["detail"])

    def test_teacher_cannot_submit_answer(self):
        """Test that teachers cannot submit answers."""
        self.client.force_authenticate(user=self.teacher)
        data = {"question_attempt": self.question_attempt.id, "answers": ["4"]}

        response = self.client.post("/api/answer-submit/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class EnrollmentCodeViewSetTests(BaseAPITestCase):
    """Tests for EnrollmentCodeViewSet."""

    def setUp(self):
        super().setUp()
        self.enrollment_code = EnrollmentCode.generate_for_class(self.classroom)

    def test_teacher_can_retrieve_enrollment_code(self):
        """Test that teachers can retrieve enrollment code for their classroom."""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/enrollment/{self.classroom.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["classroom"], self.classroom.id)
        self.assertIsNotNone(response.data["code"])

    def test_teacher_cannot_retrieve_other_teachers_enrollment_code(self):
        """Test that teachers cannot retrieve other teachers' enrollment codes."""
        other_classroom = Classroom.objects.create(
            name="Other Classroom", teacher=self.teacher2
        )
        other_enrollment_code = EnrollmentCode.generate_for_class(other_classroom)

        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f"/api/enrollment/{other_classroom.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_can_update_enrollment_code(self):
        """Test that teachers can regenerate enrollment codes."""
        old_code = self.enrollment_code.code

        self.client.force_authenticate(user=self.teacher)
        data = {"regenerate": True}

        response = self.client.put(f"/api/enrollment/{self.classroom.id}/", data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.enrollment_code.refresh_from_db()
        self.assertNotEqual(self.enrollment_code.code, old_code)

    def test_student_cannot_access_enrollment_code(self):
        """Test that students cannot access enrollment codes."""
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f"/api/enrollment/{self.classroom.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class EnrollViewTests(BaseAPITestCase):
    """Tests for EnrollView."""

    def setUp(self):
        super().setUp()
        self.enrollment_code = EnrollmentCode.generate_for_class(self.classroom)
        # Create a classroom without the test student
        self.other_classroom = Classroom.objects.create(
            name="Other Classroom", teacher=self.teacher2
        )
        self.other_enrollment_code = EnrollmentCode.generate_for_class(
            self.other_classroom
        )

    def test_student_can_enroll_with_valid_code(self):
        """Test that students can enroll with valid enrollment code."""
        self.client.force_authenticate(user=self.student2)
        data = {"code": self.enrollment_code.code}

        response = self.client.post("/api/enroll/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Successfully enrolled", response.data["detail"])
        self.assertTrue(self.classroom.students.filter(id=self.student2.id).exists())

    def test_student_cannot_enroll_with_invalid_code(self):
        """Test that students cannot enroll with invalid codes."""
        self.client.force_authenticate(user=self.student2)
        data = {"code": "INVALID123"}

        response = self.client.post("/api/enroll/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or inactive enrollment code", response.data["detail"])

    def test_student_cannot_enroll_with_inactive_code(self):
        """Test that students cannot enroll with inactive codes."""
        self.enrollment_code.is_active = False
        self.enrollment_code.save()

        self.client.force_authenticate(user=self.student2)
        data = {"code": self.enrollment_code.code}

        response = self.client.post("/api/enroll/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or inactive enrollment code", response.data["detail"])

    def test_student_cannot_enroll_twice(self):
        """Test that students cannot enroll in the same classroom twice."""
        self.client.force_authenticate(user=self.student)  # Already enrolled
        data = {"code": self.enrollment_code.code}

        response = self.client.post("/api/enroll/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already enrolled", response.data["detail"])

    def test_teacher_cannot_enroll(self):
        """Test that teachers cannot enroll in classrooms."""
        self.client.force_authenticate(user=self.teacher)
        data = {"code": self.other_enrollment_code.code}

        response = self.client.post("/api/enroll/", data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class IntegrationTests(BaseAPITestCase):
    """Integration tests for complete user workflows."""

    def test_complete_student_quiz_workflow(self):
        """Test complete workflow from enrollment to quiz completion."""
        # 1. Student enrolls in classroom
        enrollment_code = EnrollmentCode.generate_for_class(self.classroom)
        self.classroom.students.remove(self.student)  # Remove initially

        self.client.force_authenticate(user=self.student)
        response = self.client.post("/api/enroll/", {"code": enrollment_code.code})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. Student starts quiz attempt
        response = self.client.post("/api/attempts/", {"quiz": self.quiz.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attempt_id = response.data["id"]

        # 3. Student gets next question
        response = self.client.get(f"/api/attempts/{attempt_id}/next-question/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        question_attempt_id = response.data["question_attempt"]

        # 4. Student submits answer
        response = self.client.post(
            "/api/answer-submit/",
            {"question_attempt": question_attempt_id, "answers": ["4"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 5. Student gets next question (should be question2)
        response = self.client.get(f"/api/attempts/{attempt_id}/next-question/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["next_question"]["id"], self.question2.id)
        question_attempt_id2 = response.data["question_attempt"]

        # 6. Student submits multiple answers for second question
        response = self.client.post(
            "/api/answer-submit/",
            {"question_attempt": question_attempt_id2, "answers": ["2", "3"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 7. Student gets next question (should be None, completing the attempt)
        response = self.client.get(f"/api/attempts/{attempt_id}/next-question/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["next_question"])

        # Verify attempt is completed with score
        attempt = StudentQuizAttempt.objects.get(id=attempt_id)
        self.assertIsNotNone(attempt.completed_at)
        self.assertIsNotNone(attempt.score)
        self.assertEqual(attempt.score, Decimal("100.00"))  # All answers correct

    def test_complete_teacher_quiz_creation_workflow(self):
        """Test complete workflow for teacher creating and managing a quiz."""
        self.client.force_authenticate(user=self.teacher)

        # 1. Teacher creates classroom
        response = self.client.post("/api/classrooms/", {"name": "Math Class"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        classroom_id = response.data["id"]

        # 2. Teacher creates quiz
        response = self.client.post(
            "/api/quizzes/",
            {"title": "Math Quiz 1", "classroom": classroom_id, "allowed_attempts": 2},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quiz_id = response.data["id"]

        # 3. Teacher creates questions
        response = self.client.post(
            "/api/questions/",
            {
                "quiz": quiz_id,
                "text": "What is 5+5?",
                "has_multiple_answers": False,
                "time_limit": 30,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        question_id = response.data["id"]

        # 4. Teacher creates answers
        response = self.client.post(
            "/api/answers/", {"question": question_id, "text": "10", "is_correct": True}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            "/api/answers/",
            {"question": question_id, "text": "11", "is_correct": False},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 5. Teacher gets enrollment code
        response = self.client.get(f"/api/enrollment/{classroom_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enrollment_code = response.data["code"]

        # Verify everything is created correctly
        classroom = Classroom.objects.get(id=classroom_id)
        quiz = Quiz.objects.get(id=quiz_id)
        question = Question.objects.get(id=question_id)

        self.assertEqual(classroom.teacher, self.teacher)
        self.assertEqual(quiz.classroom, classroom)
        self.assertEqual(question.quiz, quiz)
        self.assertEqual(question.answers.count(), 2)
        self.assertTrue(
            EnrollmentCode.objects.filter(
                classroom=classroom, code=enrollment_code
            ).exists()
        )
