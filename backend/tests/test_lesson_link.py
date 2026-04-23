"""
Tests for lesson link sending functionality (task-17).

Covers:
- _build_lesson_url() returns correct URL with lesson_id
- /today sends message containing lesson link
- /today message contains lesson title
- LLMContentGenerator.get_or_generate() is called before sending link
- After onboarding complete -> sends link to first lesson
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers — fake model objects
# ---------------------------------------------------------------------------

def make_lesson(lesson_id: int = 1, sequence_number: int = 1, title: str = "Intro to Python", course_id: int = 1) -> MagicMock:
    lesson = MagicMock()
    lesson.lesson_id = lesson_id
    lesson.sequence_number = sequence_number
    lesson.title = title
    lesson.course_id = course_id
    lesson.description = "Mô tả bài học"
    lesson.estimated_duration_minutes = 60
    lesson.content_markdown = None
    lesson.content_generated_at = None
    return lesson


def make_course(course_id: int = 1, name: str = "Python Cơ Bản", title: str = "Python Cơ Bản") -> MagicMock:
    course = MagicMock()
    course.course_id = course_id
    course.name = name
    course.title = title
    return course


def make_enrollment(status: str = "IN_PROGRESS", course_id: int = 1) -> MagicMock:
    enrollment = MagicMock()
    enrollment.status = status
    enrollment.course_id = course_id
    return enrollment


def make_user(user_id: int = 10, telegram_id: str = "999") -> MagicMock:
    user = MagicMock()
    user.user_id = user_id
    user.telegram_id = telegram_id
    return user


# ---------------------------------------------------------------------------
# Tests for _build_lesson_url
# ---------------------------------------------------------------------------

class TestBuildLessonUrl:
    """Tests for _build_lesson_url() helper."""

    def test_returns_string_with_lesson_id(self):
        """_build_lesson_url must include lesson_id in returned URL."""
        from app.routers.lesson_helpers import _build_lesson_url

        url = _build_lesson_url(42)

        assert isinstance(url, str)
        assert "42" in url

    def test_url_format_contains_lesson_path(self):
        """URL must follow format: {frontend_url}/lesson/{lesson_id}."""
        from app.routers.lesson_helpers import _build_lesson_url

        url = _build_lesson_url(7)

        assert "/lesson/7" in url

    def test_url_starts_with_http(self):
        """URL must start with http:// or https://."""
        from app.routers.lesson_helpers import _build_lesson_url

        url = _build_lesson_url(1)

        assert url.startswith("http://") or url.startswith("https://")

    def test_url_uses_frontend_url_from_settings(self):
        """URL base must come from settings.frontend_url."""
        from app.routers.lesson_helpers import _build_lesson_url

        with patch("app.routers.lesson_helpers.settings") as mock_settings:
            mock_settings.frontend_url = "https://myapp.example.com"
            url = _build_lesson_url(5)

        assert url == "https://myapp.example.com/lesson/5"


# ---------------------------------------------------------------------------
# Tests for _send_lesson_link
# ---------------------------------------------------------------------------

