"""
Tests for GET /api/lessons/{lesson_id}/content endpoint.

Tests:
- 200 + JSON with content_markdown when lesson has cached content
- lesson without content → lazy gen (mock LLMContentGenerator)
- lesson_id not found → 404
- CORS headers present in response (Access-Control-Allow-Origin)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_lesson(lesson_id: int, title: str, sequence_number: int,
                course_id: int, content_markdown=None, content_generated_at=None) -> MagicMock:
    """Create a fake Lesson ORM object."""
    lesson = MagicMock()
    lesson.lesson_id = lesson_id
    lesson.title = title
    lesson.sequence_number = sequence_number
    lesson.course_id = course_id
    lesson.content_markdown = content_markdown
    lesson.content_generated_at = content_generated_at
    return lesson


def make_course(course_id: int, title: str) -> MagicMock:
    """Create a fake Course ORM object."""
    course = MagicMock()
    course.course_id = course_id
    course.title = title
    return course


# ---------------------------------------------------------------------------
# TestClient with DB override
# ---------------------------------------------------------------------------

class TestGetLessonContentFound:
    """GET /api/lessons/{lesson_id}/content — lesson exists with cached content."""

    def test_returns_200_with_content_markdown(self):
        """Lesson có content_markdown → trả 200 JSON với content_markdown."""
        lesson = make_lesson(
            lesson_id=1,
            title="Giới thiệu SQL",
            sequence_number=1,
            course_id=10,
            content_markdown="## SQL\n\nNội dung bài học.",
        )
        course = make_course(course_id=10, title="SQL cơ bản")

        mock_db = MagicMock()
        # db.query(Lesson).filter(...).first() → lesson
        # db.query(Course).filter(...).first() → course
        # db.query(Lesson).filter(...).count() → 5

        def query_side_effect(model):
            from app.models import Lesson, Course
            q = MagicMock()
            if model is Lesson:
                filter_mock = MagicMock()
                filter_mock.first.return_value = lesson
                filter_mock.count.return_value = 5
                q.filter.return_value = filter_mock
            elif model is Course:
                filter_mock = MagicMock()
                filter_mock.first.return_value = course
                q.filter.return_value = filter_mock
            return q

        mock_db.query.side_effect = query_side_effect

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.get("/api/lessons/1/content")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "content_markdown" in data
        assert data["content_markdown"] == "## SQL\n\nNội dung bài học."
        assert data["lesson_id"] == 1
        assert data["title"] == "Giới thiệu SQL"
        assert data["course_name"] == "SQL cơ bản"

    def test_returns_correct_sequence_number(self):
        """Response chứa đúng sequence_number."""
        lesson = make_lesson(
            lesson_id=3,
            title="Bài 3",
            sequence_number=3,
            course_id=5,
            content_markdown="## Bài 3\n\nNội dung.",
        )
        course = make_course(course_id=5, title="Python")

        mock_db = MagicMock()

        def query_side_effect(model):
            from app.models import Lesson, Course
            q = MagicMock()
            if model is Lesson:
                f = MagicMock()
                f.first.return_value = lesson
                f.count.return_value = 10
                q.filter.return_value = f
            elif model is Course:
                f = MagicMock()
                f.first.return_value = course
                q.filter.return_value = f
            return q

        mock_db.query.side_effect = query_side_effect

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.get("/api/lessons/3/content")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["sequence_number"] == 3


class TestGetLessonContentLazyGeneration:
    """GET /api/lessons/{lesson_id}/content — lesson without content → lazy gen."""

    def test_generates_content_when_missing(self):
        """Lesson chưa có content → gọi LLMContentGenerator, trả 200."""
        lesson = make_lesson(
            lesson_id=2,
            title="Câu lệnh SELECT",
            sequence_number=2,
            course_id=10,
            content_markdown=None,
        )
        course = make_course(course_id=10, title="SQL cơ bản")

        mock_db = MagicMock()

        def query_side_effect(model):
            from app.models import Lesson, Course
            q = MagicMock()
            if model is Lesson:
                f = MagicMock()
                f.first.return_value = lesson
                f.count.return_value = 8
                q.filter.return_value = f
            elif model is Course:
                f = MagicMock()
                f.first.return_value = course
                q.filter.return_value = f
            return q

        mock_db.query.side_effect = query_side_effect

        generated_content = "## Câu lệnh SELECT\n\nNội dung do LLM tạo."

        def fake_get_or_generate(lesson, course_topic, total_lessons, db):
            lesson.content_markdown = generated_content
            return generated_content

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch(
            "app.routers.lesson_content.LLMContentGenerator"
        ) as MockGenerator, patch(
            "app.routers.lesson_content.LLMService"
        ) as MockLLMService:
            mock_llm_instance = MagicMock()
            MockLLMService.return_value = mock_llm_instance

            instance = MagicMock()
            instance.get_or_generate.side_effect = fake_get_or_generate
            MockGenerator.return_value = instance

            client = TestClient(app)
            response = client.get("/api/lessons/2/content")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "content_markdown" in data
        # Generator should have been called
        instance.get_or_generate.assert_called_once()

    def test_llm_generator_called_with_correct_args(self):
        """LLMContentGenerator.get_or_generate được gọi với lesson, course_topic, total_lessons."""
        lesson = make_lesson(
            lesson_id=5,
            title="JOIN Operations",
            sequence_number=5,
            course_id=20,
            content_markdown=None,
        )
        course = make_course(course_id=20, title="Advanced SQL")

        mock_db = MagicMock()

        def query_side_effect(model):
            from app.models import Lesson, Course
            q = MagicMock()
            if model is Lesson:
                f = MagicMock()
                f.first.return_value = lesson
                f.count.return_value = 12
                q.filter.return_value = f
            elif model is Course:
                f = MagicMock()
                f.first.return_value = course
                q.filter.return_value = f
            return q

        mock_db.query.side_effect = query_side_effect

        def fake_get_or_generate(lesson, course_topic, total_lessons, db):
            lesson.content_markdown = "## JOIN\n\nNội dung."
            return lesson.content_markdown

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch(
            "app.routers.lesson_content.LLMContentGenerator"
        ) as MockGenerator, patch(
            "app.routers.lesson_content.LLMService"
        ) as MockLLMService:
            mock_llm_instance = MagicMock()
            MockLLMService.return_value = mock_llm_instance

            instance = MagicMock()
            instance.get_or_generate.side_effect = fake_get_or_generate
            MockGenerator.return_value = instance

            client = TestClient(app)
            response = client.get("/api/lessons/5/content")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        call_kwargs = instance.get_or_generate.call_args
        assert call_kwargs.kwargs.get("course_topic") == "Advanced SQL" or (
            len(call_kwargs.args) > 1 and call_kwargs.args[1] == "Advanced SQL"
        )


class TestGetLessonContentNotFound:
    """GET /api/lessons/{lesson_id}/content — lesson_id does not exist → 404."""

    def test_returns_404_when_lesson_not_found(self):
        """Lesson không tồn tại → 404."""
        mock_db = MagicMock()

        def query_side_effect(model):
            from app.models import Lesson
            q = MagicMock()
            if model is Lesson:
                f = MagicMock()
                f.first.return_value = None
                f.count.return_value = 0
                q.filter.return_value = f
            return q

        mock_db.query.side_effect = query_side_effect

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.get("/api/lessons/9999/content")
        app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_404_detail_mentions_lesson(self):
        """404 response detail phải đề cập đến lesson."""
        mock_db = MagicMock()

        def query_side_effect(model):
            from app.models import Lesson
            q = MagicMock()
            f = MagicMock()
            f.first.return_value = None
            f.count.return_value = 0
            q.filter.return_value = f
            return q

        mock_db.query.side_effect = query_side_effect

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.get("/api/lessons/42/content")
        app.dependency_overrides.clear()

        assert response.status_code == 404
        detail = response.json()["detail"].lower()
        assert "lesson" in detail


class TestCORSHeaders:
    """CORS headers present in response for frontend access."""

    def test_cors_headers_present_for_options(self):
        """OPTIONS preflight request trả Access-Control-Allow-Origin."""
        client = TestClient(app)
        response = client.options(
            "/api/lessons/1/content",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight returns 200 with allow-origin header
        assert "access-control-allow-origin" in response.headers

    def test_cors_header_present_on_get_with_lesson(self):
        """GET request with Origin header → Access-Control-Allow-Origin in response."""
        lesson = make_lesson(
            lesson_id=1,
            title="Test Lesson",
            sequence_number=1,
            course_id=1,
            content_markdown="## Test\n\nContent.",
        )
        course = make_course(course_id=1, title="Test Course")

        mock_db = MagicMock()

        def query_side_effect(model):
            from app.models import Lesson, Course
            q = MagicMock()
            if model is Lesson:
                f = MagicMock()
                f.first.return_value = lesson
                f.count.return_value = 3
                q.filter.return_value = f
            elif model is Course:
                f = MagicMock()
                f.first.return_value = course
                q.filter.return_value = f
            return q

        mock_db.query.side_effect = query_side_effect

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)
        response = client.get(
            "/api/lessons/1/content",
            headers={"Origin": "http://localhost:5173"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
