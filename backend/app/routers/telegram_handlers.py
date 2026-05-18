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

import asyncio
import logging
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
)
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.orm import Session

from app.services.onboarding_service import OnboardingService
from app.services.progress_service import ProgressService
from app.services.quiz_service import QuizService
from app.services.llm_service import LLMService
from app.services.question_store import make_question_store
from app.config import settings
from app.services.llm_topic_suggester import LLMTopicSuggester
from app.services.message_formatter import format_progress, format_quiz_list, format_quiz_detail
from app.services.llm_assessment import LLMAssessmentGenerator
from app.database import SessionLocal
from app.routers.lesson_helpers import _send_lesson_link

logger = logging.getLogger(__name__)

# Aiogram router for polling mode
router = Router()

# Redis-backed question store singleton (lazy connection on first use)
_question_store = make_question_store(settings.redis_url)


def _format_quiz_message(question: str, list_answer: list) -> str:
    """Format question with numbered choices as message text."""
    import html
    labels = ["A", "B", "C", "D"]
    choices = "\n".join(
        f"<b>{labels[i]}.</b> {html.escape(str(ans))}" for i, ans in enumerate(list_answer)
    )
    return f"{html.escape(question)}\n\n{choices}"


def _make_quiz_keyboard(session_id: int, question_id: str, list_answer: list) -> InlineKeyboardMarkup:
    """Build inline keyboard with A/B/C label buttons only (choices shown in message text)."""
    labels = ["A", "B", "C", "D"]
    buttons = [[
        InlineKeyboardButton(
            text=labels[i],
            callback_data=f"quiz:{session_id}:{question_id}:{i}",
        )
        for i in range(len(list_answer))
    ]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_preset_menu() -> tuple[str, InlineKeyboardMarkup]:
    """Build the preset-course selection shown in /start."""
    from app.services.lesson_loader import LessonLoader
    courses = LessonLoader().list_courses()
    lines = [f"📚 <b>{c['title']}</b> ({c['total_lessons']} bài)" for c in courses]
    buttons = [[
        InlineKeyboardButton(
            text=f"📚 {c['title']}",
            callback_data=f"preset:{c['slug']}",
        )
    ] for c in courses]
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


def _make_llm_service() -> LLMService:
    return LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )


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
            # Đang giữa chừng onboarding → tiếp tục
            logger.info(f"User {user.user_id} resuming onboarding at step: {ob_state.current_step}")
            await message.answer(
                f"👋 Chào lại {username}! Bạn đang chọn khoá học dở, tiếp tục nhé.\n\n"
                "Nhập tên chủ đề hoặc link Udemy bạn muốn học:"
            )
        else:
            # Chưa có state → hiển thị menu khoá học có sẵn
            logger.info(f"Showing course menu for user {user.user_id}")
            preset_text, preset_keyboard = _build_preset_menu()
            if preset_text:
                intro = (
                    f"👋 Chào {username}! Mình là học bạn AI của bạn 🤖\n\n"
                    "Mình có sẵn các khoá học sau:\n\n"
                    f"{preset_text}\n\n"
                    "Nhấn để bắt đầu ngay, hoặc nhập tên chủ đề bạn muốn học 👇"
                )
                await message.answer(intro, parse_mode="HTML", reply_markup=preset_keyboard)
            else:
                # Không có khoá học sẵn → vào onboarding bình thường
                onboarding_service.create_onboarding_state(user.user_id)
                onboarding_service.update_onboarding_state(
                    user_id=user.user_id, current_step="course_input"
                )
                await message.answer(
                    f"👋 Chào {username}! Mình là học bạn AI của bạn 🤖\n\n"
                    "Bạn muốn học gì?\n(Paste link Udemy hoặc gõ tên chủ đề)"
                )
    except Exception as e:
        logger.error(f"Error in cmd_start for telegram_id {telegram_id}: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại sau!")
    finally:
        db.close()


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    from datetime import datetime
    from app.models import User, UserCourse, Course
    from app.config import settings

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
            # Kiểm tra user đã PASS khoá nào chưa
            passed = (
                db.query(UserCourse)
                .filter(UserCourse.user_id == user.user_id, UserCourse.status == "PASS")
                .first()
            )
            if passed:
                passed_course = db.query(Course).filter(Course.course_id == passed.course_id).first()
                course_name = passed_course.name if passed_course else "khoá học"
                await message.answer(
                    f"🏆 Bạn đã hoàn thành khoá <b>{course_name}</b> rồi!\n\n"
                    "Gõ /start để chọn khoá học mới.",
                    parse_mode="HTML",
                )
            else:
                await message.answer("Bạn chưa có khoá học nào. Gõ /start để chọn khoá học!")
            return

        course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
        lesson = get_current_lesson(user.user_id, enrollment.course_id, db)

        if not lesson:
            # Tất cả lessons đã done — update status PASS lần đầu
            enrollment.status = "PASS"
            enrollment.completed_at = datetime.utcnow()
            db.commit()

            # Gợi ý chủ đề tiếp — fallback gracefully nếu LLM lỗi
            next_msg = ""
            try:
                llm_client = LLMService(
                    api_key=settings.llm_api_key,
                    base_url=settings.llm_base_url,
                    fast_model=settings.llm_fast_model,
                    smart_model=settings.llm_smart_model,
                )
                suggester = LLMTopicSuggester(
                    client=llm_client.client,
                    fast_model=settings.llm_fast_model,
                )
                async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
                    suggestions = await asyncio.to_thread(suggester.suggest_next_topics, course.name)
                next_msg = f"\n\n🎯 <b>Bạn có thể học tiếp:</b>\n{suggestions}"
            except Exception as llm_err:
                logger.warning(f"LLM suggest_next_topics failed (ignored): {llm_err}")

            await message.answer(
                f"🎉 <b>Chúc mừng!</b> Bạn đã hoàn thành khoá học <b>{course.name}</b>!\n\n"
                f"Bạn đã làm rất tốt 💪{next_msg}\n\n"
                "Gõ /start để bắt đầu khoá học mới.",
                parse_mode="HTML",
            )
            return

        from app.models import Lesson as LessonModel
        previous_lesson = db.query(LessonModel).filter(
            LessonModel.course_id == lesson.course_id,
            LessonModel.sequence_number == lesson.sequence_number - 1,
        ).first()
        await _send_lesson_link(message, lesson, course, db, previous_lesson=previous_lesson)
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

        # Guard: đang onboarding thật → không cho /done
        onboarding_service = OnboardingService(db)
        ob_state = onboarding_service.get_onboarding_state(user.user_id)
        if ob_state is not None:
            await message.answer("Bạn đang onboarding dở. Hãy hoàn thành onboarding trước!")
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

        # Update last_activity_at
        enrollment.last_activity_at = datetime.utcnow()
        db.commit()

        lesson = get_current_lesson(user.user_id, enrollment.course_id, db)
        if not lesson:
            await message.answer("Bạn đã hoàn thành tất cả bài học rồi! 🎉 Gõ /today để xem tổng kết.")
            return

        from app.models import Course, Lesson as LessonModel
        course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
        course_name = course.name if course else ""

        llm_service = _make_llm_service()

        if not lesson.content_markdown or lesson.content_markdown.startswith("```"):
            from app.services.llm_content_generator import LLMContentGenerator
            total_lessons = db.query(LessonModel).filter(LessonModel.course_id == enrollment.course_id).count()
            generator = LLMContentGenerator(client=llm_service.client, smart_model=settings.llm_smart_model)
            async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
                await asyncio.to_thread(
                    lambda: generator.get_or_generate(lesson=lesson, course_topic=course_name, total_lessons=total_lessons, db=db)
                )

        quiz_service = QuizService(llm_service, _question_store)
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            result = await asyncio.to_thread(
                lambda: quiz_service.start_quiz(
                    user_id=user.user_id,
                    lesson_id=lesson.lesson_id,
                    user_checkin=None,
                    db_session=db,
                )
            )

        keyboard = _make_quiz_keyboard(result["session_id"], result["question_id"], result["list_answer"])
        quiz_msg = _format_quiz_message(result["question"], result["list_answer"])
        await message.answer(
            f"Tốt lắm! Bắt đầu quiz <b>{lesson.title}</b> thôi 📝\n\n{quiz_msg}",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Error in cmd_done for {telegram_id}: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    from app.models import User, QuizSession

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return

        active_session = (
            db.query(QuizSession)
            .filter(QuizSession.user_id == user.user_id, QuizSession.status == "active")
            .first()
        )
        if not active_session and not user.checkin_pending:
            await message.answer("Không có quiz nào đang chạy.")
            return

        if active_session:
            active_session.status = "abandoned"
        if user.checkin_pending:
            user.checkin_pending = False
        db.commit()

        await message.answer(
            "✅ Đã huỷ quiz.\n\nGõ /done để bắt đầu quiz mới, hoặc /today để xem bài học."
        )
    except Exception as e:
        logger.error(f"Error in cmd_cancel: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("progress"))
async def cmd_progress(message: Message) -> None:
    from app.models import User, UserCourse, Course

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return

        # Header: đang học bài gì
        header = ""
        enrollment = (
            db.query(UserCourse)
            .filter(UserCourse.user_id == user.user_id, UserCourse.status == "IN_PROGRESS")
            .first()
        )
        if enrollment:
            course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
            lesson = get_current_lesson(user.user_id, enrollment.course_id, db)
            course_name = course.name if course else "khoá học"
            if lesson:
                header = f"📌 <b>{course_name}</b>\nBài đang học: <b>{lesson.title}</b>\n\n"
            else:
                header = f"📌 <b>{course_name}</b> — Đã hoàn thành! 🎉\n\n"

        progress = ProgressService.get_user_progress(user.user_id, db_session=db)
        await message.answer(header + format_progress(progress), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_progress: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("review"))
async def cmd_review(message: Message) -> None:
    from app.models import User, UserCourse, Course

    telegram_id = str(message.from_user.id)
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return

        # Header: đang học bài gì
        header = ""
        enrollment = (
            db.query(UserCourse)
            .filter(UserCourse.user_id == user.user_id, UserCourse.status == "IN_PROGRESS")
            .first()
        )
        if enrollment:
            course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
            lesson = get_current_lesson(user.user_id, enrollment.course_id, db)
            course_name = course.name if course else "khoá học"
            if lesson:
                header = f"📌 <b>{course_name}</b> — Bài đang học: <b>{lesson.title}</b>\n\n"

        if topic:
            summaries = ProgressService.get_review_by_topic(
                user_id=user.user_id, topic=topic, db_session=db
            )
            if not summaries:
                await message.answer(
                    f"Không tìm thấy quiz nào về <b>{topic}</b>.\n\nGõ /review để xem tất cả.",
                    parse_mode="HTML",
                )
                return
        else:
            summaries = ProgressService.get_quiz_summaries(user.user_id, db_session=db)

        await message.answer(header + format_quiz_list(summaries), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_review: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """Reset toàn bộ: quiz, checkin, onboarding, và course enrollment."""
    from app.models import User, QuizSession, UserCourse

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return

        cleared = []

        # Clear active quiz sessions
        active_sessions = (
            db.query(QuizSession)
            .filter(QuizSession.user_id == user.user_id, QuizSession.status == "active")
            .all()
        )
        if active_sessions:
            for s in active_sessions:
                s.status = "abandoned"
            cleared.append(f"{len(active_sessions)} quiz đang chạy")

        # Clear checkin_pending
        if user.checkin_pending:
            user.checkin_pending = False
            cleared.append("trạng thái checkin")

        # Clear onboarding state
        onboarding_service = OnboardingService(db)
        ob_state = onboarding_service.get_onboarding_state(user.user_id)
        if ob_state is not None:
            onboarding_service.clear_state(user.user_id)
            cleared.append("trạng thái onboarding")

        # Clear course enrollments
        enrollments = (
            db.query(UserCourse)
            .filter(UserCourse.user_id == user.user_id)
            .all()
        )
        if enrollments:
            for e in enrollments:
                db.delete(e)
            cleared.append(f"{len(enrollments)} khoá học")

        db.commit()

        if cleared:
            await message.answer(
                f"✅ Đã reset: {', '.join(cleared)}.\n\n"
                "Gõ /start để chọn khoá học mới!"
            )
        else:
            await message.answer("Không có trạng thái nào cần reset.")
    except Exception as e:
        logger.error(f"Error in cmd_reset: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    from app.models import User, UserCourse, Course

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
            await message.answer("Bạn chưa có khoá học nào đang học. Gõ /start để bắt đầu!")
            return
        course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
        lesson = get_current_lesson(user.user_id, enrollment.course_id, db)
        course_name = course.name if course else "khoá học"
        if lesson:
            await message.answer(
                f"▶️ Tiếp tục học *{course_name}* thôi! 💪\n\n"
                f"Bài tiếp theo: *{lesson.title}*\n\n"
                "Gõ /today để xem bài học.",
                parse_mode="Markdown",
            )
        else:
            await message.answer(f"▶️ Quay lại *{course_name}* thôi! Gõ /today để tiếp tục.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in cmd_resume: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.message(Command("pause"))
async def cmd_pause(message: Message) -> None:
    from app.models import User

    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        reminder = getattr(user, "reminder_time", None) if user else None
        if reminder:
            await message.answer(
                f"⏸ Đã tạm dừng nhắc nhở (thường nhắc lúc {reminder}).\n\nGõ /resume để tiếp tục học."
            )
        else:
            await message.answer("⏸ Đã tạm dừng nhắc nhở.\n\nGõ /resume để tiếp tục học.")
    except Exception as e:
        logger.error(f"Error in cmd_pause: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


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
        "/pause - Tạm dừng nhắc nhở\n"
        "/cancel - Huỷ quiz đang chạy\n"
        "/reset - Reset trạng thái nếu bị kẹt"
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

        # Ưu tiên 1: đang trong onboarding thật (không phải hack "checkin")
        ob_state = onboarding_service.get_onboarding_state(user_id)
        if ob_state is not None and ob_state.current_step != "checkin":
            await _handle_onboarding_step(message, text, user_id, ob_state, onboarding_service)
            return

        # Ưu tiên 2: đang trong quiz — user phải dùng inline button, không nhập text
        active_session = db.query(QuizSession).filter(
            QuizSession.user_id == user_id,
            QuizSession.status == "active",
        ).first() if user_id else None
        if active_session is not None:
            await message.answer("Hãy chọn đáp án bằng cách nhấn vào một trong các nút bên trên nhé! 👆")
            return

        # Ưu tiên 3: user đang ở màn preset menu và gõ chủ đề tùy chọn
        if user_id and text:
            from app.models import UserCourse
            has_course = db.query(UserCourse).filter(
                UserCourse.user_id == user_id,
                UserCourse.status == "IN_PROGRESS",
            ).first()
            if not has_course:
                # Tạo onboarding_state và xử lý như course_input
                onboarding_service.create_onboarding_state(user_id)
                new_state = onboarding_service.update_onboarding_state(
                    user_id=user_id, current_step="course_input"
                )
                await _handle_onboarding_step(message, text, user_id, new_state, onboarding_service)
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
        from app.config import settings

        # Generate dynamic assessment questions via LLM
        llm = LLMService(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            fast_model=settings.llm_fast_model,
            smart_model=settings.llm_smart_model,
        )
        assessor = LLMAssessmentGenerator(client=llm.client, fast_model=settings.llm_fast_model)
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            normalized_title, questions = await asyncio.gather(
                asyncio.to_thread(llm.normalize_course_title, text),
                asyncio.to_thread(assessor.generate_assessment_questions, text),
            )

        onboarding_service.update_onboarding_state(
            user_id=user_id,
            course_topic=normalized_title,
            current_step="q1",
            q1_text=questions["q1"],
            q2_text_if_no=questions["q2_if_no"],
            q2_text_if_yes=questions["q2_if_yes"],
        )
        q1_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Chưa"), KeyboardButton(text="Rồi")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(questions["q1"], reply_markup=q1_keyboard)

    elif step == "q1":
        answer = "never" if any(w in text.lower() for w in ["chưa", "không", "never", "no"]) else "yes"
        onboarding_service.update_onboarding_state(
            user_id=user_id, q1_answer=answer, current_step="q2"
        )
        q2_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Chưa"), KeyboardButton(text="Có rồi")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        q2_text = ob_state.q2_text_if_no if answer == "never" else ob_state.q2_text_if_yes
        await message.answer(q2_text or "Bạn đã có kiến thức nền tảng chưa?", reply_markup=q2_keyboard)

    elif step == "q2":
        answer = "no" if any(w in text.lower() for w in ["chưa", "không", "never", "no"]) else "yes"
        onboarding_service.update_onboarding_state(
            user_id=user_id, q2_answer=answer, current_step="deadline"
        )
        await message.answer(
            "Bạn muốn hoàn thành khoá học trong bao lâu?\n\n"
            "Ví dụ: 1 month, 3 months, 2026-06-01",
            reply_markup=ReplyKeyboardRemove(),
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
        from app.models import Lesson, UserCourse, Course

        reminder_time = text.strip()
        onboarding_service.update_onboarding_state(
            user_id=user_id, reminder_time=reminder_time
        )
        first_lesson = onboarding_service.complete_onboarding(user_id)
        if first_lesson:
            db = onboarding_service.db
            enrollment = db.query(UserCourse).filter(
                UserCourse.user_id == user_id,
            ).order_by(UserCourse.user_course_id.desc()).first()
            course = None
            if enrollment:
                course = db.query(Course).filter(
                    Course.course_id == enrollment.course_id
                ).first()
            await message.answer("🎉 Onboarding hoàn thành! Bắt đầu học thôi 🚀")
            await _send_lesson_link(message, first_lesson, course, db)
        else:
            await message.answer(
                "Onboarding hoàn thành! 🚀\n\nGõ /today để xem bài học đầu tiên."
            )

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


@router.callback_query(F.data.startswith("quiz:"))
async def handle_quiz_callback(callback: CallbackQuery) -> None:
    """Xử lý khi user nhấn nút chọn đáp án MCQ."""
    await callback.answer()  # tắt loading spinner

    parts = callback.data.split(":")
    # format: quiz:{session_id}:{question_id}:{choice_index}
    if len(parts) != 4:
        await callback.message.answer("❌ Dữ liệu không hợp lệ.")
        return

    session_id = int(parts[1])
    question_id = parts[2]
    choice_index = int(parts[3])

    db = SessionLocal()
    try:
        from app.models import QuizSession, UserCourse
        quiz_session = db.query(QuizSession).filter(QuizSession.session_id == session_id).first()
        if not quiz_session or quiz_session.status != "active":
            await callback.message.answer("Quiz đã kết thúc hoặc không tồn tại.")
            return

        llm_service = _make_llm_service()
        quiz_service = QuizService(llm_service, _question_store)

        async with ChatActionSender.typing(bot=callback.message.bot, chat_id=callback.message.chat.id):
            result = await asyncio.to_thread(
                lambda: quiz_service.submit_answer(
                    session_id=session_id,
                    question_id=question_id,
                    choice_index=choice_index,
                    db_session=db,
                )
            )

        import html as _html
        is_correct = result.get("is_correct", False)
        correct_answer = result.get("correct_answer", "")
        feedback = "✅ Đúng rồi!" if is_correct else f"❌ Chưa đúng. Đáp án đúng là: <b>{_html.escape(str(correct_answer))}</b>"
        await callback.message.answer(feedback, parse_mode="HTML")

        next_action = result.get("next_action", "continue")

        if next_action == "end":
            enrollment = db.query(UserCourse).filter(
                UserCourse.user_id == quiz_session.user_id,
                UserCourse.status == "IN_PROGRESS",
            ).first()
            if enrollment:
                enrollment.last_activity_at = datetime.utcnow()
                db.commit()

            lesson_name = quiz_session.lesson.title if quiz_session.lesson else "Bài học"
            try:
                summary_data = quiz_service.get_or_generate_summary(
                    session_id=session_id, db_session=db
                )
                msg = format_quiz_detail(
                    lesson_name=lesson_name,
                    concepts_mastered=summary_data.get("concepts_mastered", []),
                    concepts_weak=summary_data.get("concepts_weak", []),
                )
            except Exception:
                summary = result.get("summary", "")
                msg = (
                    f"Quiz hoàn thành! ✅\n\n{_html.escape(summary)}\n\nGõ /today để xem bài tiếp theo 📚"
                    if summary else "Quiz hoàn thành! ✅\n\nGõ /today để xem bài tiếp theo 📚"
                )
            await callback.message.answer(msg, parse_mode="HTML")
        else:
            next_question = result.get("next_question", "")
            next_question_id = result.get("next_question_id", "")
            next_list_answer = result.get("next_list_answer", [])
            if next_question and next_question_id:
                keyboard = _make_quiz_keyboard(session_id, next_question_id, next_list_answer)
                quiz_msg = _format_quiz_message(next_question, next_list_answer)
                await callback.message.answer(quiz_msg, parse_mode="HTML", reply_markup=keyboard)

    except ValueError as e:
        logger.error(f"Quiz callback error session={session_id}: {e}")
        await callback.message.answer("❌ Có lỗi xảy ra khi xử lý câu trả lời. Thử lại nhé!")
    except Exception as e:
        logger.error(f"Unexpected quiz callback error session={session_id}: {e}")
        await callback.message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()


@router.callback_query(F.data.startswith("preset:"))
async def handle_preset_callback(callback: CallbackQuery) -> None:
    """User chọn một khoá học có sẵn từ menu /start."""
    await callback.answer()

    slug = callback.data.split(":", 1)[1]
    telegram_id = str(callback.from_user.id)

    db = SessionLocal()
    try:
        from app.models import User, UserCourse, Course
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await callback.message.answer("Gõ /start để bắt đầu nhé!")
            return

        active = db.query(UserCourse).filter(
            UserCourse.user_id == user.user_id,
            UserCourse.status == "IN_PROGRESS",
        ).first()
        if active:
            await callback.message.answer(
                "Bạn đang học một khoá rồi! Gõ /today để tiếp tục, hoặc /reset để bắt đầu lại."
            )
            return

        onboarding_service = OnboardingService(db)
        async with ChatActionSender.typing(bot=callback.message.bot, chat_id=callback.message.chat.id):
            first_lesson = await asyncio.to_thread(
                onboarding_service.load_and_enroll_preset_course,
                user.user_id,
                slug,
            )

        if not first_lesson:
            await callback.message.answer("❌ Không tìm thấy khoá học này. Vui lòng thử lại!")
            return

        course = db.query(Course).filter(Course.course_id == first_lesson.course_id).first()
        await callback.message.answer("🎉 Đăng ký thành công! Bắt đầu học thôi 🚀")
        await _send_lesson_link(callback.message, first_lesson, course, db)

    except Exception as e:
        logger.error(f"Preset callback error slug={slug}: {e}", exc_info=True)
        await callback.message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()
