"""
Tests for get_current_lesson helper function used by /today command.

Tests verify that the function returns the correct next lesson
based on completed QuizSessions for a user.
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


# ---------------------------------------------------------------------------
# Tests for get_current_lesson
# ---------------------------------------------------------------------------

class TestGetCurrentLesson:
    """Tests cho helper function get_current_lesson."""

    def test_no_completed_quiz_returns_first_lesson(self):
        """
        User chưa có quiz nào completed → trả về lesson đầu tiên (sequence_number=1).
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
        User đã complete quiz cho lesson 1 → trả về lesson 2.
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
        User đã complete tất cả lessons → trả về None.
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
        QuizSession với status='active' không được tính là completed.
        User vẫn phải nhận lesson tương ứng.
        """
        from app.routers.telegram_handlers import get_current_lesson

        lessons = [
            make_lesson(lesson_id=1, sequence_number=1, title="Intro"),
            make_lesson(lesson_id=2, sequence_number=2, title="Basics"),
        ]
        # Lesson 1 chỉ có session active, chưa completed
        active_sessions = [
            make_quiz_session(session_id=100, lesson_id=1, status="active"),
        ]
        db = make_db_session(lessons=lessons, quiz_sessions=active_sessions)

        result = get_current_lesson(user_id=10, course_id=1, db=db)

        assert result is not None
        assert result.lesson_id == 1

    def test_no_lessons_returns_none(self):
        """
        Khoá học không có lesson nào → trả về None.
        """
        from app.routers.telegram_handlers import get_current_lesson

        db = make_db_session(lessons=[], quiz_sessions=[])

        result = get_current_lesson(user_id=10, course_id=1, db=db)

        assert result is None
