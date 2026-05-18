"""
CourseSeeder — persist a generated course (Course + Lessons + Concepts) into the database.

Separated from LessonGenerator so dry-run mode works cleanly.
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.lesson import Lesson
from app.models.concept import Concept
from app.services.lesson_generator import GeneratedLesson

logger = logging.getLogger(__name__)


class CourseSeeder:
    """
    Inserts a generated course into the database.

    Usage:
        seeder = CourseSeeder(db)
        course = seeder.seed("Go Tour Basics", "go-dev-tour-basics", lessons)
    """

    def __init__(self, db: Session):
        self.db = db

    def seed(
        self,
        course_name: str,
        slug: str,
        lessons: List[GeneratedLesson],
        overwrite: bool = False,
    ) -> Course:
        """
        Insert Course + Lessons + Concepts. Skips if course already exists (unless overwrite=True).

        Args:
            course_name: Display name for the course
            slug: Unique identifier used as source_id (e.g. 'go-dev-tour-basics')
            lessons: List of GeneratedLesson from LessonGenerator.run()
            overwrite: If True, delete existing course with same slug before inserting

        Returns:
            The newly created Course ORM object
        """
        existing = (
            self.db.query(Course)
            .filter(Course.source == "generated", Course.source_id == slug)
            .first()
        )

        if existing:
            if not overwrite:
                logger.info(f"Course '{slug}' already exists (id={existing.course_id}), skipping.")
                return existing
            logger.info(f"Overwriting existing course '{slug}' (id={existing.course_id})")
            self.db.delete(existing)
            self.db.flush()

        course = Course(
            name=course_name,
            source="generated",
            source_id=slug,
            total_lessons=len(lessons),
        )
        self.db.add(course)
        self.db.flush()  # get course_id before inserting lessons

        for gen in lessons:
            lesson = Lesson(
                course_id=course.course_id,
                sequence_number=gen.plan.sequence_number,
                title=gen.plan.title,
                description=gen.plan.description,
                content_markdown=gen.content_markdown,
                estimated_duration_minutes=10,
            )
            self.db.add(lesson)
            self.db.flush()  # get lesson_id before inserting concepts

            for c in gen.concepts:
                self.db.add(Concept(
                    lesson_id=lesson.lesson_id,
                    name=c.name,
                    description=c.description,
                ))

        self.db.commit()
        logger.info(
            f"Seeded course '{course_name}' (id={course.course_id}): "
            f"{len(lessons)} lessons, "
            f"{sum(len(g.concepts) for g in lessons)} concepts"
        )
        return course
