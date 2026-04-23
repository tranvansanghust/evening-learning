# Lesson Delivery Message Improvement

## Vấn đề

Tin nhắn giao bài học hiện tại hardcode và thiếu context:

```
📖 Bài 3: Section 3

Đọc nội dung bài học tại:
http://localhost:5173/lesson/128

Sau khi đọc xong, gõ /done để làm quiz ✍️
```

Vấn đề:
- `Section 3` không nói lên gì — user không biết sẽ học gì
- Không có recap bài trước → mất liên tục
- Không hiển thị tên khóa học

## Format mong muốn

```
[1 câu recap bài trước học gì — nếu có]

📖 Kubernetes Cơ Bản - Bài 3: Pod và Container

Đọc nội dung bài học tại:
http://localhost:5173/lesson/128

Sau khi đọc xong, gõ /done để làm quiz ✍️
```

- **Dòng recap**: chỉ hiện nếu user đã học ít nhất 1 bài trước. VD: _"Bài trước bạn đã học về Kubernetes là gì và lý do dùng."_
- **Title**: `[Course Name] - Bài N: [lesson title ngắn gọn]` — lesson title lấy từ `lesson.title` sau khi đã normalize qua LLM curriculum (không còn "Section N")
- **3 dòng cuối**: giữ nguyên

## Files cần thay đổi

- `backend/app/routers/lesson_helpers.py` — hàm `_send_lesson_link()`:
  - Nhận thêm `previous_lesson` (Lesson ORM hoặc None)
  - Build recap line từ `previous_lesson.title` hoặc quiz summary của bài trước
  - Format title: `f"{course.name} - Bài {lesson.sequence_number}: {lesson.title}"`

- `backend/app/routers/telegram_handlers.py` — các nơi gọi `_send_lesson_link()`:
  - Truyền thêm `previous_lesson` (query lesson có `sequence_number = current - 1`)

## Kế hoạch thực hiện

### `lesson_helpers.py` — `_send_lesson_link()`

```python
async def _send_lesson_link(message, lesson, course, db, previous_lesson=None):
    ...
    # Build recap line
    recap = ""
    if previous_lesson:
        recap = f"_Bài trước: {previous_lesson.title}_\n\n"

    course_prefix = f"{course.name} - " if course else ""
    title_line = f"📖 *{course_prefix}Bài {lesson.sequence_number}: {lesson.title}*"

    await message.answer(
        f"{recap}"
        f"{title_line}\n\n"
        f"[📚 Đọc bài học tại đây]({url})\n\n"
        f"Sau khi đọc xong, gõ /done để làm quiz ✍️",
        parse_mode="Markdown",
    )
```

### Lấy `previous_lesson`

```python
# Trong cmd_today hoặc onboarding completion:
from app.models import Lesson
previous_lesson = db.query(Lesson).filter(
    Lesson.course_id == lesson.course_id,
    Lesson.sequence_number == lesson.sequence_number - 1
).first()  # None nếu bài đầu tiên
```

## Lưu ý

- Bài đầu tiên (`sequence_number == 1`): không hiển thị recap
- Lesson title phải có nghĩa — phụ thuộc vào fix `course-title-normalization.md` và LLM curriculum generation
- Recap chỉ 1 dòng ngắn — không cần gọi LLM thêm, dùng `previous_lesson.title` là đủ
