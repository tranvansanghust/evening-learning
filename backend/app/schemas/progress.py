"""
Pydantic models for progress and review endpoints.

Provides schemas for:
- User progress tracking
- Quiz summary previews and details
- Concept mastery information
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class UserProgress(BaseModel):
    """
    User's overall learning progress.

    Represents summary progress metrics showing lessons completed
    and concepts mastered.

    Attributes:
        lessons_completed: Number of lessons the user has completed (has quiz summary for)
        total_lessons: Total lessons available in user's enrolled courses
        concepts_mastered: Number of unique concepts mastered (correct answers)
        total_concepts: Total unique concepts available in user's courses
    """

    lessons_completed: int = Field(
        ..., ge=0, description="Number of lessons completed"
    )
    total_lessons: int = Field(..., ge=0, description="Total lessons available")
    concepts_mastered: int = Field(
        ..., ge=0, description="Number of concepts mastered"
    )
    total_concepts: int = Field(..., ge=0, description="Total concepts available")


class ConceptDetail(BaseModel):
    """
    Detailed information about a concept performance.

    Used in quiz summary details to show which concepts were mastered
    and which need improvement.

    Attributes:
        concept: Concept name
        user_answer: What the user answered
        correct_explanation: The correct answer/explanation
    """

    concept: str = Field(..., description="Concept name")
    user_answer: str = Field(..., description="What the user answered")
    correct_explanation: str = Field(..., description="Correct answer/explanation")


class QuizSummaryPreview(BaseModel):
    """
    Brief preview of a quiz summary.

    Used in list views to show quiz history without full details.

    Attributes:
        summary_id: Quiz summary ID
        date: When the quiz was taken (UTC)
        lesson_name: Name of the lesson that was quizzed
        concepts_mastered_count: Number of concepts mastered in this quiz
        concepts_weak_count: Number of weak/incorrect concepts in this quiz
    """

    summary_id: int = Field(..., description="Quiz summary ID")
    date: datetime = Field(..., description="Date quiz was taken")
    lesson_name: str = Field(..., description="Name of the lesson")
    concepts_mastered_count: int = Field(
        ..., ge=0, description="Number of concepts mastered"
    )
    concepts_weak_count: int = Field(
        ..., ge=0, description="Number of weak concepts"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class QuizSummaryDetail(BaseModel):
    """
    Full quiz summary with all details.

    Includes complete information about what was mastered and what needs work.

    Attributes:
        summary_id: Quiz summary ID
        date: When the quiz was taken
        lesson_name: Name of the lesson
        concepts_mastered: List of mastered concept names
        concepts_weak: List of concepts with performance details
    """

    summary_id: int = Field(..., description="Quiz summary ID")
    date: datetime = Field(..., description="Date quiz was taken")
    lesson_name: str = Field(..., description="Name of the lesson")
    concepts_mastered: List[str] = Field(
        default_factory=list, description="List of mastered concept names"
    )
    concepts_weak: List[ConceptDetail] = Field(
        default_factory=list, description="List of weak concepts with explanations"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True
