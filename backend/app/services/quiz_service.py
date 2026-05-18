"""
Quiz Service for managing the MCQ quiz lifecycle.

Orchestrates session creation, MCQ generation, deterministic answer evaluation
(via Redis-stored correct answers), and summary generation.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import QuizSession, QuizAnswer, QuizSummary, Lesson, Concept, User, Course
from app.services.llm_service import LLMService
from app.services.question_store import QuestionStoreBase, MCQData

logger = logging.getLogger(__name__)


def _next_review_interval_days(review_count: int) -> int:
    """Spaced repetition intervals: 0→3d, 1→7d, 2→14d, 3+→30d."""
    return {0: 3, 1: 7, 2: 14}.get(review_count, 30)


class QuizService:
    """Manages MCQ quiz sessions using Redis for pending question storage."""

    def __init__(self, llm_service: LLMService, question_store: QuestionStoreBase) -> None:
        self.llm_service = llm_service
        self.question_store = question_store
        logger.info("QuizService initialized")

    def _load_lesson_context(self, lesson, course, user_checkin: Optional[str] = None) -> tuple[str, str, List[str]]:
        """Return (lesson_content, course_topic, concept_names)."""
        course_topic = course.name if course else lesson.title
        lesson_content = lesson.content_markdown or lesson.description or f"Bài học về {course_topic}: {lesson.title}"
        if user_checkin:
            lesson_content = f"{lesson_content}\n\nHọc viên mô tả nội dung học hôm nay: {user_checkin}".strip()
        return lesson_content, course_topic

    def _load_concepts(self, lesson_id: int, lesson_title: str, db_session: Session) -> tuple[List[Any], List[str]]:
        concepts = db_session.query(Concept).filter(Concept.lesson_id == lesson_id).all()
        names = [c.name for c in concepts] if concepts else [lesson_title]
        return concepts, names

    def _save_mcq_to_store(self, mcq) -> None:
        self.question_store.save(
            mcq.question_id,
            MCQData(question=mcq.question, list_answer=mcq.list_answer, correct_answer=mcq.correct_answer),
        )

    def start_quiz(
        self,
        user_id: int,
        lesson_id: int,
        user_checkin: Optional[str],
        db_session: Session,
    ) -> Dict[str, Any]:
        """Create a quiz session, generate the first MCQ, store it in Redis.

        Returns: session_id, question_id, question, list_answer, lesson_name, concepts
        """
        try:
            user = db_session.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")

            lesson = db_session.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
            if not lesson:
                raise ValueError(f"Lesson {lesson_id} not found")

            course = db_session.query(Course).filter(Course.course_id == lesson.course_id).first()
            lesson_content, course_topic = self._load_lesson_context(lesson, course, user_checkin)
            _, concept_names = self._load_concepts(lesson_id, lesson.title, db_session)

            quiz_session = QuizSession(user_id=user_id, lesson_id=lesson_id, status="active", messages=[])
            db_session.add(quiz_session)
            db_session.flush()
            session_id = quiz_session.session_id
            logger.info(f"Created quiz session {session_id} for user {user_id}, lesson {lesson_id}")

            try:
                mcq = self.llm_service.generate_mcq_question(
                    lesson_content=lesson_content,
                    concepts=concept_names,
                    conversation_history=[],
                    course_topic=course_topic,
                )
            except Exception as e:
                logger.error(f"Failed to generate first MCQ for session {session_id}: {e}")
                db_session.rollback()
                raise

            self._save_mcq_to_store(mcq)

            messages = [{"role": "assistant", "content": mcq.question}]
            if user_checkin:
                messages.insert(0, {"role": "_checkin", "content": user_checkin})
            quiz_session.messages = messages
            db_session.commit()

            logger.info(f"Quiz session {session_id} started, question_id={mcq.question_id}")
            return {
                "session_id": session_id,
                "question_id": mcq.question_id,
                "question": mcq.question,
                "list_answer": mcq.list_answer,
                "lesson_name": lesson.title,
                "concepts": concept_names,
            }

        except ValueError as e:
            logger.error(f"Validation error in start_quiz: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in start_quiz: {e}")
            db_session.rollback()
            raise

    def submit_answer(
        self,
        session_id: int,
        question_id: str,
        choice_index: int,
        db_session: Session,
    ) -> Dict[str, Any]:
        """Evaluate a MCQ answer deterministically, then generate the next question or end.

        Returns: is_correct, correct_answer, chosen_answer, next_action,
                 and either (next_question_id, next_question, next_list_answer) or (summary, summary_ready).
        """
        try:
            quiz_session = db_session.query(QuizSession).filter(
                QuizSession.session_id == session_id
            ).first()
            if not quiz_session:
                raise ValueError(f"Quiz session {session_id} not found")
            if quiz_session.status != "active":
                raise ValueError(f"Quiz session {session_id} is not active (status: {quiz_session.status})")

            mcq_data = self.question_store.get(question_id)
            if not mcq_data:
                raise ValueError(f"Question {question_id} not found in store (expired or already answered)")

            chosen_answer = mcq_data.list_answer[choice_index]
            is_correct = (chosen_answer == mcq_data.correct_answer)
            self.question_store.delete(question_id)

            lesson = quiz_session.lesson
            course = db_session.query(Course).filter(Course.course_id == lesson.course_id).first()
            all_messages = quiz_session.messages or []
            stored_checkin = next((m["content"] for m in all_messages if m.get("role") == "_checkin"), None)
            lesson_content, course_topic = self._load_lesson_context(lesson, course, stored_checkin)
            concepts, concept_names = self._load_concepts(lesson.lesson_id, lesson.title, db_session)

            messages = [m for m in all_messages if not m.get("role", "").startswith("_")]
            messages.append({"role": "user", "content": chosen_answer})

            question_count = sum(1 for m in messages if m.get("role") == "assistant")

            quiz_answer = QuizAnswer(
                session_id=session_id,
                concept_id=concepts[0].concept_id if concepts else None,
                question=mcq_data.question,
                user_answer=chosen_answer,
                is_correct=is_correct,
                question_id=question_id,
                correct_answer=mcq_data.correct_answer,
                choices=mcq_data.list_answer,
            )
            db_session.add(quiz_answer)

            result: Dict[str, Any] = {
                "is_correct": is_correct,
                "correct_answer": mcq_data.correct_answer,
                "chosen_answer": chosen_answer,
                "question_count": question_count,
            }

            max_questions = 5
            if question_count >= max_questions:
                quiz_session.status = "completed"
                quiz_session.completed_at = datetime.utcnow()
                logger.info(f"Quiz session {session_id} ended after {question_count} questions")

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

                result["next_action"] = "end"
                result["summary_ready"] = True
            else:
                try:
                    next_mcq = self.llm_service.generate_mcq_question(
                        lesson_content=lesson_content,
                        concepts=concept_names,
                        conversation_history=messages,
                        course_topic=course_topic,
                    )
                except Exception as e:
                    logger.error(f"Failed to generate next MCQ for session {session_id}: {e}")
                    raise

                self._save_mcq_to_store(next_mcq)
                messages.append({"role": "assistant", "content": next_mcq.question})

                result["next_action"] = "continue"
                result["next_question_id"] = next_mcq.question_id
                result["next_question"] = next_mcq.question
                result["next_list_answer"] = next_mcq.list_answer

            checkin_entries = [m for m in all_messages if m.get("role") == "_checkin"]
            quiz_session.messages = checkin_entries + messages
            db_session.commit()
            return result

        except ValueError as e:
            logger.error(f"Validation error in submit_answer: {e}")
            db_session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error in submit_answer: {e}")
            db_session.rollback()
            raise

    def get_or_generate_summary(
        self,
        session_id: int,
        db_session: Session,
    ) -> Dict[str, Any]:
        """Get existing summary or generate one via LLM."""
        try:
            quiz_session = db_session.query(QuizSession).filter(
                QuizSession.session_id == session_id
            ).first()
            if not quiz_session:
                raise ValueError(f"Quiz session {session_id} not found")

            if quiz_session.quiz_summary:
                logger.info(f"Summary already exists for session {session_id}")
                return {
                    "summary_id": quiz_session.quiz_summary.summary_id,
                    "concepts_mastered": quiz_session.quiz_summary.concepts_mastered or [],
                    "concepts_weak": quiz_session.quiz_summary.concepts_weak or [],
                    "session_id": session_id,
                    "already_exists": True,
                }

            lesson = quiz_session.lesson
            lesson_content = lesson.description or ""
            _, concept_names = self._load_concepts(lesson.lesson_id, lesson.title, db_session)
            messages = quiz_session.messages or []

            try:
                llm_summary = self.llm_service.generate_quiz_summary(
                    lesson_name=lesson.title,
                    lesson_content=lesson_content,
                    conversation_history=messages,
                    concepts=concept_names,
                )
            except Exception as e:
                logger.error(f"Failed to generate summary for session {session_id}: {e}")
                raise

            weak_concepts_json = [
                {"concept": wc.concept, "user_answer": wc.user_answer, "correct_explanation": wc.correct_explanation}
                for wc in llm_summary.concepts_weak
            ]
            quiz_summary = QuizSummary(
                session_id=session_id,
                user_course_id=None,
                concepts_mastered=llm_summary.concepts_mastered,
                concepts_weak=weak_concepts_json,
                next_review_at=datetime.utcnow() + timedelta(days=_next_review_interval_days(0)),
                review_count=0,
            )
            db_session.add(quiz_summary)
            db_session.commit()

            logger.info(
                f"Generated summary for session {session_id} "
                f"(mastered={len(llm_summary.concepts_mastered)}, weak={len(llm_summary.concepts_weak)})"
            )
            return {
                "summary_id": quiz_summary.summary_id,
                "concepts_mastered": llm_summary.concepts_mastered,
                "concepts_weak": weak_concepts_json,
                "summary_text": llm_summary.summary_text,
                "suggestions": llm_summary.suggestions,
                "engagement_quality": llm_summary.engagement_quality.value,
                "session_id": session_id,
            }

        except ValueError as e:
            logger.error(f"Validation error in get_or_generate_summary: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_or_generate_summary: {e}")
            db_session.rollback()
            raise

    def get_quiz_status(self, session_id: int, db_session: Session) -> Dict[str, Any]:
        """Return current status of a quiz session."""
        try:
            quiz_session = db_session.query(QuizSession).filter(
                QuizSession.session_id == session_id
            ).first()
            if not quiz_session:
                raise ValueError(f"Quiz session {session_id} not found")

            messages = quiz_session.messages or []
            question_count = sum(1 for m in messages if m.get("role") == "assistant")
            answer_count = db_session.query(QuizAnswer).filter(
                QuizAnswer.session_id == session_id
            ).count()

            return {
                "session_id": session_id,
                "status": quiz_session.status,
                "question_count": question_count,
                "answer_count": answer_count,
                "has_summary": quiz_session.quiz_summary is not None,
                "lesson_name": quiz_session.lesson.title,
                "user_id": quiz_session.user_id,
                "started_at": quiz_session.started_at.isoformat() if quiz_session.started_at else None,
                "completed_at": quiz_session.completed_at.isoformat() if quiz_session.completed_at else None,
            }
        except ValueError as e:
            logger.error(f"Validation error in get_quiz_status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_quiz_status: {e}")
            raise
