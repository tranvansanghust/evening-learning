"""
Tests for state-aware message routing in telegram_handlers.

Mỗi test kiểm tra: với state X, khi user gửi text Y
thì hàm nào được gọi và bot trả lời gì.

Không cần database thật — dùng MagicMock để giả lập.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — tạo fake Message object giống aiogram
# ---------------------------------------------------------------------------

def make_message(text: str, telegram_id: str = "111") -> MagicMock:
    """Tạo fake aiogram Message với from_user.id và text."""
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = int(telegram_id)
    msg.from_user.username = f"user_{telegram_id}"
    msg.answer = AsyncMock()
    return msg


def make_onboarding_state(step: str) -> MagicMock:
    """Tạo fake OnboardingState với current_step."""
    state = MagicMock()
    state.current_step = step
    return state


def make_quiz_session(session_id: int = 1) -> MagicMock:
    """Tạo fake QuizSession đang active."""
    session = MagicMock()
    session.session_id = session_id
    session.status = "active"
    return session


# ---------------------------------------------------------------------------
# Test routing — user chưa có state nào (brand new)
# ---------------------------------------------------------------------------

class TestRoutingNewUser:
    """User mới, chưa có OnboardingState."""

    @pytest.mark.asyncio
    async def test_new_user_text_prompted_to_start(self):
        """User mới gõ bất kỳ text → hướng dẫn dùng /start."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("hello")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None  # chưa có state

            # mock quiz session không có
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        reply = msg.answer.call_args[0][0]
        assert "/start" in reply


# ---------------------------------------------------------------------------
# Test routing — đang trong onboarding
# ---------------------------------------------------------------------------

class TestRoutingOnboarding:
    """User đang trong các bước onboarding."""

    @pytest.mark.asyncio
    async def test_course_input_step_saves_course(self):
        """State = course_input → nhận topic/URL → gọi detect_course_from_input."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Learn React from scratch")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("course_input")
            mock_ob.detect_course_from_input.return_value = ("topic", "Learn React from scratch")

            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        mock_ob.detect_course_from_input.assert_called_once_with("Learn React from scratch")
        reply = msg.answer.call_args[0][0]
        # Phải hỏi Q1 tiếp theo
        assert "web app" in reply.lower() or "q1" in reply.lower() or "xây dựng" in reply.lower()

    @pytest.mark.asyncio
    async def test_q1_step_never_answer(self):
        """State = q1, user trả lời 'chưa' → lưu q1=never, hỏi Q2 về HTML/CSS."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("chưa bao giờ")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        mock_ob.update_onboarding_state.assert_called()
        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("q1_answer") == "never"
        assert call_kwargs.get("current_step") == "q2"

        reply = msg.answer.call_args[0][0]
        assert "html" in reply.lower() or "css" in reply.lower()

    @pytest.mark.asyncio
    async def test_q1_step_yes_answer(self):
        """State = q1, user trả lời 'rồi' → lưu q1=yes, hỏi Q2 về framework."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("rồi, tôi đã build app")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("q1_answer") == "yes"
        assert call_kwargs.get("current_step") == "q2"

        reply = msg.answer.call_args[0][0]
        assert "framework" in reply.lower() or "react" in reply.lower()

    @pytest.mark.asyncio
    async def test_deadline_step_saves_date(self):
        """State = deadline, user nhập '3 months' → lưu deadline, hỏi hours."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("3 months")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("deadline")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("current_step") == "hours"
        assert call_kwargs.get("deadline") is not None

    @pytest.mark.asyncio
    async def test_hours_step_saves_hours(self):
        """State = hours, user nhập '2' → lưu hours=2, hỏi reminder_time."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("2")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("hours")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("hours_per_day") == 2
        assert call_kwargs.get("current_step") == "reminder"

    @pytest.mark.asyncio
    async def test_reminder_step_saves_time(self):
        """State = reminder, user nhập '21:00' → lưu reminder, hoàn thành onboarding."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("21:00")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("reminder")
            mock_ob.complete_onboarding = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("reminder_time") == "21:00"
        mock_ob.complete_onboarding.assert_called()


# ---------------------------------------------------------------------------
# Test routing — đang trong quiz
# ---------------------------------------------------------------------------

class TestRoutingQuiz:
    """User đang trong active quiz session."""

    @pytest.mark.asyncio
    async def test_text_during_quiz_routes_to_quiz_answer(self):
        """Có active QuizSession → text bất kỳ → gọi QuizService.submit_answer."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("useState là hook quản lý state trong React component")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls, \
             patch("app.routers.telegram_handlers.QuizService") as mock_quiz_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None  # onboarding done

            # Có active quiz session
            mock_db.query.return_value.filter.return_value.first.return_value = make_quiz_session(session_id=42)

            mock_quiz = MagicMock()
            mock_quiz_cls.return_value = mock_quiz
            mock_quiz.submit_answer.return_value = {
                "evaluation": {"feedback": "Tốt lắm!", "is_correct": True},
                "next_action": "continue",
                "next_question": "Hãy giải thích useEffect?"
            }

            await handle_text(msg)

        mock_quiz.submit_answer.assert_called_once()
        call_args = mock_quiz.submit_answer.call_args
        assert call_args[1]["session_id"] == 42 or call_args[0][0] == 42

    @pytest.mark.asyncio
    async def test_quiz_end_sends_summary(self):
        """Quiz kết thúc (next_action=end) → gửi summary message."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("useEffect chạy sau mỗi render")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls, \
             patch("app.routers.telegram_handlers.QuizService") as mock_quiz_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None

            mock_db.query.return_value.filter.return_value.first.return_value = make_quiz_session(42)

            mock_quiz = MagicMock()
            mock_quiz_cls.return_value = mock_quiz
            mock_quiz.submit_answer.return_value = {
                "evaluation": {"feedback": "Xuất sắc!", "is_correct": True},
                "next_action": "end",
                "summary": "Bạn đã nắm vững React Hooks!"
            }

            await handle_text(msg)

        reply = msg.answer.call_args[0][0]
        # Phải có message tổng kết
        assert any(word in reply.lower() for word in ["tổng kết", "summary", "hoàn thành", "mastered", "✅"])
