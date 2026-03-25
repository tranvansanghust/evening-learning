"""
Onboarding state model for managing multi-step onboarding flow.

Represents temporary state during the user onboarding process,
including user information, assessment answers, and scheduling preferences.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class OnboardingState(Base):
    """
    OnboardingState model for tracking user onboarding progress.

    Represents the temporary state of a user going through the onboarding flow.
    This data is used to guide the user through multi-step questions and
    eventually create a personalized curriculum.

    Attributes:
        onboarding_id: Primary key, auto-incrementing integer
        user_id: Foreign key to users table
        current_step: Current step in onboarding flow (e.g., 'start', 'course_input', 'q1', 'q2', 'deadline', 'hours_per_day', 'reminder_time', 'completed')
        course_id: Foreign key to courses table (nullable, set after course selection)
        q1_answer: Answer to Q1 about building web apps (e.g., "never" or "yes")
        q2_answer: Answer to Q2 about HTML/CSS or frameworks (e.g., "no" or "yes")
        assessed_level: User's assessed level (0-3) based on assessment questions
        deadline: Target completion date for the course
        hours_per_day: Daily study hours the user can commit
        reminder_time: Preferred time for daily reminders (e.g., "09:00", "14:00")
        created_at: When this onboarding state was created (UTC)
        updated_at: Last update timestamp (UTC)
        expires_at: When this state expires if onboarding is not completed (UTC)

    Relationships:
        user: Reference to the User object
        course: Reference to the Course object (nullable)

    Note:
        - expires_at can be used to clean up incomplete onboarding states
        - current_step tracks user's position in the onboarding flow
        - This is temporary data and can be deleted after onboarding is completed
    """

    __tablename__ = "onboarding_states"

    onboarding_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True)
    current_step = Column(String(50), nullable=False, default="start")
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="SET NULL"), nullable=True)
    q1_answer = Column(String(50), nullable=True)  # "never" or "yes"
    q2_answer = Column(String(50), nullable=True)  # "no" or "yes"
    assessed_level = Column(Integer, nullable=True)  # 0-3
    deadline = Column(Date, nullable=True)
    hours_per_day = Column(Integer, nullable=True)
    reminder_time = Column(String(10), nullable=True)  # "HH:MM" format
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship(
        "User",
        lazy="select"
    )
    course = relationship(
        "Course",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("idx_onboarding_user_id", "user_id"),
        Index("idx_onboarding_current_step", "current_step"),
    )

    def __repr__(self) -> str:
        return f"<OnboardingState(onboarding_id={self.onboarding_id}, user_id={self.user_id}, current_step={self.current_step}, assessed_level={self.assessed_level})>"
