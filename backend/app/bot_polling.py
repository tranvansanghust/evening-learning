"""
Telegram Bot with Polling (for local development)

This script runs the Telegram bot in polling mode for local testing.
Use this instead of webhook setup for development.

Usage:
    python app/bot_polling.py

Make sure:
    1. FastAPI server is running (uvicorn app.main:app --reload)
    2. MySQL database is set up
    3. .env file is configured
    4. TELEGRAM_BOT_TOKEN is set in .env
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.routers.telegram_handlers import router as handlers_router

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def send_daily_reminders(bot: Bot) -> None:
    """Gửi reminder cho users có giờ nhắc khớp với giờ hiện tại."""
    from app.database import SessionLocal
    from app.models import User, UserCourse

    current_time = datetime.now().strftime("%H:%M")
    db = SessionLocal()
    try:
        users_to_remind = (
            db.query(User)
            .join(UserCourse, UserCourse.user_id == User.user_id)
            .filter(
                User.reminder_time == current_time,
                UserCourse.status == "IN_PROGRESS",
            )
            .all()
        )
        for user in users_to_remind:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text="🔔 Đến giờ học rồi!\n\nGõ /today để xem bài học hôm nay 📚",
                )
                logger.info(f"Sent reminder to user {user.user_id}")
            except Exception as e:
                logger.warning(f"Failed to send reminder to {user.telegram_id}: {e}")
    finally:
        db.close()


async def send_spaced_repetition_reminders(bot: Bot) -> None:
    """8h sáng: nhắc users cần ôn lại bài."""
    from app.database import SessionLocal
    from app.services.progress_service import ProgressService

    db = SessionLocal()
    try:
        due_reviews = ProgressService.get_due_reviews(db_session=db)
        for summary, user in due_reviews:
            lesson_name = "bài học"
            if summary.quiz_session and summary.quiz_session.lesson:
                lesson_name = summary.quiz_session.lesson.title
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        f"🔁 Đến giờ ôn lại rồi!\n\n"
                        f"📖 Bài: <b>{lesson_name}</b>\n\n"
                        "Gõ /done để bắt đầu quiz ôn tập nhé! 💪"
                    ),
                    parse_mode="HTML",
                )
                summary.next_review_at = None
                db.commit()
                logger.info(f"Sent spaced repetition reminder to user {user.user_id}")
            except Exception as e:
                logger.warning(f"Failed spaced rep reminder to {user.telegram_id}: {e}")
    finally:
        db.close()


async def send_reengagement_messages(bot: Bot) -> None:
    """9h sáng: nhắc users bỏ học theo thang +1/+3/+5 ngày."""
    from app.database import SessionLocal
    from app.models import User, UserCourse, Course
    from app.services.message_formatter import build_reengagement_message

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        rows = (
            db.query(UserCourse, User, Course)
            .join(User, User.user_id == UserCourse.user_id)
            .join(Course, Course.course_id == UserCourse.course_id)
            .filter(UserCourse.status == "IN_PROGRESS")
            .all()
        )
        for enrollment, user, course in rows:
            if not enrollment.last_activity_at:
                continue
            days_inactive = (now - enrollment.last_activity_at).days
            if days_inactive not in (1, 3, 5):
                continue
            msg = build_reengagement_message(days_inactive, course.name)
            if not msg:
                continue
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=msg,
                    parse_mode="HTML",
                )
                logger.info(f"Re-engagement +{days_inactive}d sent to user {user.user_id}")
            except Exception as e:
                logger.warning(f"Failed re-engagement to {user.telegram_id}: {e}")
    finally:
        db.close()


async def set_bot_commands(bot: Bot) -> None:
    """Set up bot commands displayed to users."""
    commands = [
        BotCommand(command="start", description="🚀 Start onboarding"),
        BotCommand(command="today", description="📚 View today's lesson"),
        BotCommand(command="done", description="✅ Finish learning & start quiz"),
        BotCommand(command="progress", description="📊 View your progress"),
        BotCommand(command="review", description="📖 Review past quizzes"),
        BotCommand(command="review_topic", description="🔍 Review by topic"),
        BotCommand(command="answer", description="💬 Submit quiz answer"),
        BotCommand(command="resume", description="▶️ Resume learning"),
        BotCommand(command="pause", description="⏸ Pause reminders"),
        BotCommand(command="cancel", description="❌ Huỷ quiz đang chạy"),
        BotCommand(command="reset", description="🔄 Reset trạng thái nếu bị kẹt"),
        BotCommand(command="help", description="❓ Show help"),
    ]

    await bot.set_my_commands(
        commands=commands,
        scope=BotCommandScopeDefault()
    )
    logger.info("✅ Bot commands registered")


async def main() -> None:
    """Main entry point for the bot."""
    scheduler = None
    try:
        if not settings.telegram_bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env")
            sys.exit(1)

        # Initialize bot and dispatcher
        bot = Bot(token=settings.telegram_bot_token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Include routers
        dp.include_router(handlers_router)

        # Set up commands
        await set_bot_commands(bot)

        # Get bot info
        me = await bot.get_me()
        logger.info(f"🤖 Bot started: @{me.username}")
        logger.info(f"📍 Bot ID: {me.id}")
        logger.info(f"✅ Polling mode active - listening for messages...")

        # Log connection info
        logger.info("=" * 60)
        logger.info("TELEGRAM BOT POLLING")
        logger.info("=" * 60)
        logger.info(f"Bot: @{me.username}")
        logger.info(f"FastAPI: http://localhost:{settings.api_port}")
        logger.info(f"Database: {settings.db_host}:{settings.db_port}")
        logger.info("=" * 60)

        # Khởi động scheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            send_daily_reminders,
            trigger="cron",
            minute="*",
            args=[bot],
        )
        scheduler.add_job(
            send_spaced_repetition_reminders,
            trigger="cron",
            hour="8",
            minute="0",
            args=[bot],
        )
        scheduler.add_job(
            send_reengagement_messages,
            trigger="cron",
            hour="9",
            minute="0",
            args=[bot],
        )
        scheduler.start()
        logger.info("✅ Reminder scheduler started")

        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if scheduler is not None:
            scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
        sys.exit(0)