class TestSendLessonLink:
    """Tests for _send_lesson_link() async helper."""

    def _make_db(self, lesson_count: int = 3) -> MagicMock:
        db = MagicMock()
        mock_q = MagicMock()
        mock_q.filter.return_value.count.return_value = lesson_count
        db.query.return_value = mock_q
        db.commit = MagicMock()
        return db

    def test_sends_message_containing_lesson_title(self):
        """_send_lesson_link must send a message that includes the lesson title."""
        from app.routers.lesson_helpers import _send_lesson_link

        lesson = make_lesson(lesson_id=1, title="Variables and Types")
        course = make_course()
        db = self._make_db()

        mock_message = AsyncMock()

        with patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## Content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(_send_lesson_link(mock_message, lesson, course, db))

        mock_message.answer.assert_called_once()
        sent_text = mock_message.answer.call_args.args[0]
        assert "Variables and Types" in sent_text

    def test_sends_message_containing_lesson_link(self):
        """_send_lesson_link must send a message that contains a URL with lesson_id."""
        from app.routers.lesson_helpers import _send_lesson_link

        lesson = make_lesson(lesson_id=99)
        course = make_course()
        db = self._make_db()

        mock_message = AsyncMock()

        with patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## Content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(_send_lesson_link(mock_message, lesson, course, db))

        sent_text = mock_message.answer.call_args.args[0]
        assert "99" in sent_text
        assert "http" in sent_text.lower()

    def test_calls_get_or_generate_before_sending_link(self):
        """LLMContentGenerator.get_or_generate() must be called before the link is sent."""
        from app.routers.lesson_helpers import _send_lesson_link

        lesson = make_lesson(lesson_id=5)
        course = make_course()
        db = self._make_db()

        mock_message = AsyncMock()
        call_order = []

        with patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            def record_generate(*args, **kwargs):
                call_order.append("generate")
                return "## Content"

            mock_gen = MagicMock()
            mock_gen.get_or_generate.side_effect = record_generate
            mock_gen_cls.return_value = mock_gen

            async def record_answer(*args, **kwargs):
                call_order.append("send")

            mock_message.answer.side_effect = record_answer

            asyncio.run(_send_lesson_link(mock_message, lesson, course, db))

        assert call_order.index("generate") < call_order.index("send"), \
            "get_or_generate() must be called before sending the link message"

    def test_message_contains_done_instruction(self):
        """Message must contain instruction about /done command."""
        from app.routers.lesson_helpers import _send_lesson_link

        lesson = make_lesson()
        course = make_course()
        db = self._make_db()

        mock_message = AsyncMock()

        with patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## Content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(_send_lesson_link(mock_message, lesson, course, db))

        sent_text = mock_message.answer.call_args.args[0]
        assert "/done" in sent_text


# ---------------------------------------------------------------------------
# Tests for /today command with lesson link
# ---------------------------------------------------------------------------

class TestCmdTodayWithLessonLink:
    """Tests that cmd_today sends lesson link when a lesson is available."""

    def _make_db(self, user, enrollment, course, lessons, quiz_sessions=None):
        db = MagicMock()
        quiz_sessions = quiz_sessions or []

        def query_side_effect(model):
            mock_q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            if model_name == "User":
                mock_q.filter.return_value.first.return_value = user
            elif model_name == "UserCourse":
                mock_q.filter.return_value.first.return_value = enrollment
            elif model_name == "Course":
                mock_q.filter.return_value.first.return_value = course
            elif model_name == "Lesson":
                mock_q.filter.return_value.order_by.return_value.all.return_value = lessons
                mock_q.filter.return_value.count.return_value = len(lessons)
            elif model_name == "QuizSession":
                mock_q.filter.return_value.all.return_value = quiz_sessions
            else:
                mock_q.filter.return_value.first.return_value = None
                mock_q.filter.return_value.all.return_value = []
            return mock_q

        db.query.side_effect = query_side_effect
        db.commit = MagicMock()
        db.close = MagicMock()
        return db

    def test_today_sends_lesson_link_when_lesson_available(self):
        """/today must send a message containing lesson URL when lesson exists."""
        from app.routers.telegram_handlers import cmd_today

        user = make_user(user_id=10, telegram_id="999")
        enrollment = make_enrollment(status="IN_PROGRESS", course_id=1)
        course = make_course(course_id=1)
        lesson = make_lesson(lesson_id=3, sequence_number=1, title="Intro")
        db = self._make_db(user, enrollment, course, [lesson])

        mock_message = AsyncMock()
        mock_message.from_user.id = 999

        with patch("app.routers.telegram_handlers.SessionLocal", return_value=db), \
             patch("app.routers.telegram_handlers.get_current_lesson", return_value=lesson), \
             patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## Intro content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(cmd_today(mock_message))

        mock_message.answer.assert_called()
        # At least one call should contain the lesson_id in a URL
        all_calls_text = " ".join(
            str(c.args[0]) for c in mock_message.answer.call_args_list if c.args
        )
        assert "3" in all_calls_text  # lesson_id=3
        assert "http" in all_calls_text.lower()

    def test_today_message_includes_lesson_title(self):
        """/today message must include the lesson title."""
        from app.routers.telegram_handlers import cmd_today

        user = make_user(user_id=10, telegram_id="999")
        enrollment = make_enrollment(status="IN_PROGRESS", course_id=1)
        course = make_course(course_id=1)
        lesson = make_lesson(lesson_id=1, title="Functions and Closures")
        db = self._make_db(user, enrollment, course, [lesson])

        mock_message = AsyncMock()
        mock_message.from_user.id = 999

        with patch("app.routers.telegram_handlers.SessionLocal", return_value=db), \
             patch("app.routers.telegram_handlers.get_current_lesson", return_value=lesson), \
             patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## Content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(cmd_today(mock_message))

        all_calls_text = " ".join(
            str(c.args[0]) for c in mock_message.answer.call_args_list if c.args
        )
        assert "Functions and Closures" in all_calls_text

    def test_today_calls_content_generator(self):
        """/today must call LLMContentGenerator.get_or_generate() before sending link."""
        from app.routers.telegram_handlers import cmd_today

        user = make_user(user_id=10, telegram_id="999")
        enrollment = make_enrollment(status="IN_PROGRESS", course_id=1)
        course = make_course(course_id=1)
        lesson = make_lesson(lesson_id=1)
        db = self._make_db(user, enrollment, course, [lesson])

        mock_message = AsyncMock()
        mock_message.from_user.id = 999

        with patch("app.routers.telegram_handlers.SessionLocal", return_value=db), \
             patch("app.routers.telegram_handlers.get_current_lesson", return_value=lesson), \
             patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## Content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(cmd_today(mock_message))

        mock_gen.get_or_generate.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for onboarding completion → send first lesson link
