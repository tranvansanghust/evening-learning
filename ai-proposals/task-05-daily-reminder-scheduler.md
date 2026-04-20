# Task 05: Fix reminder_time Storage + Daily Reminder Scheduler

## Mục tiêu
`reminder_time` hiện lưu trong `OnboardingState` — bị xóa sau onboarding. Bot không bao giờ gửi được reminder. Cần: (1) lưu vào `users` table, (2) thêm scheduler để gửi nhắc đúng giờ.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước. Task này là prerequisite cho task-06 và task-07.

## Files cần thay đổi

- `backend/app/models/user.py` — thêm `reminder_time` column
- `backend/alembic/versions/` — tạo migration mới
- `backend/app/services/onboarding_service.py` — sửa `complete_onboarding()`
- `backend/app/bot_polling.py` — thêm APScheduler
- `backend/requirements.txt` — thêm `APScheduler`

## Kế hoạch thực hiện

### Bước 1: Thêm dependency

Thêm vào `backend/requirements.txt`:
```
apscheduler==3.10.4
```

### Bước 2: Viết test trước

Tạo `backend/tests/test_reminder_scheduler.py`:

```python
# Test: complete_onboarding() copy reminder_time vào user.reminder_time
# Test: user với reminder_time="20:00", giờ hiện tại 20:00 → should_send_reminder = True
# Test: user với reminder_time="20:00", giờ hiện tại 21:00 → should_send_reminder = False
# Test: user với reminder_time=None → should_send_reminder = False
# Test: user với UserCourse.status != IN_PROGRESS → should_send_reminder = False
```

### Bước 3: Thêm column vào User model

```python
# app/models/user.py
reminder_time = Column(String(10), nullable=True)  # format "HH:MM", e.g. "20:00"
```

### Bước 4: Tạo Alembic migration

```bash
cd backend
source eveninig-learning-venv/bin/activate
alembic revision --autogenerate -m "add_reminder_time_to_users"
alembic upgrade head
```

### Bước 5: Sửa `complete_onboarding()` trong `onboarding_service.py`

Sau khi assess level, thêm:

```python
# Copy reminder_time từ state sang user
if state.reminder_time and user:
    user.reminder_time = state.reminder_time
```

### Bước 6: Thêm scheduler vào `bot_polling.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

async def send_daily_reminders(bot: Bot) -> None:
    """Gửi reminder cho users có giờ nhắc khớp với giờ hiện tại."""
    from app.database import SessionLocal
    from app.models import User, UserCourse

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    db = SessionLocal()
    try:
        # Lấy users có reminder_time khớp + đang học
        users_to_remind = (
            db.query(User)
            .join(UserCourse, UserCourse.user_id == User.user_id)
            .filter(
                User.reminder_time == current_time,
                UserCourse.status == "IN_PROGRESS",
            )
            .all()
        )

        for user in users_to_remind:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "🔔 Đến giờ học rồi!\n\n"
                        "Gõ /today để xem bài học hôm nay 📚"
                    )
                )
                logger.info(f"Sent reminder to user {user.user_id}")
            except Exception as e:
                logger.warning(f"Failed to send reminder to {user.telegram_id}: {e}")
    finally:
        db.close()


async def main() -> None:
    # ... existing bot init code ...

    # Khởi động scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_daily_reminders,
        trigger="cron",
        minute="*",  # Chạy mỗi phút để check
        args=[bot],
    )
    scheduler.start()
    logger.info("✅ Reminder scheduler started")

    # ... existing polling code ...
```

**Lưu ý quan trọng:** Scheduler phải start TRƯỚC `dp.start_polling()`. Và cần đảm bảo scheduler shutdown gracefully khi bot dừng:

```python
finally:
    scheduler.shutdown()
    await bot.session.close()
```

### Bước 7: Chạy tests

```bash
cd backend && python -m pytest tests/test_reminder_scheduler.py -v
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `users` table có cột `reminder_time`
- [ ] `complete_onboarding()` copy `reminder_time` vào user
- [ ] `bot_polling.py` có scheduler chạy mỗi phút
- [ ] Đúng giờ → user nhận Telegram message
- [ ] Scheduler shutdown sạch khi bot dừng
- [ ] Tests pass

## Rủi ro
- Trung bình. Cần migration DB.
- Scheduler chạy mỗi phút: nếu server chậm > 1 phút, có thể gửi duplicate. Chấp nhận ở MVP.
- `reminder_time` format "HH:MM" — cần đảm bảo onboarding parse đúng format này.
