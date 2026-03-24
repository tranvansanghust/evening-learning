"""
FastAPI router for progress and review endpoints.

Provides endpoints for:
- Viewing overall learning progress (lessons completed, concepts mastered)
- Retrieving quiz summary previews
- Getting detailed quiz summaries
- Reviewing quizzes by topic

All endpoints are designed to be called by Telegram handlers or frontend applications.
Responses follow a standardized JSON format with appropriate HTTP status codes.

Endpoints:
- GET /api/progress/{user_id} → Get overall progress
- GET /api/review → Get all quiz summaries (previews)
- GET /api/review/topic/{topic} → Get summaries filtered by topic
- GET /api/review/summary/{summary_id} → Get detailed quiz summary
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.progress_service import ProgressService
from app.schemas.progress import UserProgress, QuizSummaryPreview, QuizSummaryDetail
from app.models import QuizSummary

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================


def _get_user_id_from_path(user_id: int) -> int:
    """
    Validate user_id from path parameter.

    Args:
        user_id: User ID from path

    Returns:
        int: Validated user ID

    Raises:
        HTTPException: If user_id is invalid
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a positive integer",
        )
    return user_id


def _convert_summary_to_detail(summary: QuizSummary, lesson_name: str = None) -> QuizSummaryDetail:
    """
    Convert QuizSummary ORM object to QuizSummaryDetail schema.

    Args:
        summary: QuizSummary ORM object
        lesson_name: Optional lesson name override

    Returns:
        QuizSummaryDetail: Converted schema object
    """
    if lesson_name is None and summary.quiz_session and summary.quiz_session.lesson:
        lesson_name = summary.quiz_session.lesson.title
    else:
        lesson_name = lesson_name or "Unknown Lesson"

    concepts_mastered = []
    if summary.concepts_mastered and isinstance(summary.concepts_mastered, list):
        concepts_mastered = summary.concepts_mastered

    concepts_weak = []
    if summary.concepts_weak and isinstance(summary.concepts_weak, list):
        concepts_weak = summary.concepts_weak

    return QuizSummaryDetail(
        summary_id=summary.summary_id,
        date=summary.created_at,
        lesson_name=lesson_name,
        concepts_mastered=concepts_mastered,
        concepts_weak=concepts_weak,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/progress/{user_id}",
    response_model=UserProgress,
    status_code=status.HTTP_200_OK,
    summary="Get user progress",
    description="Get user's overall learning progress including lessons completed and concepts mastered",
    responses={
        200: {"description": "Progress retrieved successfully"},
        400: {"description": "Invalid user_id"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_user_progress(
    user_id: int = Path(..., gt=0, description="User ID"),
    db: Session = Depends(get_db),
) -> UserProgress:
    """
    Get user's overall learning progress.

    Returns the number of lessons completed vs total lessons available,
    and the number of concepts mastered vs total concepts available.

    Args:
        user_id: ID of the user (from URL path)
        db: Database session (injected)

    Returns:
        UserProgress: Object containing:
            - lessons_completed: Lessons with quiz summaries
            - total_lessons: Total lessons in enrolled courses
            - concepts_mastered: Unique concepts answered correctly
            - total_concepts: Total unique concepts available

    Raises:
        HTTPException 400: If user_id is invalid (≤ 0)
        HTTPException 404: If user not found
        HTTPException 500: If database error occurs
    """
    logger.info(f"GET /api/progress/{user_id}")
    _get_user_id_from_path(user_id)

    try:
        progress = ProgressService.get_user_progress(user_id, db)
        logger.info(
            f"Retrieved progress for user {user_id}: "
            f"{progress.lessons_completed}/{progress.total_lessons} lessons, "
            f"{progress.concepts_mastered}/{progress.total_concepts} concepts"
        )
        return progress
    except ValueError as e:
        logger.warning(f"User not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving progress: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving progress",
        )


@router.get(
    "/review",
    response_model=List[QuizSummaryPreview],
    status_code=status.HTTP_200_OK,
    summary="Get all quiz summaries",
    description="Get a list of all quiz summaries for the user, sorted by date",
    responses={
        200: {"description": "Quiz summaries retrieved successfully"},
        400: {"description": "Invalid user_id"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_all_quiz_summaries(
    user_id: int = Query(..., gt=0, description="User ID"),
    db: Session = Depends(get_db),
) -> List[QuizSummaryPreview]:
    """
    Get all quiz summaries for a user.

    Returns a list of brief quiz summary previews showing:
    - When the quiz was taken
    - Which lesson it covered
    - How many concepts were mastered/weak

    Summaries are sorted by date (newest first).

    Args:
        user_id: ID of the user (from query parameter)
        db: Database session (injected)

    Returns:
        List[QuizSummaryPreview]: List of quiz summary previews,
            or empty list if user has no summaries

    Raises:
        HTTPException 400: If user_id is invalid (≤ 0)
        HTTPException 404: If user not found
        HTTPException 500: If database error occurs
    """
    logger.info(f"GET /api/review?user_id={user_id}")
    _get_user_id_from_path(user_id)

    try:
        summaries = ProgressService.get_quiz_summaries(user_id, db)
        logger.info(f"Retrieved {len(summaries)} quiz summaries for user {user_id}")
        return summaries
    except ValueError as e:
        logger.warning(f"User not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving quiz summaries: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quiz summaries",
        )


@router.get(
    "/review/topic/{topic}",
    response_model=List[QuizSummaryPreview],
    status_code=status.HTTP_200_OK,
    summary="Get summaries by topic",
    description="Get quiz summaries filtered by lesson topic/name",
    responses={
        200: {"description": "Quiz summaries retrieved successfully"},
        400: {"description": "Invalid user_id or topic"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_summaries_by_topic(
    topic: str = Path(..., min_length=1, description="Topic/lesson name to filter by"),
    user_id: int = Query(..., gt=0, description="User ID"),
    db: Session = Depends(get_db),
) -> List[QuizSummaryPreview]:
    """
    Get quiz summaries filtered by topic/lesson name.

    Returns quiz summaries for lessons matching the topic string
    (case-insensitive substring match).

    Args:
        topic: Topic/lesson name to filter by (from URL path)
        user_id: ID of the user (from query parameter)
        db: Database session (injected)

    Returns:
        List[QuizSummaryPreview]: List of matching quiz summary previews,
            or empty list if no matches found

    Raises:
        HTTPException 400: If user_id is invalid or topic is empty
        HTTPException 404: If user not found
        HTTPException 500: If database error occurs
    """
    logger.info(f"GET /api/review/topic/{topic}?user_id={user_id}")
    _get_user_id_from_path(user_id)

    if not topic or not topic.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="topic cannot be empty",
        )

    try:
        summaries = ProgressService.get_review_by_topic(user_id, topic, db)
        logger.info(
            f"Retrieved {len(summaries)} quiz summaries for topic '{topic}' "
            f"for user {user_id}"
        )
        return summaries
    except ValueError as e:
        logger.warning(f"User not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving topic summaries: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quiz summaries",
        )


@router.get(
    "/review/summary/{summary_id}",
    response_model=QuizSummaryDetail,
    status_code=status.HTTP_200_OK,
    summary="Get quiz summary details",
    description="Get full details of a specific quiz summary",
    responses={
        200: {"description": "Quiz summary retrieved successfully"},
        400: {"description": "Invalid user_id or summary_id"},
        403: {"description": "User does not have access to this summary"},
        404: {"description": "Quiz summary not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_quiz_summary_detail(
    summary_id: int = Path(..., gt=0, description="Quiz summary ID"),
    user_id: int = Query(..., gt=0, description="User ID"),
    db: Session = Depends(get_db),
) -> QuizSummaryDetail:
    """
    Get full details of a quiz summary.

    Returns complete information about a quiz including:
    - All concepts mastered
    - All weak concepts with explanations
    - Quiz metadata

    Access control: User can only retrieve their own quiz summaries.

    Args:
        summary_id: ID of the quiz summary (from URL path)
        user_id: ID of the user (from query parameter)
        db: Database session (injected)

    Returns:
        QuizSummaryDetail: Full quiz summary with all details

    Raises:
        HTTPException 400: If summary_id or user_id is invalid (≤ 0)
        HTTPException 403: If user does not own this summary
        HTTPException 404: If summary not found
        HTTPException 500: If database error occurs
    """
    logger.info(f"GET /api/review/summary/{summary_id}?user_id={user_id}")
    _get_user_id_from_path(user_id)

    if summary_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="summary_id must be a positive integer",
        )

    try:
        summary = ProgressService.get_quiz_summary_detail(user_id, summary_id, db)
        detail = _convert_summary_to_detail(summary)
        logger.info(f"Retrieved summary {summary_id} for user {user_id}")
        return detail
    except ValueError as e:
        logger.warning(f"Summary access denied: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error retrieving summary detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quiz summary",
        )
