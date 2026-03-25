"""
QuizAnswer model for the learning system.

Represents individual answers submitted during a quiz session.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class QuizAnswer(Base):
    """
    QuizAnswer model for storing individual quiz responses.

    Represents a single question-answer pair within a quiz session,
    including correctness evaluation and engagement level.

    Attributes:
        answer_id: Primary key, auto-incrementing integer
        session_id: Foreign key to quiz_sessions table
        concept_id: Foreign key to concepts table
        question: The quiz question asked to the user
        user_answer: The user's response to the question
        is_correct: Boolean indicating if the answer was correct
        engagement_level: Engagement level ('low', 'medium', 'high')
        created_at: Timestamp when answer was submitted (UTC)

    Relationships:
        session: Reference to the parent QuizSession object
        concept: Reference to the Concept being tested
        user: Reference to the User through quiz_session

    Note:
        - One answer_id per question within a session
        - engagement_level is determined by LLM based on answer depth and quality
        - is_correct is determined by LLM evaluation
    """

    __tablename__ = "quiz_answers"

    answer_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.session_id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.concept_id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    engagement_level = Column(String(20), nullable=True)  # 'low', 'medium', 'high'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship(
        "QuizSession",
        back_populates="quiz_answers",
        lazy="joined"
    )
    concept = relationship(
        "Concept",
        back_populates="quiz_answers",
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index("idx_quiz_answer_session_id", "session_id"),
        Index("idx_quiz_answer_concept_id", "concept_id"),
        Index("idx_quiz_answer_is_correct", "is_correct"),
    )

    def __repr__(self) -> str:
        return f"<QuizAnswer(answer_id={self.answer_id}, session_id={self.session_id}, concept_id={self.concept_id}, is_correct={self.is_correct})>"
