"""
Tests for get_current_lesson helper function used by /today command.

Tests verify that the function returns the correct next lesson
based on completed QuizSessions for a user.

Also includes tests for:
- LLMTopicSuggester.suggest_next_topics()
- cmd_today completion flow (status=PASS update + LLM suggestions)
"""

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers — tạo fake model objects
# ---------------------------------------------------------------------------

def make_lesson(lesson_id: int, sequence_number: int, title: str = None) -> MagicMock:
    """Tạo fake Lesson object."""
    lesson = MagicMock()
    lesson.lesson_id = lesson_id
    lesson.sequence_number = sequence_number
    lesson.title = title or f"Lesson {sequence_number}"
    return lesson


def make_quiz_session(session_id: int, lesson_id: int, status: str = "completed") -> MagicMock:
    """Tạo fake QuizSession object."""
    session = MagicMock()
    session.session_id = session_id
    session.lesson_id = lesson_id
    session.status = status
    return session


def make_db_session(lessons: list, quiz_sessions: list) -> MagicMock:
    """
    Tạo fake SQLAlchemy DB session.

    Hỗ trợ pattern:
      db.query(Lesson).filter(...).order_by(...).all()
      db.query(QuizSession).filter(...).all()
    """
    db = MagicMock()

    def query_side_effect(model):
        mock_query = MagicMock()
        if model.__name__ == "Lesson":
            mock_query.filter.return_value.order_by.return_value.all.return_value = lessons
        elif model.__name__ == "QuizSession":
            mock_query.filter.return_value.all.return_value = quiz_sessions
        else:
            mock_query.filter.return_value.all.return_value = []
        return mock_query

    db.query.side_effect = query_side_effect
    return db


def make_enrollment(status: str = "IN_PROGRESS", course_id: int = 1) -> MagicMock:
    """Tạo fake UserCourse enrollment object."""
    enrollment = MagicMock()
    enrollment.status = status
    enrollment.course_id = course_id
    enrollment.completed_at = None
    return enrollment


def make_course(course_id: int = 1, name: str = "Python Co Ban") -> MagicMock:
    """Tạo fake Course object."""
    course = MagicMock()
    course.course_id = course_id
    course.name = name
    return course


def make_user(user_id: int = 10, telegram_id: str = "999") -> MagicMock:
    """Tạo fake User object."""
    user = MagicMock()
    user.user_id = user_id
    user.telegram_id = telegram_id
    return user


# ---------------------------------------------------------------------------
# Tests for get_current_lesson
# ---------------------------------------------------------------------------

class TestGetCurrentLesson:
    """Tests cho helper function get_current_lesson."""

    def test_no_completed_quiz_returns_first_lesson(self):
        """
        User chua co quiz nao completed -> tra ve lesson dau tien (sequence_number=1).
        """
        from app.routers.telegram_handlers import get_current_lesson

        lessons = [
            make_lesson(lesson_id=1, sequence_number=1, title="Intro"),
            make_lesson(lesson_id=2, sequence_number=2, title="Basics"),
            make_lesson(lesson_id=3, sequence_number=3, title="Advanced"),
        ]
        db = make_db_session(lessons=lessons, quiz_sessions=[])

        result = get_current_lesson(user_id=10, course_id=1, db=db)

        assert result is not None
        assert result.lesson_id == 1
        assert result.sequence_number == 1

    def test_lesson1_completed_returns_lesson2(self):
        """
        User da complete quiz cho lesson 1 -> tra ve lesson 2.
        """
        from app.routers.telegram_handlers import get_current_lesson

        lessons = [
            make_lesson(lesson_id=1, sequence_number=1, title="Intro"),
            make_lesson(lesson_id=2, sequence_number=2, title="Basics"),
            make_lesson(lesson_id=3, sequence_number=3, title="Advanced"),
        ]
        completed_sessions = [
            make_quiz_session(session_id=100, lesson_id=1, status="completed"),
        ]
        db = make_db_session(lessons=lessons, quiz_sessions=completed_sessions)

        result = get_current_lesson(user_id=10, course_id=1, db=db)

        assert result is not None
        assert result.lesson_id == 2
        assert result.sequence_number == 2

    def test_all_lessons_completed_returns_none(self):
        """
        User da complete tat ca lessons -> tra ve None.
        """
        from app.routers.telegram_handlers import get_current_lesson

        lessons = [
            make_lesson(lesson_id=1, sequence_number=1, title="Intro"),
            make_lesson(lesson_id=2, sequence_number=2, title="Basics"),
            make_lesson(lesson_id=3, sequence_number=3, title="Advanced"),
        ]
        completed_sessions = [
            make_quiz_session(session_id=100, lesson_id=1, status="completed"),
            make_quiz_session(session_id=101, lesson_id=2, status="completed"),
            make_quiz_session(session_id=102, lesson_id=3, status="completed"),
        ]
        db = make_db_session(lessons=lessons, quiz_sessions=completed_sessions)

        result = get_current_lesson(user_id=10, course_id=1, db=db)

        assert result is None

    def test_active_session_not_counted_as_completed(self):
        """
        QuizSession voi status='active' khong duoc tinh la completed.
        User van phai nhan lesson tuong ung.
        """
        from app.routers.telegram_handlers import get_current_lesson

        lessons = [
            make_lesson(lesson_id=1, sequence_number=1, title="Intro"),
            make_lesson(lesson_id=2, sequence_number=2, title="Basics"),
        ]
        # Lesson 1 chi co session active, chua completed
        active_sessions = [
            make_quiz_session(session_id=100, lesson_id=1, status="active"),
        ]
        db = make_db_session(lessons=lessons, quiz_sessions=active_sessions)

        result = get_current_lesson(user_id=10, course_id=1, db=db)

        assert result is not None
        assert result.lesson_id == 1

    def test_no_lessons_returns_none(self):
        """
        Khoa hoc khong co lesson nao -> tra ve None.
        """
        from app.routers.telegram_handlers import get_current_lesson

        db = make_db_session(lessons=[], quiz_sessions=[])

        result = get_current_lesson(user_id=10, course_id=1, db=db)

        assert result is None


