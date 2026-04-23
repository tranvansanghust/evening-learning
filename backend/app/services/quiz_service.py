"""
Quiz Service for managing the quiz lifecycle.

This service orchestrates the entire quiz flow using the LLM Service.
Handles session creation, answer evaluation, progression logic, and summary generation.

Responsibilities:
    - Create and manage quiz sessions
    - Evaluate user answers with LLM
    - Decide quiz progression (continue, follow-up, end)
    - Generate post-quiz summaries
    - Track quiz status and conversation history
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import QuizSession, QuizAnswer, QuizSummary, Lesson, Concept, User, Course
from app.services.llm_service import LLMService, AnswerEvaluation, ActionType, NextAction

logger = logging.getLogger(__name__)


def _next_review_interval_days(review_count: int) -> int:
    """Return the number of days until next spaced repetition review.

    Intervals: 0 reviews -> 3 days, 1 -> 7, 2 -> 14, 3+ -> 30.
    """
    intervals = {0: 3, 1: 7, 2: 14}
    return intervals.get(review_count, 30)


class QuizService:
    """
    Service for managing quiz sessions and orchestrating the quiz flow.

    Coordinates between the database layer and LLM Service to create a seamless
    quiz experience. Handles the conversation history, determines when to ask questions,
    and tracks mastery of concepts.

    Attributes:
        llm_service (LLMService): Instance of LLMService for AI interactions
    """

    def __init__(self, llm_service: LLMService):
        """
        Initialize QuizService with an LLM Service instance.

        Args:
            llm_service: Configured instance of LLMService
        """
        self.llm_service = llm_service
        logger.info("QuizService initialized")

    def start_quiz(
        self,
        user_id: int,
        lesson_id: int,
        user_checkin: Optional[str],
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Initialize a quiz session and generate the first question.

        Creates a new QuizSession record, loads lesson content and concepts,
        and uses the LLM to generate the first question based on the lesson.

        Args:
            user_id: ID of the user starting the quiz
            lesson_id: ID of the lesson being quizzed on
            user_checkin: Optional user check-in message (Track A external learning)
            db_session: SQLAlchemy database session

        Returns:
            dict with keys:
                - session_id: The created quiz session ID
                - first_question: The generated first question
                - lesson_name: Name of the lesson
                - concepts: List of concept names in the lesson

        Raises:
            ValueError: If user or lesson not found
            Exception: On LLM service errors

        Example:
            >>> result = quiz_service.start_quiz(
            ...     user_id=1,
            ...     lesson_id=5,
            ...     user_checkin="I learned about useState",
            ...     db_session=db
            ... )
            >>> print(result["first_question"])
        """
        try:
            # Load user and lesson
            user = db_session.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            lesson = db_session.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
            if not lesson:
                raise ValueError(f"Lesson {lesson_id} not found")

            # Load course to get topic anchor
            course = db_session.query(Course).filter(Course.course_id == lesson.course_id).first()
            course_topic = course.name if course else lesson.title

            # Load concepts for this lesson
            concepts = db_session.query(Concept).filter(
                Concept.lesson_id == lesson_id
            ).all()

            if not concepts:
                logger.warning(f"Lesson {lesson_id} has no concepts, falling back to lesson title")
                concept_names = [lesson.title]
            else:
                concept_names = [c.name for c in concepts]

            # Create QuizSession record
            quiz_session = QuizSession(
                user_id=user_id,
                lesson_id=lesson_id,
                status="active",
                messages=[]
            )
            db_session.add(quiz_session)
            db_session.flush()  # Get the session_id without committing

            session_id = quiz_session.session_id
            logger.info(f"Created quiz session {session_id} for user {user_id}, lesson {lesson_id}")

            # Build lesson context — prefer content_markdown (task 14), fallback to description
            lesson_content = lesson.content_markdown or lesson.description or f"Bài học về {course_topic}: {lesson.title}"
            if user_checkin:
                # user_checkin is supplementary context only — does NOT override concept_names
                lesson_content = f"{lesson_content}\n\nHọc viên mô tả nội dung học hôm nay: {user_checkin}".strip()

            # Build conversation history (empty for first question)
            conversation_history = []

            # Generate first question
            try:
                first_question = self.llm_service.generate_quiz_question(
                    lesson_content=lesson_content,
                    conversation_history=conversation_history,
                    concepts=concept_names,
                    is_first_question=True,
                    course_topic=course_topic
                )
            except Exception as e:
                logger.error(f"Failed to generate first question for session {session_id}: {str(e)}")
                db_session.rollback()
                raise

            # Save first question (and checkin as metadata) to conversation history
            messages = [{"role": "assistant", "content": first_question}]
            if user_checkin:
                # Store checkin as metadata for submit_answer to use later
                messages.insert(0, {"role": "_checkin", "content": user_checkin})
            quiz_session.messages = messages
            db_session.commit()

            logger.info(f"Quiz session {session_id} started with first question")

            return {
                "session_id": session_id,
                "first_question": first_question,
                "lesson_name": lesson.title,
                "concepts": concept_names,
                "user_checkin": user_checkin
            }

        except ValueError as e:
            logger.error(f"Validation error in start_quiz: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in start_quiz: {str(e)}")
            db_session.rollback()
            raise

    def submit_answer(
        self,
        session_id: int,
        user_answer: str,
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Submit and evaluate a user's answer, then determine next action.

        Loads the active quiz session, evaluates the user's answer with the LLM,
        saves the answer record, and decides whether to continue with another question,
        ask a follow-up, or end the quiz.

        Args:
            session_id: ID of the quiz session
            user_answer: The user's response to the current question
            db_session: SQLAlchemy database session

        Returns:
            dict with keys:
                - evaluation: AnswerEvaluation object with feedback
                - next_action: Action type ('continue', 'followup', 'end')
                - next_question: (if continue/followup) The next question to ask
                - summary_ready: (if end) Boolean indicating summary is ready

        Raises:
            ValueError: If session not found or not active
            Exception: On LLM service errors

        Example:
            >>> result = quiz_service.submit_answer(
            ...     session_id=1,
            ...     user_answer="useState manages state in functional components",
            ...     db_session=db
            ... )
            >>> if result["next_action"] == "end":
            ...     print("Quiz complete")
        """
        try:
            # Load quiz session
            quiz_session = db_session.query(QuizSession).filter(
                QuizSession.session_id == session_id
            ).first()

            if not quiz_session:
                raise ValueError(f"Quiz session {session_id} not found")

            if quiz_session.status != "active":
                raise ValueError(f"Quiz session {session_id} is not active (status: {quiz_session.status})")

            # Load lesson for context
            lesson = quiz_session.lesson

            # Load course to get topic anchor
            course = db_session.query(Course).filter(Course.course_id == lesson.course_id).first()
            course_topic = course.name if course else lesson.title

            # Build lesson context — prefer content_markdown, fallback to description
            lesson_content = lesson.content_markdown or lesson.description or f"Bài học về {course_topic}: {lesson.title}"

            # Load concepts
            concepts = db_session.query(Concept).filter(
                Concept.lesson_id == lesson.lesson_id
            ).all()
            concept_names = [c.name for c in concepts] if concepts else [lesson.title]

            # Get conversation history (may include _checkin metadata)
            all_messages = quiz_session.messages or []

            # Recover user_checkin stored as metadata and add as supplementary context only
            # stored_checkin does NOT override concept_names — course_topic is the anchor
            stored_checkin = next(
                (m["content"] for m in all_messages if m.get("role") == "_checkin"), None
            )
            if stored_checkin:
                lesson_content = f"{lesson_content}\n\nHọc viên mô tả nội dung học hôm nay: {stored_checkin}".strip()

            # Exclude _checkin metadata from conversation history sent to LLM
            messages = [m for m in all_messages if m.get("role") != "_checkin"]

            # Get the last question asked (should be the most recent assistant message)
            current_question = None
            if messages and messages[-1].get("role") == "assistant":
                current_question = messages[-1].get("content")

            if not current_question:
                raise ValueError(f"No current question found for session {session_id}")

            # Evaluate the answer
            try:
                evaluation = self.llm_service.evaluate_answer(
                    question=current_question,
                    user_answer=user_answer,
                    lesson_context=lesson_content,
                    concepts=concept_names,
                    course_topic=course_topic
                )
            except Exception as e:
                logger.error(f"Failed to evaluate answer for session {session_id}: {str(e)}")
                raise

            # Determine which concept this question was testing
            # For now, we'll use the first concept; in a more sophisticated system,
            # we'd track which concept each question addresses
            concept = concepts[0] if concepts else None
            concept_id = concept.concept_id if concept else None

            # Save the answer
            quiz_answer = QuizAnswer(
                session_id=session_id,
                concept_id=concept_id,
                question=current_question,
                user_answer=user_answer,
                is_correct=evaluation.is_correct,
                engagement_level=evaluation.engagement_level.value
            )
            db_session.add(quiz_answer)

            # Update conversation history with user answer
            messages.append({"role": "user", "content": user_answer})

            # Count questions asked so far
            max_questions = 5
            question_count = sum(1 for m in messages if m.get("role") == "assistant")

            # Hard cap: force END if question limit reached
            if question_count >= max_questions:
                forced_end = NextAction(action_type=ActionType.END, reason="Question limit reached")
                next_action = forced_end
            else:
                # Decide next action via LLM
                try:
                    next_action = self.llm_service.decide_next_action(
                        answer_evaluation=evaluation,
                        question_count=question_count,
                        max_questions=max_questions
                    )
                except Exception as e:
                    logger.error(f"Failed to decide next action for session {session_id}: {str(e)}")
                    raise

            result = {
                "evaluation": evaluation.model_dump(),
                "next_action": next_action.action_type.value,
                "reason": next_action.reason,
                "question_count": question_count
            }

            # Handle action
            if next_action.action_type == ActionType.END:
                # Generate summary before ending
                try:
                    summary = self.llm_service.generate_quiz_summary(
                        lesson_name=lesson.title,
                        lesson_content=lesson_content,
                        conversation_history=messages,
                        concepts=concept_names,
                    )
                    result["summary"] = summary.summary_text
                except Exception:
                    result["summary"] = ""

                # End the quiz
                quiz_session.status = "completed"
                quiz_session.completed_at = datetime.utcnow()
                logger.info(f"Quiz session {session_id} ended after {question_count} questions")
                result["summary_ready"] = True

            elif next_action.action_type == ActionType.FOLLOWUP:
                # Ask follow-up question
                if next_action.follow_up_question:
                    follow_up_question = next_action.follow_up_question
                else:
                    # Generate follow-up if not provided
                    try:
                        follow_up_question = self.llm_service.generate_quiz_question(
                            lesson_content=lesson_content,
                            conversation_history=messages,
                            concepts=concept_names,
                            is_first_question=False,
                            course_topic=course_topic
                        )
                    except Exception as e:
                        logger.error(f"Failed to generate follow-up for session {session_id}: {str(e)}")
                        raise

                messages.append({"role": "assistant", "content": follow_up_question})
                result["next_question"] = follow_up_question
                logger.info(f"Quiz session {session_id}: Follow-up question #{question_count + 1}")

            else:  # CONTINUE
                # Generate next question
                try:
                    next_question = self.llm_service.generate_quiz_question(
                        lesson_content=lesson_content,
                        conversation_history=messages,
                        concepts=concept_names,
                        is_first_question=False,
                        course_topic=course_topic
                    )
                except Exception as e:
                    logger.error(f"Failed to generate next question for session {session_id}: {str(e)}")
                    raise

                messages.append({"role": "assistant", "content": next_question})
                result["next_question"] = next_question
                logger.info(f"Quiz session {session_id}: Next question #{question_count + 1}")

            # Update conversation history — re-attach _checkin metadata so it persists
            checkin_entries = [m for m in all_messages if m.get("role") == "_checkin"]
            quiz_session.messages = checkin_entries + messages
            db_session.commit()

            return result

        except ValueError as e:
            logger.error(f"Validation error in submit_answer: {str(e)}")
            db_session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error in submit_answer: {str(e)}")
            db_session.rollback()
            raise

    def get_or_generate_summary(
        self,
        session_id: int,
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Get or generate a post-quiz summary.

        Retrieves the quiz session and all answers, generates a comprehensive
        summary using the LLM, and saves it to the database.

        Args:
            session_id: ID of the quiz session
            db_session: SQLAlchemy database session

        Returns:
            dict with summary data:
                - summary_id: The created summary ID
                - concepts_mastered: List of mastered concept names
                - concepts_weak: List of weak concept objects with explanations
                - summary_text: Full text summary
                - suggestions: Recommendations for next steps

        Raises:
            ValueError: If session not found
            Exception: On LLM service errors

        Example:
            >>> summary = quiz_service.get_or_generate_summary(
            ...     session_id=1,
            ...     db_session=db
            ... )
            >>> print(summary["summary_text"])
        """
        try:
            # Load quiz session
            quiz_session = db_session.query(QuizSession).filter(
                QuizSession.session_id == session_id
            ).first()

            if not quiz_session:
                raise ValueError(f"Quiz session {session_id} not found")

            # Check if summary already exists
            if quiz_session.quiz_summary:
                logger.info(f"Summary already exists for session {session_id}")
                return {
                    "summary_id": quiz_session.quiz_summary.summary_id,
                    "concepts_mastered": quiz_session.quiz_summary.concepts_mastered or [],
                    "concepts_weak": quiz_session.quiz_summary.concepts_weak or [],
                    "session_id": session_id,
                    "already_exists": True
                }

            # Load lesson content
            lesson = quiz_session.lesson
            lesson_content = lesson.description or ""

            # Load all concepts
            concepts = db_session.query(Concept).filter(
                Concept.lesson_id == lesson.lesson_id
            ).all()
            concept_names = [c.name for c in concepts]

            # Get conversation history from quiz session
            messages = quiz_session.messages or []

            # Generate summary
            try:
                llm_summary = self.llm_service.generate_quiz_summary(
                    lesson_name=lesson.title,
                    lesson_content=lesson_content,
                    conversation_history=messages,
                    concepts=concept_names
                )
            except Exception as e:
                logger.error(f"Failed to generate summary for session {session_id}: {str(e)}")
                raise

            # Create QuizSummary record
            # Convert WeakConcept objects to JSON-serializable dicts
            weak_concepts_json = [
                {
                    "concept": wc.concept,
                    "user_answer": wc.user_answer,
                    "correct_explanation": wc.correct_explanation
                }
                for wc in llm_summary.concepts_weak
            ]

            quiz_summary = QuizSummary(
                session_id=session_id,
                user_course_id=None,  # Can be set later if needed
                concepts_mastered=llm_summary.concepts_mastered,
                concepts_weak=weak_concepts_json,
                next_review_at=datetime.utcnow() + timedelta(days=_next_review_interval_days(0)),
                review_count=0,
            )
            db_session.add(quiz_summary)
            db_session.commit()

            logger.info(
                f"Generated summary for session {session_id} "
                f"(mastered={len(llm_summary.concepts_mastered)}, "
                f"weak={len(llm_summary.concepts_weak)})"
            )

            return {
                "summary_id": quiz_summary.summary_id,
                "concepts_mastered": llm_summary.concepts_mastered,
                "concepts_weak": weak_concepts_json,
                "summary_text": llm_summary.summary_text,
                "suggestions": llm_summary.suggestions,
                "engagement_quality": llm_summary.engagement_quality.value,
                "session_id": session_id
            }

        except ValueError as e:
            logger.error(f"Validation error in get_or_generate_summary: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_or_generate_summary: {str(e)}")
            db_session.rollback()
            raise

    def get_quiz_status(
        self,
        session_id: int,
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Get the current status of a quiz session.

        Returns information about the quiz session including status, progress,
        and whether a summary is available.

        Args:
            session_id: ID of the quiz session
            db_session: SQLAlchemy database session

        Returns:
            dict with keys:
                - session_id: The quiz session ID
                - status: 'active' or 'completed'
                - question_count: Number of questions asked so far
                - answer_count: Number of answers submitted
                - has_summary: Whether a summary has been generated
                - lesson_name: Name of the lesson being quizzed on
                - user_id: ID of the user

        Raises:
            ValueError: If session not found

        Example:
            >>> status = quiz_service.get_quiz_status(1, db_session=db)
            >>> print(f"Status: {status['status']}, Questions: {status['question_count']}")
        """
        try:
            quiz_session = db_session.query(QuizSession).filter(
                QuizSession.session_id == session_id
            ).first()

            if not quiz_session:
                raise ValueError(f"Quiz session {session_id} not found")

            # Count questions (assistant messages in conversation)
            messages = quiz_session.messages or []
            question_count = sum(1 for m in messages if m.get("role") == "assistant")

            # Count answers
            answers = db_session.query(QuizAnswer).filter(
                QuizAnswer.session_id == session_id
            ).all()
            answer_count = len(answers)

            return {
                "session_id": session_id,
                "status": quiz_session.status,
                "question_count": question_count,
                "answer_count": answer_count,
                "has_summary": quiz_session.quiz_summary is not None,
                "lesson_name": quiz_session.lesson.title,
                "user_id": quiz_session.user_id,
                "started_at": quiz_session.started_at.isoformat() if quiz_session.started_at else None,
                "completed_at": quiz_session.completed_at.isoformat() if quiz_session.completed_at else None
            }

        except ValueError as e:
            logger.error(f"Validation error in get_quiz_status: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_quiz_status: {str(e)}")
            raise
