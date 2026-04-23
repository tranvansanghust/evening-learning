"""
LLM Content Generator for lesson content.

Generates Markdown lesson content using LLM and caches results in DB.
Content is generated lazily — only when first requested.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_LEVEL_DESCRIPTIONS = [
    "hoàn toàn mới bắt đầu",
    "biết cơ bản",
    "có kinh nghiệm",
    "nâng cao",
]


class LLMContentGenerator:
    """
    Generates Markdown lesson content using an LLM.

    Content is generated lazily and cached in the DB via get_or_generate().
    Falls back to a simple template if LLM fails — never crashes.

    Attributes:
        client: OpenAI-compatible API client
        smart_model: Model name for content generation (smart model for quality)
    """

    def __init__(self, client, smart_model: str):
        """
        Initialize the generator.

        Args:
            client: OpenAI-compatible client (e.g. openai.OpenAI)
            smart_model: Model identifier to use for generation
        """
        self.client = client
        self.smart_model = smart_model

    def generate_lesson_content(
        self,
        course_topic: str,
        lesson_title: str,
        lesson_sequence: int,
        total_lessons: int,
        user_level: int = 0,
    ) -> str:
        """
        Generate lesson content as Markdown.

        Calls the LLM with a structured prompt and returns the result.
        Falls back to a simple template if the LLM fails or returns empty.

        Args:
            course_topic: Name/topic of the course
            lesson_title: Title of the specific lesson
            lesson_sequence: Position of this lesson in the course (1-indexed)
            total_lessons: Total number of lessons in the course
            user_level: Learner level 0-3 (0=beginner, 3=advanced)

        Returns:
            str: Markdown content, never empty.
        """
        level_desc = _LEVEL_DESCRIPTIONS[max(0, min(3, user_level))]
        prompt = (
            f'Tạo nội dung bài học {lesson_sequence}/{total_lessons} cho khóa học "{course_topic}".\n\n'
            f"Tiêu đề bài: {lesson_title}\n"
            f"Trình độ học viên: {level_desc}\n\n"
            "Yêu cầu:\n"
            "- Viết bằng tiếng Việt\n"
            "- Format Markdown rõ ràng với headers (##, ###)\n"
            "- Bao gồm: lý thuyết ngắn gọn, ví dụ thực tế, 2-3 điểm cần nhớ\n"
            "- Độ dài: 300-500 từ\n"
            "- Phù hợp với trình độ học viên\n\n"
            "Chỉ trả về nội dung Markdown, không có text giải thích thêm."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.smart_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                logger.warning("generate_lesson_content: LLM returned empty content, using fallback")
                return self._fallback_content(lesson_title)
            content = content.strip()
            # Strip ```markdown or ``` wrapping that LLM sometimes adds
            if content.startswith("```"):
                lines = content.split("\n", 1)
                content = lines[1] if len(lines) > 1 else ""
                content = content.removesuffix("```").strip()
            if not content:
                logger.warning("generate_lesson_content: content empty after stripping code fences, using fallback")
                return self._fallback_content(lesson_title)
            return content
        except Exception as e:
            logger.warning(f"generate_lesson_content failed: {e}")
            return self._fallback_content(lesson_title)

    def get_or_generate(
        self,
        lesson,
        course_topic: str,
        total_lessons: int,
        user_level: int = 0,
        db=None,
    ) -> str:
        """
        Return cached content from DB or generate it if not yet available.

        If lesson.content_markdown is already set, return it immediately
        without calling the LLM. Otherwise generate, optionally save to DB,
        and return the new content.

        Args:
            lesson: Lesson ORM object (must have .content_markdown, .title,
                    .sequence_number, .content_generated_at attributes)
            course_topic: Name/topic of the course
            total_lessons: Total number of lessons in the course
            user_level: Learner level 0-3
            db: SQLAlchemy session (optional). If provided, commits after saving.

        Returns:
            str: Markdown content, never empty.
        """
        # Treat code-fence-wrapped content as stale/invalid (cached before fix was applied)
        if lesson.content_markdown and not lesson.content_markdown.startswith("```"):
            return lesson.content_markdown

        content = self.generate_lesson_content(
            course_topic=course_topic,
            lesson_title=lesson.title,
            lesson_sequence=lesson.sequence_number,
            total_lessons=total_lessons,
            user_level=user_level,
        )

        lesson.content_markdown = content
        lesson.content_generated_at = datetime.now(timezone.utc)

        if db is not None:
            db.commit()

        return content

    def _fallback_content(self, lesson_title: str) -> str:
        """Generate a simple fallback template when LLM is unavailable."""
        return (
            f"## {lesson_title}\n\n"
            "Nội dung bài học đang được chuẩn bị. Vui lòng quay lại sau.\n\n"
            "*Gõ /today để bắt đầu quiz bài học này.*"
        )
