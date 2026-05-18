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
    async def test_course_input_step_sends_q1(self):
        """State = course_input → user nhập topic → update_onboarding_state được gọi với course_topic."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Learn React from scratch")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls, \
             patch("app.routers.telegram_handlers.LLMService") as mock_llm_cls, \
             patch("app.routers.telegram_handlers.LLMAssessmentGenerator") as mock_assessor_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("course_input")

            mock_llm = MagicMock()
            mock_llm_cls.return_value = mock_llm
            mock_llm.normalize_course_title.return_value = "React Fundamentals"

            mock_assessor = MagicMock()
            mock_assessor_cls.return_value = mock_assessor
            mock_assessor.generate_assessment_questions.return_value = {
                "q1": "Bạn đã build web app chưa?",
                "q2_if_no": "Bạn có biết HTML/CSS không?",
                "q2_if_yes": "Bạn đã dùng framework nào chưa?",
            }

            await handle_text(msg)

        # update_onboarding_state phải được gọi với course_topic
        mock_ob.update_onboarding_state.assert_called()
        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("course_topic") == "React Fundamentals"
        assert call_kwargs.get("current_step") == "q1"

    @pytest.mark.asyncio
    async def test_q1_step_never_answer(self):
        """State = q1, user trả lời 'chưa' → lưu q1=never, current_step=q2."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("chưa bao giờ")
        state = make_onboarding_state("q1")
        state.q2_text_if_no = "Bạn có biết HTML/CSS không?"
        state.q2_text_if_yes = "Bạn đã dùng framework nào?"

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = state

            await handle_text(msg)

        mock_ob.update_onboarding_state.assert_called()
        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("q1_answer") == "never"
        assert call_kwargs.get("current_step") == "q2"

        reply = msg.answer.call_args[0][0]
        assert "html" in reply.lower() or "css" in reply.lower()

    @pytest.mark.asyncio
    async def test_q1_step_yes_answer(self):
        """State = q1, user trả lời 'rồi' → lưu q1=yes, current_step=q2."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("rồi, tôi đã build app")
        state = make_onboarding_state("q1")
        state.q2_text_if_no = "Bạn có biết HTML/CSS không?"
        state.q2_text_if_yes = "Bạn đã dùng React hay framework nào chưa?"

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = state

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
    async def test_text_during_quiz_prompts_button_press(self):
        """Có active QuizSession → text bất kỳ → nhắc nhấn nút, không gọi submit_answer."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("B")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None

            # First call: user found (truthy), second call: active quiz session
            mock_user = MagicMock()
            mock_user.user_id = 42
            mock_user.checkin_pending = False

            call_count = [0]
            def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_user
                return make_quiz_session(session_id=1)

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect

            await handle_text(msg)

        reply = msg.answer.call_args[0][0]
        assert "nút" in reply.lower() or "👆" in reply
