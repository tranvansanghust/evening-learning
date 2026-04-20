# Task 07: Re-engagement Flow (+1/+3/+5 ngày)

## Mục tiêu
Khi user bỏ học nhiều ngày, bot nhắc theo thang bậc: +1 ngày nhắc nhẹ, +3 ngày kèm context, +5 ngày hỏi reschedule, >5 ngày im lặng.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước. **Phụ thuộc task-05** — cần APScheduler đã có sẵn.

## Files cần thay đổi

- `backend/app/models/user_course.py` — thêm `last_activity_at`
- `backend/alembic/versions/` — migration mới
- `backend/app/routers/telegram_handlers.py` — update `last_activity_at` khi user hoạt động
- `backend/app/bot_polling.py` — thêm daily re-engagement job

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Tạo `backend/tests/test_reengagement.py`:

```python
# Test: days_inactive=1 → send "+1 day" message
# Test: days_inactive=3 → send "+3 day" message với context deadline
# Test: days_inactive=5 → send "+5 day" message hỏi reschedule
# Test: days_inactive=6 → không gửi gì
# Test: days_inactive=0 → không gửi gì (đang active)
# Test: UserCourse.status != IN_PROGRESS → không gửi gì
```

### Bước 2: Thêm `last_activity_at` vào `UserCourse`

```python
# app/models/user_course.py
from sqlalchemy import DateTime
from sqlalchemy.sql import func

last_activity_at = Column(DateTime, nullable=True)
```

### Bước 3: Tạo Alembic migration

```bash
cd backend
source eveninig-learning-venv/bin/activate
alembic revision --autogenerate -m "add_last_activity_at_to_user_courses"
alembic upgrade head
```

### Bước 4: Update `last_activity_at` khi user active

Trong `telegram_handlers.py`, 2 điểm cần update:

**Khi user gõ /done (cmd_done):**
```python
# Sau khi set checkin_pending = True
enrollment.last_activity_at = datetime.utcnow()
db.commit()
```

**Khi quiz hoàn thành (`_handle_quiz_answer`, khi `next_action == "end"`):**
```python
# Cần lấy enrollment và update
from app.models import UserCourse
enrollment = db.query(UserCourse).filter(
    UserCourse.user_id == user.user_id,
    UserCourse.status == "IN_PROGRESS",
).first()
if enrollment:
    enrollment.last_activity_at = datetime.utcnow()
    db.commit()
```

### Bước 5: Tạo helper `build_reengagement_message()`

Trong `telegram_handlers.py` hoặc `message_formatter.py`:

```python
def build_reengagement_message(days_inactive: int, course_name: str, deadline=None) -> str | None:
    """Trả về message text hoặc None nếu không cần nhắc."""
    if days_inactive == 1:
        return (
            "👋 Hôm qua bạn bận à?\n\n"
            f"Khoá <b>{course_name}</b> đang chờ bạn 📚\n"
            "Gõ /today để tiếp tục!"
        )
    elif days_inactive == 3:
        context = ""
        if deadline:
            from datetime import date
            days_left = (deadline - date.today()).days
            context = f"\n\n⏰ Còn <b>{days_left} ngày</b> đến deadline của bạn."
        return (
            f"📚 Bạn chưa học <b>{days_inactive} ngày</b> rồi!\n"
            f"Khoá: <b>{course_name}</b>{context}\n\n"
            "Gõ /today để học tiếp nhé! 💪"
        )
    elif days_inactive == 5:
        return (
            f"🤔 Bạn đã dừng học <b>{days_inactive} ngày</b>.\n\n"
            "Bạn có muốn tiếp tục không?\n"
            "• Gõ /today để học tiếp\n"
            "• Gõ /start nếu muốn đổi khoá học\n"
            "• Im lặng → mình sẽ không nhắc nữa cho đến khi bạn quay lại"
        )
    return None  # Không nhắc
```

### Bước 6: Thêm daily re-engagement job vào `bot_polling.py`

```python
async def send_reengagement_messages(bot: Bot) -> None:
    """Daily job: nhắc users bỏ học theo thang +1/+3/+5 ngày."""
    from datetime import datetime, date
    from app.database import SessionLocal
    from app.models import User, UserCourse, Course

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        active_enrollments = (
            db.query(UserCourse, User, Course)
            .join(User, User.user_id == UserCourse.user_id)
            .join(Course, Course.course_id == UserCourse.course_id)
            .filter(UserCourse.status == "IN_PROGRESS")
            .all()
        )

        for enrollment, user, course in active_enrollments:
            if not enrollment.last_activity_at:
                continue

            days_inactive = (now - enrollment.last_activity_at).days
            if days_inactive not in (1, 3, 5):
                continue

            deadline = enrollment.deadline if hasattr(enrollment, "deadline") else None
            msg = build_reengagement_message(days_inactive, course.name, deadline)
            if not msg:
                continue

            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=msg,
                    parse_mode="HTML",
                )
                logger.info(f"Sent re-engagement (+{days_inactive}d) to user {user.user_id}")
            except Exception as e:
                logger.warning(f"Failed re-engagement message to {user.telegram_id}: {e}")
    finally:
        db.close()
```

Thêm vào scheduler trong `main()`:

```python
scheduler.add_job(
    send_reengagement_messages,
    trigger="cron",
    hour="9",   # Gửi lúc 9 giờ sáng
    minute="0",
    args=[bot],
)
```

### Bước 7: Kiểm tra `UserCourse` có `deadline` field không

Nếu `UserCourse` không có `deadline` → deadline lưu ở đâu? Kiểm tra `onboarding_state.deadline` — sau onboarding bị xóa. Cần copy `deadline` vào `user_courses` table tương tự như `reminder_time` → hoặc bỏ qua deadline trong re-engagement message ở MVP.

### Bước 8: Chạy tests

```bash
cd backend && python -m pytest tests/test_reengagement.py -v
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `user_courses` có `last_activity_at`
- [ ] `/done` và quiz complete update `last_activity_at`
- [ ] Daily 9h sáng: nhắc đúng theo ngày bỏ học (1, 3, 5)
- [ ] Không nhắc nếu inactive > 5 ngày hoặc đang active
- [ ] Tests pass

## Lưu ý
`last_activity_at` ban đầu sẽ là NULL cho users cũ. Coi NULL là "chưa active" → không nhắc. Chỉ bắt đầu track từ khi có migration.
