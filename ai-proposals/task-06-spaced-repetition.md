# Task 06: Spaced Repetition Quiz Scheduling

## Mục tiêu
Sau khi user làm quiz xong, tự động lên lịch hỏi lại vào ngày 3, 7, 14, 30 sau đó. Bot nhắc và start quiz review khi đến hạn.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước. **Phụ thuộc task-05** — cần APScheduler đã có sẵn.

## Files cần thay đổi

- `backend/app/models/quiz_summary.py` — thêm `next_review_at`, `review_count`
- `backend/alembic/versions/` — migration mới
- `backend/app/services/quiz_service.py` — set `next_review_at` khi quiz complete
- `backend/app/bot_polling.py` — thêm job check spaced repetition

## Spaced Repetition Intervals

```
review_count = 0 (quiz gốc) → next_review_at = completed_at + 3 ngày
review_count = 1            → next_review_at = completed_at + 7 ngày
review_count = 2            → next_review_at = completed_at + 14 ngày
review_count >= 3           → next_review_at = completed_at + 30 ngày
```

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Tạo `backend/tests/test_spaced_repetition.py`:

```python
# Test: quiz complete → quiz_summary.next_review_at = now + 3 ngày
# Test: review_count=1 → interval = 7 ngày
# Test: review_count=2 → interval = 14 ngày
# Test: review_count=3 → interval = 30 ngày
# Test: get_due_reviews() trả đúng summaries cần review hôm nay
```

### Bước 2: Thêm columns vào `QuizSummary` model

```python
# app/models/quiz_summary.py
from sqlalchemy import Integer, DateTime

next_review_at = Column(DateTime, nullable=True)
review_count = Column(Integer, default=0, nullable=False, server_default="0")
```

### Bước 3: Tạo Alembic migration

```bash
cd backend
source eveninig-learning-venv/bin/activate
alembic revision --autogenerate -m "add_spaced_repetition_to_quiz_summary"
alembic upgrade head
```

### Bước 4: Sửa `quiz_service.py` — set `next_review_at` khi tạo summary

Trong `get_or_generate_summary()`, sau khi tạo `QuizSummary`:

```python
from datetime import datetime, timedelta

def _next_review_interval(review_count: int) -> int:
    """Trả số ngày cho interval tiếp theo."""
    intervals = {0: 3, 1: 7, 2: 14}
    return intervals.get(review_count, 30)

# Sau khi tạo quiz_summary:
quiz_summary.next_review_at = datetime.utcnow() + timedelta(
    days=_next_review_interval(0)
)
quiz_summary.review_count = 0
```

Trong `submit_answer()`, khi `action == END` và summary được tạo inline, cũng set `next_review_at`.

### Bước 5: Thêm helper `get_due_reviews()` vào `ProgressService`

```python
def get_due_reviews(self, db_session: Session):
    """Lấy danh sách (user, quiz_summary) cần review hôm nay."""
    from datetime import datetime
    from app.models import QuizSummary, QuizSession, User

    now = datetime.utcnow()
    due = (
        db_session.query(QuizSummary, User)
        .join(QuizSession, QuizSession.session_id == QuizSummary.session_id)
        .join(User, User.user_id == QuizSession.user_id)
        .filter(QuizSummary.next_review_at <= now)
        .all()
    )
    return due
```

### Bước 6: Thêm scheduler job vào `bot_polling.py`

```python
async def send_spaced_repetition_reminders(bot: Bot) -> None:
    """Nhắc users cần review quiz hôm nay."""
    from app.database import SessionLocal
    from app.services.progress_service import ProgressService

    db = SessionLocal()
    try:
        progress_service = ProgressService(db)
        due_reviews = progress_service.get_due_reviews(db_session=db)

        for summary, user in due_reviews:
            lesson_name = summary.quiz_session.lesson.title if summary.quiz_session else "bài học"
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        f"🔁 Đến giờ ôn lại rồi!\n\n"
                        f"📖 Bài: <b>{lesson_name}</b>\n\n"
                        "Gõ /done để bắt đầu quiz ôn tập nhé! 💪"
                    ),
                    parse_mode="HTML",
                )
                # Set next_review_at = None để không gửi lại
                # (sẽ được set lại sau khi user làm quiz xong)
                summary.next_review_at = None
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to send review reminder to {user.telegram_id}: {e}")
    finally:
        db.close()
```

Thêm vào scheduler trong `main()`:

```python
scheduler.add_job(
    send_spaced_repetition_reminders,
    trigger="cron",
    hour="8",   # Gửi lúc 8 giờ sáng
    minute="0",
    args=[bot],
)
```

### Bước 7: Update `review_count` sau quiz review

Trong `quiz_service.py`, khi quiz session được tạo từ `/done` (checkin flow), detect nếu đây là "review session" và sau khi complete → tăng `review_count` + set `next_review_at` mới.

Cách detect: check xem lesson đã có `QuizSummary` trước đó chưa. Nếu có → đây là review.

```python
# Trong get_or_generate_summary(), sau khi commit:
# Tìm summary cũ của cùng lesson để update review_count
old_summary = db_session.query(QuizSummary).join(QuizSession).filter(
    QuizSession.lesson_id == quiz_session.lesson_id,
    QuizSession.user_id == quiz_session.user_id,
    QuizSummary.summary_id != quiz_summary.summary_id,
).order_by(QuizSummary.summary_id.desc()).first()

if old_summary:
    new_count = old_summary.review_count + 1
    old_summary.review_count = new_count
    # Set next_review_at trên summary cũ (tracking spaced repetition)
    old_summary.next_review_at = datetime.utcnow() + timedelta(
        days=_next_review_interval(new_count)
    )
```

### Bước 8: Chạy tests

```bash
cd backend && python -m pytest tests/test_spaced_repetition.py -v
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `quiz_summaries` có `next_review_at` và `review_count`
- [ ] Quiz complete → `next_review_at = +3 ngày`
- [ ] Scheduler 8h sáng check và gửi nhắc cho due reviews
- [ ] Sau mỗi review: interval tăng (3→7→14→30 ngày)
- [ ] Nhắc không gửi duplicate (set `next_review_at = None` sau khi nhắc)
- [ ] Tests pass

## Rủi ro
Trung bình. Logic update `review_count` phức tạp, cần test kỹ edge cases.
