"""
Tests for LLMContentGenerator.

Tests:
- generate_lesson_content trả string markdown không rỗng
- markdown chứa tiêu đề bài học
- LLM lỗi → fallback về content template đơn giản (không crash)
- get_or_generate() trả content từ DB nếu đã có (không gọi LLM lại)
- get_or_generate() gọi LLM nếu content_markdown là None
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services.llm_content_generator import LLMContentGenerator


def make_llm_client(response_content: str) -> MagicMock:
    """Tạo fake OpenAI client trả về response_content."""
    client = MagicMock()
    choice = MagicMock()
    choice.message.content = response_content
    client.chat.completions.create.return_value = MagicMock(choices=[choice])
    return client


def make_lesson(title: str, sequence_number: int, content_markdown=None) -> MagicMock:
    """Tạo fake Lesson object."""
    lesson = MagicMock()
    lesson.title = title
    lesson.sequence_number = sequence_number
    lesson.content_markdown = content_markdown
    lesson.content_generated_at = None
    return lesson


class TestGenerateLessonContent:
    """Kiểm tra generate_lesson_content() trả về Markdown hợp lệ."""

    def test_returns_non_empty_string(self):
        """generate_lesson_content trả về string không rỗng."""
        markdown_response = "## SQL cơ bản\n\nNội dung bài học...\n\n### Ví dụ\n\nSELECT * FROM users;"
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="SQL cơ bản",
            lesson_title="Giới thiệu SQL",
            lesson_sequence=1,
            total_lessons=10,
        )

        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_markdown_contains_lesson_title(self):
        """Markdown trả về chứa tiêu đề bài học."""
        lesson_title = "Câu lệnh SELECT"
        markdown_response = f"## {lesson_title}\n\nLý thuyết SELECT...\n\n### Ví dụ thực tế\n\nSELECT name FROM users;"
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="SQL cơ bản",
            lesson_title=lesson_title,
            lesson_sequence=2,
            total_lessons=10,
        )

        assert lesson_title in result

    def test_calls_smart_model(self):
        """LLM được gọi với smart_model, không phải fast_model."""
        markdown_response = "## Bài học\n\nNội dung..."
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Biến và kiểu dữ liệu",
            lesson_sequence=1,
            total_lessons=5,
        )

        client.chat.completions.create.assert_called_once()
        call_kwargs = client.chat.completions.create.call_args
        model_used = call_kwargs.kwargs.get("model") or (call_kwargs.args[0] if call_kwargs.args else None)
        assert model_used == "gpt-4o"

    def test_prompt_contains_course_topic(self):
        """Prompt gửi LLM phải chứa course_topic."""
        markdown_response = "## Bài học\n\nNội dung..."
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        generator.generate_lesson_content(
            course_topic="Machine Learning với Python",
            lesson_title="Linear Regression",
            lesson_sequence=3,
            total_lessons=10,
        )

        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or []
        all_content = " ".join(m.get("content", "") for m in messages)
        assert "Machine Learning với Python" in all_content

    def test_prompt_contains_lesson_title(self):
        """Prompt gửi LLM phải chứa lesson_title."""
        markdown_response = "## Bài học\n\nNội dung..."
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        generator.generate_lesson_content(
            course_topic="React",
            lesson_title="useState Hook",
            lesson_sequence=4,
            total_lessons=12,
        )

        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or []
        all_content = " ".join(m.get("content", "") for m in messages)
        assert "useState Hook" in all_content

    def test_strips_whitespace_from_response(self):
        """Kết quả trả về phải được strip whitespace."""
        markdown_response = "   ## Bài học\n\nNội dung...   "
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Functions",
            lesson_sequence=1,
            total_lessons=5,
        )

        assert result == result.strip()


class TestGenerateLessonContentFallback:
    """Kiểm tra fallback khi LLM lỗi."""

    def test_fallback_when_llm_raises_exception(self):
        """LLM raise exception → fallback, không crash."""
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("LLM API down")
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Vòng lặp for",
            lesson_sequence=2,
            total_lessons=8,
        )

        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_fallback_contains_lesson_title(self):
        """Fallback phải chứa tên bài học."""
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("timeout")
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="List Comprehension",
            lesson_sequence=3,
            total_lessons=8,
        )

        assert "List Comprehension" in result

    def test_fallback_when_llm_returns_empty_string(self):
        """LLM trả chuỗi rỗng → fallback, không crash."""
        client = make_llm_client("")
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Dictionary",
            lesson_sequence=4,
            total_lessons=8,
        )

        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_no_exception_for_various_llm_errors(self):
        """Với bất kỳ exception nào từ LLM, không được raise."""
        for exc in [RuntimeError("err"), ValueError("val"), ConnectionError("conn"), TimeoutError("timeout")]:
            client = MagicMock()
            client.chat.completions.create.side_effect = exc
            generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

            result = generator.generate_lesson_content(
                course_topic="SQL",
                lesson_title="JOIN clause",
                lesson_sequence=5,
                total_lessons=10,
            )
            assert isinstance(result, str) and len(result.strip()) > 0, f"Failed for {exc}"


class TestGetOrGenerate:
    """Kiểm tra get_or_generate() — caching logic."""

    def test_returns_existing_content_without_calling_llm(self):
        """Nếu lesson.content_markdown đã có, không gọi LLM."""
        existing_content = "## Bài học đã có\n\nNội dung đã được lưu trong DB."
        lesson = make_lesson("SQL SELECT", 1, content_markdown=existing_content)

        client = MagicMock()
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.get_or_generate(
            lesson=lesson,
            course_topic="SQL cơ bản",
            total_lessons=10,
        )

        assert result == existing_content
        client.chat.completions.create.assert_not_called()

    def test_calls_llm_when_content_is_none(self):
        """Nếu lesson.content_markdown là None, gọi LLM."""
        markdown_response = "## SQL SELECT\n\nLý thuyết SELECT..."
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        lesson = make_lesson("SQL SELECT", 1, content_markdown=None)

        result = generator.get_or_generate(
            lesson=lesson,
            course_topic="SQL cơ bản",
            total_lessons=10,
        )

        client.chat.completions.create.assert_called_once()
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_saves_to_db_after_generation(self):
        """Sau khi gen, content được lưu vào lesson.content_markdown và commit DB."""
        markdown_response = "## SQL SELECT\n\nNội dung mới..."
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        lesson = make_lesson("SQL SELECT", 1, content_markdown=None)
        db = MagicMock()

        generator.get_or_generate(
            lesson=lesson,
            course_topic="SQL cơ bản",
            total_lessons=10,
            db=db,
        )

        assert lesson.content_markdown is not None
        assert lesson.content_generated_at is not None
        db.commit.assert_called_once()

    def test_no_db_commit_when_db_is_none(self):
        """Nếu db=None, không commit (không crash)."""
        markdown_response = "## Bài học\n\nNội dung..."
        client = make_llm_client(markdown_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        lesson = make_lesson("Python basics", 1, content_markdown=None)

        # Không được raise dù db=None
        result = generator.get_or_generate(
            lesson=lesson,
            course_topic="Python",
            total_lessons=5,
            db=None,
        )

        assert isinstance(result, str)

    def test_returns_cached_content_even_if_llm_would_fail(self):
        """Cache từ DB trả về đúng, dù LLM có lỗi đi nữa."""
        existing_content = "## Nội dung đã cached\n\nKhông cần gọi LLM."
        lesson = make_lesson("Cached Lesson", 2, content_markdown=existing_content)

        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("Would fail if called")
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.get_or_generate(
            lesson=lesson,
            course_topic="Python",
            total_lessons=5,
        )

        assert result == existing_content

    def test_stale_code_fence_cache_triggers_regeneration(self):
        """Content cached với code fence (stale) phải bị bỏ qua và re-generate."""
        stale_content = "```markdown\n## Bài học\n\nNội dung cũ...\n```"
        fresh_content = "## Bài học\n\nNội dung mới không có code fence."
        lesson = make_lesson("SQL SELECT", 1, content_markdown=stale_content)

        client = make_llm_client(fresh_content)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.get_or_generate(
            lesson=lesson,
            course_topic="SQL",
            total_lessons=5,
        )

        client.chat.completions.create.assert_called_once()
        assert result == fresh_content

    def test_valid_cache_skips_llm_call(self):
        """Content cached không có code fence → không gọi LLM."""
        valid_content = "## Bài học\n\nNội dung hợp lệ."
        lesson = make_lesson("SQL SELECT", 1, content_markdown=valid_content)

        client = MagicMock()
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.get_or_generate(
            lesson=lesson,
            course_topic="SQL",
            total_lessons=5,
        )

        client.chat.completions.create.assert_not_called()
        assert result == valid_content


class TestStripCodeFences:
    """Kiểm tra stripping code fences từ LLM response."""

    def test_strips_markdown_code_fence(self):
        """LLM trả về content wrapped trong ```markdown ... ``` → stripped."""
        raw_response = "```markdown\n## Bài học\n\nNội dung bài học...\n```"
        client = make_llm_client(raw_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Functions",
            lesson_sequence=1,
            total_lessons=5,
        )

        assert not result.startswith("```")
        assert "## Bài học" in result
        assert "Nội dung bài học..." in result

    def test_strips_plain_code_fence(self):
        """LLM trả về content wrapped trong ``` ... ``` (không có ngôn ngữ)."""
        raw_response = "```\n## Bài học\n\nNội dung bài học...\n```"
        client = make_llm_client(raw_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Functions",
            lesson_sequence=1,
            total_lessons=5,
        )

        assert not result.startswith("```")
        assert "## Bài học" in result

    def test_no_fence_content_unchanged(self):
        """LLM trả về content không có code fence → không thay đổi."""
        raw_response = "## Bài học\n\nNội dung bình thường."
        client = make_llm_client(raw_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Functions",
            lesson_sequence=1,
            total_lessons=5,
        )

        assert result == raw_response.strip()

    def test_fallback_when_fence_wraps_empty_content(self):
        """LLM trả về chỉ ``` không có nội dung bên trong → fallback."""
        raw_response = "```\n```"
        client = make_llm_client(raw_response)
        generator = LLMContentGenerator(client=client, smart_model="gpt-4o")

        result = generator.generate_lesson_content(
            course_topic="Python",
            lesson_title="Empty Lesson",
            lesson_sequence=1,
            total_lessons=5,
        )

        assert isinstance(result, str)
        assert len(result.strip()) > 0
        assert "Empty Lesson" in result
