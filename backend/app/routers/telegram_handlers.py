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

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.orm import Session

from app.services.onboarding_service import OnboardingService
from app.services.progress_service import ProgressService
from app.services.quiz_service import QuizService
from app.services.llm_service import LLMService
from app.services.llm_topic_suggester import LLMTopicSuggester
from app.services.message_formatter import format_progress, format_quiz_list, format_quiz_detail
from app.services.llm_assessment import LLMAssessmentGenerator
from app.database import SessionLocal
from app.routers.lesson_helpers import _send_lesson_link

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

        # Set checkin_pending thay vì hack OnboardingState
        user.checkin_pending = True

        # Update last_activity_at
        enrollment.last_activity_at = datetime.utcnow()
        db.commit()

        # Load current lesson để personalise message
        lesson = get_current_lesson(user.user_id, enrollment.course_id, db)
        if lesson:
            from app.config import settings
            from app.models import Course
            course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
            course_topic = course.name if course else ""
            llm_service = LLMService(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                fast_model=settings.llm_fast_model,
                smart_model=settings.llm_smart_model,
            )
            async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
                checkin_q = await asyncio.to_thread(
                    llm_service.generate_checkin_question,
                    lesson.title,
                    lesson.content_markdown or lesson.description or "",
                    course_topic,
                )
            await message.answer(
                f"Tốt lắm! Bạn vừa học xong *{lesson.title}* 🎉\n\n{checkin_q}",
                parse_mode="Markdown",
            )
        else:
            await message.answer("Tốt lắm! 🎉\n\nHôm nay bạn học được gì? Kể mình nghe nhé!")
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

        progress_service = ProgressService(db)
        if topic:
            summaries = progress_service.get_review_by_topic(
                user_id=user.user_id, topic=topic, db_session=db
            )
            if not summaries:
                await message.answer(
                    f"Không tìm thấy quiz nào về <b>{topic}</b>.\n\nGõ /review để xem tất cả.",
                    parse_mode="HTML",
                )
                return
        else:
            summaries = progress_service.get_quiz_summaries(user.user_id, db_session=db)

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

        # Ưu tiên 2: user đang chờ nhập mô tả bài học (checkin_pending)
        if user and user.checkin_pending:
            await _handle_checkin(message, text, user, db)
            return

        # Ưu tiên 3: đang trong quiz
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


def _is_off_topic(checkin: str, course_name: str, lesson_title: str) -> bool:
    """True nếu checkin không có từ nào liên quan đến course/lesson."""
    checkin_lower = checkin.lower()
    # Lấy các từ có nghĩa (>= 3 ký tự) từ course_name và lesson_title
    topic_words = {
        w.lower() for w in (course_name + " " + lesson_title).split()
        if len(w) >= 3
    }
    return len(topic_words) > 0 and not any(w in checkin_lower for w in topic_words)


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
    user,
    db,
) -> None:
    """User vừa mô tả hôm nay học được gì → start quiz."""
    from app.models import UserCourse, Lesson
    from app.config import settings

    user_id = user.user_id

    enrollment = (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id, UserCourse.status == "IN_PROGRESS")
        .first()
    )
    if not enrollment:
        await message.answer("Bạn chưa có khoá học. Gõ /start để bắt đầu!")
        return

    lesson = get_current_lesson(user_id, enrollment.course_id, db)
    if not lesson:
        await message.answer("Bạn đã hoàn thành tất cả bài học rồi! Gõ /today để xem tổng kết.")
        return

    # Nhắc nhẹ nếu checkin lạc đề
    from app.models import Course
    course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
    course_name = course.name if course else ""
    if _is_off_topic(text, course_name, lesson.title):
        await message.answer(
            f"_Bài hôm nay là *{lesson.title}* ({course_name}) — mình sẽ quiz bạn về nội dung đó nhé 😄_",
            parse_mode="Markdown",
        )

    # Xoá checkin_pending trước khi start quiz
    user.checkin_pending = False
    db.commit()

    llm_service = LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )

    # Ensure content_markdown exists trước khi quiz (generate nếu chưa có)
    if not lesson.content_markdown or lesson.content_markdown.startswith("```"):
        from app.services.llm_content_generator import LLMContentGenerator
        from app.models import Lesson as LessonModel
        total_lessons = db.query(LessonModel).filter(LessonModel.course_id == enrollment.course_id).count()
        generator = LLMContentGenerator(client=llm_service.client, smart_model=settings.llm_smart_model)
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            await asyncio.to_thread(
                lambda: generator.get_or_generate(lesson=lesson, course_topic=course_name, total_lessons=total_lessons, db=db)
            )

    # Evaluate checkin trước — gửi nhận xét cho user
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        feedback = await asyncio.to_thread(
            llm_service.evaluate_checkin,
            text,
            lesson.title,
            lesson.content_markdown or lesson.description or "",
            course_name,
        )
    if feedback:
        await message.answer(feedback)

    quiz_service = QuizService(llm_service)
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        result = await asyncio.to_thread(
            lambda: quiz_service.start_quiz(
                user_id=user_id,
                lesson_id=lesson.lesson_id,
                user_checkin=text,
                db_session=db,
            )
        )

    await message.answer(
        f"Quiz *{lesson.title}* bắt đầu! 📝\n\n{result['first_question']}",
        parse_mode="Markdown",
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
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        result = await asyncio.to_thread(
            lambda: quiz_service.submit_answer(
                session_id=active_session.session_id,
                user_answer=text,
                db_session=db,
            )
        )

    evaluation = result.get("evaluation", {})
    feedback = evaluation.get("feedback", "")
    next_action = result.get("next_action", "continue")
    user_requested_end = result.get("user_requested_end", False)

    if feedback and not user_requested_end:
        await message.answer(feedback)

    if next_action == "end":
        # Update last_activity_at on quiz completion
        from app.models import UserCourse
        enrollment = db.query(UserCourse).filter(
            UserCourse.user_id == active_session.user_id,
            UserCourse.status == "IN_PROGRESS",
        ).first()
        if enrollment:
            enrollment.last_activity_at = datetime.utcnow()
            db.commit()

        lesson_name = active_session.lesson.title if active_session.lesson else "Bài học"
        try:
            summary_data = quiz_service.get_or_generate_summary(
                session_id=active_session.session_id, db_session=db
            )
            msg = format_quiz_detail(
                lesson_name=lesson_name,
                concepts_mastered=summary_data.get("concepts_mastered", []),
                concepts_weak=summary_data.get("concepts_weak", []),
            )
        except Exception:
            summary = result.get("summary", "")
            msg = (
                f"Quiz hoàn thành! ✅\n\n{summary}\n\nGõ /today để xem bài tiếp theo 📚"
                if summary else "Quiz hoàn thành! ✅\n\nGõ /today để xem bài tiếp theo 📚"
            )
        await message.answer(msg, parse_mode="HTML")
    else:
        next_question = result.get("next_question", "")
        if next_question:
            await message.answer(next_question)
