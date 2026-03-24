"""
FastAPI router for learning flow endpoints.

Provides endpoints for the learning phase of the daily loop:
- Start learning session (Track A or Track B)
- Mark learning as done and start quiz
- Get today's lesson status

All endpoints are designed to be called by Telegram handlers.
Responses follow a standardized JSON format.

Implements both Track A (external learning) and Track B (internal content).
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserCourse, Lesson
from app.services.quiz_service import QuizService
from app.services.llm_service import LLMService
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize services (will be instantiated on first use)
_quiz_service = None


def get_quiz_service() -> QuizService:
    """
    Get or create QuizService instance.

    Lazy initialization to ensure LLMService is properly configured.
    """
    global _quiz_service
    if _quiz_service is None:
        llm_service = LLMService(api_key=settings.anthropic_api_key)
        _quiz_service = QuizService(llm_service=llm_service)
    return _quiz_service


# ============================================================================
# Request/Response Models
# ============================================================================

class StartLearningRequest(BaseModel):
    """Request body for POST /api/learn/start."""

    user_id: int = Field(..., description="User ID")
    lesson_id: int = Field(..., description="Lesson ID to learn")
    track: str = Field(..., description="Learning track: 'A' (external) or 'B' (internal)")


class StartLearningResponse(BaseModel):
    """Response for learning session start."""

    success: bool
    message: str
    lesson_id: int
    lesson_name: str
    track: str
    content_url: Optional[str] = None  # For Track B only
    estimated_duration: Optional[int] = None


class DoneLearningRequest(BaseModel):
    """Request body for POST /api/learn/done."""

    user_id: int = Field(..., description="User ID")
    lesson_id: int = Field(..., description="Lesson ID being completed")
    user_checkin: Optional[str] = Field(
        None,
        description="User's summary of what they learned (Track A)"
    )


class QuizStartResponse(BaseModel):
    """Response when quiz is ready to start."""

    success: bool
    message: str
    session_id: int
    first_question: str
    lesson_name: str
    concepts: list


class GetLearningStatusRequest(BaseModel):
    """Request for GET /api/learn/status/{user_id}."""

    user_id: int = Field(..., description="User ID")


class LessonStatus(BaseModel):
    """Status of a lesson for a user."""

    lesson_id: int
    lesson_name: str
    status: str  # 'pending', 'in_progress', 'completed'
    started_at: Optional[str] = None
    estimated_duration: Optional[int] = None


class GetLearningStatusResponse(BaseModel):
    """Response for GET /api/learn/status/{user_id}."""

    success: bool
    user_id: int
    today_lesson: Optional[LessonStatus] = None
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/start", response_model=StartLearningResponse, tags=["Learning"])
async def start_learning(
    request: StartLearningRequest,
    db: Session = Depends(get_db)
) -> StartLearningResponse:
    """
    Start a learning session for a lesson.

    Handles both Track A (external learning) and Track B (internal content).

    For Track B: Returns content URL for the user to learn from.
    For Track A: Just acknowledges the learning has started.

    Args:
        request: StartLearningRequest with user_id, lesson_id, and track
        db: Database session

    Returns:
        StartLearningResponse with lesson details

    Raises:
        HTTPException 404: If user or lesson not found
        HTTPException 400: If invalid track specified

    Example:
        POST /api/learn/start
        {
            "user_id": 1,
            "lesson_id": 5,
            "track": "B"
        }
    """
    try:
        # Validate user
        user = db.query(User).filter(User.user_id == request.user_id).first()
        if not user:
            logger.warning(f"User {request.user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found"
            )

        # Validate lesson
        lesson = db.query(Lesson).filter(Lesson.lesson_id == request.lesson_id).first()
        if not lesson:
            logger.warning(f"Lesson {request.lesson_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson {request.lesson_id} not found"
            )

        # Validate track
        if request.track not in ["A", "B"]:
            logger.warning(f"Invalid track: {request.track}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Track must be 'A' or 'B'"
            )

        logger.info(f"User {request.user_id} started learning lesson {request.lesson_id} (Track {request.track})")

        # Track B: Return content for user to read
        if request.track == "B":
            return StartLearningResponse(
                success=True,
                message=f"Starting learning: {lesson.title}",
                lesson_id=lesson.lesson_id,
                lesson_name=lesson.title,
                track="B",
                content_url=lesson.content_url,
                estimated_duration=lesson.estimated_duration_minutes
            )
        # Track A: Just acknowledge
        else:
            return StartLearningResponse(
                success=True,
                message=f"Starting learning: {lesson.title}. Go ahead and learn from your external source!",
                lesson_id=lesson.lesson_id,
                lesson_name=lesson.title,
                track="A",
                estimated_duration=lesson.estimated_duration_minutes
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in start_learning: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start learning session"
        )


@router.post("/done", response_model=QuizStartResponse, tags=["Learning"])
async def done_learning(
    request: DoneLearningRequest,
    db: Session = Depends(get_db)
) -> QuizStartResponse:
    """
    Mark learning as done and initialize quiz session.

    Transitions from learning phase to quiz phase. Creates a new quiz session,
    loads lesson content and concepts, and generates the first question.

    Called when user completes learning and is ready for quiz.

    Args:
        request: DoneLearningRequest with user_id, lesson_id, and optional user_checkin
        db: Database session

    Returns:
        QuizStartResponse with quiz session and first question

    Raises:
        HTTPException 404: If user or lesson not found
        HTTPException 500: On LLM service errors

    Example:
        POST /api/learn/done
        {
            "user_id": 1,
            "lesson_id": 5,
            "user_checkin": "I learned about useState and basic hooks"
        }
    """
    try:
        # Validate user
        user = db.query(User).filter(User.user_id == request.user_id).first()
        if not user:
            logger.warning(f"User {request.user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found"
            )

        # Validate lesson
        lesson = db.query(Lesson).filter(Lesson.lesson_id == request.lesson_id).first()
        if not lesson:
            logger.warning(f"Lesson {request.lesson_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson {request.lesson_id} not found"
            )

        # Start quiz session
        quiz_service = get_quiz_service()
        quiz_result = quiz_service.start_quiz(
            user_id=request.user_id,
            lesson_id=request.lesson_id,
            user_checkin=request.user_checkin,
            db_session=db
        )

        logger.info(
            f"User {request.user_id} completed learning lesson {request.lesson_id}, "
            f"quiz session {quiz_result['session_id']} started"
        )

        return QuizStartResponse(
            success=True,
            message="Great! Let's check what you've learned.",
            session_id=quiz_result["session_id"],
            first_question=quiz_result["first_question"],
            lesson_name=quiz_result["lesson_name"],
            concepts=quiz_result["concepts"]
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in done_learning: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in done_learning: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start quiz session"
        )


@router.get("/status/{user_id}", response_model=GetLearningStatusResponse, tags=["Learning"])
async def get_learning_status(
    user_id: int,
    db: Session = Depends(get_db)
) -> GetLearningStatusResponse:
    """
    Get today's lesson status for a user.

    Returns information about the lesson the user is supposed to learn today,
    including whether they've started and completed it.

    Args:
        user_id: The user ID
        db: Database session

    Returns:
        GetLearningStatusResponse with today's lesson status

    Raises:
        HTTPException 404: If user not found

    Example:
        GET /api/learn/status/1
    """
    try:
        # Validate user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Get user's current course enrollment
        user_course = db.query(UserCourse).filter(
            UserCourse.user_id == user_id,
            UserCourse.status == "IN_PROGRESS"
        ).first()

        if not user_course:
            logger.info(f"User {user_id} has no active course enrollment")
            return GetLearningStatusResponse(
                success=True,
                user_id=user_id,
                today_lesson=None,
                message="No active course. User should start a course first."
            )

        # Get next lesson for the course
        # This is a simplified approach - in a real system, you'd have more sophisticated
        # logic to determine which lesson should be done "today"
        next_lesson = db.query(Lesson).filter(
            Lesson.course_id == user_course.course_id
        ).order_by(Lesson.sequence_number).first()

        if not next_lesson:
            logger.info(f"Course {user_course.course_id} has no lessons")
            return GetLearningStatusResponse(
                success=True,
                user_id=user_id,
                today_lesson=None,
                message="Course has no lessons available."
            )

        today_lesson = LessonStatus(
            lesson_id=next_lesson.lesson_id,
            lesson_name=next_lesson.title,
            status="pending",
            estimated_duration=next_lesson.estimated_duration_minutes
        )

        return GetLearningStatusResponse(
            success=True,
            user_id=user_id,
            today_lesson=today_lesson,
            message=f"User has lesson: {next_lesson.title}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_learning_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get learning status"
        )
