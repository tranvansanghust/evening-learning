"""
FastAPI router for user onboarding flow.

Provides endpoints for the multi-step onboarding process:
- User creation and welcome
- Course/topic input
- Level assessment (Q1, Q2)
- Scheduling (deadline, hours per day, reminder time)
- Curriculum generation and first lesson

All endpoints are designed to be called by Telegram handlers.
Responses follow a standardized JSON format.
"""

import logging
from datetime import datetime, date
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.onboarding_service import OnboardingService
from app.models import User, Lesson

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class StartOnboardingRequest(BaseModel):
    """Request body for /start endpoint."""

    telegram_id: str = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="User's display name")


class StartOnboardingResponse(BaseModel):
    """Response for onboarding start."""

    success: bool
    message: str
    user_id: int
    next_step: str = "course_input"


class CourseInputRequest(BaseModel):
    """Request body for /course_input endpoint."""

    user_id: int = Field(..., description="User ID from start endpoint")
    input_text: str = Field(..., description="Udemy URL or topic name")


class CourseInputResponse(BaseModel):
    """Response for course input."""

    success: bool
    message: str
    detected_type: Optional[str] = Field(None, description="'udemy' or 'topic'")
    course_name: Optional[str] = Field(None, description="Detected course name")
    next_step: str


class LevelQ1Request(BaseModel):
    """Request body for /level_q1 endpoint."""

    user_id: int = Field(..., description="User ID")
    answer: str = Field(..., description="'never' or 'yes'")


class LevelQ1Response(BaseModel):
    """Response for Q1, includes Q2 question."""

    success: bool
    message: str
    question: str = Field(description="Q2 question text")
    question_type: str = Field(description="'q2a' or 'q2b' depending on Q1 answer")
    next_step: str = "level_q2"


class LevelQ2Request(BaseModel):
    """Request body for /level_q2 endpoint."""

    user_id: int = Field(..., description="User ID")
    answer: str = Field(..., description="'no' or 'yes'")


class LevelQ2Response(BaseModel):
    """Response for Q2, includes assessed level."""

    success: bool
    message: str
    assessed_level: int = Field(description="0-3")
    level_description: str = Field(description="Human-readable level")
    next_step: str = "deadline"


class DeadlineRequest(BaseModel):
    """Request body for /deadline endpoint."""

    user_id: int = Field(..., description="User ID")
    deadline_date: str = Field(..., description="ISO format date YYYY-MM-DD")


class DeadlineResponse(BaseModel):
    """Response for deadline input."""

    success: bool
    message: str
    deadline: str
    next_step: str = "hours_per_day"


class HoursPerDayRequest(BaseModel):
    """Request body for /hours_per_day endpoint."""

    user_id: int = Field(..., description="User ID")
    hours: int = Field(..., description="Daily study hours (1-12)")


class HoursPerDayResponse(BaseModel):
    """Response for hours per day input."""

    success: bool
    message: str
    hours_per_day: int
    next_step: str = "reminder_time"


class ReminderTimeRequest(BaseModel):
    """Request body for /reminder_time endpoint."""

    user_id: int = Field(..., description="User ID")
    time: str = Field(..., description="Time in HH:MM format")


class LessonInfo(BaseModel):
    """Information about a lesson."""

    lesson_id: int
    sequence_number: int
    title: str
    description: Optional[str]
    estimated_duration_minutes: Optional[int]


class ReminderTimeResponse(BaseModel):
    """Response for reminder time, includes curriculum generated."""

    success: bool
    message: str
    reminder_time: str
    curriculum_generated: bool
    first_lesson: Optional[LessonInfo] = Field(None, description="First lesson to study")
    total_lessons: int
    estimated_total_hours: float


