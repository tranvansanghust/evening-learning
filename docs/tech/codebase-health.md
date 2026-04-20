# Codebase Health Map

Tài liệu này mô tả trạng thái thực tế của source code — đâu đang chạy, đâu là dead code, đâu bị gãy. Dùng để lập kế hoạch cleanup/refactor.

---

## Entry Points

| Entry point | Cách khởi động | Dùng cho |
|---|---|---|
| `app/bot_polling.py` | `python -m app.bot_polling` | Telegram bot (dev) |
| `app/main.py` | `uvicorn app.main:app` | FastAPI REST API |

**Quan trọng:** Bot polling và FastAPI là hai process riêng. Bot polling KHÔNG gọi FastAPI — nó gọi thẳng services và DB.

---

## Luồng thực tế của Telegram Bot

```
bot_polling.py
  └─ aiogram Dispatcher
       └─ handlers_router  ← từ telegram_handlers.py (dòng 1–474)
            ├─ cmd_start      /start
            ├─ cmd_today      /today
            ├─ cmd_done       /done
            ├─ cmd_progress   /progress   ← STUB
            ├─ cmd_review     /review     ← STUB
            ├─ cmd_resume     /resume     ← STUB
            ├─ cmd_pause      /pause      ← STUB
            ├─ cmd_help       /help
            └─ handle_text    (mọi text không phải command)
                 ├─ _handle_onboarding_step  ← khi ob_state != None
                 │    step: course_input → q1 → q2 → deadline → hours → reminder
                 │    bước cuối: OnboardingService.complete_onboarding()
                 ├─ _handle_checkin          ← khi step == "checkin"
                 │    → QuizService.start_quiz() → gửi câu hỏi đầu
                 └─ _handle_quiz_answer      ← khi có QuizSession active
                      → QuizService.submit_answer() → feedback + câu tiếp / summary
```

---

## Dead Code (không được gọi từ đâu)

### `TelegramHandlers` class — `telegram_handlers.py:476–1010`

Class cũ, ~535 dòng, không được import ở bất kỳ file nào. Chứa các methods placeholder với `user_id = 1` hardcode.

**An toàn để xóa toàn bộ.**

### `HandlerService` — `app/services/handler_service.py`

Chỉ được tham chiếu bởi `TelegramHandlers` (dead code ở trên). Không được dùng bởi hệ thống aiogram router thực.

**An toàn để xóa toàn bộ file.**

### `TelegramService` / `ParsedUpdate` — `app/services/telegram_service.py`

`ParsedUpdate` chỉ được import trong `TelegramHandlers` (dead). `TelegramService` chứa send_message wrapper nhưng không được gọi trong aiogram router.

**An toàn để xóa toàn bộ file.**

---

## Các file đang hoạt động

