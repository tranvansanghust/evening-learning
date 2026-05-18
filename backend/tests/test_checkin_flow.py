"""
Tests for the /done and text-routing behavior.

After the MCQ refactor: /done starts quiz directly (no checkin_pending step).
Text input when user has no active course → creates onboarding state.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_message(text: str, telegram_id: str = "111") -> MagicMock:
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = int(telegram_id)
    msg.from_user.username = f"user_{telegram_id}"
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.chat.id = 111
    return msg


def make_user(user_id: int = 1, checkin_pending: bool = False) -> MagicMock:
    user = MagicMock()
    user.user_id = user_id
    user.checkin_pending = checkin_pending
    return user


def make_onboarding_state(step: str) -> MagicMock:
    state = MagicMock()
    state.current_step = step
    return state


# ---------------------------------------------------------------------------
# /done behavior
# ---------------------------------------------------------------------------

class TestCmdDone:
    @pytest.mark.asyncio
    async def test_done_during_real_onboarding_returns_error(self):
        """/done khi user đang onboarding thật → trả về message lỗi."""
        from app.routers.telegram_handlers import cmd_done

        msg = make_message("/done")
        user = make_user(user_id=1)

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")

            call_count = [0]
            def side_effect_first():
                call_count[0] += 1
                if call_count[0] == 1:
                    return user
                return None

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first

            await cmd_done(msg)

        reply = msg.answer.call_args[0][0]
        assert "onboarding" in reply.lower()
        assert user.checkin_pending is False

    @pytest.mark.asyncio
    async def test_done_without_enrollment_returns_error(self):
        """/done khi user chưa có khoá học → thông báo chọn khoá học."""
        from app.routers.telegram_handlers import cmd_done

        msg = make_message("/done")
        user = make_user(user_id=1)

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None

            call_count = [0]
            def side_effect_first():
                call_count[0] += 1
                if call_count[0] == 1:
                    return user        # User
                elif call_count[0] == 2:
                    return None        # no active quiz
                return None            # no enrollment

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first

            await cmd_done(msg)

        reply = msg.answer.call_args[0][0]
        assert "khoá học" in reply.lower() or "start" in reply.lower()


# ---------------------------------------------------------------------------
# handle_text routing: text khi đang trong quiz
# ---------------------------------------------------------------------------

class TestHandleTextDuringQuiz:
    @pytest.mark.asyncio
    async def test_text_during_active_quiz_prompts_button(self):
        """handle_text khi đang có active quiz → nhắc nhấn nút, không gọi submit_answer."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("B")
        user = make_user(user_id=1)
        mock_session = MagicMock()
        mock_session.status = "active"

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None

            call_count = [0]
            def side_effect_first():
                call_count[0] += 1
                if call_count[0] == 1:
                    return user
                return mock_session    # active quiz session

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first

            await handle_text(msg)

        reply = msg.answer.call_args[0][0]
        assert "nút" in reply.lower() or "button" in reply.lower() or "👆" in reply


# ---------------------------------------------------------------------------
# handle_text routing: user gõ chủ đề khi chưa có khoá
# ---------------------------------------------------------------------------

class TestHandleTextNoCourse:
    @pytest.mark.asyncio
    async def test_text_with_no_course_starts_onboarding(self):
        """handle_text khi user không có khoá IN_PROGRESS → tạo onboarding và xử lý course_input."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Python cơ bản")
        user = make_user(user_id=1)

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None  # no onboarding
            new_state = MagicMock()
            new_state.current_step = "course_input"
            mock_ob.update_onboarding_state.return_value = new_state

            call_count = [0]
            def side_effect_first():
                call_count[0] += 1
                if call_count[0] == 1:
                    return user
                return None  # no active quiz, no course

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first

            with patch("app.routers.telegram_handlers._handle_onboarding_step") as mock_step:
                mock_step.return_value = None
                await handle_text(msg)

        # create_onboarding_state phải được gọi
        mock_ob.create_onboarding_state.assert_called_once_with(user.user_id)
        # _handle_onboarding_step phải được gọi với step course_input
        mock_step.assert_called_once()
