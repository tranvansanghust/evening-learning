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

Note:
    These handlers are placeholder infrastructure - actual business logic
    will be implemented by the learning system services.
"""

import logging
from typing import Optional

from app.services.telegram_service import ParsedUpdate, TelegramService

logger = logging.getLogger(__name__)


class TelegramHandlers:
    """
    Handler dispatcher for Telegram messages and commands.

    Manages routing of incoming updates to appropriate command handlers
    and logs all interactions for debugging.
    """

    def __init__(self, telegram_service: TelegramService):
        """
        Initialize handlers with a TelegramService instance.

        Args:
            telegram_service: Service instance for sending messages to users
        """
        self.service = telegram_service
        logger.info("TelegramHandlers initialized")

    async def handle_update(self, update: ParsedUpdate) -> None:
        """
        Main dispatcher for routing updates to appropriate handlers.

        Routes messages to command-specific handlers based on message content.
        If no command is recognized, treats message as regular input for
        the current state.

        Args:
            update: ParsedUpdate object containing user_id, message_text, etc.

        Example:
            >>> handlers = TelegramHandlers(service)
            >>> parsed = ParsedUpdate("123456", "/start", "message")
            >>> await handlers.handle_update(parsed)
        """
        if not update or not update.user_id:
            logger.warning("Invalid update received")
            return

        logger.info(
            f"Handling update from user {update.user_id}: "
            f"type={update.update_type}, text={update.message_text}"
        )

        # Extract command from message text
        message_text = update.message_text or ""
        command = self._extract_command(message_text)

        # Route to appropriate handler
        if command == "start":
            await self.handle_start(update)
        elif command == "done":
            await self.handle_done(update)
        elif command == "progress":
            await self.handle_progress(update)
        elif command == "resume":
            await self.handle_resume(update)
        elif command == "review":
            await self.handle_review(update, message_text)
        else:
            # Handle regular message input (not a command)
            await self.handle_message(update)

    @staticmethod
    def _extract_command(message_text: str) -> Optional[str]:
        """
        Extract command name from message text.

        Handles both "/command" and "/command@botname" formats.
        Returns lowercase command name without leading slash.

        Args:
            message_text: Raw message text from user

        Returns:
            str: Command name (lowercase), or None if message is not a command

        Example:
            >>> TelegramHandlers._extract_command("/start")
            "start"
            >>> TelegramHandlers._extract_command("/review React")
            "review"
            >>> TelegramHandlers._extract_command("Hello")
            None
        """
        if not message_text or not message_text.startswith("/"):
            return None

        parts = message_text.split()
        if not parts:
            return None

        # Remove leading slash and @botname suffix
        command = parts[0].lstrip("/").split("@")[0].lower()
        return command if command else None

    async def handle_start(self, update: ParsedUpdate) -> None:
        """
        Handle /start command - initiate onboarding flow.

        Logs the user's first interaction and sends initial greeting message
        asking for learning topic/URL.

        This is a placeholder that will be replaced with actual onboarding
        logic by the onboarding service.

        Args:
            update: ParsedUpdate containing user_id and message context
        """
        logger.info(f"User {update.user_id} initiated /start command")

        greeting = (
            "Chào bạn! Mình là học bạn AI 👋\n\n"
            "Mình giúp bạn học có hệ thống và biết "
            "mình thực sự đang tiến bộ đến đâu.\n\n"
            "Bạn đang muốn học gì?\n"
            "(paste link Udemy hoặc gõ tên chủ đề)"
        )

        await self.service.send_message(update.user_id, greeting)
        logger.info(f"Sent greeting to user {update.user_id}")

    async def handle_done(self, update: ParsedUpdate) -> None:
        """
        Handle /done command - mark learning session as complete.

        Logs the completion and sends acknowledgment message.
        Transitions user to check-in phase (asking what they learned).

        This is a placeholder for the post-learning summary flow.

        Args:
            update: ParsedUpdate containing user_id and session context
        """
        logger.info(f"User {update.user_id} reported learning session complete")

        response = (
            "Tốt lắm! 🎉\n\n"
            "Hôm nay bạn học đến đâu rồi?\n"
            "Kể mình nghe bạn tiếp thu được gì nào!"
        )

        await self.service.send_message(update.user_id, response)
        logger.info(f"Sent check-in prompt to user {update.user_id}")

    async def handle_progress(self, update: ParsedUpdate) -> None:
        """
        Handle /progress command - show user's learning progress.

        Displays overall progress summary including:
        - Current course/topic
        - Concepts mastered vs. needs review
        - Retention rate
        - Next review dates

        This is a placeholder for the knowledge tracker display.

        Args:
            update: ParsedUpdate containing user_id and progress context
        """
        logger.info(f"User {update.user_id} requested progress view")

        response = (
            "📊 Tiến độ học tập của bạn:\n\n"
            "Tính năng này sẽ hiển thị:\n"
            "• Khoá học hiện tại\n"
            "• Concepts bạn đã nắm chắc\n"
            "• Concepts cần ôn lại\n"
            "• Tỉ lệ retention\n\n"
            "Đang được phát triển..."
        )

        await self.service.send_message(update.user_id, response)
        logger.info(f"Sent progress placeholder to user {update.user_id}")

    async def handle_resume(self, update: ParsedUpdate) -> None:
        """
        Handle /resume command - resume paused learning session.

        Called when user wants to continue learning after skipping
        multiple reminders. Fetches last session and continues from there.

        This is a placeholder for session resumption logic.

        Args:
            update: ParsedUpdate containing user_id and session context
        """
        logger.info(f"User {update.user_id} requested to resume learning")

        response = (
            "Quay lại học tiếp thôi! 💪\n\n"
            "Bài tiếp theo:\n"
            "[Tên bài học]\n\n"
            "Dự kiến: ~45 phút"
        )

        await self.service.send_message(update.user_id, response)
        logger.info(f"Sent resume prompt to user {update.user_id}")

    async def handle_review(
        self,
        update: ParsedUpdate,
        full_message: str
    ) -> None:
        """
        Handle /review command - review past quiz summaries.

        Shows user their past quiz summaries, optionally filtered by topic.

        Usage:
            /review              - Show all recent summaries
            /review React        - Show React-specific summaries
            /review useState     - Show useState-specific summary

        This is a placeholder for the knowledge review display.

        Args:
            update: ParsedUpdate containing user_id and context
            full_message: Full message text including command and arguments

        Example:
            User sends: "/review React"
            Args: ["review", "React"]
            Topic: "React"
        """
        parts = full_message.split(maxsplit=1)
        topic = parts[1] if len(parts) > 1 else None

        logger.info(f"User {update.user_id} requested review of {topic or 'all topics'}")

        if topic:
            response = f"📚 Review: {topic}\n\nCác summary về {topic}:\n[sẽ hiển thị]"
        else:
            response = (
                "📚 Tất cả các summary:\n\n"
                "[Danh sách các quiz summary]\n\n"
                "Gõ /review [tên topic] để xem chi tiết"
            )

        await self.service.send_message(update.user_id, response)
        logger.info(f"Sent review response to user {update.user_id}")

    async def handle_message(self, update: ParsedUpdate) -> None:
        """
        Handle regular message input (not a command).

        Routes message to appropriate handler based on current user state.
        State is determined by the learning system's session tracker.

        Examples:
            - During onboarding: Parse course URL or topic
            - During check-in: Parse what user learned
            - During quiz: Parse quiz answer

        This is a placeholder - actual routing logic depends on user state.

        Args:
            update: ParsedUpdate containing user_id and message content

        Note:
            This handler is a no-op placeholder. Routing to state-specific
            handlers will be implemented by the service layer.
        """
        logger.info(
            f"User {update.user_id} sent regular message: {update.message_text}"
        )

        # TODO: Implement state-based routing:
        # 1. Check user's current state from database
        # 2. Route to appropriate handler:
        #    - onboarding_state: route to onboarding service
        #    - check_in_state: route to check_in service
        #    - quiz_state: route to quiz service
        # 3. Log the action

        logger.debug(f"Message routing to be implemented for user {update.user_id}")
