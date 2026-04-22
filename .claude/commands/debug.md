# Debug: Evening Learning Project

## Stack
- FastAPI backend · SQLAlchemy ORM · MySQL
- aiogram 3.x Telegram bot (polling via `bot_polling.py`)
- LLM: OpenAI-compatible API (`llm_service.py`)
- Tests: pytest (mock-based, no real DB)

## Khi có bug, điều tra theo thứ tự này:

### 1. Xác định nguồn gốc
- **Telegram bot lỗi** → đọc log `telegram_handlers.py`, tìm `ERROR` hoặc exception
- **LLM call lỗi** → kiểm tra `llm_service.py`, xem API key, model name, response format
- **DB lỗi** → kiểm tra SQLAlchemy query, migration đã chạy chưa (`alembic upgrade head`)
- **Logic lỗi** → chạy test liên quan: `python -m pytest tests/test_<feature>.py -v`

### 2. Entry points chính
| Command | Handler | Service |
|---------|---------|---------|
| `/start` | `cmd_start` | `OnboardingService` |
| `/today` | `cmd_today` | `get_current_lesson()` |
| `/done` | `cmd_done` | sets `user.checkin_pending` |
| `/progress` | `cmd_progress` | `ProgressService.get_user_progress` |
| `/review` | `cmd_review` | `ProgressService.get_quiz_summaries` |
| text input | `handle_text` | routing: onboarding → checkin → quiz → fallback |

### 3. State machine — `handle_text` routing order
1. `ob_state != None` AND `step != "checkin"` → onboarding flow
2. `user.checkin_pending == True` → `_handle_checkin`
3. active `QuizSession` exists → `_handle_quiz_answer`
4. fallback → "gõ /start"

### 4. Checklist debug nhanh
```bash
# Chạy bot local
cd backend && source eveninig-learning-venv/bin/activate
python -m app.bot_polling

# Chạy tests
python -m pytest tests/ -v

# Kiểm tra DB migration
alembic current
alembic upgrade head

# Import check
python -c "from app.routers.telegram_handlers import router; from app.main import app; print('OK')"
```

### 5. Files quan trọng nhất
- `backend/app/routers/telegram_handlers.py` — tất cả Telegram handlers
- `backend/app/services/onboarding_service.py` — onboarding + state management
- `backend/app/services/quiz_service.py` — quiz flow + LLM evaluation
- `backend/app/services/llm_service.py` — LLM API calls
- `backend/app/models/user.py` — User model (có `checkin_pending`)

### 6. Common errors
| Error | Cause | Fix |
|-------|-------|-----|
| `API key cannot be empty` | `.env` thiếu `LLM_API_KEY` | Thêm vào `.env` |
| `Invalid API Key` | API key sai / hết hạn | Kiểm tra `LLM_API_KEY` trong `.env` |
| `checkin_pending` column missing | Migration chưa chạy | `alembic upgrade head` |
| `ModuleNotFoundError` | Import dead code bị xóa | Check imports trong file |

---

$ARGUMENTS
