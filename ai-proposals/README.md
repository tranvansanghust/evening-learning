# Cleanup, Refactor & Feature Tasks

Trước khi làm bất kỳ task nào, đọc `docs/tech/codebase-health.md` để hiểu trạng thái hiện tại.

## Trạng thái

| Task | Mô tả | Trạng thái |
|---|---|---|
| [01](task-01-remove-dead-code.md) | Xóa ~700 dòng dead code | ✅ Done |
| [02](task-02-fix-today-lesson-tracking.md) | Fix `/today` luôn trả lesson đầu | ✅ Done |
| [03](task-03-implement-progress-review.md) | Implement `/progress` và `/review` thật | ✅ Done |
| [04](task-04-fix-checkin-state.md) | Tách checkin state ra khỏi OnboardingState | ✅ Done |
| [05](task-05-daily-reminder-scheduler.md) | Daily reminder scheduler + fix reminder_time | ✅ Done |
| [06](task-06-spaced-repetition.md) | Spaced repetition 3/7/14/30 ngày | ✅ Done |
| [07](task-07-reengagement-flow.md) | Re-engagement +1/+3/+5 ngày bỏ học | ✅ Done |
| [08](task-08-inline-buttons.md) | Inline keyboard buttons onboarding Q1/Q2 | ✅ Done |
| [09](task-09-quiz-summary-format.md) | Quiz summary format ✅/⚠️ | ✅ Done |
| [10](task-10-review-topic-parsing.md) | `/review [topic]` filter theo chủ đề | ✅ Done |
| [11](task-11-course-completion.md) | Course completion PASS + gợi ý khóa tiếp | ✅ Done |

## Tasks còn lại

### Nhóm C — LLM-powered Onboarding (task-12 trước, task-13 sau)

| Task | File | Mô tả | Trạng thái |
|---|---|---|---|
| [12](task-12-llm-assessment-questions.md) | `llm_assessment.py`, `onboarding_state.py`, `telegram_handlers.py` | LLM gen câu hỏi phù hợp course_topic | ✅ Done |
| [13](task-13-llm-level-assessment.md) | `llm_service.py`, `telegram_handlers.py`, `onboarding_service.py` | LLM đánh giá trình độ từ free-text answers | 🔲 Todo |

**Thứ tự:** task-12 done, task-13 tiếp theo.

### Nhóm D — Frontend Web Lesson Viewer (sequential, 14→15→16→17)

| Task | File | Mô tả | Rủi ro |
|---|---|---|---|
| [14](task-14-lesson-content-generation.md) | `llm_content_generator.py`, `models/lesson.py` | LLM gen nội dung bài học Markdown + cache DB | Thấp |
| [15](task-15-lesson-content-api.md) | `routers/lesson_content.py`, `main.py` | FastAPI endpoint serve lesson content + CORS | Thấp |
| [16](task-16-frontend-lesson-viewer.md) | `frontend/` (Vite + React) | Web app render Markdown, mobile-friendly | Thấp |
| [17](task-17-telegram-lesson-link.md) | `telegram_handlers.py` | Bot gửi link bài học sau onboarding và /today | Thấp |

**Thứ tự bắt buộc:** 14 → 15 → 16 → 17 (mỗi task phụ thuộc task trước).

## Thứ tự đề xuất

1. ~~**Nhóm A** (08–11)~~ ✅ Done
2. ~~**Nhóm B** (05–07)~~ ✅ Done
3. ~~**Task 12**~~ ✅ Done → **Task 13** — LLM level assessment
4. **Nhóm D** (14→15→16→17) — Frontend web lesson viewer

## Quy tắc chung cho mọi agent

1. **Đọc** `docs/tech/codebase-health.md` trước
2. **Đọc lại** file proposal ngay trước khi code (user có thể đã chỉnh)
3. **Viết test trước** — test phải fail trước khi implement
4. **Chạy toàn bộ tests** sau khi implement: `cd backend && python -m pytest tests/ -v`
5. **Không vượt 300 dòng** mỗi file — tách nếu cần
6. **Không import** `HandlerService` hoặc `TelegramService` (đã xóa)