class OnboardingStatusResponse(BaseModel):
    """Response for onboarding status."""

    success: bool
    user_id: int
    current_step: str
    course_id: Optional[int]
    assessed_level: Optional[int]
    deadline: Optional[str]
    hours_per_day: Optional[int]
    reminder_time: Optional[str]


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: str
    detail: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/start",
    response_model=StartOnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start onboarding",
    description="Create a new user and initialize onboarding state"
)
async def start_onboarding(
    request: StartOnboardingRequest,
    db: Session = Depends(get_db)
) -> StartOnboardingResponse:
    """
    Start the onboarding flow for a new user.

    Creates a new user in the system and initializes their onboarding state.
    The user should then provide course/topic information.

    Args:
        request: Contains telegram_id and optional username
        db: Database session

    Returns:
        StartOnboardingResponse: Confirmation and next step

    Raises:
        HTTPException: If user already exists or database error occurs

    Example:
        POST /api/onboard/start
        {
            "telegram_id": "123456789",
            "username": "john_doe"
        }
    """
    try:
        service = OnboardingService(db)

        # Create user
        user = service.create_user(request.telegram_id, request.username)

        # Initialize onboarding state
        state = service.create_onboarding_state(user.user_id)

        logger.info(f"Started onboarding for user {user.user_id}")

        return StartOnboardingResponse(
            success=True,
            message=f"Welcome {user.username}! Let's set up your learning journey.",
            user_id=user.user_id,
            next_step="course_input"
        )

    except ValueError as e:
        logger.error(f"Validation error in start_onboarding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in start_onboarding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start onboarding"
        )


@router.post(
    "/course_input",
    response_model=CourseInputResponse,
    summary="Process course/topic input",
    description="Parse Udemy URL or topic name and prepare for assessment"
)
async def course_input(
    request: CourseInputRequest,
    db: Session = Depends(get_db)
) -> CourseInputResponse:
    """
    Process user's course/topic input.

    Detects whether input is a Udemy URL or a general topic.
    - If Udemy: Fetch curriculum, confirm with user
    - If topic: Skip to assessment questions (Q1)

    Args:
        request: Contains user_id and input_text
        db: Database session

    Returns:
        CourseInputResponse: Detection result and next step

    Example:
        POST /api/onboard/course_input
        {
            "user_id": 1,
            "input_text": "https://www.udemy.com/course/react-complete-guide/"
        }
    """
    try:
        service = OnboardingService(db)

        # Get onboarding state
        state = service.get_onboarding_state(request.user_id)
        if not state:
            raise ValueError(f"No onboarding state found for user {request.user_id}")

        # Detect course input
        detected_type, detected_value = service.detect_course_from_input(request.input_text)

        if not detected_type:
            raise ValueError("Invalid input. Please provide a Udemy URL or topic name.")

        if detected_type == "udemy":
            # Fetch curriculum from Udemy
            curriculum = service.fetch_udemy_curriculum(detected_value)

            # Create course from curriculum
            course = service.create_course_from_curriculum(
                course_name=f"Udemy Course: {detected_value}",
                course_slug=detected_value,
                curriculum=curriculum,
                source="udemy",
                source_id=detected_value
            )

            # Update onboarding state
            state = service.update_onboarding_state(
                request.user_id,
                current_step="confirm_course",
                course_id=course.course_id
            )

            logger.info(f"User {request.user_id} selected Udemy course {course.course_id}")

            return CourseInputResponse(
                success=True,
                message=f"Found: {detected_value}",
                detected_type="udemy",
                course_name=detected_value,
                next_step="confirm_course"
            )

        else:  # topic
            # For topic input, move directly to assessment
            state = service.update_onboarding_state(
                request.user_id,
                current_step="level_q1"
            )

            logger.info(f"User {request.user_id} entered topic: {detected_value}")

            return CourseInputResponse(
                success=True,
                message=f"Topic: {detected_value}",
                detected_type="topic",
                course_name=detected_value,
                next_step="level_q1"
            )

    except ValueError as e:
        logger.error(f"Validation error in course_input: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in course_input: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process course input"
        )


