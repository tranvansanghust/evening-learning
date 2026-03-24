"""
QuizSession model for the learning system.

Represents a single quiz/oral-test session for a user on a lesson.
Stores conversation history and session metadata.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class QuizSession(Base):
    """
    QuizSession model for managing interactive quiz sessions.

    Represents a single quiz session where a user is tested on concepts from a lesson.
    Stores the complete conversation history between user and AI tutor.

    Attributes:
        session_id: Primary key, auto-incrementing integer
        user_id: Foreign key to users table
        lesson_id: Foreign key to lessons table
        status: Session status ('active' or 'completed')
        messages: JSON array storing conversation history
                  Format: [{"role": "bot"|"user", "content": "..."}, ...]
        started_at: Session start time (UTC)
        completed_at: Session completion time, if applicable (UTC)

    Relationships:
        user: Reference to the User object
        lesson: Reference to the Lesson object
        quiz_answers: All individual answers submitted in this session
        quiz_summary: Post-quiz summary with mastery information

    Note:
        - messages is a JSON array that grows as the quiz progresses
        - status should be 'completed' when the quiz ends
        - completed_at is NULL while session is active
    """

    __tablename__ = "quiz_sessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.lesson_id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="active")  # 'active', 'completed'
    messages = Column(JSON, nullable=True)  # Conversation history as JSON array
    started_at = Column(DateTime(timezone=True), server_default=func.utc_timestamp(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship(
        "User",
        back_populates="quiz_sessions",
        lazy="joined"
    )
    lesson = relationship(
        "Lesson",
        back_populates="quiz_sessions",
        lazy="joined"
    )
    quiz_answers = relationship(
        "QuizAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select"
    )
    quiz_summary = relationship(
        "QuizSummary",
        back_populates="quiz_session",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index("idx_quiz_session_user_id", "user_id"),
        Index("idx_quiz_session_lesson_id", "lesson_id"),
        Index("idx_quiz_session_status", "status"),
        Index("idx_quiz_session_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<QuizSession(session_id={self.session_id}, user_id={self.user_id}, lesson_id={self.lesson_id}, status={self.status})>"
