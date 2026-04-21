"""
Onboarding service for managing user onboarding flow.

This module provides the OnboardingService class which handles:
- User creation and initialization
- Course detection from URLs or topics
- Level assessment based on binary tree questions
- Curriculum generation from course structure
- Onboarding state management
"""

import logging
import re
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from sqlalchemy.orm import Session

from app.models import User, Course, UserCourse, Lesson, Concept
from app.models.onboarding_state import OnboardingState

logger = logging.getLogger(__name__)


class OnboardingService:
    """
    Service for managing the user onboarding flow.

    Handles all business logic for the multi-step onboarding process,
    including user creation, assessment, and curriculum generation.
    """

    def __init__(self, db: Session):
        """
        Initialize the OnboardingService.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_user(self, telegram_id: str, username: Optional[str] = None) -> User:
        """
        Create a new user in the system.

        Args:
            telegram_id: Unique Telegram user ID
            username: Optional user display name

        Returns:
            User: The created User object

        Raises:
            ValueError: If user with this telegram_id already exists

        Example:
            >>> service = OnboardingService(db)
            >>> user = service.create_user("123456789", "john_doe")
            >>> print(user.user_id, user.telegram_id)
            1 123456789
        """
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            User.telegram_id == telegram_id
        ).first()

        if existing_user:
            logger.warning(f"User with telegram_id {telegram_id} already exists")
            raise ValueError(f"User with telegram_id {telegram_id} already exists")

        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=username or f"user_{telegram_id}",
            level=0  # Default to level 0 (beginner)
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"Created user: {user.user_id} (telegram_id={telegram_id})")
        return user

    def create_onboarding_state(self, user_id: int) -> OnboardingState:
        """
        Create an onboarding state record for a new user.

        Args:
            user_id: ID of the user starting onboarding

        Returns:
            OnboardingState: The created onboarding state

        Raises:
            ValueError: If user already has an active onboarding state

        Example:
            >>> state = service.create_onboarding_state(user_id=1)
            >>> print(state.current_step)
            'start'
        """
        # Check if user already has an onboarding state
        existing_state = self.db.query(OnboardingState).filter(
            OnboardingState.user_id == user_id
        ).first()

        if existing_state:
            logger.warning(f"User {user_id} already has an onboarding state")
            raise ValueError(f"User {user_id} already has an active onboarding state")

        # Create new onboarding state
        onboarding_state = OnboardingState(
            user_id=user_id,
            current_step="start",
            expires_at=datetime.utcnow() + timedelta(days=7)  # Expire after 7 days
        )

        self.db.add(onboarding_state)
        self.db.commit()
        self.db.refresh(onboarding_state)

        logger.info(f"Created onboarding state for user {user_id}")
        return onboarding_state

    def get_onboarding_state(self, user_id: int) -> Optional[OnboardingState]:
        """
        Retrieve the current onboarding state for a user.

        Args:
            user_id: ID of the user

        Returns:
            OnboardingState: The user's onboarding state, or None if not found

        Example:
            >>> state = service.get_onboarding_state(user_id=1)
            >>> if state:
            ...     print(state.current_step)
        """
        return self.db.query(OnboardingState).filter(
            OnboardingState.user_id == user_id
        ).first()

    def detect_course_from_input(self, user_input: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect if input is a Udemy URL or a general topic.

        Args:
            user_input: User's input (URL or topic name)

        Returns:
            Tuple[Optional[str], Optional[str]]: (type, value) where type is 'udemy' or 'topic', value is URL or topic name

        Example:
            >>> service.detect_course_from_input("https://www.udemy.com/course/react-guide/")
            ('udemy', 'react-guide')
            >>> service.detect_course_from_input("Learn React")
            ('topic', 'Learn React')
        """
        user_input = user_input.strip()

        # Check if input is a URL
        if user_input.startswith("http://") or user_input.startswith("https://"):
            parsed_url = urlparse(user_input)

            # Check for Udemy URL
            if "udemy.com" in parsed_url.netloc:
                # Extract course slug from URL
                path_parts = parsed_url.path.strip("/").split("/")
                if "course" in path_parts:
                    course_idx = path_parts.index("course")
                    if course_idx + 1 < len(path_parts):
                        course_slug = path_parts[course_idx + 1]
                        logger.info(f"Detected Udemy course: {course_slug}")
                        return ("udemy", course_slug)

            # Unknown URL type
            logger.info(f"Unknown URL type: {parsed_url.netloc}")
            return (None, None)

        # Input is a topic
        logger.info(f"Detected topic input: {user_input}")
        return ("topic", user_input)

    def fetch_udemy_curriculum(self, course_slug: str) -> List[dict]:
        """
        Fetch or mock curriculum from a Udemy course.

        This is a mock implementation for MVP. In production, this would:
        - Call Udemy API to fetch actual course content
        - Parse course structure into lessons

        Args:
            course_slug: Udemy course identifier (e.g., "react-guide")

        Returns:
            List[dict]: List of lessons with structure {'title', 'description', 'duration_minutes', 'sequence_number'}

        Example:
            >>> lessons = service.fetch_udemy_curriculum("react-guide")
            >>> print(len(lessons), lessons[0]['title'])
            12 Section 1: Introduction to React
        """
        # Mock curriculum - in production, call Udemy API
        mock_curriculums = {
            "react-complete-guide": [
                {"sequence_number": 1, "title": "Section 1: Getting Started", "description": "Introduction to React", "duration_minutes": 45},
                {"sequence_number": 2, "title": "Section 2: Components & JSX", "description": "Learn about React components", "duration_minutes": 60},
                {"sequence_number": 3, "title": "Section 3: State & Props", "description": "Managing component state", "duration_minutes": 75},
                {"sequence_number": 4, "title": "Section 4: Hooks", "description": "React Hooks deep dive", "duration_minutes": 90},
                {"sequence_number": 5, "title": "Section 5: Forms & Validation", "description": "Handling form inputs", "duration_minutes": 60},
                {"sequence_number": 6, "title": "Section 6: API Integration", "description": "Fetching data from APIs", "duration_minutes": 75},
            ],
            "javascript-advanced": [
                {"sequence_number": 1, "title": "Section 1: Closures", "description": "Understanding closures", "duration_minutes": 50},
                {"sequence_number": 2, "title": "Section 2: Async/Await", "description": "Async programming", "duration_minutes": 60},
                {"sequence_number": 3, "title": "Section 3: Promises", "description": "Promise patterns", "duration_minutes": 55},
                {"sequence_number": 4, "title": "Section 4: Functional Programming", "description": "Functional paradigms", "duration_minutes": 65},
            ],
        }

        lessons = mock_curriculums.get(course_slug.lower(), [])

        if not lessons:
            logger.warning(f"No mock curriculum found for course slug: {course_slug}")
            # Return generic structure for unknown courses
            lessons = [
                {"sequence_number": i+1, "title": f"Section {i+1}", "description": f"Content for section {i+1}", "duration_minutes": 60}
                for i in range(5)
            ]

        logger.info(f"Fetched {len(lessons)} lessons for course: {course_slug}")
        return lessons

    def assess_level(self, q1_answer: str, q2_answer: str) -> int:
        """
        Determine user's learning level based on assessment answers.

        Assessment uses a binary tree:
        - Q1: Have you built a web app? (never/yes)
        - Q2a (if Q1=never): Know HTML/CSS? (no/yes) → Level 0 or 1
        - Q2b (if Q1=yes): Used other frameworks? (no/yes) → Level 2 or 3

        Args:
            q1_answer: Answer to Q1 ('never' or 'yes')
            q2_answer: Answer to Q2 ('no' or 'yes')

        Returns:
            int: Assessed level (0, 1, 2, or 3)

        Raises:
            ValueError: If answers are invalid

        Example:
            >>> level = service.assess_level("never", "no")
            >>> print(level)
            0
            >>> level = service.assess_level("yes", "yes")
            >>> print(level)
            3
        """
        q1_answer = q1_answer.lower().strip()
        q2_answer = q2_answer.lower().strip()

        # Validate answers
        valid_answers = ("never", "yes", "no")
        if q1_answer not in valid_answers or q2_answer not in valid_answers:
            logger.error(f"Invalid assessment answers: Q1={q1_answer}, Q2={q2_answer}")
            raise ValueError(f"Invalid assessment answers: Q1={q1_answer}, Q2={q2_answer}")

        # Assessment matrix
        if q1_answer == "never":
            if q2_answer == "no":
                level = 0  # Never built app, no HTML/CSS knowledge
            else:  # "yes"
                level = 1  # Never built app, but knows HTML/CSS
        else:  # q1_answer == "yes"
            if q2_answer == "no":
                level = 2  # Built app, no other framework experience
            else:  # "yes"
                level = 3  # Built app, experienced with frameworks

        logger.info(f"Assessed user level: {level} (Q1={q1_answer}, Q2={q2_answer})")
        return level

    def update_onboarding_state(
        self,
        user_id: int,
        current_step: Optional[str] = None,
        course_topic: Optional[str] = None,
        course_id: Optional[int] = None,
        q1_answer: Optional[str] = None,
        q2_answer: Optional[str] = None,
        assessed_level: Optional[int] = None,
        deadline: Optional[date] = None,
        hours_per_day: Optional[int] = None,
        reminder_time: Optional[str] = None,
    ) -> OnboardingState:
        """
        Update the onboarding state for a user.

        Args:
            user_id: ID of the user
            current_step: New current step (optional)
            course_id: Course ID (optional)
            q1_answer: Q1 assessment answer (optional)
            q2_answer: Q2 assessment answer (optional)
            assessed_level: Assessed level (optional)
            deadline: Course completion deadline (optional)
            hours_per_day: Daily study hours (optional)
            reminder_time: Reminder time in HH:MM format (optional)

        Returns:
            OnboardingState: The updated onboarding state

        Raises:
            ValueError: If user has no onboarding state

        Example:
            >>> state = service.update_onboarding_state(
            ...     user_id=1,
            ...     current_step="q1",
            ...     q1_answer="yes"
            ... )
        """
        state = self.get_onboarding_state(user_id)

        if not state:
            logger.error(f"No onboarding state found for user {user_id}")
            raise ValueError(f"No onboarding state found for user {user_id}")

        # Update fields
        if current_step is not None:
            state.current_step = current_step
        if course_topic is not None:
            state.course_topic = course_topic
        if course_id is not None:
            state.course_id = course_id
        if q1_answer is not None:
            state.q1_answer = q1_answer
        if q2_answer is not None:
            state.q2_answer = q2_answer
        if assessed_level is not None:
            state.assessed_level = assessed_level
        if deadline is not None:
            state.deadline = deadline
        if hours_per_day is not None:
            state.hours_per_day = hours_per_day
        if reminder_time is not None:
            state.reminder_time = reminder_time

        self.db.commit()
        self.db.refresh(state)

        logger.info(f"Updated onboarding state for user {user_id}: {current_step}")
        return state

    def create_course_from_curriculum(
        self,
        course_name: str,
        course_slug: str,
        curriculum: List[dict],
        source: str = "internal",
        source_id: Optional[str] = None,
    ) -> Course:
        """
        Create a course record from curriculum data.

        Args:
            course_name: Course title
            course_slug: Unique course identifier
            curriculum: List of lesson data
            source: Source platform ('udemy', 'internal', etc.)
            source_id: External ID from source platform

        Returns:
            Course: The created Course object

        Example:
            >>> lessons_data = [{"title": "Lesson 1", ...}]
            >>> course = service.create_course_from_curriculum(
            ...     "React Guide",
            ...     "react-guide",
            ...     lessons_data,
            ...     source="udemy"
            ... )
        """
        course = Course(
            name=course_name,
            description=f"Course: {course_name}",
            source=source,
            source_id=source_id or course_slug,
            total_lessons=len(curriculum),
        )

        self.db.add(course)
        self.db.flush()  # Get course_id without committing

        # Create lessons
        for lesson_data in curriculum:
            lesson = Lesson(
                course_id=course.course_id,
                sequence_number=lesson_data.get("sequence_number", 0),
                title=lesson_data.get("title", ""),
                description=lesson_data.get("description", ""),
                estimated_duration_minutes=lesson_data.get("duration_minutes", 60),
            )
            self.db.add(lesson)

        self.db.commit()
        self.db.refresh(course)

        logger.info(f"Created course: {course.course_id} ({course_name}) with {len(curriculum)} lessons")
        return course

    def create_curriculum(
        self,
        course: Course,
        user_level: int,
        deadline: date,
        hours_per_day: int,
    ) -> List[Lesson]:
        """
        Create a personalized curriculum schedule for a user.

        This schedules lessons based on:
        - Course structure
        - User's learning level (affects lesson selection/difficulty)
        - Deadline (total available days)
        - Daily available hours

        Args:
            course: The Course object
            user_level: User's assessed level (0-3)
            deadline: Target completion date
            hours_per_day: Available hours per day

        Returns:
            List[Lesson]: Ordered list of lessons for the user

        Example:
            >>> lessons = service.create_curriculum(
            ...     course=course,
            ...     user_level=1,
            ...     deadline=date(2025, 5, 31),
            ...     hours_per_day=2
            ... )
            >>> for lesson in lessons:
            ...     print(f"{lesson.sequence_number}: {lesson.title}")
        """
        # Get all lessons for the course, ordered by sequence
        lessons = self.db.query(Lesson).filter(
            Lesson.course_id == course.course_id
        ).order_by(Lesson.sequence_number).all()

        if not lessons:
            logger.warning(f"Course {course.course_id} has no lessons")
            return []

        # Filter lessons based on user level
        # For MVP: return all lessons (in production, could filter based on level)
        personalized_lessons = lessons

        # Calculate total available minutes
        days_available = (deadline - date.today()).days
        total_minutes_available = days_available * hours_per_day * 60

        # Calculate total duration of curriculum
        total_duration = sum(
            l.estimated_duration_minutes or 60
            for l in personalized_lessons
        )

        logger.info(
            f"Curriculum planning: {len(personalized_lessons)} lessons, "
            f"{total_duration} minutes total, {total_minutes_available} minutes available"
        )

        return personalized_lessons

    def save_user_course_enrollment(
        self,
        user_id: int,
        course_id: int,
    ) -> UserCourse:
        """
        Create a UserCourse enrollment record.

        Args:
            user_id: ID of the user
            course_id: ID of the course

        Returns:
            UserCourse: The created enrollment record

        Raises:
            ValueError: If user or course not found, or enrollment already exists

        Example:
            >>> enrollment = service.save_user_course_enrollment(
            ...     user_id=1,
            ...     course_id=5
            ... )
            >>> print(enrollment.user_course_id)
            1
        """
        # Check if user exists
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            raise ValueError(f"User {user_id} not found")

        # Check if course exists
        course = self.db.query(Course).filter(Course.course_id == course_id).first()
        if not course:
            logger.error(f"Course {course_id} not found")
            raise ValueError(f"Course {course_id} not found")

        # Check if enrollment already exists
        existing = self.db.query(UserCourse).filter(
            UserCourse.user_id == user_id,
            UserCourse.course_id == course_id
        ).first()

        if existing:
            logger.warning(f"User {user_id} already enrolled in course {course_id}")
            return existing

        # Create enrollment
        enrollment = UserCourse(
            user_id=user_id,
            course_id=course_id,
            status="IN_PROGRESS",
        )

        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)

        logger.info(f"Created enrollment: user {user_id} → course {course_id}")
        return enrollment

    def complete_onboarding(self, user_id: int) -> Optional[Lesson]:
        """
        Mark onboarding as completed: tạo Course + UserCourse, cập nhật user level.

        Returns:
            Lesson đầu tiên của course vừa tạo (để gửi cho user), hoặc None.
        """
        state = self.get_onboarding_state(user_id)
        if not state:
            logger.warning(f"No onboarding state found for user {user_id}")
            return None

        user = self.db.query(User).filter(User.user_id == user_id).first()

        # Cập nhật level nếu có đủ Q1/Q2
        if state.q1_answer and state.q2_answer:
            try:
                level = self.assess_level(state.q1_answer, state.q2_answer)
                if user:
                    user.level = level
            except ValueError:
                pass

        # Copy reminder_time từ onboarding state sang user record
        if state.reminder_time and user:
            user.reminder_time = state.reminder_time
            self.db.commit()

        # Tạo Course + Lessons từ course_topic
        first_lesson = None
        course_topic = state.course_topic or "General Learning"
        course_slug = course_topic.lower().replace(" ", "-")[:50]
        curriculum = self.fetch_udemy_curriculum(course_slug)
        course = self.create_course_from_curriculum(
            course_name=course_topic,
            course_slug=course_slug,
            curriculum=curriculum,
        )
        self.save_user_course_enrollment(user_id, course.course_id)
        first_lesson = self.get_first_lesson(course.course_id)

        logger.info(f"Completed onboarding for user {user_id}, course={course.course_id}")

        # Xoá onboarding state
        self.db.delete(state)
        self.db.commit()

        return first_lesson

    def clear_state(self, user_id: int) -> None:
        """Delete onboarding state without any side effects (no course creation)."""
        state = self.get_onboarding_state(user_id)
        if state:
            self.db.delete(state)
            self.db.commit()

    def get_first_lesson(self, course_id: int) -> Optional[Lesson]:
        """
        Get the first lesson of a course.

        Args:
            course_id: ID of the course

        Returns:
            Lesson: The first lesson, or None if course has no lessons

        Example:
            >>> lesson = service.get_first_lesson(course_id=5)
            >>> if lesson:
            ...     print(lesson.title)
        """
        lesson = self.db.query(Lesson).filter(
            Lesson.course_id == course_id
        ).order_by(Lesson.sequence_number).first()

        return lesson
