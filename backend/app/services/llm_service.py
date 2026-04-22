"""
LLM Service for Claude API integration.

This module provides the LLMService class which handles all AI interactions
for the learning system. It manages quiz question generation, answer evaluation,
quiz progression, summary generation, and course recommendations.

Uses Anthropic's Claude API with Pydantic models for type-safe responses.
"""

import logging
import json
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field
import httpx
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from app.services.llm_prompts import LLMPrompts

logger = logging.getLogger(__name__)


class EngagementLevel(str, Enum):
    """Engagement level categories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """Quiz action types for progression."""
    CONTINUE = "continue"
    FOLLOWUP = "followup"
    END = "end"


class ConversationMessage(BaseModel):
    """Represents a single message in the conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class AnswerEvaluation(BaseModel):
    """Structured evaluation of a user's answer."""
    is_correct: bool = Field(..., description="Whether the answer is fundamentally correct")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in evaluation (0.0-1.0)"
    )
    engagement_level: EngagementLevel = Field(..., description="Quality of response engagement")
    key_concepts_covered: List[str] = Field(
        default_factory=list,
        description="Concepts the student demonstrated understanding of"
    )
    key_concepts_missed: List[str] = Field(
        default_factory=list,
        description="Concepts the student failed to address or misunderstood"
    )
    feedback: str = Field(..., description="Constructive feedback for the student")


class NextAction(BaseModel):
    """Decision for next quiz action."""
    action_type: ActionType = Field(..., description="continue/followup/end")
    reason: str = Field(..., description="Explanation for the decision")
    follow_up_question: Optional[str] = Field(
        None,
        description="Follow-up question if action_type is 'followup'"
    )


class WeakConcept(BaseModel):
    """Represents a concept the student struggled with."""
    concept: str = Field(..., description="Concept name")
    user_answer: str = Field(..., description="What the student answered")
    correct_explanation: str = Field(..., description="What the correct understanding is")


class QuizSummary(BaseModel):
    """Post-quiz summary with mastery information."""
    concepts_mastered: List[str] = Field(
        default_factory=list,
        description="Concepts student clearly understands"
    )
    concepts_weak: List[WeakConcept] = Field(
        default_factory=list,
        description="Concepts student struggled with"
    )
    engagement_quality: EngagementLevel = Field(..., description="Overall engagement level")
    summary_text: str = Field(..., description="Summary of performance")
    suggestions: List[str] = Field(..., description="Recommendations for next steps")


class CourseSuggestion(BaseModel):
    """A suggested next course."""
    course_name: str = Field(..., description="Name of the suggested course")
    reason: str = Field(..., description="Why this course is a good next step")