# ---------------------------------------------------------------------------
# Tests for LLMTopicSuggester
# ---------------------------------------------------------------------------

class TestSuggestNextTopics:
    """Tests cho LLMTopicSuggester.suggest_next_topics()."""

    def test_returns_string(self):
        """
        suggest_next_topics phai tra ve string tu LLM response.
        """
        from app.services.llm_topic_suggester import LLMTopicSuggester

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "1. Topic A\n2. Topic B\n3. Topic C"
        mock_client.chat.completions.create.return_value = mock_response

        suggester = LLMTopicSuggester(client=mock_client, fast_model="gpt-4o-mini")
        result = suggester.suggest_next_topics("Python Co Ban")

        assert isinstance(result, str)
        assert "Topic A" in result

    def test_calls_llm_with_course_name(self):
        """
        suggest_next_topics phai dua ten khoa hoc vao prompt LLM.
        """
        from app.services.llm_topic_suggester import LLMTopicSuggester

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "1. Django\n2. FastAPI\n3. Flask"
        mock_client.chat.completions.create.return_value = mock_response

        suggester = LLMTopicSuggester(client=mock_client, fast_model="gpt-4o-mini")
        suggester.suggest_next_topics("Python Co Ban")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs.get("messages", [])
        prompt_content = messages[0]["content"]
        assert "Python Co Ban" in prompt_content

    def test_llm_error_raises_exception(self):
        """
        Khi LLM raise exception, suggest_next_topics phai propagate exception.
        (Caller xu ly try/except va fallback gracefully.)
        """
        from app.services.llm_topic_suggester import LLMTopicSuggester

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API timeout")

        suggester = LLMTopicSuggester(client=mock_client, fast_model="gpt-4o-mini")

        with pytest.raises(Exception, match="API timeout"):
            suggester.suggest_next_topics("Python Co Ban")


# ---------------------------------------------------------------------------
# Tests for cmd_today completion flow
# ---------------------------------------------------------------------------

