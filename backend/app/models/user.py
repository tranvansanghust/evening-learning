"""
User model for the learning system.

Represents a user of the platform, including their Telegram ID, username, and learning level.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """
    User model for managing user accounts and metadata.

    Attributes:
        user_id: Primary key, auto-incrementing integer
        telegram_id: Unique Telegram user ID for bot integration
        username: User's display name
        level: Learning level (0-3, where 0 is beginner and 3 is advanced)
        created_at: Account creation timestamp (UTC)
        updated_at: Last update timestamp (UTC)

    Relationships:
        user_courses: Association between users and courses they're enrolled in
        quiz_sessions: All quiz sessions initiated by this user

    Note:
        - telegram_id must be unique to prevent duplicate accounts
        - level can be 0 (beginner), 1 (intermediate), 2 (advanced), or 3 (expert)
    """

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    level = Column(Integer, default=0, nullable=False)  # 0-3
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user_courses = relationship(
        "UserCourse",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="joined"
    )
    quiz_sessions = relationship(
        "QuizSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, telegram_id={self.telegram_id}, username={self.username}, level={self.level})>"
