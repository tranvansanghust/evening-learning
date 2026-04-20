"""
Tests for the checkin flow using checkin_pending column on User model.

Replaces the old OnboardingState hack where step="checkin" was abused
to track the checkin state.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_message(text: str, telegram_id: str = "111") -> MagicMock:
    """Tạo fake aiogram Message với from_user.id và text."""
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = int(telegram_id)
    msg.from_user.username = f"user_{telegram_id}"
    msg.answer = AsyncMock()
    return msg


def make_user(user_id: int = 1, checkin_pending: bool = False) -> MagicMock:
    """Tạo fake User object."""
    user = MagicMock()
    user.user_id = user_id
    user.checkin_pending = checkin_pending
    return user


def make_onboarding_state(step: str) -> MagicMock:
    """Tạo fake OnboardingState với current_step."""
    state = MagicMock()
    state.current_step = step
    return state


# ---------------------------------------------------------------------------
# Test 1: /done sets checkin_pending=True, KHÔNG tạo OnboardingState
# ---------------------------------------------------------------------------

class TestCmdDoneSetsPending:
    """cmd_done phải set user.checkin_pending=True và không tạo OnboardingState."""

    @pytest.mark.asyncio
    async def test_done_sets_checkin_pending_true(self):
        """
        /done với user đã có course, không có active quiz, không onboarding
        → user.checkin_pending = True, KHÔNG gọi create_onboarding_state.
        """
        from app.routers.telegram_handlers import cmd_done

        msg = make_message("/done")
        user = make_user(user_id=1, checkin_pending=False)

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None  # không có onboarding thật

            # Simulate db.query(...).filter(...).first() for different models
            # First call: User lookup → return user
            # Second call: QuizSession active → None
            # Third call: UserCourse → return enrollment
            mock_enrollment = MagicMock()
            mock_enrollment.course_id = 10

            call_count = [0]
            def side_effect_first():
                call_count[0] += 1
                if call_count[0] == 1:
                    return user
                elif call_count[0] == 2:
                    return None  # no active quiz session
                elif call_count[0] == 3:
                    return mock_enrollment
                return None

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first

            await cmd_done(msg)

        # user.checkin_pending phải được set True
        assert user.checkin_pending is True
        # db.commit() phải được gọi
        mock_db.commit.assert_called()
        # create_onboarding_state KHÔNG được gọi
        mock_ob.create_onboarding_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_done_during_real_onboarding_returns_error(self):
        """
        /done khi user đang onboarding thật (ob_state.current_step != "checkin")
        → trả về message lỗi, user.checkin_pending KHÔNG được set.
        """
        from app.routers.telegram_handlers import cmd_done

        msg = make_message("/done")
        user = make_user(user_id=1, checkin_pending=False)

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            # User đang onboarding ở bước q1
            mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")

            call_count = [0]
            def side_effect_first():
                call_count[0] += 1
                if call_count[0] == 1:
                    return user
                elif call_count[0] == 2:
                    return None  # no active quiz session
                return None

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first

            await cmd_done(msg)

        # Phải trả về message lỗi onboarding
        reply = msg.answer.call_args[0][0]
        assert "onboarding" in reply.lower()

        # user.checkin_pending KHÔNG được set
        assert user.checkin_pending is False


# ---------------------------------------------------------------------------
# Test 2: text khi checkin_pending=True → start quiz, set checkin_pending=False
# ---------------------------------------------------------------------------

class TestHandleTextCheckinPending:
    """handle_text routing: user.checkin_pending=True → _handle_checkin."""

    @pytest.mark.asyncio
    async def test_text_with_checkin_pending_starts_quiz(self):
        """
        handle_text khi user.checkin_pending=True, ob_state=None
        → QuizService.start_quiz được gọi, user.checkin_pending set False.
        """
        from app.routers.telegram_handlers import handle_text

        msg = make_message("Hôm nay tôi học về React hooks, useState và useEffect")
        user = make_user(user_id=1, checkin_pending=True)

        mock_enrollment = MagicMock()
        mock_enrollment.course_id = 10

        mock_lesson = MagicMock()
        mock_lesson.lesson_id = 5
        mock_lesson.title = "React Hooks"

        with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
             patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls, \
             patch("app.routers.telegram_handlers.QuizService") as mock_quiz_cls, \
             patch("app.routers.telegram_handlers.LLMService"):

            mock_db = MagicMock()
            mock_db_cls.return_value = mock_db

            mock_ob = MagicMock()
            mock_ob_cls.return_value = mock_ob
            mock_ob.get_onboarding_state.return_value = None  # không onboarding

            # Simulate db.query chain: User, then UserCourse, then Lesson
            call_count = [0]
            def side_effect_first():
                call_count[0] += 1
                if call_count[0] == 1:
                    return user           # User lookup
                elif call_count[0] == 2:
                    return mock_enrollment  # UserCourse lookup
                elif call_count[0] == 3:
                    return mock_lesson    # Lesson lookup
                return None

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first
            mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_lesson

            mock_quiz = MagicMock()
            mock_quiz_cls.return_value = mock_quiz
            mock_quiz.start_quiz.return_value = {
                "first_question": "useState là gì?"
            }

            await handle_text(msg)

        # QuizService.start_quiz phải được gọi
        mock_quiz.start_quiz.assert_called_once()

        # user.checkin_pending phải được set False
        assert user.checkin_pending is False

    @pytest.mark.asyncio
    async def test_text_without_checkin_pending_routes_to_fallback(self):
        """
        handle_text khi user.checkin_pending=False, ob_state=None, no active quiz
        → fallback message với /start.
        (Covers Test 3 from the task description)
        """
        from app.routers.telegram_handlers import handle_text

        msg = make_message("hello there")
        user = make_user(user_id=1, checkin_pending=False)

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
                    return user    # User lookup
                return None        # no active quiz

            mock_db.query.return_value.filter.return_value.first.side_effect = side_effect_first

            await handle_text(msg)

        reply = msg.answer.call_args[0][0]
        assert "/start" in reply