class TestCmdTodayCompletionFlow:
    """
    Tests cho logic completion trong cmd_today khi get_current_lesson tra None.
    Dung unittest.mock de mock DB, LLM, va aiogram message.
    """

    def _make_mock_db_for_completion(self, user, enrollment, course):
        """
        Helper tao mock DB session cho truong hop tat ca lessons da hoan thanh.
        enrollment.status = IN_PROGRESS, get_current_lesson se tra None.
        """
        db = MagicMock()

        def query_side_effect(model):
            mock_q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            if model_name == "User":
                mock_q.filter.return_value.first.return_value = user
            elif model_name == "UserCourse":
                mock_q.filter.return_value.first.return_value = enrollment
            elif model_name == "Course":
                mock_q.filter.return_value.first.return_value = course
            else:
                mock_q.filter.return_value.first.return_value = None
                mock_q.filter.return_value.all.return_value = []
            return mock_q

        db.query.side_effect = query_side_effect
        db.commit = MagicMock()
        db.close = MagicMock()
        return db

    def test_completion_updates_status_to_pass(self):
        """
        Khi lesson=None va enrollment.status=IN_PROGRESS
        -> enrollment.status phai duoc set thanh PASS va db.commit() duoc goi.
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        user = make_user(user_id=10, telegram_id="999")
        enrollment = make_enrollment(status="IN_PROGRESS", course_id=1)
        course = make_course(course_id=1, name="Python Co Ban")

        db = self._make_mock_db_for_completion(user, enrollment, course)

        mock_message = AsyncMock()
        mock_message.from_user.id = 999
        mock_message.from_user.username = "testuser"

        with patch("app.routers.telegram_handlers.SessionLocal", return_value=db), \
             patch("app.routers.telegram_handlers.get_current_lesson", return_value=None), \
             patch("app.routers.telegram_handlers.LLMService") as mock_llm_cls, \
             patch("app.routers.telegram_handlers.LLMTopicSuggester") as mock_suggester_cls:

            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            mock_suggester = MagicMock()
            mock_suggester.suggest_next_topics.return_value = "1. Django\n2. FastAPI"
            mock_suggester_cls.return_value = mock_suggester

            asyncio.run(cmd_today_runner(mock_message))

        assert enrollment.status == "PASS"
        db.commit.assert_called()

    def test_completion_sends_congratulation_message(self):
        """
        Khi lesson=None va enrollment.status=IN_PROGRESS
        -> bot phai gui tin nhan chuc mung chua ten khoa hoc.
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        user = make_user(user_id=10, telegram_id="999")
        enrollment = make_enrollment(status="IN_PROGRESS", course_id=1)
        course = make_course(course_id=1, name="Python Co Ban")

        db = self._make_mock_db_for_completion(user, enrollment, course)

        mock_message = AsyncMock()
        mock_message.from_user.id = 999
        mock_message.from_user.username = "testuser"

        with patch("app.routers.telegram_handlers.SessionLocal", return_value=db), \
             patch("app.routers.telegram_handlers.get_current_lesson", return_value=None), \
             patch("app.routers.telegram_handlers.LLMService") as mock_llm_cls, \
             patch("app.routers.telegram_handlers.LLMTopicSuggester") as mock_suggester_cls:

            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            mock_suggester = MagicMock()
            mock_suggester.suggest_next_topics.return_value = "1. Django\n2. FastAPI\n3. Flask"
            mock_suggester_cls.return_value = mock_suggester

            asyncio.run(cmd_today_runner(mock_message))

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        sent_text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
        assert "Python Co Ban" in sent_text
        assert "Chuc mung" in sent_text or "mung" in sent_text.lower() or "congratulations" in sent_text.lower() or "mừng" in sent_text or "Chúc mừng" in sent_text

    def test_already_passed_shows_different_message(self):
        """
        Khi khong co enrollment IN_PROGRESS nhung co enrollment PASS
        -> gui tin nhan khac, khong update DB.
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        user = make_user(user_id=10, telegram_id="999")
        passed_enrollment = make_enrollment(status="PASS", course_id=1)
        course = make_course(course_id=1, name="Python Co Ban")

        db = MagicMock()

        uc_call_count = [0]

        def query_side_effect(model):
            mock_q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            if model_name == "User":
                mock_q.filter.return_value.first.return_value = user
            elif model_name == "UserCourse":
                uc_call_count[0] += 1
                if uc_call_count[0] == 1:
                    mock_q.filter.return_value.first.return_value = None  # IN_PROGRESS
                else:
                    mock_q.filter.return_value.first.return_value = passed_enrollment  # PASS
            elif model_name == "Course":
                mock_q.filter.return_value.first.return_value = course
            else:
                mock_q.filter.return_value.first.return_value = None
            return mock_q

        db.query.side_effect = query_side_effect
        db.commit = MagicMock()
        db.close = MagicMock()

        mock_message = AsyncMock()
        mock_message.from_user.id = 999
        mock_message.from_user.username = "testuser"

        with patch("app.routers.telegram_handlers.SessionLocal", return_value=db):
            asyncio.run(cmd_today_runner(mock_message))

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        sent_text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
        assert "Python Co Ban" in sent_text
        # DB khong duoc commit lai (status khong thay doi)
        db.commit.assert_not_called()

    def test_llm_error_fallback_no_crash(self):
        """
        Khi LLM raise exception trong suggest_next_topics
        -> bot van gui tin chuc mung (khong crash).
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        user = make_user(user_id=10, telegram_id="999")
        enrollment = make_enrollment(status="IN_PROGRESS", course_id=1)
        course = make_course(course_id=1, name="Python Co Ban")

        db = self._make_mock_db_for_completion(user, enrollment, course)

        mock_message = AsyncMock()
        mock_message.from_user.id = 999
        mock_message.from_user.username = "testuser"

        with patch("app.routers.telegram_handlers.SessionLocal", return_value=db), \
             patch("app.routers.telegram_handlers.get_current_lesson", return_value=None), \
             patch("app.routers.telegram_handlers.LLMService") as mock_llm_cls, \
             patch("app.routers.telegram_handlers.LLMTopicSuggester") as mock_suggester_cls:

            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            mock_suggester = MagicMock()
            mock_suggester.suggest_next_topics.side_effect = Exception("LLM timeout")
            mock_suggester_cls.return_value = mock_suggester

            # Should NOT raise — bot must fallback gracefully
            asyncio.run(cmd_today_runner(mock_message))

        # Bot phai van gui tin nhan (khong crash)
        mock_message.answer.assert_called_once()


# ---------------------------------------------------------------------------
# Runner helper for async cmd_today tests
# ---------------------------------------------------------------------------

async def cmd_today_runner(message):
    """Wrapper to call cmd_today directly for testing."""
    from app.routers.telegram_handlers import cmd_today
    await cmd_today(message)
