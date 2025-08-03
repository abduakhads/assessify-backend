from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from django.db import IntegrityError
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


class UserModelTest(TestCase):
    def test_create_teacher_and_student(self):
        """Test creating users with different roles"""
        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.assertEqual(teacher.role, User.Role.TEACHER)
        self.assertEqual(student.role, User.Role.STUDENT)
        self.assertTrue(teacher.check_password("pass"))
        self.assertTrue(student.check_password("pass"))

    def test_user_role_choices(self):
        """Test that role choices are properly defined"""
        self.assertEqual(User.Role.TEACHER, "teacher")
        self.assertEqual(User.Role.STUDENT, "student")
        # Check choices exist (order may vary)
        choice_values = [choice[0] for choice in User.Role.choices]
        choice_labels = [choice[1] for choice in User.Role.choices]
        self.assertIn("teacher", choice_values)
        self.assertIn("student", choice_values)
        self.assertIn("Teacher", choice_labels)
        self.assertIn("Student", choice_labels)

    def test_user_without_role(self):
        """Test creating user without specifying role"""
        user = User.objects.create_user(
            username="test_user", email="test_user@example.com", password="pass"
        )
        self.assertEqual(user.role, "")  # Default empty string

    def test_user_inheritance(self):
        """Test that User inherits from AbstractUser"""
        user = User.objects.create_user(
            username="test",
            password="pass",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.username, "test")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")

    def test_unique_email_constraint(self):
        """Test that email field has unique constraint"""
        # Create first user
        User.objects.create_user(
            username="user1",
            email="test@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )

        # Try to create another user with the same email
        with self.assertRaises(Exception):  # IntegrityError
            User.objects.create_user(
                username="user2",
                email="test@example.com",
                password="pass",
                role=User.Role.STUDENT,
            )


class ClassroomModelTest(TestCase):
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

    def test_create_classroom(self):
        """Test basic classroom creation and relationships"""
        classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        classroom.students.add(self.student1, self.student2)

        self.assertEqual(classroom.teacher, self.teacher)
        self.assertIn(self.student1, classroom.students.all())
        self.assertIn(self.student2, classroom.students.all())
        self.assertEqual(classroom.student_count(), 2)

    def test_classroom_str_method(self):
        """Test classroom string representation"""
        classroom = Classroom.objects.create(name="Science", teacher=self.teacher)
        expected_str = f"{classroom.id}. Science"
        self.assertEqual(str(classroom), expected_str)

    def test_student_count_method(self):
        """Test student count method with various scenarios"""
        classroom = Classroom.objects.create(name="History", teacher=self.teacher)

        # Empty classroom
        self.assertEqual(classroom.student_count(), 0)

        # Add one student
        classroom.students.add(self.student1)
        self.assertEqual(classroom.student_count(), 1)

        # Add second student
        classroom.students.add(self.student2)
        self.assertEqual(classroom.student_count(), 2)

        # Remove a student
        classroom.students.remove(self.student1)
        self.assertEqual(classroom.student_count(), 1)

    def test_invalid_teacher_role(self):
        """Test validation when assigning non-teacher as teacher"""
        student = User.objects.create_user(
            username="student_fake_teacher", password="pass", role=User.Role.STUDENT
        )
        classroom = Classroom(name="Science", teacher=student)
        with self.assertRaises(ValidationError) as context:
            classroom.clean()
        self.assertIn("teacher role", str(context.exception))

    def test_teacher_limit_choices(self):
        """Test that teacher field limits choices to teachers only"""
        classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        # This tests the limit_choices_to constraint at the model level
        self.assertEqual(classroom.teacher.role, User.Role.TEACHER)

    def test_students_limit_choices(self):
        """Test that students field limits choices to students only"""
        classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        classroom.students.add(self.student1)
        for student in classroom.students.all():
            self.assertEqual(student.role, User.Role.STUDENT)

    def test_classroom_related_names(self):
        """Test reverse relationships work correctly"""
        classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        classroom.students.add(self.student1)

        # Test teacher's reverse relationship
        self.assertIn(classroom, self.teacher.classrooms.all())

        # Test student's reverse relationship
        self.assertIn(classroom, self.student1.classes.all())


class QuizModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)

    def test_create_quiz(self):
        """Test basic quiz creation with default values"""
        quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)

        self.assertEqual(quiz.title, "Quiz 1")
        self.assertEqual(quiz.classroom, self.classroom)
        self.assertTrue(quiz.is_active)
        self.assertEqual(quiz.allowed_attempts, 1)
        self.assertIsNone(quiz.deadline)
        self.assertIsNotNone(quiz.created_at)
        self.assertEqual(quiz.question_count(), 0)

    def test_quiz_str_method(self):
        """Test quiz string representation"""
        quiz = Quiz.objects.create(title="Advanced Math Quiz", classroom=self.classroom)
        expected_str = f"{quiz.id}. Advanced Math Quiz"
        self.assertEqual(str(quiz), expected_str)

    def test_quiz_with_deadline(self):
        """Test creating quiz with deadline"""
        deadline = timezone.now() + timezone.timedelta(days=7)
        quiz = Quiz.objects.create(
            title="Timed Quiz", classroom=self.classroom, deadline=deadline
        )
        self.assertEqual(quiz.deadline, deadline)

    def test_quiz_inactive(self):
        """Test creating inactive quiz"""
        quiz = Quiz.objects.create(
            title="Inactive Quiz", classroom=self.classroom, is_active=False
        )
        self.assertFalse(quiz.is_active)

    def test_quiz_multiple_attempts(self):
        """Test quiz with multiple allowed attempts"""
        quiz = Quiz.objects.create(
            title="Multi-attempt Quiz", classroom=self.classroom, allowed_attempts=3
        )
        self.assertEqual(quiz.allowed_attempts, 3)

    def test_question_count_method(self):
        """Test question count method"""
        quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)

        # No questions initially
        self.assertEqual(quiz.question_count(), 0)

        # Add questions and test count
        Question.objects.create(quiz=quiz, text="Question 1")
        self.assertEqual(quiz.question_count(), 1)

        Question.objects.create(quiz=quiz, text="Question 2")
        self.assertEqual(quiz.question_count(), 2)

    def test_allowed_attempts_validation(self):
        """Test validation for allowed_attempts field"""
        quiz = Quiz(
            title="Invalid Quiz",
            classroom=self.classroom,
            allowed_attempts=0,
        )
        with self.assertRaises(ValidationError) as context:
            quiz.clean()
        self.assertIn("at least 1", str(context.exception))

    def test_negative_allowed_attempts_validation(self):
        """Test validation for negative allowed_attempts"""
        quiz = Quiz(
            title="Invalid Quiz",
            classroom=self.classroom,
            allowed_attempts=-1,
        )
        with self.assertRaises(ValidationError):
            quiz.clean()

    def test_quiz_classroom_relationship(self):
        """Test quiz-classroom relationship"""
        quiz = Quiz.objects.create(title="Test Quiz", classroom=self.classroom)
        self.assertIn(quiz, self.classroom.quizzes.all())


class QuestionModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)

    def test_create_question_with_auto_order(self):
        """Test question creation with automatic ordering"""
        q1 = Question.objects.create(quiz=self.quiz, text="Question 1")
        q2 = Question.objects.create(quiz=self.quiz, text="Question 2")
        q3 = Question.objects.create(quiz=self.quiz, text="Question 3")

        self.assertEqual(q1.order, 1)
        self.assertEqual(q2.order, 2)
        self.assertEqual(q3.order, 3)

    def test_create_question_with_manual_order(self):
        """Test question creation with manually specified order"""
        q1 = Question.objects.create(quiz=self.quiz, text="Question 1", order=5)
        q2 = Question.objects.create(quiz=self.quiz, text="Question 2")  # Should be 6

        self.assertEqual(q1.order, 5)
        self.assertEqual(q2.order, 6)

    def test_question_str_method(self):
        """Test question string representation"""
        question = Question.objects.create(
            quiz=self.quiz,
            text="What is the capital of France? This is a very long question text that should be truncated.",
        )
        expected_str = (
            f"{question.id}. What is the capital of France? This is a very long"
        )
        self.assertEqual(str(question), expected_str)

    def test_question_default_values(self):
        """Test question default field values"""
        question = Question.objects.create(quiz=self.quiz, text="Test question")

        self.assertFalse(question.has_multiple_answers)
        self.assertFalse(question.is_written)
        self.assertIsNone(question.time_limit)

    def test_question_with_all_fields(self):
        """Test question with all fields specified"""
        question = Question.objects.create(
            quiz=self.quiz,
            text="Complex question",
            order=10,
            has_multiple_answers=True,
            is_written=True,
            time_limit=120,
        )

        self.assertEqual(question.text, "Complex question")
        self.assertEqual(question.order, 10)
        self.assertTrue(question.has_multiple_answers)
        self.assertTrue(question.is_written)
        self.assertEqual(question.time_limit, 120)

    def test_get_correct_answers_method(self):
        """Test getting correct answers for a question"""
        question = Question.objects.create(quiz=self.quiz, text="Test question")

        # Create answers
        a1 = Answer.objects.create(question=question, text="Correct 1", is_correct=True)
        a2 = Answer.objects.create(question=question, text="Wrong 1", is_correct=False)
        a3 = Answer.objects.create(question=question, text="Correct 2", is_correct=True)
        a4 = Answer.objects.create(question=question, text="Wrong 2", is_correct=False)

        correct_answers = question.get_correct_answers()

        self.assertEqual(correct_answers.count(), 2)
        self.assertIn(a1, correct_answers)
        self.assertIn(a3, correct_answers)
        self.assertNotIn(a2, correct_answers)
        self.assertNotIn(a4, correct_answers)

    def test_get_correct_answers_empty(self):
        """Test getting correct answers when none exist"""
        question = Question.objects.create(quiz=self.quiz, text="Test question")

        # Create only wrong answers
        Answer.objects.create(question=question, text="Wrong 1", is_correct=False)
        Answer.objects.create(question=question, text="Wrong 2", is_correct=False)

        correct_answers = question.get_correct_answers()
        self.assertEqual(correct_answers.count(), 0)

    def test_question_quiz_relationship(self):
        """Test question-quiz relationship"""
        question = Question.objects.create(quiz=self.quiz, text="Test question")
        self.assertIn(question, self.quiz.questions.all())

    def test_order_assignment_across_multiple_quizzes(self):
        """Test that order assignment is independent for different quizzes"""
        quiz2 = Quiz.objects.create(title="Quiz 2", classroom=self.classroom)

        # Create questions in first quiz
        q1_quiz1 = Question.objects.create(quiz=self.quiz, text="Q1 Quiz1")
        q2_quiz1 = Question.objects.create(quiz=self.quiz, text="Q2 Quiz1")

        # Create questions in second quiz
        q1_quiz2 = Question.objects.create(quiz=quiz2, text="Q1 Quiz2")
        q2_quiz2 = Question.objects.create(quiz=quiz2, text="Q2 Quiz2")

        # Each quiz should have independent ordering
        self.assertEqual(q1_quiz1.order, 1)
        self.assertEqual(q2_quiz1.order, 2)
        self.assertEqual(q1_quiz2.order, 1)
        self.assertEqual(q2_quiz2.order, 2)


class AnswerModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)
        self.quiz = Quiz.objects.create(title="Quiz 1", classroom=self.classroom)
        self.question = Question.objects.create(quiz=self.quiz, text="Test Question")

    def test_create_answer_default_values(self):
        """Test answer creation with default values"""
        answer = Answer.objects.create(question=self.question, text="Test answer")

        self.assertEqual(answer.text, "Test answer")
        self.assertFalse(answer.is_correct)
        self.assertEqual(answer.question, self.question)

    def test_create_correct_answer(self):
        """Test creating a correct answer"""
        answer = Answer.objects.create(
            question=self.question, text="Correct answer", is_correct=True
        )
        self.assertTrue(answer.is_correct)

    def test_answer_str_method(self):
        """Test answer string representation"""
        answer = Answer.objects.create(
            question=self.question,
            text="This is a very long answer text that should be truncated in the string representation",
        )
        expected_str = (
            f"{answer.id}. This is a very long answer text that should be tru"
        )
        self.assertEqual(str(answer), expected_str)

    def test_text_stripping_on_save(self):
        """Test that answer text is stripped of whitespace on save"""
        answer = Answer.objects.create(
            question=self.question, text="  Answer with spaces  "
        )
        self.assertEqual(answer.text, "Answer with spaces")

    def test_empty_text_handling(self):
        """Test handling of empty text"""
        answer = Answer.objects.create(question=self.question, text="")
        self.assertEqual(answer.text, "")

    def test_none_text_handling(self):
        """Test handling when text is None"""
        answer = Answer(question=self.question, text=None)
        # Should raise IntegrityError due to NOT NULL constraint
        with self.assertRaises(IntegrityError):
            answer.save()

    def test_unique_answer_per_question_constraint(self):
        """Test unique constraint for answer text per question"""
        Answer.objects.create(question=self.question, text="Duplicate answer")

        with self.assertRaises(IntegrityError):
            Answer.objects.create(question=self.question, text="Duplicate answer")

    def test_same_answer_text_different_questions(self):
        """Test same answer text is allowed for different questions"""
        question2 = Question.objects.create(quiz=self.quiz, text="Another question")

        answer1 = Answer.objects.create(question=self.question, text="Same text")
        answer2 = Answer.objects.create(question=question2, text="Same text")

        self.assertEqual(answer1.text, answer2.text)
        self.assertNotEqual(answer1.question, answer2.question)

    def test_case_sensitive_uniqueness(self):
        """Test that uniqueness constraint is case sensitive"""
        Answer.objects.create(question=self.question, text="Answer")
        # this should work as it's different case, (should it bro?) note: change in case model change
        answer2 = Answer.objects.create(question=self.question, text="answer")
        self.assertEqual(answer2.text, "answer")

    def test_answer_question_relationship(self):
        """Test answer-question relationship"""
        answer = Answer.objects.create(question=self.question, text="Test")
        self.assertIn(answer, self.question.answers.all())

    def test_multiple_correct_answers(self):
        """Test that multiple answers can be correct for one question"""
        answer1 = Answer.objects.create(
            question=self.question, text="Correct 1", is_correct=True
        )
        answer2 = Answer.objects.create(
            question=self.question, text="Correct 2", is_correct=True
        )

        correct_answers = self.question.get_correct_answers()
        self.assertEqual(correct_answers.count(), 2)
        self.assertIn(answer1, correct_answers)
        self.assertIn(answer2, correct_answers)


