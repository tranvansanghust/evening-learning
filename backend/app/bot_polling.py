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
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.routers.telegram_handlers import router as handlers_router

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
        BotCommand(command="help", description="❓ Show help"),
    ]

    await bot.set_my_commands(
        commands=commands,
        scope=BotCommandScopeDefault()
    )
    logger.info("✅ Bot commands registered")


async def main() -> None:
    """Main entry point for the bot."""
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

        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
        sys.exit(0)
