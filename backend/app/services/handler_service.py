"""
Handler service for formatting data for Telegram display.

This module provides helper functions to format backend data structures
into user-friendly Telegram messages with proper emoji, formatting, and structure.

Services:
    - HandlerService: Service class with formatting methods
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from app.schemas.progress import UserProgress, QuizSummaryPreview
from app.models import QuizSummary

logger = logging.getLogger(__name__)


class HandlerService:
    """
    Service for formatting data structures into Telegram-friendly messages.

    Provides methods to convert backend models and schemas into nicely formatted
    text for Telegram Bot API, including emoji usage, clear structure, and
    user-friendly language.
    """

    @staticmethod
    def format_progress_message(user_progress: UserProgress) -> str:
        """
        Format user progress as a nice Telegram message with emoji.

        Displays overall learning progress in an engaging, easy-to-read format
        with progress indicators and emoji.

        Args:
            user_progress: UserProgress object with progress metrics

        Returns:
            str: Formatted message for sending to Telegram

        Example:
            >>> progress = UserProgress(
            ...     lessons_completed=3,
            ...     total_lessons=10,
            ...     concepts_mastered=15,
            ...     total_concepts=40
            ... )
            >>> msg = HandlerService.format_progress_message(progress)
            >>> print(msg)
        """
        logger.info("Formatting progress message")

        # Calculate percentages
        lesson_percentage = 0
        if user_progress.total_lessons > 0:
            lesson_percentage = int(
                (user_progress.lessons_completed / user_progress.total_lessons) * 100
            )

        concept_percentage = 0
        if user_progress.total_concepts > 0:
            concept_percentage = int(
                (user_progress.concepts_mastered / user_progress.total_concepts) * 100
            )

        # Build progress bars
        lesson_bar = HandlerService._build_progress_bar(lesson_percentage)
        concept_bar = HandlerService._build_progress_bar(concept_percentage)

        # Format message
        message = (
            "📊 <b>Tiến độ học tập của bạn</b>\n\n"
            f"📚 <b>Bài học:</b>\n"
            f"{lesson_bar} {user_progress.lessons_completed}/{user_progress.total_lessons} ({lesson_percentage}%)\n\n"
            f"💡 <b>Khái niệm:</b>\n"
            f"{concept_bar} {user_progress.concepts_mastered}/{user_progress.total_concepts} ({concept_percentage}%)\n\n"
        )

        # Add motivational message based on progress
        if lesson_percentage == 0:
            message += "🚀 Hãy bắt đầu học ngay nào!"
        elif lesson_percentage < 30:
            message += "💪 Bạn đang đi đúng hướng! Tiếp tục cố gắng!"
        elif lesson_percentage < 70:
            message += "👏 Tuyệt vời! Bạn đã hoàn thành nửa chặng đường!"
        elif lesson_percentage < 100:
            message += "🎯 Gần xong rồi! Cố lên bạn!"
        else:
            message += "🏆 Chúc mừng bạn hoàn thành khóa học!"

        return message

    @staticmethod
    def format_quiz_summaries(summaries: List[QuizSummaryPreview]) -> str:
        """
        Format list of quiz summaries as a Telegram-friendly list.

        Displays all quiz summaries in a compact, scannable format with
        lesson names, dates, and mastery counts.

        Args:
            summaries: List of QuizSummaryPreview objects

        Returns:
            str: Formatted message for sending to Telegram

        Example:
            >>> summaries = [
            ...     QuizSummaryPreview(
            ...         summary_id=1,
            ...         date=datetime.now(),
            ...         lesson_name="React Hooks",
            ...         concepts_mastered_count=5,
            ...         concepts_weak_count=2
            ...     )
            ... ]
            >>> msg = HandlerService.format_quiz_summaries(summaries)
        """
        logger.info(f"Formatting {len(summaries)} quiz summaries")

        if not summaries:
            return "📚 Bạn chưa có bất kỳ quiz nào. Hãy hoàn thành bài học đầu tiên! 🚀"

        message = "📚 <b>Danh sách các quiz của bạn</b>\n\n"

        for i, summary in enumerate(summaries, 1):
            # Format date
            date_str = summary.date.strftime("%d/%m/%Y")

            # Create a visual summary
            message += (
                f"{i}. <b>{summary.lesson_name}</b>\n"
                f"   📅 {date_str}\n"
                f"   ✅ {summary.concepts_mastered_count} khái niệm đạt\n"
                f"   ⚠️ {summary.concepts_weak_count} khái niệm cần ôn\n"
                f"   /review_detail_{summary.summary_id}\n\n"
            )

        message += "💡 Gõ /review_detail_[số hiệu] để xem chi tiết"

        return message

    @staticmethod
    def format_quiz_detail(summary: QuizSummary) -> str:
        """
        Format full quiz details for Telegram display.

        Shows complete information about a quiz including mastered concepts,
        weak concepts with explanations, and recommendations.

        Args:
            summary: QuizSummary object with full details

        Returns:
            str: Formatted message for sending to Telegram

        Example:
            >>> summary = QuizSummary(...)
            >>> msg = HandlerService.format_quiz_detail(summary)
        """
        logger.info(f"Formatting quiz detail for summary {summary.summary_id}")

        # Get lesson name
        lesson_name = "Unknown Lesson"
        if summary.quiz_session and summary.quiz_session.lesson:
            lesson_name = summary.quiz_session.lesson.title

        # Format date
        date_str = summary.created_at.strftime("%d/%m/%Y %H:%M") if summary.created_at else "Unknown"

        message = (
            f"📊 <b>{lesson_name}</b>\n"
            f"📅 {date_str}\n\n"
        )

        # Mastered concepts
        if summary.concepts_mastered and isinstance(summary.concepts_mastered, list):
            message += "<b>✅ Khái niệm đạt:</b>\n"
            for concept in summary.concepts_mastered:
                message += f"  • {concept}\n"
            message += "\n"

        # Weak concepts
        if summary.concepts_weak and isinstance(summary.concepts_weak, list):
            message += "<b>⚠️ Khái niệm cần ôn:</b>\n"
            for weak in summary.concepts_weak:
                if isinstance(weak, dict):
                    concept = weak.get("concept", "Unknown")
                    explanation = weak.get("correct_explanation", "")
                    message += f"  • <b>{concept}</b>\n"
                    if explanation:
                        # Truncate long explanations
                        if len(explanation) > 100:
                            explanation = explanation[:97] + "..."
                        message += f"    {explanation}\n"
            message += "\n"

        message += "💪 Hãy ôn lại những khái niệm này để nắm vững hơn!"

        return message

    @staticmethod
    def format_quiz_question(question: str) -> str:
        """
        Format a quiz question nicely for display.

        Simply adds formatting to ensure questions display clearly in Telegram.

        Args:
            question: The quiz question text

        Returns:
            str: Formatted question message

        Example:
            >>> question = "What is useState?"
            >>> msg = HandlerService.format_quiz_question(question)
        """
        logger.info("Formatting quiz question")

        return (
            f"❓ <b>Câu hỏi:</b>\n\n"
            f"{question}\n\n"
            f"<i>Hãy gõ câu trả lời của bạn:</i>"
        )

    @staticmethod
    def format_evaluation(evaluation: Dict[str, Any]) -> str:
        """
        Format answer evaluation as an encouraging message.

        Provides feedback on the user's answer including correctness,
        explanation, and encouragement.

        Args:
            evaluation: Dictionary containing evaluation data from LLM service
                       Keys: is_correct, feedback, explanation, engagement_level

        Returns:
            str: Formatted evaluation message

        Example:
            >>> evaluation = {
            ...     "is_correct": True,
            ...     "feedback": "Great answer!",
            ...     "explanation": "useState is...",
            ...     "engagement_level": "high"
            ... }
            >>> msg = HandlerService.format_evaluation(evaluation)
        """
        logger.info("Formatting evaluation message")

        is_correct = evaluation.get("is_correct", False)
        feedback = evaluation.get("feedback", "")
        explanation = evaluation.get("explanation", "")

        # Determine emoji based on correctness
        emoji = "✅" if is_correct else "❌"
        result_text = "Tuyệt vời!" if is_correct else "Không đúng rồi."

        message = f"{emoji} <b>{result_text}</b>\n\n"

        if feedback:
            message += f"<b>Nhận xét:</b>\n{feedback}\n\n"

        if explanation:
            message += f"<b>Giải thích:</b>\n{explanation}\n\n"

        # Add encouragement
        if is_correct:
            message += "💪 Bạn làm rất tốt! Hãy tiếp tục!"
        else:
            message += "💡 Đừng nản chí! Hãy cố gắng học tập thêm!"

        return message

    @staticmethod
    def format_welcome_message(username: str) -> str:
        """
        Format a welcome message for new users.

        Args:
            username: User's username or name

        Returns:
            str: Welcome message

        Example:
            >>> msg = HandlerService.format_welcome_message("John")
        """
        logger.info(f"Formatting welcome message for {username}")

        return (
            f"Chào {username}! 👋\n\n"
            f"Mình là học bạn AI của bạn 🤖\n\n"
            f"Mình giúp bạn:\n"
            f"• Học có hệ thống 📚\n"
            f"• Kiểm tra hiểu biết qua quiz 📝\n"
            f"• Theo dõi tiến độ 📈\n"
            f"• Nhận lời khuyên cá nhân 💡\n\n"
            f"Bạn muốn học gì?\n"
            f"(Paste link Udemy hoặc gõ tên chủ đề)"
        )

    @staticmethod
    def format_quiz_ready_message(lesson_name: str, track: str) -> str:
        """
        Format a message when quiz is about to start.

        Args:
            lesson_name: Name of the lesson
            track: Learning track ('A' for external, 'B' for internal)

        Returns:
            str: Formatted message

        Example:
            >>> msg = HandlerService.format_quiz_ready_message("React Basics", "A")
        """
        logger.info(f"Formatting quiz ready message for {lesson_name}")

        message = (
            f"📝 <b>Kiểm tra kiến thức: {lesson_name}</b>\n\n"
            f"Mình sẽ hỏi bạn một vài câu hỏi để kiểm tra hiểu biết.\n\n"
        )

        if track == "A":
            message += (
                "💡 <i>Bạn đã học từ khoá học ngoài, "
                "nên mình sẽ hỏi về những gì bạn vừa học!</i>"
            )
        else:
            message += (
                "💡 <i>Mình sẽ hỏi về các khái niệm chính trong bài học này.</i>"
            )

        message += "\n\nHãy sẵn sàng! 💪"

        return message

    @staticmethod
    def format_error_message(error_type: str = "general") -> str:
        """
        Format a user-friendly error message.

        Args:
            error_type: Type of error ('general', 'not_found', 'invalid_input', etc.)

        Returns:
            str: Formatted error message

        Example:
            >>> msg = HandlerService.format_error_message("not_found")
        """
        logger.warning(f"Formatting error message for type: {error_type}")

        error_messages = {
            "general": (
                "❌ <b>Có lỗi xảy ra</b>\n\n"
                "Xin lỗi, mình gặp sự cố. Vui lòng thử lại sau!"
            ),
            "not_found": (
                "❌ <b>Không tìm thấy</b>\n\n"
                "Không thể tìm thấy dữ liệu bạn yêu cầu. "
                "Hãy kiểm tra lại thông tin!"
            ),
            "invalid_input": (
                "❌ <b>Dữ liệu không hợp lệ</b>\n\n"
                "Dữ liệu bạn gửi không đúng định dạng. "
                "Vui lòng thử lại!"
            ),
            "quiz_incomplete": (
                "⚠️ <b>Quiz chưa hoàn thành</b>\n\n"
                "Bạn cần hoàn thành quiz trước khi xem kết quả."
            ),
        }

        return error_messages.get(
            error_type,
            error_messages["general"]
        )

    @staticmethod
    def _build_progress_bar(percentage: int, width: int = 10) -> str:
        """
        Build a text-based progress bar.

        Args:
            percentage: Percentage complete (0-100)
            width: Width of the progress bar in characters

        Returns:
            str: Progress bar representation

        Example:
            >>> bar = HandlerService._build_progress_bar(50)
            >>> print(bar)
            ████████░░
        """
        filled = int((percentage / 100) * width)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        return bar
