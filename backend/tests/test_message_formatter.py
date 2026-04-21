"""Tests for message_formatter.py — format_quiz_detail function."""

import pytest
from app.services.message_formatter import format_quiz_detail


class TestFormatQuizDetail:
    """Tests for format_quiz_detail()."""

    def test_full_result_with_mastered_and_weak(self):
        """format_quiz_detail với cả concepts_mastered và concepts_weak đầy đủ."""
        lesson_name = "React Hooks"
        concepts_mastered = ["useState", "useEffect"]
        concepts_weak = [
            {
                "concept": "useCallback",
                "user_answer": "dùng để cache",
                "correct_explanation": "useCallback memoizes a callback function to prevent re-creation on every render.",
            }
        ]
        result = format_quiz_detail(lesson_name, concepts_mastered, concepts_weak)

        assert "React Hooks" in result
        assert "✅" in result
        assert "useState" in result
        assert "useEffect" in result
        assert "⚠️" in result
        assert "useCallback" in result
        assert "memoizes" in result
        assert "<b>" in result
        assert "<i>" in result
        assert "/today" in result

    def test_no_weak_concepts_hides_weak_section(self):
        """format_quiz_detail không có weak concepts → không hiển thị section ⚠️."""
        result = format_quiz_detail(
            lesson_name="Python Basics",
            concepts_mastered=["variables", "loops"],
            concepts_weak=[],
        )

        assert "✅" in result
        assert "variables" in result
        assert "loops" in result
        assert "⚠️" not in result

    def test_no_mastered_concepts_hides_mastered_section(self):
        """format_quiz_detail không có mastered → không hiển thị section ✅."""
        result = format_quiz_detail(
            lesson_name="Python Basics",
            concepts_mastered=[],
            concepts_weak=[
                {
                    "concept": "generators",
                    "user_answer": "không biết",
                    "correct_explanation": "Generators yield values lazily.",
                }
            ],
        )

        assert "✅" not in result
        assert "⚠️" in result
        assert "generators" in result

    def test_long_explanation_is_truncated_at_150_chars(self):
        """Weak concept với correct_explanation dài → truncate ở 150 chars."""
        long_explanation = "A" * 200  # 200 chars, sẽ bị truncate
        result = format_quiz_detail(
            lesson_name="Some Lesson",
            concepts_mastered=[],
            concepts_weak=[
                {
                    "concept": "thing",
                    "user_answer": "idk",
                    "correct_explanation": long_explanation,
                }
            ],
        )

        # Phần explanation trong result phải bị truncate (kết thúc bằng "...")
        assert "..." in result
        # Không được có chuỗi 200 ký tự A liên tục
        assert "A" * 200 not in result
        # Nhưng vẫn phải có 147 ký tự A (147 + 3 dấu "..." = 150)
        assert "A" * 147 in result

    def test_no_concepts_at_all_shows_fallback(self):
        """Khi không có cả hai danh sách → hiển thị fallback message."""
        result = format_quiz_detail(
            lesson_name="Empty Lesson",
            concepts_mastered=[],
            concepts_weak=[],
        )

        assert "Quiz hoàn thành" in result
        assert "/today" in result

    def test_weak_concept_as_plain_string(self):
        """Weak concept là plain string (không phải dict) → hiển thị đúng."""
        result = format_quiz_detail(
            lesson_name="Some Lesson",
            concepts_mastered=[],
            concepts_weak=["closures", "hoisting"],
        )

        assert "closures" in result
        assert "hoisting" in result
        assert "⚠️" in result

    def test_lesson_name_in_header(self):
        """Lesson name phải xuất hiện trong header của message."""
        result = format_quiz_detail(
            lesson_name="Advanced TypeScript",
            concepts_mastered=["generics"],
            concepts_weak=[],
        )

        assert "Advanced TypeScript" in result
        # Header phải có bold formatting
        assert "<b>" in result

    def test_today_command_always_present(self):
        """/today luôn xuất hiện ở cuối message."""
        result = format_quiz_detail("Lesson", ["concept"], [])
        assert "/today" in result

        result2 = format_quiz_detail("Lesson", [], [])
        assert "/today" in result2

    def test_short_explanation_not_truncated(self):
        """Explanation ngắn hơn 150 chars không bị truncate."""
        short_explanation = "Short explanation here."
        result = format_quiz_detail(
            lesson_name="Lesson",
            concepts_mastered=[],
            concepts_weak=[
                {
                    "concept": "topic",
                    "user_answer": "answer",
                    "correct_explanation": short_explanation,
                }
            ],
        )

        assert short_explanation in result
        # Không kết thúc bằng "..." (không bị truncate)
        # Kiểm tra rằng full explanation có mặt
        assert "Short explanation here." in result
