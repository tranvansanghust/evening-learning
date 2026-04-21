"""
Tests for ReplyKeyboardMarkup in onboarding steps Q1/Q2.

Kiểm tra rằng:
- Bước course_input → Q1 được hỏi với ReplyKeyboardMarkup ["Chưa bao giờ", "Rồi"]
- Bước q1 → Q2 được hỏi với ReplyKeyboardMarkup ["Chưa", "Có rồi"]
- Bước q2 → deadline được hỏi với ReplyKeyboardRemove()
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_message(text: str, telegram_id: str = "111") -> MagicMock:
    """Tạo fake aiogram Message."""
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


# ---------------------------------------------------------------------------
# Tests: keyboard presence in each step
# ---------------------------------------------------------------------------

class TestOnboardingKeyboards:
    """Kiểm tra ReplyKeyboardMarkup được truyền vào reply_markup."""

    @pytest.mark.asyncio
    async def test_course_input_step_sends_q1_with_keyboard(self):
        """Bước course_input → bot hỏi Q1 kèm keyboard ['Chưa bao giờ', 'Rồi']."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Learn React")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("course_input")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        # Kiểm tra reply_markup là ReplyKeyboardMarkup
        call_kwargs = msg.answer.call_args[1]
        reply_markup = call_kwargs.get("reply_markup")
        assert reply_markup is not None, "reply_markup phải được truyền vào"
        assert isinstance(reply_markup, ReplyKeyboardMarkup), \
            "reply_markup phải là ReplyKeyboardMarkup"

        # Kiểm tra buttons
        buttons = [btn.text for row in reply_markup.keyboard for btn in row]
        assert "Chưa bao giờ" in buttons, "'Chưa bao giờ' phải có trong keyboard"
        assert "Rồi" in buttons, "'Rồi' phải có trong keyboard"

    @pytest.mark.asyncio
    async def test_q1_never_answer_sends_q2_with_keyboard(self):
        """Bước q1 (trả lời 'chưa') → bot hỏi Q2 kèm keyboard ['Chưa', 'Có rồi']."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Chưa bao giờ")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        call_kwargs = msg.answer.call_args[1]
        reply_markup = call_kwargs.get("reply_markup")
        assert reply_markup is not None, "reply_markup phải được truyền vào"
        assert isinstance(reply_markup, ReplyKeyboardMarkup), \
            "reply_markup phải là ReplyKeyboardMarkup"

        buttons = [btn.text for row in reply_markup.keyboard for btn in row]
        assert "Chưa" in buttons, "'Chưa' phải có trong keyboard"
        assert "Có rồi" in buttons, "'Có rồi' phải có trong keyboard"

    @pytest.mark.asyncio
    async def test_q1_yes_answer_sends_q2_with_keyboard(self):
        """Bước q1 (trả lời 'rồi') → bot hỏi Q2 kèm keyboard ['Chưa', 'Có rồi']."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Rồi")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        call_kwargs = msg.answer.call_args[1]
        reply_markup = call_kwargs.get("reply_markup")
        assert reply_markup is not None, "reply_markup phải được truyền vào"
        assert isinstance(reply_markup, ReplyKeyboardMarkup), \
            "reply_markup phải là ReplyKeyboardMarkup"

        buttons = [btn.text for row in reply_markup.keyboard for btn in row]
        assert "Chưa" in buttons, "'Chưa' phải có trong keyboard"
        assert "Có rồi" in buttons, "'Có rồi' phải có trong keyboard"

    @pytest.mark.asyncio
    async def test_q2_step_sends_deadline_with_keyboard_remove(self):
        """Bước q2 → bot hỏi deadline kèm ReplyKeyboardRemove để xoá keyboard."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Chưa")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q2")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        call_kwargs = msg.answer.call_args[1]
        reply_markup = call_kwargs.get("reply_markup")
        assert reply_markup is not None, "reply_markup phải được truyền vào"
        assert isinstance(reply_markup, ReplyKeyboardRemove), \
            "reply_markup phải là ReplyKeyboardRemove để xoá keyboard"

    @pytest.mark.asyncio
    async def test_keyboard_buttons_parseable_by_text_parser(self):
        """Button text 'Chưa bao giờ' phải match parser q1 → answer='never'."""
        from app.routers.telegram_handlers import handle_text

        # Simulate user clicking button "Chưa bao giờ" (aiogram sends the text directly)
        msg = make_message("Chưa bao giờ")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        # "Chưa bao giờ" chứa "chưa" → phải parse thành "never"
        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("q1_answer") == "never", \
            "Button 'Chưa bao giờ' phải parse thành q1_answer='never'"

    @pytest.mark.asyncio
    async def test_rồi_button_parseable_by_text_parser(self):
        """Button text 'Rồi' phải match parser q1 → answer='yes'."""
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Rồi")

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await handle_text(msg)

        # "Rồi" không chứa "chưa/không/never/no" → phải parse thành "yes"
        call_kwargs = mock_ob.update_onboarding_state.call_args[1]
        assert call_kwargs.get("q1_answer") == "yes", \
            "Button 'Rồi' phải parse thành q1_answer='yes'"
