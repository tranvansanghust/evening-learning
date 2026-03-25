"""
UserCourse model for the learning system.

Represents the enrollment of a user in a course (many-to-many relationship with metadata).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserCourse(Base):
    """
    UserCourse model for tracking course enrollments and progress.

    Represents the enrollment relationship between users and courses, including progress tracking.

    Attributes:
        user_course_id: Primary key, auto-incrementing integer
        user_id: Foreign key to users table
        course_id: Foreign key to courses table
        status: Enrollment status ('PASS', 'FAIL', 'IN_PROGRESS')
        started_at: When user started the course (UTC)
        completed_at: When user completed the course, if applicable (UTC)

    Relationships:
        user: Reference to the User object
        course: Reference to the Course object
        quiz_summaries: All quiz summaries for this enrollment

    Note:
        - status transitions: IN_PROGRESS → PASS or IN_PROGRESS → FAIL
        - completed_at is nullable (NULL while IN_PROGRESS)
    """

    __tablename__ = "user_courses"

    user_course_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="IN_PROGRESS")  # PASS, FAIL, IN_PROGRESS
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship(
        "User",
        back_populates="user_courses",
        lazy="joined"
    )
    course = relationship(
        "Course",
        back_populates="user_courses",
        lazy="joined"
    )
    quiz_summaries = relationship(
        "QuizSummary",
        back_populates="user_course",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_course_user_id", "user_id"),
        Index("idx_user_course_course_id", "course_id"),
        Index("idx_user_course_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<UserCourse(user_course_id={self.user_course_id}, user_id={self.user_id}, course_id={self.course_id}, status={self.status})>"
