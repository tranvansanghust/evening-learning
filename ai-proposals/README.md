# Cleanup, Refactor & Feature Tasks

Trước khi làm bất kỳ task nào, đọc `docs/tech/codebase-health.md` để hiểu trạng thái hiện tại.

## Trạng thái

| Task | Mô tả | Trạng thái |
|---|---|---|
| [01](task-01-remove-dead-code.md) | Xóa ~700 dòng dead code | ✅ Done |
| [02](task-02-fix-today-lesson-tracking.md) | Fix `/today` luôn trả lesson đầu | ✅ Done |
| [03](task-03-implement-progress-review.md) | Implement `/progress` và `/review` thật | ✅ Done |
| [04](task-04-fix-checkin-state.md) | Tách checkin state ra khỏi OnboardingState | ✅ Done |

## Tasks còn lại

### Nhóm A — Độc lập, có thể spawn song song

| Task | File | Mô tả | Rủi ro |
|---|---|---|---|
| [08](task-08-inline-buttons.md) | `telegram_handlers.py` | Thêm ReplyKeyboardMarkup cho onboarding Q1/Q2 | Thấp |
| [09](task-09-quiz-summary-format.md) | `message_formatter.py`, `telegram_handlers.py` | Format quiz summary đẹp với ✅/⚠️ | Thấp |
| [10](task-10-review-topic-parsing.md) | `telegram_handlers.py` | `/review [topic]` filter theo chủ đề | Thấp |
| [11](task-11-course-completion.md) | `telegram_handlers.py`, `llm_service.py` | PASS flow — chúc mừng + gợi ý khóa tiếp | Thấp |

### Nhóm B — Cần scheduler (task-05 phải làm trước)

| Task | File | Mô tả | Rủi ro |
|---|---|---|---|
| [05](task-05-daily-reminder-scheduler.md) | `models/user.py`, `onboarding_service.py`, `bot_polling.py` | **Prerequisite** — fix reminder_time + APScheduler | Trung bình |
| [06](task-06-spaced-repetition.md) | `models/quiz_summary.py`, `quiz_service.py`, `bot_polling.py` | Spaced repetition 3/7/14/30 ngày | Trung bình |
| [07](task-07-reengagement-flow.md) | `models/user_course.py`, `bot_polling.py`, `telegram_handlers.py` | Re-engagement +1/+3/+5 ngày bỏ học | Trung bình |

## Thứ tự đề xuất

1. **Nhóm A** (08, 09, 10, 11) — làm song song, không phụ thuộc gì
2. **Task 05** — prerequisite cho nhóm B
3. **Task 06 + 07** — song song sau khi task 05 xong

## Quy tắc chung cho mọi agent

1. **Đọc** `docs/tech/codebase-health.md` trước
2. **Đọc lại** file proposal ngay trước khi code (user có thể đã chỉnh)
3. **Viết test trước** — test phải fail trước khi implement
4. **Chạy toàn bộ tests** sau khi implement: `cd backend && python -m pytest tests/ -v`
5. **Không vượt 300 dòng** mỗi file — tách nếu cần
6. **Không import** `HandlerService` hoặc `TelegramService` (đã xóa)
