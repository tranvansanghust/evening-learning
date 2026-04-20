"""
Message handlers for Telegram commands and interactions.

This module provides handler functions for various Telegram commands
and user interactions. Handlers receive parsed updates and route them
to appropriate services for business logic processing.

Handlers defined:
- /start: User onboarding flow
- /done: Mark learning session as complete
- /progress: Show user's learning progress
- /resume: Resume a paused learning session
- /review: Review past quiz summaries
- /answer: Submit quiz answer

Handlers integrate with backend services to provide actual functionality
for learning, quizzes, progress tracking, and more.
"""

import logging
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.orm import Session

from app.services.onboarding_service import OnboardingService
from app.services.progress_service import ProgressService
from app.services.quiz_service import QuizService
from app.services.llm_service import LLMService
from app.services.message_formatter import format_progress, format_quiz_list
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Aiogram router for polling mode
router = Router()


def get_current_lesson(user_id: int, course_id: int, db: Session):
    from app.models import Lesson, QuizSession

    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id)
        .order_by(Lesson.sequence_number)
        .all()
    )
    completed_lesson_ids = {
        qs.lesson_id
        for qs in db.query(QuizSession).filter(
            QuizSession.user_id == user_id,
            QuizSession.status == "completed",
        ).all()
        if qs.status == "completed"
    }
    for lesson in lessons:
        if lesson.lesson_id not in completed_lesson_ids:
            return lesson
    return None


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    from app.models import User

    telegram_id = str(message.from_user.id)
    username = message.from_user.username or f"user_{telegram_id}"

    db = SessionLocal()
    try:
        onboarding_service = OnboardingService(db)

        # Tìm hoặc tạo user
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = onboarding_service.create_user(telegram_id=telegram_id, username=username)
            logger.info(f"Created user {user.user_id} for telegram_id {telegram_id}")

        # Kiểm tra onboarding state
        ob_state = onboarding_service.get_onboarding_state(user.user_id)

        if ob_state is not None:
            # Đang giữa chừng onboarding → tiếp tục từ bước hiện tại
            logger.info(f"User {user.user_id} resuming onboarding at step: {ob_state.current_step}")
            await message.answer(
                f"👋 Chào lại {username}! Bạn đang onboarding dở, tiếp tục nhé.\n\n"
                "Bạn muốn học gì?\n"
                "(Paste link Udemy hoặc gõ tên chủ đề)"
            )
        else:
            # Chưa có state → bắt đầu onboarding mới
            logger.info(f"Creating onboarding state for user {user.user_id}")
            onboarding_service.create_onboarding_state(user.user_id)
            onboarding_service.update_onboarding_state(
                user_id=user.user_id, current_step="course_input"
            )
            logger.info(f"Onboarding state created for user {user.user_id}, step=course_input")
            await message.answer(
                f"👋 Chào {username}! Mình là học bạn AI của bạn 🤖\n\n"
                "Mình giúp bạn:\n"
                "• Học có hệ thống 📚\n"
                "• Kiểm tra hiểu biết qua quiz 📝\n"
                "• Theo dõi tiến độ 📈\n\n"
                "Bạn muốn học gì?\n"
                "(Paste link Udemy hoặc gõ tên chủ đề)"
            )
    except Exception as e:
        logger.error(f"Error in cmd_start for telegram_id {telegram_id}: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại sau!")
    finally:
        db.close()


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    from app.models import User, UserCourse, Lesson, Course

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return

        enrollment = (
            db.query(UserCourse)
            .filter(UserCourse.user_id == user.user_id, UserCourse.status == "IN_PROGRESS")
            .first()
        )
        if not enrollment:
            await message.answer("Bạn chưa có khoá học nào. Gõ /start để chọn khoá học!")
            return

        course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
        lesson = get_current_lesson(user.user_id, enrollment.course_id, db)
        if not lesson:
            await message.answer(
                f"🎉 Bạn đã hoàn thành toàn bộ khoá học *{course.name}*!\n\n"
                "Gõ /progress để xem kết quả.",
                parse_mode="Markdown",
            )
            return

        await message.answer(
            f"📚 Khoá học: *{course.name}*\n\n"
            f"📖 Bài hiện tại: *{lesson.title}*\n\n"
            f"{lesson.description or ''}\n\n"
            f"⏱ Thời lượng: ~{lesson.estimated_duration_minutes or 60} phút\n\n"
            "Học xong thì gõ /done nhé! 💪",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Error in cmd_today for {telegram_id}: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("done"))
