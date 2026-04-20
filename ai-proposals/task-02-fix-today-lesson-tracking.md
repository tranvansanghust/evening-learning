# Task 02: Fix /today — Track bài học hiện tại đúng

## Mục tiêu
Lệnh `/today` hiện luôn trả về lesson đầu tiên của khóa học dù user đã học bao nhiêu bài. Cần sửa để trả về đúng bài học tiếp theo mà user chưa làm quiz.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước.

## File cần thay đổi

- `backend/app/routers/telegram_handlers.py` — sửa `cmd_today` (dòng 95–139)

## Không cần migration DB

Logic có thể suy ra từ dữ liệu đã có: một lesson được coi là "đã học" khi có `QuizSession` với `status="completed"` cho lesson đó của user.

## Kế hoạch thực hiện

### Bước 1: Viết test trước (TDD)

Tạo hoặc thêm vào `backend/tests/test_today_command.py`:

```python
# Test: user chưa có quiz nào → trả lesson đầu tiên
# Test: user đã complete quiz lesson 1 → trả lesson 2
# Test: user đã complete tất cả → trả thông báo hoàn thành
```

Dùng fixtures tạo User, Course, 3 Lessons, UserCourse(IN_PROGRESS). Test gọi trực tiếp helper function (không cần Telegram mock).

### Bước 2: Extract helper function `get_current_lesson`

Tạo helper function trong `telegram_handlers.py` (hoặc trong `OnboardingService` nếu phù hợp hơn):

```python
def get_current_lesson(user_id: int, course_id: int, db: Session) -> Optional[Lesson]:
    """
    Trả về lesson tiếp theo mà user chưa complete quiz.
    Logic: lesson nào chưa có QuizSession completed → đó là bài hiện tại.
    Nếu tất cả đã done → trả None.
    """
    from app.models import Lesson, QuizSession
    
    lessons = db.query(Lesson).filter(
        Lesson.course_id == course_id
    ).order_by(Lesson.sequence_number).all()
    
    completed_lesson_ids = {
        qs.lesson_id
        for qs in db.query(QuizSession).filter(
            QuizSession.user_id == user_id,
            QuizSession.status == "completed",
        ).all()
    }
    
    for lesson in lessons:
        if lesson.lesson_id not in completed_lesson_ids:
            return lesson
    
    return None  # Tất cả đã xong
```

### Bước 3: Sửa `cmd_today` để dùng helper

Thay `.order_by(Lesson.sequence_number).first()` bằng `get_current_lesson(user_id, course_id, db)`.

Thêm case khi trả về `None` (user hoàn thành toàn bộ khóa học):

```python
if not lesson:
    await message.answer(
        f"🎉 Bạn đã hoàn thành toàn bộ khoá học *{course.name}*!\n\n"
        "Gõ /progress để xem kết quả.",
        parse_mode="Markdown",
    )
    return
```

### Bước 4: Chạy tests

```bash
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] Test cover 3 cases: chưa làm gì / đã làm một phần / đã xong hết
- [ ] `cmd_today` hiển thị đúng bài chưa học
- [ ] Khi hoàn thành hết, trả thông báo chúc mừng thay vì lỗi
- [ ] Tests pass

## Lưu ý
Một lesson có thể có nhiều QuizSession (user có thể làm lại). Coi là "done" khi có ÍT NHẤT một session `status="completed"` cho lesson đó.
