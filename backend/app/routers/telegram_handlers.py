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

from app.services.telegram_service import ParsedUpdate, TelegramService
from app.services.handler_service import HandlerService
from app.services.onboarding_service import OnboardingService
from app.services.progress_service import ProgressService
from app.services.quiz_service import QuizService
from app.services.llm_service import LLMService
from app.database import SessionLocal
from app.models import QuizSummary

logger = logging.getLogger(__name__)

# Aiogram router for polling mode
router = Router()


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
    await message.answer("📚 Bài học hôm nay đang được tải...")


@router.message(Command("done"))
async def cmd_done(message: Message) -> None:
    await message.answer(
        "Tốt lắm! 🎉\n\n"
        "Hôm nay bạn học đến đâu rồi?\n\n"
        "Hãy kể mình nghe:\n"
        "• Bạn vừa học bài gì?\n"
        "• Hiểu được những khái niệm gì?\n"
        "• Phần nào còn khó hiểu?"
    )


@router.message(Command("progress"))
async def cmd_progress(message: Message) -> None:
    await message.answer("📊 Đang tải tiến độ học tập của bạn...")


@router.message(Command("review"))
async def cmd_review(message: Message) -> None:
    await message.answer("📖 Đang tải danh sách quiz đã làm...")


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
        onboarding_service.detect_course_from_input(text)
        onboarding_service.update_onboarding_state(
            user_id=user_id, current_step="q1"
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
        onboarding_service.complete_onboarding(user_id)
        await message.answer(
            "Onboarding hoàn thành! Bắt đầu học thôi 🚀\n\n"
            "Dùng /today để xem bài học đầu tiên."
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


async def _handle_quiz_answer(message: Message, text: str, active_session, db) -> None:
    """Xử lý câu trả lời quiz, gửi feedback và câu tiếp theo hoặc tổng kết."""
    quiz_service = QuizService(db)
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
            f"Quiz hoàn thành! ✅\n\n{summary}" if summary
            else "Quiz hoàn thành! ✅\n\nDùng /progress để xem tiến độ."
        )
    else:
        next_question = result.get("next_question", "")
        if next_question:
            await message.answer(next_question)


class TelegramHandlers:
    """
    Handler dispatcher for Telegram messages and commands.

    Manages routing of incoming updates to appropriate command handlers,
    integrating with backend services for business logic, and logs all
    interactions for debugging.

    Attributes:
        service: TelegramService for sending messages
        onboarding_service: Service for onboarding flow
        progress_service: Service for progress tracking
        quiz_service: Service for quiz management
        handler_service: Service for formatting responses
    """

    def __init__(
        self,
        telegram_service: TelegramService,
        onboarding_service: Optional[OnboardingService] = None,
        progress_service: Optional[ProgressService] = None,
        quiz_service: Optional[QuizService] = None,
    ):
        """
        Initialize handlers with service instances.

        Args:
            telegram_service: Service instance for sending messages to users
            onboarding_service: Optional OnboardingService instance
            progress_service: Optional ProgressService instance
            quiz_service: Optional QuizService instance
        """
        self.service = telegram_service
        self.onboarding_service = onboarding_service
        self.progress_service = progress_service
        self.quiz_service = quiz_service
        self.handler_service = HandlerService()
        logger.info("TelegramHandlers initialized with integrated services")

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

        Creates a new user in the system and sends welcome message.
        Calls onboarding_service.create_user() to register the user,
        then sends a formatted welcome message.

        Args:
            update: ParsedUpdate containing user_id and message context

        Raises:
            Logs errors but doesn't raise - sends error message to user instead
        """
        logger.info(f"User {update.user_id} initiated /start command")

        try:
            # Get database session
            db = SessionLocal()

            try:
                # Create user in the system
                if self.onboarding_service:
                    user = self.onboarding_service.create_user(
                        telegram_id=update.user_id,
                        username=f"user_{update.user_id}"
                    )
                    logger.info(f"Created user {user.user_id} for telegram_id {update.user_id}")

                    # Send welcome message
                    greeting = self.handler_service.format_welcome_message(
                        user.username or update.user_id
                    )
                else:
                    # Fallback if service not available
                    greeting = self.handler_service.format_welcome_message(update.user_id)

                await self.service.send_message(update.user_id, greeting)
                logger.info(f"Sent greeting to user {update.user_id}")

            finally:
                db.close()

        except ValueError as e:
            # User already exists
            logger.warning(f"User {update.user_id} already exists: {str(e)}")
            msg = (
                "👋 Bạn đã có tài khoản rồi!\n\n"
                "Hãy sử dụng các lệnh:\n"
                "/progress - Xem tiến độ học tập\n"
                "/review - Xem các quiz đã làm\n"
                "/done - Hoàn thành bài học"
            )
            await self.service.send_message(update.user_id, msg)

        except Exception as e:
            logger.error(f"Error in handle_start for user {update.user_id}: {str(e)}")
            error_msg = self.handler_service.format_error_message("general")
            await self.service.send_message(update.user_id, error_msg)

    async def handle_done(self, update: ParsedUpdate) -> None:
        """
        Handle /done command - mark learning session as complete.

        Checks if user is in a learning session and routes appropriately:
        - For Track A (external learning): Asks "what did you learn?"
        - For Track B (internal learning): Auto-starts quiz

        Args:
            update: ParsedUpdate containing user_id and session context

        Note:
            This is a simplified version. Full implementation would check
            user's onboarding state and active sessions from database.
        """
        logger.info(f"User {update.user_id} reported learning session complete")

        try:
            # In a full implementation, we would:
            # 1. Check user's onboarding state
            # 2. Get active learning session
            # 3. Determine track (A or B)
            # 4. Route accordingly

            # For now, ask for check-in with option for both tracks
            response = (
                "Tốt lắm! 🎉\n\n"
                "Hôm nay bạn học đến đâu rồi?\n\n"
                "Hãy kể mình nghe:\n"
                "• Bạn vừa học bài gì?\n"
                "• Hiểu được những khái niệm gì?\n"
                "• Phần nào còn khó hiểu?\n\n"
                "Câu trả lời của bạn sẽ giúp mình tạo quiz phù hợp!"
            )

            await self.service.send_message(update.user_id, response)
            logger.info(f"Sent check-in prompt to user {update.user_id}")

        except Exception as e:
            logger.error(f"Error in handle_done for user {update.user_id}: {str(e)}")
            error_msg = self.handler_service.format_error_message("general")
            await self.service.send_message(update.user_id, error_msg)

    async def handle_progress(self, update: ParsedUpdate) -> None:
        """
        Handle /progress command - show user's learning progress.

        Calls progress_service.get_user_progress() to fetch actual progress data,
        formats it nicely with emoji and progress bars, and sends to user.

        Args:
            update: ParsedUpdate containing user_id and progress context
        """
        logger.info(f"User {update.user_id} requested progress view")

        try:
            # Get database session
            db = SessionLocal()

            try:
                # In a real implementation, we'd need to convert telegram_id to user_id
                # For now, we use telegram_id as a temporary identifier
                # This should be linked to actual user_id in database

                if self.progress_service:
                    # Get user progress (this would need proper user_id lookup)
                    # For now, we'll use a simplified approach
                    logger.info(f"Fetching progress for telegram user {update.user_id}")

                    # This is a placeholder - in production, lookup user_id by telegram_id first
                    progress = self.progress_service.get_user_progress(
                        user_id=1,  # Would be looked up from database
                        db_session=db
                    )

                    # Format as nice Telegram message
                    msg = self.handler_service.format_progress_message(progress)
                else:
                    msg = (
                        "📊 Tiến độ học tập của bạn:\n\n"
                        "Chức năng đang được phát triển..."
                    )

                await self.service.send_message(update.user_id, msg)
                logger.info(f"Sent progress to user {update.user_id}")

            finally:
                db.close()

        except ValueError as e:
            # User not found
            logger.warning(f"User {update.user_id} not found: {str(e)}")
            msg = (
                "⚠️ <b>Không tìm thấy tài khoản</b>\n\n"
                "Bạn chưa hoàn thành onboarding.\n"
                "Hãy sử dụng /start để bắt đầu!"
            )
            await self.service.send_message(update.user_id, msg)

        except Exception as e:
            logger.error(f"Error in handle_progress for user {update.user_id}: {str(e)}")
            error_msg = self.handler_service.format_error_message("general")
            await self.service.send_message(update.user_id, error_msg)

    async def handle_resume(self, update: ParsedUpdate) -> None:
        """
        Handle /resume command - resume paused learning session.

        Clears "busy" status and reschedules learning session for the user.
        Fetches the last incomplete session and offers to continue.

        Args:
            update: ParsedUpdate containing user_id and session context
        """
        logger.info(f"User {update.user_id} requested to resume learning")

        try:
            # In a full implementation:
            # 1. Look up user and current session
            # 2. Clear "busy" status if set
            # 3. Fetch last incomplete lesson
            # 4. Reschedule learning reminders
            # 5. Send lesson details and offer to start

            response = (
                "Quay lại học tiếp thôi! 💪\n\n"
                "Bài tiếp theo đang được tải...\n\n"
                "Dự kiến: ~45 phút"
            )

            await self.service.send_message(update.user_id, response)
            logger.info(f"Sent resume prompt to user {update.user_id}")

        except Exception as e:
            logger.error(f"Error in handle_resume for user {update.user_id}: {str(e)}")
            error_msg = self.handler_service.format_error_message("general")
            await self.service.send_message(update.user_id, error_msg)

    async def handle_review(
        self,
        update: ParsedUpdate,
        full_message: str
    ) -> None:
        """
        Handle /review command - review past quiz summaries.

        Shows user their past quiz summaries, optionally filtered by topic.
        Calls progress_service to fetch summaries and formats as list with
        inline buttons for viewing details.

        Usage:
            /review              - Show all recent summaries
            /review React        - Show React-specific summaries
            /review useState     - Show useState-specific summary

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

        try:
            # Get database session
            db = SessionLocal()

            try:
                if self.progress_service:
                    # Get summaries (filtered by topic if provided)
                    if topic:
                        summaries = self.progress_service.get_review_by_topic(
                            user_id=1,  # Would be looked up from telegram_id
                            topic=topic,
                            db_session=db
                        )
                    else:
                        summaries = self.progress_service.get_quiz_summaries(
                            user_id=1,  # Would be looked up from telegram_id
                            db_session=db
                        )

                    # Format summaries
                    msg = self.handler_service.format_quiz_summaries(summaries)
                else:
                    if topic:
                        msg = f"📚 Review: {topic}\n\nCác summary về {topic}:\n[sẽ hiển thị]"
                    else:
                        msg = (
                            "📚 Tất cả các summary:\n\n"
                            "[Danh sách các quiz summary]\n\n"
                            "Gõ /review [tên topic] để xem chi tiết"
                        )

                await self.service.send_message(update.user_id, msg)
                logger.info(f"Sent review response to user {update.user_id}")

            finally:
                db.close()

        except ValueError as e:
            # User not found
            logger.warning(f"User {update.user_id} not found: {str(e)}")
            msg = (
                "⚠️ <b>Không tìm thấy tài khoản</b>\n\n"
                "Bạn chưa hoàn thành onboarding.\n"
                "Hãy sử dụng /start để bắt đầu!"
            )
            await self.service.send_message(update.user_id, msg)

        except Exception as e:
            logger.error(f"Error in handle_review for user {update.user_id}: {str(e)}")
            error_msg = self.handler_service.format_error_message("general")
            await self.service.send_message(update.user_id, error_msg)

    async def handle_message(self, update: ParsedUpdate) -> None:
        """
        Handle regular message input (not a command).

        Routes message to appropriate handler based on current user state.
        State is determined by the learning system's session tracker.

        Examples:
            - During onboarding: Parse course URL or topic
            - During check-in: Parse what user learned
            - During quiz: Parse quiz answer

        Args:
            update: ParsedUpdate containing user_id and message content

        Note:
            Full implementation requires tracking user state in database.
            For now, this is a placeholder that logs the message.
        """
        logger.info(
            f"User {update.user_id} sent regular message: {update.message_text}"
        )

        try:
            # In a full implementation:
            # 1. Look up user's current state from database
            # 2. Route based on state:
            #    - onboarding_state: route to onboarding service
            #    - check_in_state: route to check_in service
            #    - quiz_state: call handle_answer
            # 3. Update state and send response

            # For now, send a helpful message
            response = (
                "💭 Pesan của bạn đã được nhận!\n\n"
                "Vui lòng sử dụng các lệnh sau:\n"
                "/start - Bắt đầu học\n"
                "/progress - Xem tiến độ\n"
                "/review - Xem các quiz\n"
                "/done - Hoàn thành bài học"
            )

            await self.service.send_message(update.user_id, response)
            logger.debug(f"Sent instruction message to user {update.user_id}")

        except Exception as e:
            logger.error(f"Error in handle_message for user {update.user_id}: {str(e)}")

    async def handle_answer(
        self,
        update: ParsedUpdate,
        session_id: int
    ) -> None:
        """
        Handle quiz answer submission.

        Receives user's answer in quiz session, calls quiz_service.submit_answer(),
        formats response (next question or summary), and sends to user.

        Args:
            update: ParsedUpdate containing user_id and answer text
            session_id: ID of the active quiz session

        Example:
            >>> update = ParsedUpdate("123456", "useState manages state in components")
            >>> await handlers.handle_answer(update, session_id=1)
        """
        logger.info(f"User {update.user_id} submitted quiz answer for session {session_id}")

        try:
            # Get database session
            db = SessionLocal()

            try:
                if not self.quiz_service:
                    await self.service.send_message(
                        update.user_id,
                        "❌ Dịch vụ quiz không khả dụng. Vui lòng thử lại sau!"
                    )
                    return

                # Submit answer
                result = self.quiz_service.submit_answer(
                    session_id=session_id,
                    user_answer=update.message_text,
                    db_session=db
                )

                # Format evaluation message
                eval_msg = self.handler_service.format_evaluation(
                    result.get("evaluation", {})
                )
                await self.service.send_message(update.user_id, eval_msg)

                # Check next action
                next_action = result.get("next_action")

                if next_action == "end":
                    # Quiz is complete, generate and show summary
                    summary_result = self.quiz_service.get_or_generate_summary(
                        session_id=session_id,
                        db_session=db
                    )

                    summary_msg = self.handler_service.format_quiz_detail(
                        db.query(QuizSummary).filter(
                            QuizSummary.summary_id == summary_result.get("summary_id")
                        ).first()
                    )
                    await self.service.send_message(update.user_id, summary_msg)

                    logger.info(f"Quiz session {session_id} completed for user {update.user_id}")

                else:
                    # Send next question
                    next_question = result.get("next_question")
                    if next_question:
                        question_msg = self.handler_service.format_quiz_question(next_question)
                        await self.service.send_message(update.user_id, question_msg)
                        logger.info(f"Sent question #{result.get('question_count')} for session {session_id}")

            finally:
                db.close()

        except ValueError as e:
            # Session not found
            logger.warning(f"Invalid session {session_id} for user {update.user_id}: {str(e)}")
            msg = self.handler_service.format_error_message("quiz_incomplete")
            await self.service.send_message(update.user_id, msg)

        except Exception as e:
            logger.error(
                f"Error in handle_answer for user {update.user_id}, "
                f"session {session_id}: {str(e)}"
            )
            error_msg = self.handler_service.format_error_message("general")
            await self.service.send_message(update.user_id, error_msg)
