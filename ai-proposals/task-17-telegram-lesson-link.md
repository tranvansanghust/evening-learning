# Task 17: Telegram Bot Gửi Link Bài Học

## Mục tiêu
Sau khi onboarding xong hoặc khi user gõ `/today`, bot gửi link tới web app (task-16) để user đọc nội dung bài học. Content được gen trước (task-14) trước khi gửi link để tránh user mở web thấy loading lâu.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước. Phụ thuộc task-14, task-15, task-16 đã hoàn thành.

## Flow chi tiết

```
User gõ /today
    → get_current_lesson()
    → Nếu có lesson:
        → LLMContentGenerator.get_or_generate() ← gen content nếu chưa có
        → Gửi message: "📖 Bài học hôm nay: {title}\n\n{link}"
        → Gửi tiếp: "Sau khi đọc xong, nhấn /done để làm quiz"
    → Nếu không có lesson (hoàn thành course):
        → Flow completion hiện tại (task-11)

Sau onboarding complete (complete_onboarding()):
    → Lấy lesson đầu tiên của course
    → Gen content
    → Gửi: "🎉 Bắt đầu học thôi! Đây là bài đầu tiên của bạn: {link}"
```

## Files cần thay đổi

- `backend/app/routers/telegram_handlers.py` — sửa `cmd_today` và `_handle_onboarding_step` (bước `completed`)
- `backend/app/config.py` — thêm `frontend_url` (nếu task-15 chưa thêm)
- `backend/tests/test_lesson_link.py` — **tạo mới** — tests

## Kế hoạch thực hiện

### Bước 1: Viết tests trước

`backend/tests/test_lesson_link.py`:

```python
# Test: /today gửi message chứa link http(s)://...
# Test: link chứa lesson_id đúng
# Test: message chứa tên bài học
# Test: LLMContentGenerator.get_or_generate() được gọi trước khi gửi link
# Test: sau onboarding complete → gửi link bài học đầu tiên
```

### Bước 2: Thêm helper `_build_lesson_link()`

Tránh lặp code giữa `cmd_today` và onboarding complete:

```python
# Trong telegram_handlers.py
def _build_lesson_url(lesson_id: int) -> str:
    from app.config import settings
    return f"{settings.frontend_url}/lesson/{lesson_id}"


async def _send_lesson_link(message: Message, lesson, course, db) -> None:
    """Gen content nếu chưa có, gửi link bài học."""
    from app.services.llm_content_generator import LLMContentGenerator
    from app.services.llm_service import LLMService
    from app.config import settings
    from app.models import Lesson

    total_lessons = db.query(Lesson).filter(Lesson.course_id == lesson.course_id).count()

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

    url = _build_lesson_url(lesson.lesson_id)
    await message.answer(
        f"📖 *Bài {lesson.sequence_number}: {lesson.title}*\n\n"
        f"Đọc nội dung bài học tại:\n{url}\n\n"
        f"Sau khi đọc xong, gõ /done để làm quiz ✍️",
        parse_mode="Markdown",
    )
```

### Bước 3: Sửa `cmd_today`

```python
@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    # ... existing code để get enrollment và lesson ...
    
    lesson = get_current_lesson(user_id=user.user_id, course_id=enrollment.course_id, db=db)
    
    if lesson is None:
        # Course completion flow (task-11)
        ...
    else:
        course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
        await _send_lesson_link(message, lesson, course, db)
```

### Bước 4: Gửi link sau onboarding complete

Trong `_handle_onboarding_step`, bước `reminder_time` (bước cuối onboarding) sau khi gọi `complete_onboarding()`:

```python
# Sau complete_onboarding() thành công
from app.models import Lesson, UserCourse, Course

enrollment = db.query(UserCourse).filter(
    UserCourse.user_id == user_id,
    UserCourse.status == "in_progress",
).first()

if enrollment:
    first_lesson = db.query(Lesson).filter(
        Lesson.course_id == enrollment.course_id
    ).order_by(Lesson.sequence_number).first()
    
    if first_lesson:
        course = db.query(Course).filter(Course.course_id == enrollment.course_id).first()
        await message.answer("🎉 Tuyệt! Đây là bài học đầu tiên của bạn:")
        await _send_lesson_link(message, first_lesson, course, db)
```

### Bước 5: Thêm `frontend_url` vào config (nếu task-15 chưa làm)

```python
# backend/app/config.py
frontend_url: str = "http://localhost:5173"
```

```env
# .env
FRONTEND_URL=https://your-domain.com
```

### Bước 6: Chạy tests

```bash
cd backend && python -m pytest tests/test_lesson_link.py -v
cd backend && python -m pytest tests/ -v  # toàn bộ
```

## Định nghĩa "Done"

- [ ] `/today` gửi link chứa `lesson_id` đúng
- [ ] Link format: `{FRONTEND_URL}/lesson/{lesson_id}`
- [ ] Message chứa tên bài học và hướng dẫn
- [ ] Content được gen trước khi gửi link (không để user mở web thấy loading)
- [ ] Sau onboarding complete → gửi link bài đầu tiên tự động
- [ ] `_send_lesson_link()` là helper dùng chung, không lặp code
- [ ] `FRONTEND_URL` trong settings
- [ ] Tests pass

## Rủi ro

- `_send_lesson_link()` gọi LLM sync trong handler → chậm ~3-5s. Cân nhắc gửi "Đang chuẩn bị bài học..." trước, rồi gen, rồi gửi link — tránh user nghĩ bot lag.
- Nếu LLM gen content thất bại → fallback content vẫn được lưu → link vẫn hoạt động, chỉ hiển thị "Nội dung đang chuẩn bị".
- `parse_mode="Markdown"` với aiogram cần escape ký tự đặc biệt trong `lesson.title`. Dùng `ParseMode.MARKDOWN_V2` hoặc bỏ parse_mode nếu gặp lỗi.
