# Coding Conventions
_Last updated: 2026-03-28_

## Summary
Python FastAPI backend using OOP-first design with async handlers. All service logic is in classes; routers delegate to services. Code style is consistent across the codebase with Google-style docstrings, `logging` for observability, and Pydantic for I/O validation.

---

## Naming Patterns

**Files:**
- `snake_case` for all Python files: `onboarding_service.py`, `handler_service.py`, `quiz_service.py`
- Models named after the entity: `user.py`, `quiz_session.py`, `onboarding_state.py`
- Routers named after domain: `onboarding.py`, `telegram_handlers.py`, `progress.py`

**Classes:**
- `PascalCase` always: `OnboardingService`, `QuizService`, `LLMService`, `HandlerService`
- Services end in `Service`: `OnboardingService`, `ProgressService`, `TelegramService`
- SQLAlchemy models are plain PascalCase nouns: `User`, `Course`, `Lesson`, `QuizSession`
- Pydantic schemas use descriptive PascalCase: `StartOnboardingRequest`, `UserProgress`, `QuizSummaryPreview`
- Enums use PascalCase: `EngagementLevel`, `ActionType`

**Functions and Methods:**
- `snake_case` always: `create_user`, `get_onboarding_state`, `submit_answer`
- Command handlers prefixed with `cmd_`: `cmd_start`, `cmd_done`, `cmd_today`
- Formatting helpers prefixed with `format_`: `format_progress_message`, `format_quiz_detail`
- Boolean-returning helpers prefixed with `get_` + noun: `get_onboarding_state`, `get_first_lesson`
- Private static helpers prefixed with `_`: `_build_progress_bar`

**Variables:**
- `snake_case` for local variables: `telegram_id`, `quiz_session`, `lesson_content`
- DB session always named `db` (in handlers) or `db_session` (in service method parameters)
- Logger always named `logger` at module level

**Constants (class attributes):**
- `UPPER_SNAKE_CASE`: `FAST_MODEL`, `SMART_MODEL`

---

## Class Design

**Services own all business logic.** Routers call services; services hold all state-mutation and query logic.

Services are instantiated with a `db: Session` injected at `__init__`:
```python
class OnboardingService:
    def __init__(self, db: Session):
        self.db = db
```

Exception: `LLMService` takes API credentials; `QuizService` takes an `LLMService` instance.

`HandlerService` uses only `@staticmethod` methods (no instance state needed) — it is a formatting utility class.

**Max file length is 300 lines** per project rules. Files currently approach this threshold (e.g., `onboarding_service.py` is ~609 lines — a known concern).

---

## Async/Sync Patterns

**Router handlers are always `async def`:**
```python
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    ...
    await message.answer("...")
```

**Service methods are regular `def` (synchronous):**
```python
def create_user(self, telegram_id: str, username: Optional[str] = None) -> User:
    ...
```

**LLM calls in `LLMService` are synchronous** (OpenAI client is sync): `self.client.chat.completions.create(...)`.

Handlers open a `SessionLocal()` directly and close it in `finally`:
```python
db = SessionLocal()
try:
    ...
finally:
    db.close()
```

FastAPI REST endpoints use `Depends(get_db)` for session injection.

---

## Import Organization

Imports follow this order across all files:

1. Standard library (`logging`, `json`, `re`, `datetime`, `typing`)
2. Third-party packages (`fastapi`, `sqlalchemy`, `pydantic`, `aiogram`, `openai`)
3. Internal app modules (`from app.models import ...`, `from app.services import ...`, `from app.config import settings`)

No path aliases — all imports use full `app.*` package paths.

Local imports inside function bodies are used in some handlers to avoid circular imports:
```python
async def cmd_start(message: Message) -> None:
    from app.models import User  # deferred to avoid circular
```

---

## Error Handling

**Pattern: raise `ValueError` for validation errors, `Exception` for unexpected ones.**

Services raise typed exceptions with descriptive messages:
```python
raise ValueError(f"User with telegram_id {telegram_id} already exists")
raise ValueError(f"No onboarding state found for user {user_id}")
```

Handlers catch broadly at the boundary and send a user-friendly Telegram reply:
```python
try:
    ...
except Exception as e:
    logger.error(f"Error in cmd_start for telegram_id {telegram_id}: {e}", exc_info=True)
    await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại sau!")
finally:
    db.close()
```

In `QuizService` and `LLMService`, specific API error types are caught explicitly then re-raised:
```python
except RateLimitError as e:
    logger.error(f"Rate limit exceeded: {str(e)}")
    raise
except APIError as e:
    logger.error(f"API error: {str(e)}")
    raise
```

DB rollback on failure:
```python
except Exception as e:
    db_session.rollback()
    raise
```

---

## Logging

**Framework:** Python standard `logging` module.

**Initialization at module level (every file):**
```python
logger = logging.getLogger(__name__)
```

**Log levels used:**
- `logger.info(...)` — normal flow events: "Created user: 1", "Quiz session 3 started"
- `logger.warning(...)` — recoverable non-errors: "User already exists", "No mock curriculum found"
- `logger.error(f"...: {str(e)}")` — errors with context, often with `exc_info=True` in handlers

Log messages include entity IDs for traceability: `f"Created quiz session {session_id} for user {user_id}"`.

---

## Docstrings

All public classes and methods have full Google-style docstrings with:
- One-line summary
- Multi-line description
- `Args:` section with types and descriptions
- `Returns:` section with type and description
- `Raises:` section listing exception types
- `Example:` section with usage snippet

```python
def create_user(self, telegram_id: str, username: Optional[str] = None) -> User:
    """
    Create a new user in the system.

    Args:
        telegram_id: Unique Telegram user ID
        username: Optional user display name

    Returns:
        User: The created User object

    Raises:
        ValueError: If user with this telegram_id already exists

    Example:
        >>> user = service.create_user("123456789", "john_doe")
    """
```

Module-level docstrings describe purpose, contents, and usage.

---

## SQLAlchemy Model Conventions

- `__tablename__` is plural snake_case: `"users"`, `"quiz_sessions"`
- Primary key column named `{entity}_id`: `user_id`, `session_id`, `lesson_id`
- Timestamps: `created_at` with `server_default=func.now()`, `updated_at` with `onupdate=func.now()`
- `__repr__` defined on every model for debugging
- Relationships use `back_populates` (explicit), `cascade="all, delete-orphan"` where appropriate
- `lazy="select"` used explicitly on all relationships

---

## Pydantic Schema Conventions

- Schemas in `backend/app/schemas/`: `progress.py`
- Request/Response schemas defined inline in router files when endpoint-specific: `StartOnboardingRequest`, `CourseInputResponse`
- All fields use `Field(...)` with `description=` always present
- Validators for non-negative counts: `Field(..., ge=0)`
- `class Config: from_attributes = True` on response schemas that map from ORM models
- LLM response models (`AnswerEvaluation`, `QuizSummary`, etc.) defined in `backend/app/services/llm_service.py` and use `BaseModel`

---

## Configuration

Always import from `app.config`:
```python
from app.config import settings
```

Never hardcode credentials or env-specific values in logic files. `settings` is a global singleton from `pydantic_settings.BaseSettings`, loaded from `.env`.
