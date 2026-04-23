"""
Helper functions for lesson link generation and delivery.

Shared between cmd_today and onboarding completion to avoid duplicating
content-generation + link-sending logic.
"""

import asyncio
import logging

from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from app.config import settings
from app.services.llm_content_generator import LLMContentGenerator
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def _build_lesson_url(lesson_id: int) -> str:
    """Build the frontend URL for a lesson.

    Args:
        lesson_id: Primary key of the lesson.

    Returns:
        str: Full URL, e.g. "http://localhost:5173/lesson/42"
    """
    return f"{settings.frontend_url}/lesson/{lesson_id}"


async def _send_lesson_link(message: Message, lesson, course, db, previous_lesson=None) -> None:
    """Generate lesson content (if not cached) then send the lesson link.

    This is the single shared helper used by both cmd_today and onboarding
    completion — do NOT duplicate this logic elsewhere.

    Args:
        message: Aiogram Message to reply to.
        lesson: Lesson ORM object.
        course: Course ORM object (may be None).
        db: SQLAlchemy session.
        previous_lesson: Previous lesson ORM object for recap line (may be None).
    """
    from app.models import Lesson

    total_lessons = db.query(Lesson).filter(
        Lesson.course_id == lesson.course_id
    ).count()

    llm = LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )
    generator = LLMContentGenerator(
        client=llm.client,
        smart_model=settings.llm_smart_model,
    )

    course_topic = course.name if course else lesson.title
    try:
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            await asyncio.to_thread(
                lambda: generator.get_or_generate(
                    lesson=lesson,
                    course_topic=course_topic,
                    total_lessons=total_lessons,
                    db=db,
                )
            )
    except Exception as e:
        logger.warning(f"_send_lesson_link: content generation failed (fallback used): {e}")

    url = _build_lesson_url(lesson.lesson_id)
    course_prefix = f"{course.name} - " if course else ""
    recap = f"<i>Bài trước: {previous_lesson.title}</i>\n\n" if previous_lesson else ""
    await message.answer(
        f"{recap}"
        f"📖 <b>{course_prefix}Bài {lesson.sequence_number}: {lesson.title}</b>\n\n"
        f'<a href="{url}">📚 Đọc bài học tại đây</a>\n\n'
        f"Sau khi đọc xong, gõ /done để làm quiz ✍️",
        parse_mode="HTML",
    )
