"""
SQLAlchemy ORM models for the intelligent learning system.

This module provides all database models for managing users, courses, lessons,
quizzes, and learning progress tracking.

Models:
    - User: User accounts and profile information
    - Course: Course content and metadata
    - UserCourse: User course enrollment and progress
    - Lesson: Individual lessons within courses
    - Concept: Learning objectives/concepts within lessons
    - QuizSession: Quiz session instances with conversation history
    - QuizAnswer: Individual quiz answers with evaluation
    - QuizSummary: Post-quiz summaries with mastery information
    - OnboardingState: Temporary state during onboarding flow

Example:
    from app.models import User, Course, QuizSession
    from app.database import SessionLocal

    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == "12345").first()
    courses = db.query(Course).all()
"""

from app.models.user import User
from app.models.course import Course
from app.models.user_course import UserCourse
from app.models.lesson import Lesson
from app.models.concept import Concept
from app.models.quiz_session import QuizSession
from app.models.quiz_answer import QuizAnswer
from app.models.quiz_summary import QuizSummary
from app.models.onboarding_state import OnboardingState

__all__ = [
    "User",
    "Course",
    "UserCourse",
    "Lesson",
    "Concept",
    "QuizSession",
    "QuizAnswer",
    "QuizSummary",
    "OnboardingState",
]
