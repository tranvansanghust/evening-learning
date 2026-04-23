"""
Progress tracking service for the learning system.

Provides methods to retrieve user learning progress, quiz summaries, and review data.
Used by progress router endpoints to expose progress tracking functionality.

Services:
    - ProgressService: Main service class with all progress-related methods
"""

import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import User, UserCourse, QuizSummary, Lesson, Concept, QuizSession
from app.schemas.progress import UserProgress, QuizSummaryPreview, ConceptDetail

logger = logging.getLogger(__name__)


class ProgressService:
    """
    Service for tracking and retrieving user learning progress.

    Provides methods to:
    - Get overall user progress (lessons completed, concepts mastered)
    - Get quiz summary previews for a user
    - Get detailed quiz summary information
    - Get quizzes filtered by topic
    """

    @staticmethod
    def get_user_progress(user_id: int, db_session: Session) -> UserProgress:
        """
        Get user's overall learning progress.

        Calculates:
        - Total lessons completed vs total lessons available
        - Total concepts mastered vs total concepts available

        Args:
            user_id: User ID to get progress for
            db_session: SQLAlchemy database session

        Returns:
            UserProgress: Object containing:
                - lessons_completed: Number of lessons started/completed
                - total_lessons: Total lessons available to user's current courses
                - concepts_mastered: Number of unique concepts mastered
                - total_concepts: Total unique concepts available

        Raises:
            ValueError: If user does not exist
        """
        # Verify user exists
        user = db_session.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            raise ValueError(f"User {user_id} not found")

        logger.info(f"Getting progress for user {user_id}")

        # Get all courses the user is enrolled in
        user_courses = db_session.query(UserCourse).filter(
            UserCourse.user_id == user_id
        ).all()

        if not user_courses:
            logger.info(f"User {user_id} has no course enrollments")
            return UserProgress(
                lessons_completed=0,
                total_lessons=0,
                concepts_mastered=0,
                total_concepts=0,
            )

        course_ids = [uc.course_id for uc in user_courses]

        # Count lessons completed (distinct lessons with a completed quiz session for this user)
        lessons_completed = (
            db_session.query(func.count(func.distinct(QuizSession.lesson_id)))
            .join(QuizSummary, QuizSummary.session_id == QuizSession.session_id)
            .join(UserCourse, UserCourse.user_course_id == QuizSummary.user_course_id)
            .filter(UserCourse.user_id == user_id)
            .scalar() or 0
        )

        # Simpler approach: count unique lessons with quiz summaries
        lessons_with_quizzes = (
            db_session.query(func.count(func.distinct(QuizSummary.session_id)))
            .join(UserCourse, UserCourse.user_course_id == QuizSummary.user_course_id)
            .filter(UserCourse.user_id == user_id)
            .scalar() or 0
        )

        # Total lessons available in user's courses
        total_lessons = (
            db_session.query(func.count(Lesson.lesson_id))
            .filter(Lesson.course_id.in_(course_ids))
            .scalar() or 0
        )

        # Total unique concepts mastered (from concepts_mastered in quiz summaries)
        concepts_mastered_count = 0
        all_mastered_concepts = set()

        quiz_summaries = (
            db_session.query(QuizSummary)
            .join(UserCourse, UserCourse.user_course_id == QuizSummary.user_course_id)
            .filter(UserCourse.user_id == user_id)
            .all()
        )

        for summary in quiz_summaries:
            if summary.concepts_mastered:
                # concepts_mastered is a JSON array of concept names
                if isinstance(summary.concepts_mastered, list):
                    all_mastered_concepts.update(summary.concepts_mastered)

        concepts_mastered_count = len(all_mastered_concepts)

        # Total concepts available in user's courses
        total_concepts = (
            db_session.query(func.count(Concept.concept_id))
            .join(Lesson, Lesson.lesson_id == Concept.lesson_id)
            .filter(Lesson.course_id.in_(course_ids))
            .scalar() or 0
        )

        logger.info(
            f"Progress for user {user_id}: {lessons_with_quizzes} lessons "
            f"(total: {total_lessons}), {concepts_mastered_count} concepts "
            f"(total: {total_concepts})"
        )

        return UserProgress(
            lessons_completed=lessons_with_quizzes,
            total_lessons=total_lessons,
            concepts_mastered=concepts_mastered_count,
            total_concepts=total_concepts,
        )

    @staticmethod
    def get_quiz_summaries(user_id: int, db_session: Session) -> List[QuizSummaryPreview]:
        """
        Get all quiz summary previews for a user.

        Returns brief information about each quiz summary:
        - Date taken
        - Lesson name
        - Count of mastered concepts
        - Count of weak concepts

        Args:
            user_id: User ID to get summaries for
            db_session: SQLAlchemy database session

        Returns:
            List[QuizSummaryPreview]: List of summary previews, sorted by date (newest first)

        Raises:
            ValueError: If user does not exist
        """
        # Verify user exists
        user = db_session.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            raise ValueError(f"User {user_id} not found")

        logger.info(f"Getting quiz summaries for user {user_id}")

        # Query all quiz summaries for this user via QuizSession
        summaries = (
            db_session.query(QuizSummary)
            .join(QuizSession, QuizSession.session_id == QuizSummary.session_id)
            .filter(QuizSession.user_id == user_id)
            .order_by(QuizSummary.created_at.desc())
            .all()
        )

        previews = []
        for summary in summaries:
            # Get lesson name from the quiz session's lesson
            lesson_name = "Unknown Lesson"
            if summary.quiz_session and summary.quiz_session.lesson:
                lesson_name = summary.quiz_session.lesson.title

            # Count mastered concepts
            concepts_mastered_count = 0
            if summary.concepts_mastered and isinstance(summary.concepts_mastered, list):
                concepts_mastered_count = len(summary.concepts_mastered)

            # Count weak concepts
            concepts_weak_count = 0
            if summary.concepts_weak and isinstance(summary.concepts_weak, list):
                concepts_weak_count = len(summary.concepts_weak)

            preview = QuizSummaryPreview(
                summary_id=summary.summary_id,
                date=summary.created_at,
                lesson_name=lesson_name,
                concepts_mastered_count=concepts_mastered_count,
                concepts_weak_count=concepts_weak_count,
            )
            previews.append(preview)

        logger.info(f"Found {len(previews)} quiz summaries for user {user_id}")
        return previews

    @staticmethod
    def get_quiz_summary_detail(
        user_id: int, summary_id: int, db_session: Session
    ) -> QuizSummary:
        """
        Get full quiz summary with all details.

        Returns complete information about a quiz summary including:
        - All concepts mastered
        - All weak concepts with explanations
        - Quiz session information

        Args:
            user_id: User ID (for authorization)
            summary_id: Summary ID to retrieve
            db_session: SQLAlchemy database session

        Returns:
            QuizSummary: Full quiz summary object with all details

        Raises:
            ValueError: If summary not found or user does not own it
        """
        logger.info(f"Getting quiz summary detail {summary_id} for user {user_id}")

        # Query and verify ownership
        summary = (
            db_session.query(QuizSummary)
            .join(UserCourse, UserCourse.user_course_id == QuizSummary.user_course_id)
            .filter(
                QuizSummary.summary_id == summary_id,
                UserCourse.user_id == user_id,
            )
            .first()
        )

        if not summary:
            logger.warning(
                f"Quiz summary {summary_id} not found for user {user_id}"
            )
            raise ValueError(
                f"Quiz summary {summary_id} not found or access denied"
            )

        logger.info(f"Retrieved quiz summary {summary_id}")
        return summary

    @staticmethod
    def get_due_reviews(db_session: Session):
        """Lấy (QuizSummary, User) pairs cần review hôm nay.

        Returns:
            List of (QuizSummary, User) tuples where next_review_at <= now
            and the user's course is still IN_PROGRESS.
        """
        now = datetime.utcnow()
        return (
            db_session.query(QuizSummary, User)
            .join(QuizSession, QuizSession.session_id == QuizSummary.session_id)
            .join(User, User.user_id == QuizSession.user_id)
            .join(UserCourse, UserCourse.user_id == User.user_id)
            .filter(
                QuizSummary.next_review_at <= now,
                QuizSummary.next_review_at.isnot(None),
                UserCourse.status == "IN_PROGRESS",
            )
            .all()
        )

    @staticmethod
    def get_review_by_topic(
        user_id: int, topic: str, db_session: Session
    ) -> List[QuizSummaryPreview]:
        """
        Get all quiz summaries for a specific topic/lesson.

        Filters quiz summaries by lesson name containing the topic string.

        Args:
            user_id: User ID to get summaries for
            topic: Topic/lesson name to filter by (case-insensitive substring match)
            db_session: SQLAlchemy database session

        Returns:
            List[QuizSummaryPreview]: List of matching summaries sorted by date (newest first)

        Raises:
            ValueError: If user does not exist
        """
        # Verify user exists
        user = db_session.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            raise ValueError(f"User {user_id} not found")

        logger.info(f"Getting quiz summaries for topic '{topic}' for user {user_id}")

        # Query summaries filtered by topic via QuizSession
        summaries = (
            db_session.query(QuizSummary)
            .join(QuizSession, QuizSession.session_id == QuizSummary.session_id)
            .join(Lesson, Lesson.lesson_id == QuizSession.lesson_id)
            .filter(
                QuizSession.user_id == user_id,
                Lesson.title.ilike(f"%{topic}%"),
            )
            .order_by(QuizSummary.created_at.desc())
            .all()
        )

        previews = []
        for summary in summaries:
            # Get lesson name
            lesson_name = "Unknown Lesson"
            if summary.quiz_session and summary.quiz_session.lesson:
                lesson_name = summary.quiz_session.lesson.title

            # Count mastered concepts
            concepts_mastered_count = 0
            if summary.concepts_mastered and isinstance(summary.concepts_mastered, list):
                concepts_mastered_count = len(summary.concepts_mastered)

            # Count weak concepts
            concepts_weak_count = 0
            if summary.concepts_weak and isinstance(summary.concepts_weak, list):
                concepts_weak_count = len(summary.concepts_weak)

            preview = QuizSummaryPreview(
                summary_id=summary.summary_id,
                date=summary.created_at,
                lesson_name=lesson_name,
                concepts_mastered_count=concepts_mastered_count,
                concepts_weak_count=concepts_weak_count,
            )
            previews.append(preview)

        logger.info(
            f"Found {len(previews)} quiz summaries for topic '{topic}' "
            f"for user {user_id}"
        )
        return previews
