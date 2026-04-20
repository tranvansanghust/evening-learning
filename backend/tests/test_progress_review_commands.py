"""
Tests for _format_progress and _format_quiz_list helper functions.

Only tests pure helper functions — no Telegram mock needed.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock


def make_progress(lessons_completed=2, total_lessons=5, concepts_mastered=10, total_concepts=20):
    """Create a fake UserProgress object."""
    progress = MagicMock()
    progress.lessons_completed = lessons_completed
    progress.total_lessons = total_lessons
    progress.concepts_mastered = concepts_mastered
    progress.total_concepts = total_concepts
    return progress


def make_quiz_summary_preview(
    summary_id=1,
    lesson_name="React Hooks",
    concepts_mastered_count=3,
    concepts_weak_count=1,
    date=None,
):
    """Create a fake QuizSummaryPreview object."""
    preview = MagicMock()
    preview.summary_id = summary_id
    preview.lesson_name = lesson_name
    preview.concepts_mastered_count = concepts_mastered_count
    preview.concepts_weak_count = concepts_weak_count
    preview.date = date or datetime(2026, 4, 20, 10, 0, 0)
    return preview


# ---------------------------------------------------------------------------
# Tests for format_progress
# ---------------------------------------------------------------------------

class TestFormatProgress:
    """Tests for the format_progress helper function."""

    def test_format_progress_shows_lesson_counts(self):
        """format_progress includes lessons_completed / total_lessons."""
        from app.services.message_formatter import format_progress

        progress = make_progress(lessons_completed=2, total_lessons=5)
        result = format_progress(progress)

        assert "2" in result
        assert "5" in result

    def test_format_progress_shows_concept_counts(self):
        """format_progress includes concepts_mastered / total_concepts."""
        from app.services.message_formatter import format_progress

        progress = make_progress(concepts_mastered=10, total_concepts=20)
        result = format_progress(progress)

        assert "10" in result
        assert "20" in result

    def test_format_progress_shows_percentage(self):
        """format_progress shows percentage for lessons (2/5 = 40%)."""
        from app.services.message_formatter import format_progress

        progress = make_progress(lessons_completed=2, total_lessons=5)
        result = format_progress(progress)

        assert "40" in result

    def test_format_progress_zero_lessons(self):
        """format_progress handles 0/0 gracefully without division error."""
        from app.services.message_formatter import format_progress

        progress = make_progress(lessons_completed=0, total_lessons=0, concepts_mastered=0, total_concepts=0)
        result = format_progress(progress)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_progress_returns_string(self):
        """format_progress always returns a string."""
        from app.services.message_formatter import format_progress

        progress = make_progress()
        result = format_progress(progress)

        assert isinstance(result, str)

    def test_format_progress_has_emoji_header(self):
        """format_progress has a header with emoji."""
        from app.services.message_formatter import format_progress

        progress = make_progress()
        result = format_progress(progress)

        # Should have some kind of header
        assert "📊" in result or "Tiến độ" in result


# ---------------------------------------------------------------------------
# Tests for format_quiz_list
# ---------------------------------------------------------------------------

class TestFormatQuizList:
    """Tests for the format_quiz_list helper function."""

    def test_empty_list_returns_no_quiz_message(self):
        """Empty list → message prompting to use /done."""
        from app.services.message_formatter import format_quiz_list

        result = format_quiz_list([])

        assert "Chưa có quiz nào" in result
        assert "/done" in result

    def test_single_summary_appears_in_output(self):
        """One summary → lesson name and concept counts appear."""
        from app.services.message_formatter import format_quiz_list

        summaries = [
            make_quiz_summary_preview(
                lesson_name="React Hooks",
                concepts_mastered_count=3,
                concepts_weak_count=1,
            )
        ]
        result = format_quiz_list(summaries)

        assert "React Hooks" in result
        assert "3" in result

    def test_multiple_summaries_numbered(self):
        """3 summaries → all 3 appear, numbered."""
        from app.services.message_formatter import format_quiz_list

        summaries = [
            make_quiz_summary_preview(summary_id=1, lesson_name="Lesson A"),
            make_quiz_summary_preview(summary_id=2, lesson_name="Lesson B"),
            make_quiz_summary_preview(summary_id=3, lesson_name="Lesson C"),
        ]
        result = format_quiz_list(summaries)

        assert "Lesson A" in result
        assert "Lesson B" in result
        assert "Lesson C" in result
        # Should be numbered
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_returns_string(self):
        """format_quiz_list always returns a string."""
        from app.services.message_formatter import format_quiz_list

        result = format_quiz_list([])
        assert isinstance(result, str)

    def test_summary_with_weak_concepts_shown(self):
        """Summary with weak concepts shows weak concept count."""
        from app.services.message_formatter import format_quiz_list

        summaries = [
            make_quiz_summary_preview(
                concepts_mastered_count=2,
                concepts_weak_count=3,
            )
        ]
        result = format_quiz_list(summaries)

        assert "3" in result