| File | Vai trò | Trạng thái |
|---|---|---|
| `routers/telegram_handlers.py` (dòng 1–474) | Aiogram handlers + routing logic | Hoạt động, có bugs |
| `services/onboarding_service.py` | Tạo user, onboarding state machine, tạo course | Hoạt động |
| `services/quiz_service.py` | Quản lý quiz session, evaluate answers | Hoạt động |
| `services/llm_service.py` | Gọi LLM để gen câu hỏi, evaluate, summary | Hoạt động |
| `services/llm_prompts.py` | Prompt templates cho LLM | Hoạt động |
| `services/progress_service.py` | Tính progress, lấy quiz summaries | Hoạt động, chưa được gọi từ bot |
| `routers/onboarding.py` | REST API /api/onboard/* | Hoạt động, không dùng bởi bot |
| `routers/quiz.py` | REST API /api/quiz/* | Hoạt động, không dùng bởi bot |
| `routers/learning.py` | REST API /api/learn/* | Hoạt động, không dùng bởi bot |
| `routers/progress.py` | REST API /api/progress/* | Hoạt động, không dùng bởi bot |
| `models/` | SQLAlchemy models | Hoạt động |
| `bot_polling.py` | Khởi động aiogram | Hoạt động |
| `main.py` | FastAPI app | Hoạt động |

---

## Bugs đã xác nhận

### Bug 1: `/today` luôn trả về lesson đầu tiên
- **File:** `telegram_handlers.py:118`
- **Code:** `.order_by(Lesson.sequence_number).first()`
- **Hậu quả:** User không bao giờ học được bài tiếp theo dù đã làm quiz xong
- **Fix cần:** Track "bài đang học hiện tại" — có thể dựa vào số QuizSession đã completed

### Bug 2: `/progress` không trả dữ liệu thật
- **File:** `telegram_handlers.py:198`
- **Code:** Chỉ gửi "📊 Đang tải tiến độ học tập của bạn..."
- **Hậu quả:** User không xem được progress
- **Fix cần:** Gọi `ProgressService.get_user_progress()` + format kết quả

### Bug 3: `/review` không trả dữ liệu thật
- **File:** `telegram_handlers.py:202`
- **Code:** Chỉ gửi "📖 Đang tải danh sách quiz đã làm..."
- **Hậu quả:** User không xem được lịch sử quiz
- **Fix cần:** Gọi `ProgressService.get_quiz_summaries()` + format kết quả

### Bug 4: OnboardingState bị tái dụng cho "checkin"
- **File:** `telegram_handlers.py:179` và `_handle_checkin:419`
- **Mô tả:** Sau khi onboarding xong, state bị xóa. Khi user gõ `/done`, code tạo lại `OnboardingState` với `step="checkin"` — dùng bảng onboarding để lưu trạng thái quiz checkin.
- **Hậu quả:** Logic không rõ ràng, nếu user chưa hoàn thành onboarding mà gõ `/done` sẽ bị lẫn lộn state.

---

## Models & Database

```
users
  ├─ user_id (PK)
  ├─ telegram_id (UNIQUE)
  ├─ username
  └─ level (0-3)

onboarding_states
  ├─ onboarding_id (PK)
  ├─ user_id (FK → users)
  ├─ current_step  ← "course_input"|"q1"|"q2"|"deadline"|"hours"|"reminder"|"checkin"
  ├─ course_topic, q1_answer, q2_answer
  ├─ deadline, hours_per_day, reminder_time
  └─ expires_at

courses
  ├─ course_id (PK)
  ├─ name, description, source (udemy/internal)
  └─ total_lessons

user_courses
  ├─ user_course_id (PK)
  ├─ user_id (FK), course_id (FK)
  └─ status (IN_PROGRESS/PASS/FAIL)

lessons
  ├─ lesson_id (PK)
  ├─ course_id (FK)
  ├─ sequence_number, title, description
  └─ estimated_duration_minutes

concepts
  ├─ concept_id (PK)
  ├─ lesson_id (FK)
  └─ name, description

quiz_sessions
  ├─ session_id (PK)
  ├─ user_id (FK), lesson_id (FK)
  ├─ status (active/completed)
  ├─ messages (JSON — conversation history)
  └─ started_at, completed_at

quiz_answers
  ├─ answer_id (PK)
  ├─ session_id (FK), concept_id (FK nullable)
  ├─ question, user_answer
  ├─ is_correct, engagement_level
  └─ created_at

quiz_summaries
  ├─ summary_id (PK)
  ├─ session_id (FK)
  ├─ concepts_mastered (JSON array of strings)
  └─ concepts_weak (JSON array of {concept, user_answer, correct_explanation})
```

---

## Config & Environment

Tất cả config qua `app/config.py` → đọc từ `.env`:

```
DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
TELEGRAM_BOT_TOKEN
LLM_BASE_URL, LLM_API_KEY, LLM_FAST_MODEL, LLM_SMART_MODEL
```

Import: `from app.config import settings`

---

## Conventions quan trọng

- Tất cả service methods dùng `async def` — NGOẠI TRỪ `OnboardingService` và `QuizService` đang dùng `def` đồng bộ (gọi trực tiếp, không await)
- `QuizService.__init__(llm_service)` — không inject db, nhận `db_session` qua từng method call
- `OnboardingService.__init__(db)` — inject db trong constructor
- `ProgressService` tương tự OnboardingService — inject db
- DB session: `db = SessionLocal()` tạo thủ công, đóng trong `finally`