@router.post(
    "/level_q1",
    response_model=LevelQ1Response,
    summary="Submit Q1 assessment answer",
    description="Store Q1 answer and return Q2 (Q2a or Q2b based on Q1)"
)
async def level_q1(
    request: LevelQ1Request,
    db: Session = Depends(get_db)
) -> LevelQ1Response:
    """
    Process Q1 assessment answer.

    Q1: Have you built a web app before?
    - Answer: "never" or "yes"

    Response includes Q2 question:
    - If Q1="never" → Q2a: Do you know HTML/CSS?
    - If Q1="yes" → Q2b: Have you used other frameworks?

    Args:
        request: Contains user_id and answer
        db: Database session

    Returns:
        LevelQ1Response: Q2 question based on Q1 answer

    Example:
        POST /api/onboard/level_q1
        {
            "user_id": 1,
            "answer": "yes"
        }
    """
    try:
        service = OnboardingService(db)

        # Validate answer
        if request.answer.lower() not in ("never", "yes"):
            raise ValueError("Invalid answer. Must be 'never' or 'yes'")

        # Get and update state
        state = service.get_onboarding_state(request.user_id)
        if not state:
            raise ValueError(f"No onboarding state for user {request.user_id}")

        state = service.update_onboarding_state(
            request.user_id,
            current_step="level_q2",
            q1_answer=request.answer.lower()
        )

        logger.info(f"User {request.user_id} answered Q1: {request.answer}")

        # Determine Q2 based on Q1
        if request.answer.lower() == "never":
            q2_text = "Do you know HTML/CSS?"
            q2_type = "q2a"
        else:  # "yes"
            q2_text = "Have you used other frameworks (Vue, Angular, etc)?"
            q2_type = "q2b"

        return LevelQ1Response(
            success=True,
            message="Great! Next question...",
            question=q2_text,
            question_type=q2_type,
            next_step="level_q2"
        )

    except ValueError as e:
        logger.error(f"Validation error in level_q1: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in level_q1: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Q1 answer"
        )


@router.post(
    "/level_q2",
    response_model=LevelQ2Response,
    summary="Submit Q2 assessment answer",
    description="Store Q2 answer and determine user level"
)
async def level_q2(
    request: LevelQ2Request,
    db: Session = Depends(get_db)
) -> LevelQ2Response:
    """
    Process Q2 assessment answer and determine level.

    Based on Q1 and Q2 answers, assigns a level (0-3):
    - Q1: never + Q2a: no → Level 0 (Beginner)
    - Q1: never + Q2a: yes → Level 1 (Intermediate)
    - Q1: yes + Q2b: no → Level 2 (Advanced)
    - Q1: yes + Q2b: yes → Level 3 (Expert)

    Args:
        request: Contains user_id and answer
        db: Database session

    Returns:
        LevelQ2Response: Assessed level and description

    Example:
        POST /api/onboard/level_q2
        {
            "user_id": 1,
            "answer": "yes"
        }
    """
    try:
        service = OnboardingService(db)

        # Validate answer
        if request.answer.lower() not in ("no", "yes"):
            raise ValueError("Invalid answer. Must be 'no' or 'yes'")

        # Get state and Q1 answer
        state = service.get_onboarding_state(request.user_id)
        if not state or not state.q1_answer:
            raise ValueError(f"Invalid state for user {request.user_id}")

        # Assess level
        level = service.assess_level(state.q1_answer, request.answer.lower())

        # Update state with level and move to deadline
        state = service.update_onboarding_state(
            request.user_id,
            current_step="deadline",
            q2_answer=request.answer.lower(),
            assessed_level=level
        )

        # Update user's level
        user = service.db.query(User).filter(User.user_id == request.user_id).first()
        if user:
            user.level = level
            service.db.commit()

        logger.info(f"User {request.user_id} assessed at level {level}")

        # Level descriptions
        level_descriptions = {
            0: "Beginner - Starting from basics",
            1: "Intermediate - Know HTML/CSS",
            2: "Advanced - Web app experience",
            3: "Expert - Framework experience"
        }

        return LevelQ2Response(
            success=True,
            message="Assessment complete!",
            assessed_level=level,
            level_description=level_descriptions.get(level, ""),
            next_step="deadline"
        )

    except ValueError as e:
        logger.error(f"Validation error in level_q2: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in level_q2: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Q2 answer"
        )


