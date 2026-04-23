"""
FastAPI router for lesson content endpoint.

Serves Markdown lesson content for frontend web consumption.
Content is generated lazily via LLM if not yet cached in DB.

Endpoints:
- GET /api/lessons/{lesson_id}/content → Return lesson Markdown content
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.llm_content_generator import LLMContentGenerator
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


class LessonContentResponse(BaseModel):
    """Response schema for lesson content endpoint."""

    lesson_id: int
    title: str
    sequence_number: int
    content_markdown: str
    course_name: str
    generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/{lesson_id}/content", response_model=LessonContentResponse)
async def get_lesson_content(
    lesson_id: int,
    db: Session = Depends(get_db),
) -> LessonContentResponse:
    """
    Return lesson content as Markdown.

    If content_markdown is not yet cached, generate it via LLM and save to DB.

    Args:
        lesson_id: ID of the lesson to retrieve
        db: Database session (injected)

    Returns:
        LessonContentResponse: JSON with lesson metadata and Markdown content

    Raises:
        HTTPException 404: If lesson_id does not exist
    """
    from app.models import Lesson, Course
    from app.config import settings

    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    course = db.query(Course).filter(Course.course_id == lesson.course_id).first()
    total_lessons = db.query(Lesson).filter(Lesson.course_id == lesson.course_id).count()

    if not lesson.content_markdown:
        logger.info(f"Generating content for lesson {lesson_id} via LLM")
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
        generator.get_or_generate(
            lesson=lesson,
            course_topic=course.name if course else lesson.title,
            total_lessons=total_lessons,
            db=db,
        )

    return LessonContentResponse(
        lesson_id=lesson.lesson_id,
        title=lesson.title,
        sequence_number=lesson.sequence_number,
        content_markdown=lesson.content_markdown or "",
        course_name=course.name if course else "",
        generated_at=lesson.content_generated_at,
    )
