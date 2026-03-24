"""
FastAPI router for quiz flow endpoints.

Provides endpoints for the quiz/oral-test phase of the daily loop:
- Initialize quiz session
- Submit and evaluate answers
- Get quiz status
- Retrieve post-quiz summary

All endpoints are designed to be called by Telegram handlers.
Responses follow a standardized JSON format.

Quiz progression:
1. POST /api/quiz/start → Initialize session, get first question
2. POST /api/quiz/answer → Submit answer, get evaluation + next action
3. GET /api/quiz/status/{session_id} → Check quiz progress
4. GET /api/quiz/summary/{session_id} → Get post-quiz summary (after completion)
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuizSession
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

class QuizStartRequest(BaseModel):
    """Request body for POST /api/quiz/start."""

    user_id: int = Field(..., description="User ID")
    lesson_id: int = Field(..., description="Lesson ID to quiz on")
    user_checkin: Optional[str] = Field(
        None,
        description="User's check-in message (what they learned)"
    )


class AnswerEvaluationResponse(BaseModel):
    """Evaluation result for an answer."""

    is_correct: bool
    confidence: float
    engagement_level: str
    key_concepts_covered: list
    key_concepts_missed: list
    feedback: str


class QuizAnswerRequest(BaseModel):
    """Request body for POST /api/quiz/answer."""

    session_id: int = Field(..., description="Quiz session ID")
    user_answer: str = Field(..., description="User's answer to the current question")


class QuizAnswerResponse(BaseModel):
    """Response after submitting an answer."""

    success: bool
    evaluation: AnswerEvaluationResponse
    next_action: str  # 'continue', 'followup', 'end'
    reason: str
    next_question: Optional[str] = None
    question_count: int
    summary_ready: bool = False


class QuizStatusResponse(BaseModel):
    """Response for quiz status."""

    success: bool
    session_id: int
    status: str  # 'active', 'completed'
    question_count: int
    answer_count: int
    has_summary: bool
    lesson_name: str
    user_id: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class WeakConceptSummary(BaseModel):
    """Summary of a weak concept."""

    concept: str
    user_answer: str
    correct_explanation: str


class QuizSummaryResponse(BaseModel):
    """Response for quiz summary."""

    success: bool
    session_id: int
    summary_id: int
    concepts_mastered: list
    concepts_weak: list  # List of WeakConceptSummary
    summary_text: str
    suggestions: list
    engagement_quality: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/start", tags=["Quiz"])
async def start_quiz(
    request: QuizStartRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Initialize a quiz session and get the first question.

    Creates a QuizSession record, loads lesson content and concepts,
    and generates the first question via LLM.

    Args:
        request: QuizStartRequest with user_id, lesson_id, and optional user_checkin
        db: Database session

    Returns:
        dict with:
            - success: Boolean indicating success
            - session_id: The created quiz session ID
            - first_question: The first question for the quiz
            - lesson_name: Name of the lesson
            - concepts: List of concepts being tested

    Raises:
        HTTPException 404: If user or lesson not found
        HTTPException 500: On service errors

    Example:
        POST /api/quiz/start
        {
            "user_id": 1,
            "lesson_id": 5,
            "user_checkin": "I learned useState hooks"
        }
    """
    try:
        quiz_service = get_quiz_service()
        result = quiz_service.start_quiz(
            user_id=request.user_id,
            lesson_id=request.lesson_id,
            user_checkin=request.user_checkin,
            db_session=db
        )

        logger.info(f"Quiz session {result['session_id']} started for user {request.user_id}")

        return {
            "success": True,
            "message": "Quiz started. Answer the question to begin.",
            "session_id": result["session_id"],
            "first_question": result["first_question"],
            "lesson_name": result["lesson_name"],
            "concepts": result["concepts"]
        }

    except ValueError as e:
        logger.error(f"Validation error in start_quiz: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in start_quiz: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start quiz"
        )