# ---------------------------------------------------------------------------

class TestOnboardingCompletionSendsLink:
    """Tests that completing onboarding sends a link to the first lesson."""

    def _make_onboarding_service_with_db(self, lesson, course, enrollment):
        """Create a mock OnboardingService with a pre-wired db mock."""
        db = MagicMock()

        def query_side_effect(model):
            mock_q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            if model_name == "UserCourse":
                # Support .filter().order_by().first() pattern
                mock_q.filter.return_value.order_by.return_value.first.return_value = enrollment
                mock_q.filter.return_value.first.return_value = enrollment
            elif model_name == "Lesson":
                mock_q.filter.return_value.order_by.return_value.first.return_value = lesson
                mock_q.filter.return_value.count.return_value = 5
            elif model_name == "Course":
                mock_q.filter.return_value.first.return_value = course
            else:
                mock_q.filter.return_value.first.return_value = None
            return mock_q

        db.query.side_effect = query_side_effect

        mock_onboarding_service = MagicMock()
        mock_onboarding_service.db = db
        mock_onboarding_service.complete_onboarding.return_value = lesson
        return mock_onboarding_service, db

    def test_onboarding_complete_sends_lesson_link(self):
        """After complete_onboarding(), bot must send a message with lesson URL."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        user_id = 10
        lesson = make_lesson(lesson_id=7, sequence_number=1, title="First Lesson")
        course = make_course(course_id=1)
        enrollment = make_enrollment(status="in_progress", course_id=1)

        ob_state = MagicMock()
        ob_state.current_step = "reminder"

        mock_onboarding_service, _ = self._make_onboarding_service_with_db(
            lesson, course, enrollment
        )

        mock_message = AsyncMock()

        with patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## First lesson content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(_handle_onboarding_step(
                mock_message, "21:00", user_id, ob_state, mock_onboarding_service
            ))

        mock_message.answer.assert_called()
        all_calls_text = " ".join(
            str(c.args[0]) for c in mock_message.answer.call_args_list if c.args
        )
        # Should contain URL with lesson_id
        assert "http" in all_calls_text.lower()
        assert "7" in all_calls_text  # lesson_id=7

    def test_onboarding_complete_calls_content_generator(self):
        """After complete_onboarding(), LLMContentGenerator.get_or_generate() must be called."""
        from app.routers.telegram_handlers import _handle_onboarding_step

        user_id = 10
        lesson = make_lesson(lesson_id=7)
        course = make_course(course_id=1)
        enrollment = make_enrollment(status="in_progress", course_id=1)

        ob_state = MagicMock()
        ob_state.current_step = "reminder"

        mock_onboarding_service, _ = self._make_onboarding_service_with_db(
            lesson, course, enrollment
        )

        mock_message = AsyncMock()

        with patch("app.routers.lesson_helpers.LLMService"), \
             patch("app.routers.lesson_helpers.LLMContentGenerator") as mock_gen_cls:

            mock_gen = MagicMock()
            mock_gen.get_or_generate.return_value = "## Content"
            mock_gen_cls.return_value = mock_gen

            asyncio.run(_handle_onboarding_step(
                mock_message, "21:00", user_id, ob_state, mock_onboarding_service
            ))

        mock_gen.get_or_generate.assert_called_once()
