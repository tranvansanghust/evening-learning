"""
Development bot runner with auto-reload.

Watches app/ for file changes and automatically restarts the bot.
Use this during development instead of bot_polling.py directly.

Usage:
    cd backend
    source eveninig-learning-venv/bin/activate
    python bot_dev.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from watchfiles import run_process


def _start_bot():
    """Entry point run in subprocess by watchfiles."""
    from app.bot_polling import main
    asyncio.run(main())


if __name__ == "__main__":
    watch_dir = Path(__file__).parent / "app"
    print("🔄 Bot dev runner — auto-reload enabled")
    print(f"📁 Watching: {watch_dir}")
    print("⏹️  Ctrl+C to stop\n")

    run_process(str(watch_dir), target=_start_bot)