@router.post(
    "/deadline",
    response_model=DeadlineResponse,
    summary="Submit course deadline",
    description="Store target completion date"
)
async def deadline(
    request: DeadlineRequest,
    db: Session = Depends(get_db)
) -> DeadlineResponse:
    """
    Process deadline input.

    Accepts a date in ISO format (YYYY-MM-DD) as the target
    course completion date.

    Args:
        request: Contains user_id and deadline_date
        db: Database session

    Returns:
        DeadlineResponse: Confirmation and next step

    Raises:
        HTTPException: If date is invalid or in the past

    Example:
        POST /api/onboard/deadline
        {
            "user_id": 1,
            "deadline_date": "2025-05-31"
        }
    """
    try:
        service = OnboardingService(db)

        # Parse and validate date
        try:
            deadline_date = datetime.strptime(request.deadline_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")

        if deadline_date <= date.today():
            raise ValueError("Deadline must be in the future")

        # Update state
        state = service.update_onboarding_state(
            request.user_id,
            current_step="hours_per_day",
            deadline=deadline_date
        )

        logger.info(f"User {request.user_id} set deadline: {deadline_date}")

        return DeadlineResponse(
            success=True,
            message=f"Great! Deadline set to {deadline_date.strftime('%B %d, %Y')}",
            deadline=deadline_date.isoformat(),
            next_step="hours_per_day"
        )

    except ValueError as e:
        logger.error(f"Validation error in deadline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in deadline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process deadline"
        )


@router.post(
    "/hours_per_day",
    response_model=HoursPerDayResponse,
    summary="Submit daily study hours",
    description="Store available hours per day for learning"
)
async def hours_per_day(
    request: HoursPerDayRequest,
    db: Session = Depends(get_db)
) -> HoursPerDayResponse:
    """
    Process daily study hours input.

    Args:
        request: Contains user_id and hours (1-12)
        db: Database session

    Returns:
        HoursPerDayResponse: Confirmation and next step

    Raises:
        HTTPException: If hours are invalid

    Example:
        POST /api/onboard/hours_per_day
        {
            "user_id": 1,
            "hours": 2
        }
    """
    try:
        service = OnboardingService(db)

        # Validate hours
        if not (1 <= request.hours <= 12):
            raise ValueError("Hours per day must be between 1 and 12")

        # Update state
        state = service.update_onboarding_state(
            request.user_id,
            current_step="reminder_time",
            hours_per_day=request.hours
        )

        logger.info(f"User {request.user_id} set daily hours: {request.hours}")

        return HoursPerDayResponse(
            success=True,
            message=f"Perfect! {request.hours} hour(s) per day is a solid commitment.",
            hours_per_day=request.hours,
            next_step="reminder_time"
        )

    except ValueError as e:
        logger.error(f"Validation error in hours_per_day: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in hours_per_day: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process hours per day"
        )


@router.post(
    "/reminder_time",
    response_model=ReminderTimeResponse,
    summary="Submit reminder time and generate curriculum",
    description="Store preferred reminder time and create personalized curriculum"
)
async def reminder_time(
    request: ReminderTimeRequest,
    db: Session = Depends(get_db)
) -> ReminderTimeResponse:
    """
    Process reminder time and generate curriculum.

    This is the final step of onboarding:
    1. Store reminder time preference
    2. Generate personalized curriculum
    3. Return first lesson to study

    Args:
        request: Contains user_id and time in HH:MM format
        db: Database session

    Returns:
        ReminderTimeResponse: Confirmation, curriculum info, and first lesson

    Example:
        POST /api/onboard/reminder_time
        {
            "user_id": 1,
            "time": "09:00"
        }
    """
    try:
        service = OnboardingService(db)

        # Validate time format
        try:
            time_parts = request.time.split(":")
            if len(time_parts) != 2:
                raise ValueError()
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except (ValueError, IndexError):
            raise ValueError("Invalid time format. Use HH:MM (24-hour)")

        # Get current state
        state = service.get_onboarding_state(request.user_id)
        if not state:
            raise ValueError(f"No onboarding state for user {request.user_id}")

        if not state.deadline or not state.hours_per_day:
            raise ValueError("Missing deadline or hours per day information")

        # Update reminder time
        state = service.update_onboarding_state(
            request.user_id,
            current_step="completed",
            reminder_time=request.time
        )

        # Generate curriculum
        course = None
        first_lesson = None
        total_lessons = 0
        estimated_hours = 0.0

        if state.course_id:
            from app.models import Course
            course = db.query(Course).filter(Course.course_id == state.course_id).first()

            if course:
                # Generate curriculum schedule
                lessons = service.create_curriculum(
                    course=course,
                    user_level=state.assessed_level or 0,
                    deadline=state.deadline,
                    hours_per_day=state.hours_per_day
                )

                total_lessons = len(lessons)
                estimated_hours = sum(
                    (l.estimated_duration_minutes or 60) / 60
                    for l in lessons
                )

                # Get first lesson
                first_lesson = service.get_first_lesson(course.course_id)

                # Create user course enrollment
                enrollment = service.save_user_course_enrollment(
                    request.user_id,
                    course.course_id
                )

                logger.info(
                    f"Generated curriculum for user {request.user_id}: "
                    f"{total_lessons} lessons, {estimated_hours:.1f} hours"
                )

        # Clean up onboarding state
        service.complete_onboarding(request.user_id)

        # Prepare response
        first_lesson_info = None
        if first_lesson:
            first_lesson_info = LessonInfo(
                lesson_id=first_lesson.lesson_id,
                sequence_number=first_lesson.sequence_number,
                title=first_lesson.title,
                description=first_lesson.description,
                estimated_duration_minutes=first_lesson.estimated_duration_minutes
            )

        return ReminderTimeResponse(
            success=True,
            message="Your learning journey is ready!",
            reminder_time=request.time,
            curriculum_generated=True,
            first_lesson=first_lesson_info,
            total_lessons=total_lessons,
            estimated_total_hours=estimated_hours
        )

    except ValueError as e:
        logger.error(f"Validation error in reminder_time: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in reminder_time: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process reminder time or generate curriculum"
        )


@router.get(
    "/status/{user_id}",
    response_model=OnboardingStatusResponse,
    summary="Get onboarding status",
    description="Retrieve current onboarding progress for a user"
)
async def onboarding_status(
    user_id: int,
    db: Session = Depends(get_db)
) -> OnboardingStatusResponse:
    """
    Get the current onboarding status for a user.

    Returns all relevant information about the user's progress through
    the onboarding flow.

    Args:
        user_id: ID of the user
        db: Database session

    Returns:
        OnboardingStatusResponse: Current onboarding state

    Example:
        GET /api/onboard/status/1
    """
    try:
        service = OnboardingService(db)

        # Get onboarding state
        state = service.get_onboarding_state(user_id)

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No onboarding state found for user {user_id}"
            )

        return OnboardingStatusResponse(
            success=True,
            user_id=user_id,
            current_step=state.current_step,
            course_id=state.course_id,
            assessed_level=state.assessed_level,
            deadline=state.deadline.isoformat() if state.deadline else None,
            hours_per_day=state.hours_per_day,
            reminder_time=state.reminder_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in onboarding_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve onboarding status"
        )
