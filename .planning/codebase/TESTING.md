# Testing Patterns
_Last updated: 2026-03-28_

## Summary
Tests use pytest with `pytest-asyncio` for async handler tests. The single test file covers state-aware Telegram message routing using `unittest.mock` — no real database or Telegram connection required. TDD is the mandated workflow: write a failing test first, then implement.

---

## Test Framework

**Runner:** pytest (no version pinned in `requirements.txt` — installed separately in venv)

**Async support:** `pytest-asyncio` — all async tests marked `@pytest.mark.asyncio`

**Mocking:** `unittest.mock` from standard library — `MagicMock`, `AsyncMock`, `patch`

**Run Commands:**
```bash
cd backend
source eveninig-learning-venv/bin/activate

python -m pytest tests/ -v              # Run all tests with verbose output
python -m pytest tests/test_message_routing.py -v   # Run specific test file
```

No coverage tooling is currently configured (no `pytest.ini`, `setup.cfg`, or `pyproject.toml`).

---

## Test File Organization

**Location:** `backend/tests/`

**Files:**
- `backend/tests/__init__.py` — empty, makes tests a package
- `backend/tests/test_message_routing.py` — all current tests (314 lines)

**Naming convention:**
- Test files: `test_{feature_area}.py`
- Test classes: `Test{Scenario}` e.g. `TestRoutingNewUser`, `TestRoutingOnboarding`, `TestRoutingQuiz`
- Test methods: `test_{what_is_being_tested}` e.g. `test_new_user_text_prompted_to_start`, `test_q1_step_never_answer`

---

## Test Structure

Tests are organized into classes by user state scenario. Each class tests one "mode" the user can be in:

```python
class TestRoutingNewUser:
    """User mới, chưa có OnboardingState."""

    @pytest.mark.asyncio
    async def test_new_user_text_prompted_to_start(self):
        ...

class TestRoutingOnboarding:
    """User đang trong các bước onboarding."""

    @pytest.mark.asyncio
    async def test_course_input_step_saves_course(self):
        ...

class TestRoutingQuiz:
    """User đang trong active quiz session."""

    @pytest.mark.asyncio
    async def test_text_during_quiz_routes_to_quiz_answer(self):
        ...
```

---

## Mocking Pattern

**Framework:** `unittest.mock` — `patch` as context manager.

The standard pattern patches `SessionLocal` (DB) and service classes at the point of import (in `app.routers.telegram_handlers`):

```python
with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
     patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls:

    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db

    mock_ob = MagicMock()
    mock_ob_cls.return_value = mock_ob
    mock_ob.get_onboarding_state.return_value = make_onboarding_state("q1")

    await handle_text(msg)
```

For quiz tests, `QuizService` is also patched:
```python
with patch("app.routers.telegram_handlers.SessionLocal") as mock_db_cls, \
     patch("app.routers.telegram_handlers.OnboardingService") as mock_ob_cls, \
     patch("app.routers.telegram_handlers.QuizService") as mock_quiz_cls:
```

**What is mocked:**
- `SessionLocal` — no real DB connection
- `OnboardingService` — no real state queries
- `QuizService` — no real LLM calls
- `msg.answer` — `AsyncMock()` to capture Telegram reply text

**What is NOT mocked:**
- The handler function itself (`handle_text`) — it is imported and called directly
- Assertions on message text — real string content is checked

---

## Fixtures and Helpers

No pytest fixtures (`@pytest.fixture`) are used. Instead, three plain helper functions at module top create fake objects:

```python
def make_message(text: str, telegram_id: str = "111") -> MagicMock:
    """Tạo fake aiogram Message với from_user.id và text."""
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = int(telegram_id)
    msg.from_user.username = f"user_{telegram_id}"
    msg.answer = AsyncMock()
    return msg

def make_onboarding_state(step: str) -> MagicMock:
    """Tạo fake OnboardingState với current_step."""
    state = MagicMock()
    state.current_step = step
    return state

def make_quiz_session(session_id: int = 1) -> MagicMock:
    """Tạo fake QuizSession đang active."""
    session = MagicMock()
    session.session_id = session_id
    session.status = "active"
    return session
```

These helpers are defined once at the top of `backend/tests/test_message_routing.py` and reused in all test methods.

---

## Assertions Pattern

**Two assertion styles are used:**

1. **Service call assertions** — verify the right service method was called with the right kwargs:
```python
mock_ob.update_onboarding_state.assert_called()
call_kwargs = mock_ob.update_onboarding_state.call_args[1]
assert call_kwargs.get("q1_answer") == "never"
assert call_kwargs.get("current_step") == "q2"
```

2. **Reply text assertions** — verify the Telegram reply contains expected content:
```python
reply = msg.answer.call_args[0][0]
assert "/start" in reply
assert "html" in reply.lower() or "css" in reply.lower()
```

Text assertions use `.lower()` for case-insensitive matching and `or` for multiple valid phrasings.

---

## Test Categories

**Unit Tests (only category present):**
- Scope: individual handler function (`handle_text`) in isolation
- Location: `backend/tests/test_message_routing.py`
- All dependencies mocked

**Integration Tests:** Not present. No tests hit a real database or Telegram API.

**E2E Tests:** Not present.

---

## Coverage

No coverage configuration or enforcement exists. No `--cov` flags in any run command.

**Covered areas:**
- `app.routers.telegram_handlers.handle_text` — state routing for onboarding steps and quiz mode
- `OnboardingService.update_onboarding_state` call verification per step
- `QuizService.submit_answer` call and response handling

**Not covered (gaps):**
- `app.services.onboarding_service` — no unit tests for `create_user`, `assess_level`, `complete_onboarding`
- `app.services.quiz_service` — no unit tests for `start_quiz`, `submit_answer`, `get_or_generate_summary`
- `app.services.llm_service` — no unit tests for any LLM method
- `app.services.handler_service` — formatting methods untested
- `app.routers.*` REST endpoints — no HTTP-level tests (no `TestClient`)
- `app.models.*` — no model-level tests

---

## TDD Workflow (project-mandated)

Per `CLAUDE.md`, the required workflow for every feature or bugfix:

1. Write test in `backend/tests/` — test must fail first
2. Run test to confirm it fails for the right reason: `python -m pytest tests/ -v`
3. Implement code until test passes
4. Run all tests to confirm nothing is broken: `python -m pytest tests/ -v`

**No new code should be written without a corresponding test.**