class StudentQuizAttemptModelTest(TestCase):
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

    def test_create_quiz_attempt(self):
        """Test basic quiz attempt creation"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.assertEqual(attempt.student, self.student)
        self.assertEqual(attempt.quiz, self.quiz)
        self.assertIsNotNone(attempt.started_at)
        self.assertIsNone(attempt.completed_at)
        self.assertIsNone(attempt.score)

    def test_quiz_attempt_str_method(self):
        """Test quiz attempt string representation"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )
        expected_str = f"attempt #{attempt.id}"
        self.assertEqual(str(attempt), expected_str)

    def test_get_next_question_first_question(self):
        """Test getting the first question in a new attempt"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        next_question = attempt.get_next_question()
        self.assertEqual(next_question, self.question1)  # Should be first by order

    def test_get_next_question_after_attempt(self):
        """Test getting next question after answering some questions"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        # Create a completed question attempt for first question
        question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=attempt, question=self.question1
        )
        question_attempt.submitted_at = timezone.now()
        question_attempt.save()

        # Next question should be question2
        next_question = attempt.get_next_question()
        self.assertEqual(next_question, self.question2)

    def test_get_next_question_all_completed(self):
        """Test getting next question when all questions are completed"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        # Complete both questions
        for question in [self.question1, self.question2]:
            question_attempt = StudentQuestionAttempt.objects.create(
                quiz_attempt=attempt, question=question
            )
            question_attempt.submitted_at = timezone.now()
            question_attempt.save()

        # Should return None when all questions are completed
        next_question = attempt.get_next_question()
        self.assertIsNone(next_question)

    # NOTE: calculate_score method is commented out in the model
    # def test_calculate_score_empty_attempt(self):
    #     """Test calculating score for attempt with no answers"""
    #     attempt = StudentQuizAttempt.objects.create(
    #         student=self.student, quiz=self.quiz
    #     )

    #     attempt.calculate_score()

    #     self.assertEqual(attempt.score, Decimal("0.00"))
    #     self.assertIsNotNone(attempt.completed_at)

    # def test_calculate_score_all_correct(self):
    #     """Test calculating score with all correct answers"""
    #     attempt = StudentQuizAttempt.objects.create(
    #         student=self.student, quiz=self.quiz
    #     )

    #     # Add correct answers for both questions
    #     for question in [self.question1, self.question2]:
    #         Answer.objects.create(question=question, text="Correct", is_correct=True)
    #         question_attempt = StudentQuestionAttempt.objects.create(
    #             quiz_attempt=attempt, question=question
    #         )
    #         question_attempt.submitted_at = timezone.now()
    #         question_attempt.save()
    #         StudentAnswer.objects.create(
    #             question_attempt=question_attempt, text="Correct", is_correct=True
    #         )

    #     attempt.calculate_score()

    #     self.assertEqual(attempt.score, Decimal("100.00"))
    #     self.assertIsNotNone(attempt.completed_at)

    # def test_calculate_score_mixed_answers(self):
    #     """Test calculating score with mixed correct/incorrect answers"""
    #     attempt = StudentQuizAttempt.objects.create(
    #         student=self.student, quiz=self.quiz
    #     )

    #     # Add answers - one correct, one incorrect
    #     Answer.objects.create(question=self.question1, text="Correct", is_correct=True)
    #     Answer.objects.create(question=self.question2, text="Correct", is_correct=True)

    #     # First question - correct answer
    #     q1_attempt = StudentQuestionAttempt.objects.create(
    #         quiz_attempt=attempt, question=self.question1
    #     )
    #     q1_attempt.submitted_at = timezone.now()
    #     q1_attempt.save()
    #     StudentAnswer.objects.create(
    #         question_attempt=q1_attempt, text="Correct", is_correct=True
    #     )

    #     # Second question - incorrect answer
    #     q2_attempt = StudentQuestionAttempt.objects.create(
    #         quiz_attempt=attempt, question=self.question2
    #     )
    #     q2_attempt.submitted_at = timezone.now()
    #     q2_attempt.save()
    #     StudentAnswer.objects.create(
    #         question_attempt=q2_attempt, text="Wrong", is_correct=False
    #     )

    #     attempt.calculate_score()

    #     self.assertEqual(attempt.score, Decimal("50.00"))

    def test_invalid_student_role_validation(self):
        """Test validation when non-student attempts quiz"""
        teacher_attempt = StudentQuizAttempt(student=self.teacher, quiz=self.quiz)

        with self.assertRaises(ValidationError) as context:
            teacher_attempt.clean()
        self.assertIn("student role", str(context.exception))

    def test_student_quiz_relationship(self):
        """Test relationship with student and quiz"""
        attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.assertIn(attempt, self.student.quiz_attempts.all())

    def test_multiple_attempts_same_quiz(self):
        """Test that same student can have multiple attempts for same quiz"""
        attempt1 = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )
        attempt2 = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

        self.assertNotEqual(attempt1.id, attempt2.id)
        self.assertEqual(attempt1.student, attempt2.student)
        self.assertEqual(attempt1.quiz, attempt2.quiz)


class StudentQuestionAttemptModelTest(TestCase):
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
        self.question = Question.objects.create(quiz=self.quiz, text="Question 1")
        self.quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )

    def test_create_question_attempt(self):
        """Test basic question attempt creation"""
        attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )

        self.assertEqual(attempt.quiz_attempt, self.quiz_attempt)
        self.assertEqual(attempt.question, self.question)
        self.assertIsNotNone(attempt.started_at)
        self.assertIsNone(attempt.submitted_at)

    def test_question_attempt_str_method(self):
        """Test question attempt string representation"""
        attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )
        expected_str = f"{attempt.id}. {self.student} - {self.question.text[:50]}"
        self.assertEqual(str(attempt), expected_str)

    def test_submitted_question_attempt(self):
        """Test question attempt with submission time"""
        attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )

        submit_time = timezone.now()
        attempt.submitted_at = submit_time
        attempt.save()

        self.assertEqual(attempt.submitted_at, submit_time)

    def test_unique_question_attempt_constraint(self):
        """Test unique constraint for question attempt per quiz attempt"""
        StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )

        with self.assertRaises(IntegrityError):
            StudentQuestionAttempt.objects.create(
                quiz_attempt=self.quiz_attempt, question=self.question
            )

    def test_same_question_different_attempts(self):
        """Test same question can be attempted by different quiz attempts"""
        student2 = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        quiz_attempt2 = StudentQuizAttempt.objects.create(
            student=student2, quiz=self.quiz
        )

        attempt1 = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )
        attempt2 = StudentQuestionAttempt.objects.create(
            quiz_attempt=quiz_attempt2, question=self.question
        )

        self.assertNotEqual(attempt1.id, attempt2.id)
        self.assertEqual(attempt1.question, attempt2.question)

    def test_invalid_question_quiz_validation(self):
        """Test validation when question doesn't belong to quiz"""
        other_classroom = Classroom.objects.create(name="Science", teacher=self.teacher)
        other_quiz = Quiz.objects.create(title="Quiz 2", classroom=other_classroom)
        other_question = Question.objects.create(quiz=other_quiz, text="Other question")

        attempt = StudentQuestionAttempt(
            quiz_attempt=self.quiz_attempt, question=other_question
        )

        with self.assertRaises(ValidationError) as context:
            attempt.clean()
        self.assertIn("does not belong to the quiz", str(context.exception))

    def test_valid_question_quiz_validation(self):
        """Test validation passes when question belongs to quiz"""
        attempt = StudentQuestionAttempt(
            quiz_attempt=self.quiz_attempt, question=self.question
        )

        # Should not raise validation error
        try:
            attempt.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_question_attempt_relationship(self):
        """Test relationships work correctly"""
        attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )

        self.assertIn(attempt, self.quiz_attempt.question_attempts.all())

    def test_multiple_questions_same_attempt(self):
        """Test multiple questions can be attempted in same quiz attempt"""
        question2 = Question.objects.create(quiz=self.quiz, text="Question 2")

        attempt1 = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )
        attempt2 = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=question2
        )

        self.assertEqual(self.quiz_attempt.question_attempts.count(), 2)
        self.assertIn(attempt1, self.quiz_attempt.question_attempts.all())
        self.assertIn(attempt2, self.quiz_attempt.question_attempts.all())


