"""
Concept model for the learning system.

Represents key concepts taught within a lesson.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Concept(Base):
    """
    Concept model for managing learning objectives within lessons.

    Represents a key concept or learning objective within a lesson.
    Used for tracking student understanding of specific topics.

    Attributes:
        concept_id: Primary key, auto-incrementing integer
        lesson_id: Foreign key to lessons table
        name: Concept name (e.g., "Variables", "Functions")
        description: Detailed explanation of the concept

    Relationships:
        lesson: Reference to the parent Lesson object
        quiz_answers: All quiz answers related to this concept

    Note:
        - Each lesson can have multiple concepts
        - Concepts are the basis for quiz questions and mastery tracking
    """

    __tablename__ = "concepts"

    concept_id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, ForeignKey("lessons.lesson_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    lesson = relationship(
        "Lesson",
        back_populates="concepts",
        lazy="joined"
    )
    quiz_answers = relationship(
        "QuizAnswer",
        back_populates="concept",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("idx_concept_lesson_id", "lesson_id"),
    )

    def __repr__(self) -> str:
        return f"<Concept(concept_id={self.concept_id}, lesson_id={self.lesson_id}, name={self.name})>"