@router.post("/answer", response_model=QuizAnswerResponse, tags=["Quiz"])
async def submit_answer(
    request: QuizAnswerRequest,
    db: Session = Depends(get_db)
) -> QuizAnswerResponse:
    """
    Submit an answer to the current quiz question.

    Evaluates the answer, saves it, and decides the next action:
    - continue: Ask the next question
    - followup: Ask a follow-up question on the same topic
    - end: Quiz is complete, summary is ready

    Args:
        request: QuizAnswerRequest with session_id and user_answer
        db: Database session

    Returns:
        QuizAnswerResponse with evaluation, next action, and next question if applicable

    Raises:
        HTTPException 404: If quiz session not found or not active
        HTTPException 500: On service errors

    Example:
        POST /api/quiz/answer
        {
            "session_id": 1,
            "user_answer": "useState is used to manage state in functional components"
        }
    """
    try:
        quiz_service = get_quiz_service()
        result = quiz_service.submit_answer(
            session_id=request.session_id,
            user_answer=request.user_answer,
            db_session=db
        )

        logger.info(
            f"Answer submitted for session {request.session_id}, "
            f"next action: {result['next_action']}"
        )

        # Build response
        return QuizAnswerResponse(
            success=True,
            evaluation=AnswerEvaluationResponse(**result["evaluation"]),
            next_action=result["next_action"],
            reason=result["reason"],
            next_question=result.get("next_question"),
            question_count=result["question_count"],
            summary_ready=result.get("summary_ready", False)
        )

    except ValueError as e:
        logger.error(f"Validation error in submit_answer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in submit_answer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit answer"
        )


@router.get("/status/{session_id}", response_model=QuizStatusResponse, tags=["Quiz"])
async def get_quiz_status(
    session_id: int,
    db: Session = Depends(get_db)
) -> QuizStatusResponse:
    """
    Get the current status of a quiz session.

    Returns information about the quiz including number of questions asked,
    answers submitted, and whether the quiz is complete.

    Args:
        session_id: The quiz session ID
        db: Database session

    Returns:
        QuizStatusResponse with session status and progress

    Raises:
        HTTPException 404: If quiz session not found
        HTTPException 500: On service errors

    Example:
        GET /api/quiz/status/1
    """
    try:
        quiz_service = get_quiz_service()
        status_result = quiz_service.get_quiz_status(
            session_id=session_id,
            db_session=db
        )

        return QuizStatusResponse(
            success=True,
            **status_result
        )

    except ValueError as e:
        logger.error(f"Validation error in get_quiz_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in get_quiz_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quiz status"
        )


@router.get("/summary/{session_id}", response_model=QuizSummaryResponse, tags=["Quiz"])
async def get_quiz_summary(
    session_id: int,
    db: Session = Depends(get_db)
) -> QuizSummaryResponse:
    """
    Get or generate the post-quiz summary.

    Retrieves the quiz session and all answers, generates a comprehensive
    summary using the LLM if not already created, and returns the summary.

    This endpoint should only be called after the quiz is completed
    (when submit_answer returns next_action='end').

    Args:
        session_id: The quiz session ID
        db: Database session

    Returns:
        QuizSummaryResponse with mastered/weak concepts and recommendations

    Raises:
        HTTPException 404: If quiz session not found
        HTTPException 500: On service errors

    Example:
        GET /api/quiz/summary/1
    """
    try:
        # Verify session exists and is completed
        quiz_session = db.query(QuizSession).filter(
            QuizSession.session_id == session_id
        ).first()

        if not quiz_session:
            raise ValueError(f"Quiz session {session_id} not found")

        if quiz_session.status != "completed":
            raise ValueError(
                f"Quiz session {session_id} is not completed "
                f"(current status: {quiz_session.status})"
            )

        # Generate or retrieve summary
        quiz_service = get_quiz_service()
        summary_result = quiz_service.get_or_generate_summary(
            session_id=session_id,
            db_session=db
        )

        logger.info(f"Summary retrieved for session {session_id}")

        return QuizSummaryResponse(
            success=True,
            session_id=session_id,
            summary_id=summary_result["summary_id"],
            concepts_mastered=summary_result["concepts_mastered"],
            concepts_weak=summary_result["concepts_weak"],
            summary_text=summary_result.get("summary_text", ""),
            suggestions=summary_result.get("suggestions", []),
            engagement_quality=summary_result.get("engagement_quality", "medium")
        )

    except ValueError as e:
        logger.error(f"Validation error in get_quiz_summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in get_quiz_summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quiz summary"
        )
