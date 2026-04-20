# Cleanup & Refactor Tasks

Trước khi làm bất kỳ task nào, đọc `docs/tech/codebase-health.md` để hiểu trạng thái hiện tại.

## Thứ tự thực hiện

Các task 01, 02, 03 **độc lập** — có thể spawn agents làm song song.  
Task 04 **nên làm sau** task 01 (vì task 01 dọn import sạch trước).

| Task | File | Mô tả | Rủi ro | Ưu tiên |
|---|---|---|---|---|
| [01](task-01-remove-dead-code.md) | `telegram_handlers.py`, `handler_service.py`, `telegram_service.py` | Xóa ~700 dòng dead code | Thấp | Cao — làm trước |
| [02](task-02-fix-today-lesson-tracking.md) | `telegram_handlers.py` | Fix `/today` luôn trả lesson đầu | Thấp | Cao |
| [03](task-03-implement-progress-review.md) | `telegram_handlers.py` | Implement `/progress` và `/review` thật | Thấp | Cao |
| [04](task-04-fix-checkin-state.md) | `models/user.py`, migration, `telegram_handlers.py` | Tách checkin state ra khỏi OnboardingState | Trung bình | Trung bình |

## Quy tắc chung cho mọi agent

1. **Đọc** `docs/tech/codebase-health.md` trước
2. **Đọc lại** file proposal ngay trước khi code (user có thể đã chỉnh)
3. **Viết test trước** — test phải fail trước khi implement
4. **Chạy toàn bộ tests** sau khi implement: `cd backend && python -m pytest tests/ -v`
5. **Không vượt 300 dòng** mỗi file — tách nếu cần
6. **Không import** `HandlerService` hoặc `TelegramService` (dead code)