async def cmd_done(message: Message) -> None:
    from app.models import User, UserCourse, Lesson, QuizSession

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return

        # Đang có quiz active rồi
        active_session = (
            db.query(QuizSession)
            .filter(QuizSession.user_id == user.user_id, QuizSession.status == "active")
            .first()
        )
        if active_session:
            await message.answer("Bạn đang làm quiz rồi! Trả lời câu hỏi hiện tại nhé 😊")
            return

        # Kiểm tra có course chưa
        enrollment = (
            db.query(UserCourse)
            .filter(UserCourse.user_id == user.user_id, UserCourse.status == "IN_PROGRESS")
            .first()
        )
        if not enrollment:
            await message.answer("Bạn chưa có khoá học. Gõ /start để chọn khoá học!")
            return

        # Set state "checkin" → handle_text sẽ nhận text tiếp theo
        onboarding_service = OnboardingService(db)
        ob_state = onboarding_service.get_onboarding_state(user.user_id)
        if ob_state is None:
            onboarding_service.create_onboarding_state(user.user_id)
        onboarding_service.update_onboarding_state(user_id=user.user_id, current_step="checkin")

        await message.answer(
            "Tốt lắm! 🎉\n\n"
            "Hôm nay bạn học được gì?\n\n"
            "Kể mình nghe:\n"
            "• Bạn vừa học bài gì?\n"
            "• Hiểu được những khái niệm gì?\n"
            "• Phần nào còn chưa rõ?"
        )
    except Exception as e:
        logger.error(f"Error in cmd_done for {telegram_id}: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("progress"))
async def cmd_progress(message: Message) -> None:
    from app.models import User

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return
        progress = ProgressService.get_user_progress(user.user_id, db_session=db)
        await message.answer(format_progress(progress), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_progress: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("review"))
async def cmd_review(message: Message) -> None:
    from app.models import User

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return
        summaries = ProgressService.get_quiz_summaries(user.user_id, db_session=db)
        await message.answer(format_quiz_list(summaries), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_review: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    await message.answer("▶️ Quay lại học tiếp thôi! 💪")


@router.message(Command("pause"))
async def cmd_pause(message: Message) -> None:
    await message.answer("⏸ Đã tạm dừng nhắc nhở. Gõ /resume để tiếp tục.")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "❓ Trợ giúp:\n\n"
        "/start - Bắt đầu onboarding\n"
        "/today - Xem bài học hôm nay\n"
        "/done - Hoàn thành & quiz\n"
        "/progress - Tiến độ học tập\n"
        "/review - Xem quiz đã làm\n"
        "/resume - Tiếp tục học\n"
        "/pause - Tạm dừng nhắc nhở"
    )


@router.message()
async def handle_text(message: Message) -> None:
    from app.models import User, QuizSession

    telegram_id = str(message.from_user.id)
    text = (message.text or "").strip()

    db = SessionLocal()
    try:
        onboarding_service = OnboardingService(db)

        # Lấy user từ telegram_id
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        user_id = user.user_id if user else None

        # Ưu tiên 1: đang trong onboarding
        ob_state = onboarding_service.get_onboarding_state(user_id)
        if ob_state is not None:
            await _handle_onboarding_step(message, text, user_id, ob_state, onboarding_service)
            return

        # Ưu tiên 2: đang trong quiz
        active_session = db.query(QuizSession).filter(
            QuizSession.user_id == user_id,
            QuizSession.status == "active",
        ).first() if user_id else None
        if active_session is not None:
            await _handle_quiz_answer(message, text, active_session, db)
            return

        # Fallback
        await message.answer(
            "Gõ /start để bắt đầu học nhé! 👋\n\n"
            "Hoặc dùng các lệnh:\n"
            "/progress - Tiến độ học tập\n"
            "/review - Xem quiz đã làm"
        )
    except Exception as e:
        logger.error(f"Error in handle_text for {telegram_id}: {e}")
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


async def _handle_onboarding_step(
    message: Message,
    text: str,
    user_id: int,
    ob_state,
    onboarding_service: OnboardingService,
) -> None:
    """Route tin nhắn đến đúng bước onboarding."""
    from datetime import date, timedelta

    step = ob_state.current_step

    if step == "course_input":
        # Lưu topic/URL vào state để dùng khi complete_onboarding
        onboarding_service.update_onboarding_state(
            user_id=user_id, course_topic=text, current_step="q1"
        )
        await message.answer(
            "Bạn đã từng xây dựng web app chưa?\n\n"
            "Trả lời: có / chưa"
        )

    elif step == "q1":
        answer = "never" if any(w in text.lower() for w in ["chưa", "không", "never", "no"]) else "yes"
        onboarding_service.update_onboarding_state(
            user_id=user_id, q1_answer=answer, current_step="q2"
        )
        if answer == "never":
            await message.answer("Bạn có biết HTML/CSS chưa?\n\nTrả lời: có / chưa")
        else:
            await message.answer("Bạn đã dùng framework nào khác như React, Vue chưa?\n\nTrả lời: có / chưa")

    elif step == "q2":
        answer = "no" if any(w in text.lower() for w in ["chưa", "không", "never", "no"]) else "yes"
        onboarding_service.update_onboarding_state(
            user_id=user_id, q2_answer=answer, current_step="deadline"
        )
        await message.answer(
            "Bạn muốn hoàn thành khoá học trong bao lâu?\n\n"
            "Ví dụ: 1 month, 3 months, 2026-06-01"
        )

    elif step == "deadline":
        deadline = _parse_deadline(text)
        onboarding_service.update_onboarding_state(
            user_id=user_id, deadline=deadline, current_step="hours"
        )
        await message.answer("Mỗi ngày bạn có thể học bao nhiêu giờ?\n\nVí dụ: 1, 2, 3")

    elif step == "hours":
        try:
            hours = int("".join(filter(str.isdigit, text)) or "1")
        except ValueError:
            hours = 1
        onboarding_service.update_onboarding_state(
            user_id=user_id, hours_per_day=hours, current_step="reminder"
        )
        await message.answer("Bạn muốn nhận nhắc nhở lúc mấy giờ?\n\nVí dụ: 20:00, 21:30")

    elif step == "reminder":
        reminder_time = text.strip()
        onboarding_service.update_onboarding_state(
            user_id=user_id, reminder_time=reminder_time
        )
        first_lesson = onboarding_service.complete_onboarding(user_id)
        if first_lesson:
            await message.answer(
                "Onboarding hoàn thành! Bắt đầu học thôi 🚀\n\n"
                f"📖 Bài học đầu tiên của bạn:\n*{first_lesson.title}*\n\n"
                f"{first_lesson.description or ''}\n\n"
                "Học xong thì gõ /done để làm quiz nhé! 💪",
                parse_mode="Markdown",
            )
        else:
            await message.answer(
                "Onboarding hoàn thành! 🚀\n\nGõ /today để xem bài học đầu tiên."
            )

    elif step == "checkin":
        await _handle_checkin(message, text, user_id, onboarding_service)

    else:
        await message.answer("Gõ /help để xem các lệnh có sẵn.")


def _parse_deadline(text: str):
    """Parse deadline từ text: '3 months', '1 month', hoặc 'YYYY-MM-DD'."""
    from datetime import date, timedelta
    import re

    text = text.lower().strip()

    # "N months"
    m = re.search(r"(\d+)\s*month", text)
    if m:
        months = int(m.group(1))
        return date.today() + timedelta(days=months * 30)

    # "N weeks"
    m = re.search(r"(\d+)\s*week", text)
    if m:
        weeks = int(m.group(1))
        return date.today() + timedelta(weeks=weeks)

    # "YYYY-MM-DD"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Default: 3 months
    return date.today() + timedelta(days=90)


async def _handle_checkin(
    message: Message,
    text: str,
    user_id: int,
    onboarding_service: OnboardingService,
) -> None:
    """User vừa mô tả hôm nay học được gì → start quiz."""
    from app.models import UserCourse, Lesson
    from app.config import settings

    db = onboarding_service.db

    enrollment = (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id, UserCourse.status == "IN_PROGRESS")
        .first()
    )
    if not enrollment:
        await message.answer("Bạn chưa có khoá học. Gõ /start để bắt đầu!")
        return

    lesson = (
        db.query(Lesson)
        .filter(Lesson.course_id == enrollment.course_id)
        .order_by(Lesson.sequence_number)
        .first()
    )
    if not lesson:
        await message.answer("Chưa có bài học nào trong khoá. Liên hệ admin nhé!")
        return

    # Xoá checkin state trước khi start quiz (không tạo course mới)
    onboarding_service.clear_state(user_id)

    llm_service = LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )
    quiz_service = QuizService(llm_service)
    result = quiz_service.start_quiz(
        user_id=user_id,
        lesson_id=lesson.lesson_id,
        user_checkin=text,
        db_session=db,
    )

    await message.answer(
        f"Bắt đầu quiz! 📝\n\n{result['first_question']}"
    )


async def _handle_quiz_answer(message: Message, text: str, active_session, db) -> None:
    """Xử lý câu trả lời quiz, gửi feedback và câu tiếp theo hoặc tổng kết."""
    from app.config import settings

    llm_service = LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )
    quiz_service = QuizService(llm_service)
    result = quiz_service.submit_answer(
        session_id=active_session.session_id,
        user_answer=text,
        db_session=db,
    )

    evaluation = result.get("evaluation", {})
    feedback = evaluation.get("feedback", "")
    next_action = result.get("next_action", "continue")

    if feedback:
        await message.answer(feedback)

    if next_action == "end":
        summary = result.get("summary", "")
        await message.answer(
            f"Quiz hoàn thành! ✅\n\n{summary}\n\nGõ /today để xem bài tiếp theo 📚" if summary
            else "Quiz hoàn thành! ✅\n\nGõ /today để xem bài tiếp theo 📚"
        )
    else:
        next_question = result.get("next_question", "")
        if next_question:
            await message.answer(next_question)
