"""
Course model for the learning system.

Represents courses available in the system, including metadata and integration with external sources like Udemy.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Course(Base):
    """
    Course model for managing educational content.

    Attributes:
        course_id: Primary key, auto-incrementing integer
        name: Course title
        description: Detailed course description
        source: Source platform (e.g., 'udemy', 'internal')
        source_id: External ID from source platform (e.g., Udemy course ID)
        total_lessons: Total number of lessons in the course
        created_at: Course creation timestamp (UTC)

    Relationships:
        lessons: All lessons associated with this course
        user_courses: All user enrollments for this course

    Note:
        - source can be 'udemy', 'internal', or other platform names
        - source_id is nullable for internal courses without external source
    """

    __tablename__ = "courses"

    course_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, default="internal")  # 'udemy', 'internal', etc.
    source_id = Column(String(255), nullable=True)  # External ID from Udemy API or scraping
    total_lessons = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.utc_timestamp(), nullable=False)

    # Relationships
    lessons = relationship(
        "Lesson",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select"
    )
    user_courses = relationship(
        "UserCourse",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Indexes
    __table_args__ = (
        Index("idx_source_source_id", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Course(course_id={self.course_id}, name={self.name}, source={self.source}, total_lessons={self.total_lessons})>"
