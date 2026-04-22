# Task 14: LLM Lesson Content Generation

## Mục tiêu
Khi user nhận bài học mới, hệ thống gọi LLM để sinh nội dung bài học dưới dạng Markdown và lưu vào DB. Nội dung này sẽ được serve qua web (task-15) và link gửi qua Telegram (task-17).

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước. Làm trước task-15, task-16, task-17.

## Vấn đề cụ thể

Hiện tại `Lesson` model chỉ có `title` và `sequence_number` — không có nội dung thực tế. User nhận `/today` nhưng không có gì để đọc, chỉ làm quiz.

## Approach

- Thêm `content_markdown` (Text, nullable) vào `Lesson` model
- Thêm `content_generated_at` (DateTime, nullable) để biết khi nào content được gen
- Tạo `LLMContentGenerator` class trong `backend/app/services/llm_content_generator.py`
- Content được gen **lazy** (lần đầu được yêu cầu) và cached trong DB
- Không gen tất cả cùng lúc — tốn token và chậm

## Files cần thay đổi / tạo mới

- `backend/app/models/lesson.py` — thêm `content_markdown`, `content_generated_at`
- `backend/alembic/versions/` — migration mới
- `backend/app/services/llm_content_generator.py` — **tạo mới** — `LLMContentGenerator` class
- `backend/tests/test_llm_content_generator.py` — **tạo mới** — tests

## Kế hoạch thực hiện

### Bước 1: Viết tests trước

`backend/tests/test_llm_content_generator.py`:

```python
# Test: generate_lesson_content trả string markdown không rỗng
# Test: markdown chứa tiêu đề bài học
# Test: LLM lỗi → fallback về content template đơn giản (không crash)
# Test: get_or_generate() trả content từ DB nếu đã có (không gọi LLM lại)
# Test: get_or_generate() gọi LLM nếu content_markdown là None
```

### Bước 2: Thêm columns vào `Lesson` model

```python
# backend/app/models/lesson.py
from sqlalchemy import Text
content_markdown = Column(Text, nullable=True)
content_generated_at = Column(DateTime(timezone=True), nullable=True)
```

### Bước 3: Tạo Alembic migration

```bash
cd backend
source eveninig-learning-venv/bin/activate
alembic revision --autogenerate -m "add_content_markdown_to_lessons"
alembic upgrade head
```

### Bước 4: Tạo `LLMContentGenerator`

```python
# backend/app/services/llm_content_generator.py
class LLMContentGenerator:
    def __init__(self, client, smart_model: str):
        self.client = client
        self.smart_model = smart_model  # dùng smart_model vì content quan trọng

    def generate_lesson_content(
        self,
        course_topic: str,
        lesson_title: str,
        lesson_sequence: int,
        total_lessons: int,
        user_level: int = 0,  # 0-3
    ) -> str:
        """
        Sinh nội dung bài học dưới dạng Markdown.
        
        Returns:
            str: Markdown content. Fallback về template đơn giản nếu LLM lỗi.
        """
        level_desc = ["hoàn toàn mới bắt đầu", "biết cơ bản", "có kinh nghiệm", "nâng cao"][user_level]
        prompt = f"""Tạo nội dung bài học {lesson_sequence}/{total_lessons} cho khóa học "{course_topic}".

Tiêu đề bài: {lesson_title}
Trình độ học viên: {level_desc}

Yêu cầu:
- Viết bằng tiếng Việt
- Format Markdown rõ ràng với headers (##, ###)
- Bao gồm: lý thuyết ngắn gọn, ví dụ thực tế, 2-3 điểm cần nhớ
- Độ dài: 300-500 từ
- Phù hợp với trình độ học viên

Chỉ trả về nội dung Markdown, không có text giải thích thêm."""

        try:
            response = self.client.chat.completions.create(
                model=self.smart_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                return self._fallback_content(lesson_title)
            return content.strip()
        except Exception as e:
            logger.warning(f"generate_lesson_content failed: {e}")
            return self._fallback_content(lesson_title)

    def _fallback_content(self, lesson_title: str) -> str:
        return f"## {lesson_title}\n\nNội dung bài học đang được chuẩn bị. Vui lòng quay lại sau.\n\n*Gõ /today để bắt đầu quiz bài học này.*"

    def get_or_generate(self, lesson, course_topic: str, total_lessons: int, user_level: int = 0, db=None) -> str:
        """Trả content từ DB nếu đã có, sinh mới nếu chưa có."""
        if lesson.content_markdown:
            return lesson.content_markdown
        
        content = self.generate_lesson_content(
            course_topic=course_topic,
            lesson_title=lesson.title,
            lesson_sequence=lesson.sequence_number,
            total_lessons=total_lessons,
            user_level=user_level,
        )
        
        if db:
            from datetime import datetime, timezone
            lesson.content_markdown = content
            lesson.content_generated_at = datetime.now(timezone.utc)
            db.commit()
        
        return content
```

### Bước 5: Chạy tests

```bash
cd backend && python -m pytest tests/test_llm_content_generator.py -v
```

## Định nghĩa "Done"

- [ ] `Lesson` model có `content_markdown` và `content_generated_at`
- [ ] Migration chạy được
- [ ] `LLMContentGenerator` class tồn tại trong `llm_content_generator.py`
- [ ] `generate_lesson_content()` sinh Markdown hợp lệ
- [ ] LLM lỗi → fallback về template, không crash
- [ ] `get_or_generate()` dùng cache từ DB, không gen lại nếu đã có
- [ ] File không vượt 300 dòng
- [ ] Tests pass

## Rủi ro

- Smart model tốn token hơn fast model. Có thể dùng fast_model nếu budget thấp.
- Content gen lần đầu có thể chậm (~3-5s). Task-17 sẽ handle bằng cách gen trước khi gửi link.
- Content cố định trong DB — nếu prompt thay đổi, content cũ không được re-gen tự động. Có thể xóa `content_markdown = None` để force re-gen.
