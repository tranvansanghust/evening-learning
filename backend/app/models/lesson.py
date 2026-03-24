"""
Lesson model for the learning system.

Represents individual lessons within a course.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Lesson(Base):
    """
    Lesson model for managing course content.

    Represents a single lesson within a course, containing educational content and metadata.

    Attributes:
        lesson_id: Primary key, auto-incrementing integer
        course_id: Foreign key to courses table
        sequence_number: Order of lesson within the course (1-indexed)
        title: Lesson title
        description: Lesson description or summary
        content_url: URL to lesson content (for frontend to render)
        estimated_duration_minutes: Estimated time to complete lesson in minutes

    Relationships:
        course: Reference to the parent Course object
        concepts: All concepts taught in this lesson
        quiz_sessions: All quiz sessions for this lesson

    Note:
        - sequence_number should be unique per course and sequential
        - content_url can be a markdown file URL, video link, or external resource
    """

    __tablename__ = "lessons"

    lesson_id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content_url = Column(String(500), nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)

    # Relationships
    course = relationship(
        "Course",
        back_populates="lessons",
        lazy="joined"
    )
    concepts = relationship(
        "Concept",
        back_populates="lesson",
        cascade="all, delete-orphan",
        lazy="select"
    )
    quiz_sessions = relationship(
        "QuizSession",
        back_populates="lesson",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("idx_lesson_course_id", "course_id"),
        Index("idx_lesson_sequence", "course_id", "sequence_number"),
    )

    def __repr__(self) -> str:
        return f"<Lesson(lesson_id={self.lesson_id}, course_id={self.course_id}, sequence_number={self.sequence_number}, title={self.title})>"
