# Bug: /review và /review_topic Không Hoạt Động

## Triệu chứng
- `/review_topic` → bot trả về welcome message (không nhận lệnh)
- `/review` → "❌ Có lỗi xảy ra. Vui lòng thử lại!"

---

## Root Causes

### Bug 1: ProgressService khởi tạo sai (gây crash)

**File:** `routers/telegram_handlers.py` — `cmd_review`

```python
# Sai — ProgressService chỉ có @staticmethod, không có __init__
progress_service = ProgressService(db)
summaries = progress_service.get_quiz_summaries(...)

# Đúng — gọi static method trực tiếp
summaries = ProgressService.get_quiz_summaries(...)
```

**Lỗi:** `TypeError: ProgressService() takes no arguments`

---

### Bug 2: JOIN sai qua user_course_id=None (kết quả rỗng)

**File:** `services/progress_service.py` — `get_quiz_summaries` và `get_review_by_topic`

```python
# Sai — user_course_id luôn là NULL (quiz_service.py set None)
.join(UserCourse, UserCourse.user_course_id == QuizSummary.user_course_id)
.filter(UserCourse.user_id == user_id)

# Đúng — join qua QuizSession.user_id (luôn được set đúng)
.join(QuizSession, QuizSession.session_id == QuizSummary.session_id)
.filter(QuizSession.user_id == user_id)
```

**Nguyên nhân sâu:** `quiz_service.py` tạo QuizSummary với `user_course_id=None` (TODO chưa implement).
Dù có fix Bug 1, kết quả vẫn rỗng vì inner join với NULL không trả về row nào.

---

### Bug 3: Không có lệnh /review_topic

Lệnh `/review_topic` không được định nghĩa trong handlers. Bot rơi vào unknown-message handler và trả về welcome message.

**Giải pháp dự kiến:** Đây là task-10 trong backlog — parse argument từ `/review [topic]` thay vì tạo lệnh riêng.

---

## Files đã sửa

- `routers/telegram_handlers.py`: bỏ `ProgressService(db)`, gọi static method trực tiếp
- `services/progress_service.py`: đổi JOIN từ `user_course_id` sang `QuizSession.user_id`