class StudentAnswerModelTest(TestCase):
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
        self.question = Question.objects.create(
            quiz=self.quiz, text="What is 2+2?", time_limit=60
        )
        self.quiz_attempt = StudentQuizAttempt.objects.create(
            student=self.student, quiz=self.quiz
        )
        self.question_attempt = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=self.question
        )

    def test_create_student_answer(self):
        """Test basic student answer creation"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="4"
        )

        self.assertEqual(answer.question_attempt, self.question_attempt)
        self.assertEqual(answer.text, "4")
        self.assertFalse(answer.is_correct)  # will be calculated

    def test_student_answer_str_method(self):
        """Test student answer string representation"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        # Add a correct answer to the question so the student answer will be correct
        Answer.objects.create(
            question=self.question, text="Test answer", is_correct=True
        )

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="Test answer", is_correct=True
        )

        expected_str = (
            f"{answer.id}. {self.student} - What is 2+2?: Test answer (Correct)"
        )
        self.assertEqual(str(answer), expected_str)

    def test_student_answer_str_method_incorrect(self):
        """Test student answer string representation for incorrect answer"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt,
            text="Wrong answer",
            is_correct=False,
        )

        expected_str = (
            f"{answer.id}. {self.student} - What is 2+2?: Wrong answer (Incorrect)"
        )
        self.assertEqual(str(answer), expected_str)

    def test_text_stripping_on_save(self):
        """Test that answer text is stripped on save"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="  4  "
        )

        self.assertEqual(answer.text, "4")

    def test_correctness_calculation_correct_answer(self):
        """Test correctness calculation for correct answer"""
        # Add correct answer to question
        Answer.objects.create(question=self.question, text="4", is_correct=True)

        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="4"
        )

        self.assertTrue(answer.is_correct)

    def test_correctness_calculation_incorrect_answer(self):
        """Test correctness calculation for incorrect answer"""
        # Add correct answer to question
        Answer.objects.create(question=self.question, text="4", is_correct=True)

        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="5"
        )

        self.assertFalse(answer.is_correct)

    def test_correctness_case_insensitive(self):
        """Test that correctness check is case insensitive"""
        Answer.objects.create(question=self.question, text="Paris", is_correct=True)

        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="paris"
        )

        self.assertTrue(answer.is_correct)

    def test_time_limit_exceeded(self):
        """Test answer is marked incorrect when time limit exceeded"""
        Answer.objects.create(question=self.question, text="4", is_correct=True)

        # Set submitted_at to exceed time limit (60 seconds + buffer)
        start_time = timezone.now() - timedelta(seconds=65)
        self.question_attempt.started_at = start_time
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="4"
        )

        self.assertFalse(answer.is_correct)

    def test_time_limit_within_bounds(self):
        """Test answer is correct when within time limit"""
        Answer.objects.create(question=self.question, text="4", is_correct=True)

        # Set submitted_at within time limit
        start_time = timezone.now() - timedelta(seconds=30)
        self.question_attempt.started_at = start_time
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="4"
        )

        self.assertTrue(answer.is_correct)

    def test_no_time_limit_question(self):
        """Test answer correctness for question without time limit"""
        question_no_limit = Question.objects.create(
            quiz=self.quiz, text="No time limit", time_limit=None
        )
        question_attempt_no_limit = StudentQuestionAttempt.objects.create(
            quiz_attempt=self.quiz_attempt, question=question_no_limit
        )
        question_attempt_no_limit.submitted_at = timezone.now()
        question_attempt_no_limit.save()

        Answer.objects.create(
            question=question_no_limit, text="Answer", is_correct=True
        )

        answer = StudentAnswer.objects.create(
            question_attempt=question_attempt_no_limit, text="Answer"
        )

        self.assertTrue(answer.is_correct)

    def test_unique_student_answer_constraint(self):
        """Test unique constraint for student answer per question attempt"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="First answer"
        )

        with self.assertRaises(IntegrityError):
            StudentAnswer.objects.create(
                question_attempt=self.question_attempt, text="First answer"
            )

    def test_different_answers_same_question_attempt(self):
        """Test different answers can be created for same question attempt (different text)"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer1 = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="Answer 1"
        )
        answer2 = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="Answer 2"
        )

        self.assertNotEqual(answer1.text, answer2.text)
        self.assertEqual(answer1.question_attempt, answer2.question_attempt)

    def test_clean_method_no_question_attempt_submitted(self):
        """Test clean method validation when question attempt not submitted"""
        answer = StudentAnswer(
            question_attempt=self.question_attempt, text="Test answer"
        )

        with self.assertRaises(ValidationError) as context:
            answer.clean()
        self.assertIn(
            "before the question attempt is submitted", str(context.exception)
        )

    def test_clean_method_question_attempt_submitted(self):
        """Test clean method passes when question attempt is submitted"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer(
            question_attempt=self.question_attempt, text="Test answer"
        )

        # Should not raise validation error
        try:
            answer.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly")

    def test_multiple_correct_answers_matching(self):
        """Test when multiple correct answers exist and student provides one"""
        Answer.objects.create(question=self.question, text="4", is_correct=True)
        Answer.objects.create(question=self.question, text="four", is_correct=True)

        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="four"
        )

        self.assertTrue(answer.is_correct)

    def test_student_answer_relationship(self):
        """Test student answer relationship with question attempt"""
        self.question_attempt.submitted_at = timezone.now()
        self.question_attempt.save()

        answer = StudentAnswer.objects.create(
            question_attempt=self.question_attempt, text="Test"
        )

        self.assertIn(answer, self.question_attempt.student_answers.all())


class EnrollmentCodeModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(name="Math", teacher=self.teacher)

    def test_create_enrollment_code(self):
        """Test basic enrollment code creation"""
        code = EnrollmentCode.objects.create(code="TEST1234", classroom=self.classroom)

        self.assertEqual(code.code, "TEST1234")
        self.assertEqual(code.classroom, self.classroom)
        self.assertTrue(code.is_active)

    def test_enrollment_code_str_method(self):
        """Test enrollment code string representation"""
        code = EnrollmentCode.objects.create(code="SAMPLE123", classroom=self.classroom)

        expected_str = f"SAMPLE123 - {self.classroom.id}. {self.classroom.name}"
        self.assertEqual(str(code), expected_str)

    def test_enrollment_code_default_active(self):
        """Test enrollment code is active by default"""
        code = EnrollmentCode.objects.create(code="ACTIVE123", classroom=self.classroom)

        self.assertTrue(code.is_active)

    def test_enrollment_code_inactive(self):
        """Test creating inactive enrollment code"""
        code = EnrollmentCode.objects.create(
            code="INACTIVE1", classroom=self.classroom, is_active=False
        )

        self.assertFalse(code.is_active)

    def test_unique_code_constraint(self):
        """Test unique constraint for enrollment codes"""
        EnrollmentCode.objects.create(code="DUPLICATE", classroom=self.classroom)

        classroom2 = Classroom.objects.create(name="Science", teacher=self.teacher)

        with self.assertRaises(IntegrityError):
            EnrollmentCode.objects.create(code="DUPLICATE", classroom=classroom2)

    def test_generate_code_method(self):
        """Test static generate_code method"""
        code = EnrollmentCode.generate_code()

        # Default length is 8
        self.assertEqual(len(code), 8)

        # Should contain only uppercase letters and digits
        self.assertTrue(all(c.isupper() or c.isdigit() for c in code))

    def test_generate_code_custom_length(self):
        """Test generate_code with custom length"""
        code = EnrollmentCode.generate_code(length=12)

        self.assertEqual(len(code), 12)
        self.assertTrue(all(c.isupper() or c.isdigit() for c in code))

    def test_generate_code_uniqueness(self):
        """Test that generate_code produces different codes (probabilistically)"""
        codes = [EnrollmentCode.generate_code() for _ in range(10)]
        unique_codes = set(codes)

        # With 8 character codes, we should get all unique codes in 10 attempts
        self.assertEqual(len(unique_codes), 10)

    def test_generate_for_class_new_code(self):
        """Test generate_for_class method for new classroom"""
        enrollment_code = EnrollmentCode.generate_for_class(self.classroom)

        self.assertEqual(enrollment_code.classroom, self.classroom)
        self.assertEqual(len(enrollment_code.code), 8)
        self.assertTrue(enrollment_code.is_active)

    def test_generate_for_class_existing_code(self):
        """Test generate_for_class method updates existing code"""
        initial_code = EnrollmentCode.objects.create(
            code="OLD12345", classroom=self.classroom, is_active=False
        )

        new_enrollment_code = EnrollmentCode.generate_for_class(self.classroom)

        self.assertEqual(new_enrollment_code.id, initial_code.id)
        self.assertNotEqual(new_enrollment_code.code, "OLD12345")
        self.assertEqual(len(new_enrollment_code.code), 8)

        # NOTE: is_active is not updated by generate_for_class, only the code,
        # p.s it updates (is_active) at put request to renew the code (may be i should move it to model method TODO)
        self.assertFalse(new_enrollment_code.is_active)  # Remains as originally set

    def test_generate_for_class_collision_handling(self):
        """Test generate_for_class handles code collisions"""
        # Create a code that might collide
        existing_code = EnrollmentCode.objects.create(
            code="EXIST123", classroom=self.classroom
        )

        # Mock the generate_code method to return existing code first, then unique
        original_generate = EnrollmentCode.generate_code
        call_count = 0

        def mock_generate(length=8):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "EXIST123"  # Collision on first call
            return original_generate(length)

        # Temporarily replace the method
        EnrollmentCode.generate_code = staticmethod(mock_generate)

        try:
            classroom2 = Classroom.objects.create(name="Science", teacher=self.teacher)
            new_code = EnrollmentCode.generate_for_class(classroom2)

            # Should have generated a different code due to collision
            self.assertNotEqual(new_code.code, "EXIST123")
            self.assertEqual(new_code.classroom, classroom2)
            self.assertTrue(
                call_count > 1
            )  # Should have called generate multiple times

        finally:
            # Restore original method
            EnrollmentCode.generate_code = staticmethod(original_generate)

    def test_classroom_enrollment_codes_relationship(self):
        """Test reverse relationship from classroom to enrollment codes"""
        code1 = EnrollmentCode.objects.create(code="CODE1", classroom=self.classroom)
        code2 = EnrollmentCode.objects.create(code="CODE2", classroom=self.classroom)

        classroom_codes = self.classroom.enrollment_codes.all()

        self.assertIn(code1, classroom_codes)
        self.assertIn(code2, classroom_codes)
        self.assertEqual(classroom_codes.count(), 2)

    def test_enrollment_code_cascade_delete(self):
        """Test enrollment code is deleted when classroom is deleted"""
        code = EnrollmentCode.objects.create(code="DELETE1", classroom=self.classroom)
        code_id = code.id

        # Delete classroom
        self.classroom.delete()

        # Enrollment code should be deleted too
        self.assertFalse(EnrollmentCode.objects.filter(id=code_id).exists())

    def test_generate_for_class_return_value(self):
        """Test that generate_for_class returns the enrollment code object"""
        enrollment_code = EnrollmentCode.generate_for_class(self.classroom)

        self.assertIsInstance(enrollment_code, EnrollmentCode)
        self.assertEqual(
            EnrollmentCode.objects.filter(classroom=self.classroom).count(), 1
        )

        # Should return the same object on subsequent calls (update_or_create)
        enrollment_code2 = EnrollmentCode.generate_for_class(self.classroom)
        self.assertEqual(enrollment_code.id, enrollment_code2.id)