class LLMService:
    """
    Service for managing all AI interactions via OpenAI-compatible API.

    Handles quiz generation, evaluation, summarization, and recommendations.
    Supports any OpenAI-compatible endpoint (OpenAI, OpenRouter, local models, etc.).
    """

    def __init__(self, api_key: str, base_url: str, fast_model: str, smart_model: str):
        """
        Initialize the LLMService with custom API credentials.

        Args:
            api_key: API key for the LLM provider
            base_url: Base URL of the OpenAI-compatible API
            fast_model: Model name for fast/cheap tasks
            smart_model: Model name for complex tasks

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        self.FAST_MODEL = fast_model
        self.SMART_MODEL = smart_model
        # Explicit proxy map: dùng HTTP proxy cho HTTPS, bỏ qua ALL_PROXY socks5h (httpx không hỗ trợ)
        # max_retries=3: tự retry khi gặp 503 (server overloaded)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        logger.info(f"LLMService initialized (base_url={base_url}, fast={fast_model}, smart={smart_model})")

    def generate_quiz_question(
        self,
        lesson_content: str,
        conversation_history: List[Dict[str, str]],
        concepts: List[str],
        is_first_question: bool = True
    ) -> str:
        """
        Generate a natural conversational quiz question.

        Uses claude-haiku-4-5 (fast model) for simple question generation.

        Args:
            lesson_content: The lesson text the user just learned
            conversation_history: List of previous Q&A pairs as [{"role": "user"|"assistant", "content": "..."}]
            concepts: List of concept names to test
            is_first_question: Whether this is the first question in the quiz

        Returns:
            str: The generated question

        Raises:
            ValueError: If lesson_content or concepts are empty
            APIError: On Anthropic API errors
            RateLimitError: If rate limit exceeded

        Example:
            >>> service = LLMService(api_key)
            >>> question = await service.generate_quiz_question(
            ...     lesson_content="SQL WHERE clause...",
            ...     conversation_history=[],
            ...     concepts=["WHERE", "conditions"],
            ...     is_first_question=True
            ... )
        """
        if not lesson_content or not lesson_content.strip():
            raise ValueError("lesson_content cannot be empty")
        if not concepts or not any(c.strip() for c in concepts):
            raise ValueError("At least one concept must be provided")

        prompt = LLMPrompts.quiz_question_generation(
            lesson_content=lesson_content,
            conversation_history=conversation_history,
            concepts=concepts,
            is_first_question=is_first_question
        )

        try:
            message = self.client.chat.completions.create(
                model=self.FAST_MODEL,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý tạo câu hỏi ôn tập kiến thức. Nhiệm vụ của bạn là tạo các câu hỏi ngắn gọn bằng tiếng Việt dựa trên nội dung bài học được cung cấp."},
                    {"role": "user", "content": prompt}
                ]
            )

            question = message.choices[0].message.content.strip()
            logger.info(f"Generated quiz question (first={is_first_question}, concepts={len(concepts)})")
            return question

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded when generating question: {str(e)}")
            raise
        except APITimeoutError as e:
            logger.error(f"API timeout when generating question: {str(e)}")
            raise
        except APIError as e:
            logger.error(f"API error when generating question: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating question: {str(e)}")
            raise

    def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        lesson_context: str,
        concepts: List[str]
    ) -> AnswerEvaluation:
        """
        Evaluate if a user's answer is correct and extract insights.

        Uses claude-sonnet-4-6 (smart model) for accurate evaluation.

        Args:
            question: The question that was asked
            user_answer: The user's response
            lesson_context: The lesson content for reference
            concepts: Key concepts being tested

        Returns:
            AnswerEvaluation: Structured evaluation with correctness, confidence, engagement, and concept coverage

        Raises:
            ValueError: If inputs are empty
            APIError: On Anthropic API errors

        Example:
            >>> evaluation = await service.evaluate_answer(
            ...     question="What is a WHERE clause?",
            ...     user_answer="It filters rows based on conditions",
            ...     lesson_context="WHERE is used to filter...",
            ...     concepts=["WHERE", "filtering"]
            ... )
            >>> print(evaluation.is_correct, evaluation.engagement_level)
            True medium
        """
        if not question or not user_answer or not lesson_context:
            raise ValueError("question, user_answer, and lesson_context are required")

        prompt = LLMPrompts.answer_evaluation(
            question=question,
            user_answer=user_answer,
            lesson_context=lesson_context,
            concepts=concepts
        )

        try:
            message = self.client.chat.completions.create(
                model=self.SMART_MODEL,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý đánh giá câu trả lời học viên. Chỉ trả về JSON object theo đúng format yêu cầu, không thêm text khác."},
                    {"role": "user", "content": prompt}
                ]
            )

            raw = message.choices[0].message.content
            if not raw or not raw.strip():
                raise ValueError("LLM returned empty response for evaluation")
            response_text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            evaluation_dict = json.loads(response_text)

            evaluation = AnswerEvaluation(
                is_correct=evaluation_dict.get("is_correct", False),
                confidence=float(evaluation_dict.get("confidence", 0.5)),
                engagement_level=evaluation_dict.get("engagement_level", "medium"),
                key_concepts_covered=evaluation_dict.get("key_concepts_covered", []),
                key_concepts_missed=evaluation_dict.get("key_concepts_missed", []),
                feedback=evaluation_dict.get("feedback", "")
            )

            logger.info(
                f"Evaluated answer (correct={evaluation.is_correct}, "
                f"engagement={evaluation.engagement_level}, "
                f"concepts_covered={len(evaluation.key_concepts_covered)})"
            )
            return evaluation

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation JSON: {str(e)}")
            raise
        except (APIError, RateLimitError, APITimeoutError) as e:
            logger.error(f"API error when evaluating answer: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error evaluating answer: {str(e)}")
            raise

    def decide_next_action(
        self,
        answer_evaluation: AnswerEvaluation,
        question_count: int,
        max_questions: int = 5
    ) -> NextAction:
        """
        Decide whether to continue, follow-up, or end the quiz.

        Uses claude-haiku-4-5 (fast model) for quick decision making.

        Args:
            answer_evaluation: The evaluation result from evaluate_answer
            question_count: Number of questions asked so far (1-indexed)
            max_questions: Maximum questions before mandatory end (default: 5)

        Returns:
            NextAction: Decision with action type and optional follow-up question

        Raises:
            APIError: On Anthropic API errors

        Example:
            >>> evaluation = AnswerEvaluation(...)
            >>> action = await service.decide_next_action(
            ...     answer_evaluation=evaluation,
            ...     question_count=2,
            ...     max_questions=5
            ... )
            >>> if action.action_type == "end":
            ...     print("Quiz complete")
        """
        evaluation_dict = answer_evaluation.model_dump()

        prompt = LLMPrompts.decide_next_action(
            answer_evaluation=evaluation_dict,
            question_count=question_count,
            max_questions=max_questions
        )

        try:
            message = self.client.chat.completions.create(
                model=self.FAST_MODEL,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý quyết định bước tiếp theo trong buổi ôn tập. Chỉ trả về JSON object theo đúng format yêu cầu, không thêm text khác."},
                    {"role": "user", "content": prompt}
                ]
            )

            raw = message.choices[0].message.content
            if not raw or not raw.strip():
                raise ValueError("LLM returned empty response for next action")
            response_text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            decision_dict = json.loads(response_text)

            action = NextAction(
                action_type=decision_dict.get("action_type", "continue"),
                reason=decision_dict.get("reason", ""),
                follow_up_question=decision_dict.get("follow_up_question")
            )

            logger.info(f"Decision made: {action.action_type} (q{question_count}/{max_questions})")
            return action

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse decision JSON: {str(e)}")
            raise
        except (APIError, RateLimitError, APITimeoutError) as e:
            logger.error(f"API error when deciding next action: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deciding next action: {str(e)}")
            raise

    def generate_quiz_summary(
        self,
        lesson_name: str,
        lesson_content: str,
        conversation_history: List[Dict[str, str]],
        concepts: List[str]
    ) -> QuizSummary:
        """
        Generate a comprehensive post-quiz summary.

        Uses claude-sonnet-4-6 (smart model) for thorough analysis.

        Args:
            lesson_name: Name of the lesson
            lesson_content: The lesson text
            conversation_history: Complete Q&A history from quiz
            concepts: List of all concepts in the lesson

        Returns:
            QuizSummary: Comprehensive summary with mastered/weak concepts and suggestions

        Raises:
            ValueError: If inputs are empty
            APIError: On Anthropic API errors

        Example:
            >>> summary = await service.generate_quiz_summary(
            ...     lesson_name="SQL Basics",
            ...     lesson_content="SELECT, WHERE, JOIN...",
            ...     conversation_history=[...],
            ...     concepts=["SELECT", "WHERE", "JOIN"]
            ... )
            >>> print(summary.summary_text)
        """
        if not lesson_name or not conversation_history:
            raise ValueError("lesson_name and conversation_history are required")

        prompt = LLMPrompts.quiz_summary_generation(
            lesson_name=lesson_name,
            lesson_content=lesson_content,
            conversation_history=conversation_history,
            concepts=concepts
        )

        try:
            message = self.client.chat.completions.create(
                model=self.SMART_MODEL,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý tổng kết buổi ôn tập kiến thức. Chỉ trả về JSON object theo đúng format yêu cầu, không thêm text khác."},
                    {"role": "user", "content": prompt}
                ]
            )

            raw = message.choices[0].message.content
            if not raw or not raw.strip():
                raise ValueError("LLM returned empty response for quiz summary")
            response_text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            summary_dict = json.loads(response_text)

            # Parse weak concepts with nested structure
            weak_concepts = []
            for weak in summary_dict.get("concepts_weak", []):
                if isinstance(weak, dict):
                    weak_concepts.append(WeakConcept(
                        concept=weak.get("concept", ""),
                        user_answer=weak.get("user_answer", ""),
                        correct_explanation=weak.get("correct_explanation", "")
                    ))

            summary = QuizSummary(
                concepts_mastered=summary_dict.get("concepts_mastered", []),
                concepts_weak=weak_concepts,
                engagement_quality=summary_dict.get("engagement_quality", "medium"),
                summary_text=summary_dict.get("summary_text", ""),
                suggestions=summary_dict.get("suggestions", [])
            )

            logger.info(
                f"Generated summary (mastered={len(summary.concepts_mastered)}, "
                f"weak={len(summary.concepts_weak)})"
            )
            return summary

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse summary JSON: {str(e)}")
            raise
        except (APIError, RateLimitError, APITimeoutError) as e:
            logger.error(f"API error when generating summary: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating summary: {str(e)}")
            raise

    def suggest_next_courses(
        self,
        completed_course_name: str,
        user_level: int,
        completed_concepts: List[str] = None
    ) -> List[CourseSuggestion]:
        """
        Suggest 3 logical next courses for the user.

        Uses claude-sonnet-4-6 (smart model) for thoughtful recommendations.

        Args:
            completed_course_name: Name of the course just completed (PASS flow)
            user_level: User's skill level (0-3)
                - 0: Beginner
                - 1: Beginner-Intermediate
                - 2: Intermediate
                - 3: Advanced
            completed_concepts: List of concepts mastered (optional)

        Returns:
            List[CourseSuggestion]: 3 recommended next courses with explanations

        Raises:
            ValueError: If course_name is empty or level invalid
            APIError: On Anthropic API errors

        Example:
            >>> suggestions = await service.suggest_next_courses(
            ...     completed_course_name="SQL Basics",
            ...     user_level=1,
            ...     completed_concepts=["SELECT", "WHERE"]
            ... )
            >>> for s in suggestions:
            ...     print(s.course_name, s.reason)
        """
        if not completed_course_name or not completed_course_name.strip():
            raise ValueError("completed_course_name cannot be empty")
        if not 0 <= user_level <= 3:
            raise ValueError("user_level must be between 0 and 3")

        concepts = completed_concepts or []

        prompt = LLMPrompts.suggest_next_courses(
            completed_course_name=completed_course_name,
            user_level=user_level,
            completed_concepts=concepts
        )

        try:
            message = self.client.chat.completions.create(
                model=self.SMART_MODEL,
                max_tokens=800,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý gợi ý lộ trình học tập. Chỉ trả về JSON object theo đúng format yêu cầu, không thêm text khác."},
                    {"role": "user", "content": prompt}
                ]
            )

            raw = message.choices[0].message.content
            if not raw or not raw.strip():
                raise ValueError("LLM returned empty response for course suggestions")
            response_text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            suggestions_dict = json.loads(response_text)

            suggestions = [
                CourseSuggestion(
                    course_name=s.get("course_name", ""),
                    reason=s.get("reason", "")
                )
                for s in suggestions_dict.get("suggestions", [])
            ]

            logger.info(f"Generated {len(suggestions)} course suggestions for level {user_level}")
            return suggestions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse suggestions JSON: {str(e)}")
            raise
        except (APIError, RateLimitError, APITimeoutError) as e:
            logger.error(f"API error when suggesting courses: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error suggesting courses: {str(e)}")
            raise
