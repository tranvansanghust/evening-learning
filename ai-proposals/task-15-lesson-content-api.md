# Task 15: Lesson Content API Endpoint

## Mục tiêu
Tạo FastAPI endpoint để serve nội dung bài học (Markdown) cho frontend web. Cần làm **sau task-14** (content generation).

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước. Phụ thuộc vào task-14.

## Files cần thay đổi / tạo mới

- `backend/app/routers/lesson_content.py` — **tạo mới** — API router
- `backend/app/main.py` — đăng ký router mới
- `backend/app/config.py` — thêm `frontend_url` setting
- `backend/tests/test_lesson_content_api.py` — **tạo mới** — tests

## Kế hoạch thực hiện

### Bước 1: Viết tests trước

`backend/tests/test_lesson_content_api.py`:

```python
# Test: GET /api/lessons/{lesson_id}/content trả 200 + JSON có content_markdown
# Test: lesson chưa có content → tự gen (mock LLMContentGenerator)
# Test: lesson_id không tồn tại → 404
# Test: CORS headers có trong response (Access-Control-Allow-Origin)
```

### Bước 2: Thêm `FRONTEND_URL` vào config

```python
# backend/app/config.py
frontend_url: str = "http://localhost:5173"  # Vite dev default
```

```env
# .env
FRONTEND_URL=https://your-domain.com
```

### Bước 3: Tạo router `lesson_content.py`

```python
# backend/app/routers/lesson_content.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


class LessonContentResponse(BaseModel):
    lesson_id: int
    title: str
    sequence_number: int
    content_markdown: str
    course_name: str
    generated_at: Optional[datetime] = None


@router.get("/{lesson_id}/content", response_model=LessonContentResponse)
async def get_lesson_content(lesson_id: int, db: Session = Depends(get_db)):
    """
    Trả nội dung bài học dưới dạng Markdown.
    Nếu chưa có content → gọi LLM gen và cache vào DB.
    """
    from app.models import Lesson, Course
    from app.services.llm_content_generator import LLMContentGenerator
    from app.services.llm_service import LLMService
    from app.config import settings

    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    course = db.query(Course).filter(Course.course_id == lesson.course_id).first()
    total_lessons = db.query(Lesson).filter(Lesson.course_id == lesson.course_id).count()

    if not lesson.content_markdown:
        llm = LLMService(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            fast_model=settings.llm_fast_model,
            smart_model=settings.llm_smart_model,
        )
        generator = LLMContentGenerator(client=llm.client, smart_model=settings.llm_smart_model)
        generator.get_or_generate(
            lesson=lesson,
            course_topic=course.title if course else lesson.title,
            total_lessons=total_lessons,
            db=db,
        )

    return LessonContentResponse(
        lesson_id=lesson.lesson_id,
        title=lesson.title,
        sequence_number=lesson.sequence_number,
        content_markdown=lesson.content_markdown or "",
        course_name=course.title if course else "",
        generated_at=lesson.content_generated_at,
    )
```

### Bước 4: Đăng ký router và CORS trong `main.py`

```python
# backend/app/main.py
from app.routers.lesson_content import router as lesson_content_router
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# CORS — cho phép frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(lesson_content_router)
```

### Bước 5: Chạy tests

```bash
cd backend && python -m pytest tests/test_lesson_content_api.py -v
```

## Định nghĩa "Done"

- [ ] `GET /api/lessons/{lesson_id}/content` trả JSON với `content_markdown`
- [ ] Lesson chưa có content → tự gen lazy, không crash
- [ ] 404 khi lesson_id không tồn tại
- [ ] CORS headers có trong response
- [ ] `FRONTEND_URL` trong settings và `.env`
- [ ] Router đăng ký trong `main.py`
- [ ] Tests pass

## Rủi ro

- Endpoint public (không cần auth) — ai cũng có thể gọi nếu biết lesson_id. Acceptable vì content không nhạy cảm.
- Gen lazy trong request có thể chậm ~3-5s nếu chưa có cache. Có thể add timeout hoặc background task nếu cần.
