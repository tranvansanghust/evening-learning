# Architecture
_Last updated: 2026-03-28_

## Summary

Evening Learning is a Python FastAPI backend following a layered service architecture. Telegram users interact via bot commands; the bot runs in aiogram polling mode (dev) or webhook mode (prod). All business logic lives in service classes; routers are thin HTTP adapters that delegate to services.

## Pattern Overview

**Overall:** Layered Architecture (Presentation → Service → Data)

**Key Characteristics:**
- Async-first: all route handlers and service methods use `async def`
- Services encapsulate all business logic; routers only handle HTTP/Telegram plumbing
- Database sessions injected via FastAPI `Depends(get_db)` or instantiated directly in Telegram handler functions
- LLM calls are centralized through `LLMService` — no direct OpenAI client usage elsewhere
- Two Telegram entry modes: webhook (prod, via `/webhook/telegram`) and polling (dev, via `app/bot_polling.py`)

## Layers

**Presentation — Routers & Telegram Handlers:**
- Purpose: Receive HTTP requests or Telegram updates; validate inputs; call services; return responses
- Location: `backend/app/routers/`
- Contains: FastAPI `APIRouter` instances, request/response Pydantic models (defined inline per router), Telegram command handlers
- Depends on: Services layer, `app.database.get_db`
- Used by: FastAPI app (`main.py`), aiogram Dispatcher (`bot_polling.py`)

**Service Layer:**
- Purpose: All business logic — onboarding flow, quiz orchestration, LLM interaction, progress tracking, message formatting
- Location: `backend/app/services/`
- Contains: Class-based services with `async def` or `staticmethod` methods
- Depends on: Models layer, `LLMService`, `app.config.settings`
- Used by: Routers, Telegram handlers

**Data / Models Layer:**
- Purpose: SQLAlchemy ORM models and database session management
- Location: `backend/app/models/`, `backend/app/database/`
- Contains: ORM model classes, relationship definitions, `SessionLocal`, `Base`, `get_db` generator
- Depends on: `app.config.settings` (for DB URL)
- Used by: Services, routers

**Schemas Layer:**
- Purpose: Pydantic schemas for API input/output validation (shared across routers)
- Location: `backend/app/schemas/`
- Contains: `UserProgress`, `QuizSummaryPreview`, `ConceptDetail`
- Used by: Routers and services that return structured data

## Key Components

**`app/main.py`:**
- FastAPI app initialization
- CORS middleware configuration
- Router registration via `include_routers()`
- Startup/shutdown lifecycle hooks

**`app/services/onboarding_service.py` — `OnboardingService`:**
- Multi-step onboarding state machine: `start → course_input → q1 → q2 → deadline → hours_per_day → reminder_time → completed`
- Creates users, courses, `OnboardingState` records
- Detects Udemy URLs vs plain topic names
- Generates curriculum (lessons and concepts) using LLM

**`app/services/quiz_service.py` — `QuizService`:**
- Orchestrates full quiz lifecycle: session creation, question generation, answer evaluation, summary generation
- Maintains conversation history for multi-turn LLM interactions
- Decides quiz action: `CONTINUE`, `FOLLOWUP`, or `END`
- Takes `LLMService` as constructor dependency

**`app/services/llm_service.py` — `LLMService`:**
- Single gateway for all AI interactions (OpenAI-compatible API)
- Returns typed Pydantic models: `AnswerEvaluation`, `ActionType`
- Uses `LLMPrompts` for prompt templates
- Handles fast model (`gpt-4o-mini`) vs smart model (`gpt-4o`) selection

**`app/services/telegram_service.py` — `TelegramService`:**
- Wraps aiogram `Bot` for sending messages and inline keyboards
- Parses raw Telegram update dicts into `ParsedUpdate` dataclass

**`app/services/handler_service.py` — `HandlerService`:**
- Stateless formatting service (all `@staticmethod`)
- Converts backend models/schemas into Telegram-friendly HTML messages
- Builds progress bars, formats quiz questions, evaluations, and summaries

**`app/services/progress_service.py` — `ProgressService`:**
- Stateless (`@staticmethod` methods)
- Queries DB to compute lesson/concept completion metrics
- Returns `UserProgress`, `QuizSummaryPreview`, and detail schemas

## Data Flow

**Telegram Polling Flow (dev):**

1. `app/bot_polling.py` — aiogram `Dispatcher` starts long-polling
2. `app/routers/telegram_handlers.py` — aiogram `Router` matches `/command` → handler function
3. Handler instantiates `SessionLocal()`, creates service instances, calls service methods
4. Service calls LLM via `LLMService` if needed; reads/writes DB via `Session`
5. Handler calls `message.answer(...)` directly to respond to user

**Webhook Flow (prod):**

1. Telegram sends POST to `POST /webhook/telegram` (`app/routers/telegram.py`)
2. Router parses JSON into `ParsedUpdate` via `TelegramService.parse_update()`
3. Returns 200 immediately; routing to handlers is partially stubbed (TODO in code)

**REST API Flow:**

1. External caller or Telegram handler sends HTTP request to `/api/onboard/*`, `/api/learn/*`, `/api/quiz/*`, `/api/progress/*`
2. Router validates request using inline Pydantic models
3. Router calls appropriate service method with `db` session from `Depends(get_db)`
4. Service executes business logic, reads/writes ORM models
5. Router returns JSON response

**LLM Interaction Flow:**

1. `QuizService` or `OnboardingService` calls `LLMService` method
2. `LLMService` retrieves prompt template from `LLMPrompts`
3. Sends request to OpenAI-compatible endpoint configured via `settings.llm_base_url`
4. Parses structured JSON response into typed Pydantic model
5. Returns result to calling service

## Data Model Relationships

```
User (1) ──── (many) UserCourse ──── (many) Course
User (1) ──── (1) OnboardingState
User (1) ──── (many) QuizSession
Course (1) ──── (many) Lesson
Lesson (1) ──── (many) Concept
QuizSession (1) ──── (many) QuizAnswer
QuizSession (1) ──── (1) QuizSummary
```

**Key fields:**
- `User.level` (0–3): beginner to expert, set during onboarding assessment
- `OnboardingState.current_step`: state machine position during onboarding
- `QuizSession` stores full conversation history for multi-turn LLM context
- `QuizSummary.concepts_mastered` / `concepts_weak`: JSON arrays tracking knowledge state

## Entry Points

**FastAPI Server:**
- Location: `backend/app/main.py`
- Run: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Registers: onboarding, learning, quiz, progress, telegram routers

**Telegram Polling (dev):**
- Location: `backend/app/bot_polling.py`
- Run: `python -m app.bot_polling`
- Registers: `telegram_handlers.router` with aiogram Dispatcher

**Webhook Receiver (prod):**
- Location: `backend/app/routers/telegram.py`
- Endpoint: `POST /webhook/telegram`
- Note: Update routing from webhook to handlers is currently stubbed with a TODO

## Error Handling

**Strategy:** Defensive with 200-OK for Telegram; HTTP exceptions for REST

**Patterns:**
- Telegram webhook always returns 200 to prevent Telegram retries, even on errors
- REST routers raise `HTTPException` with appropriate status codes
- Services raise `ValueError` for business logic violations (e.g., duplicate user)
- LLM errors (rate limit, timeout, API error) are caught and re-raised with logging
- DB sessions are closed in `finally` blocks in Telegram handlers; in REST endpoints via `Depends(get_db)` generator

## Cross-Cutting Concerns

**Logging:** Python standard `logging` module; `logger = logging.getLogger(__name__)` in each module; level set to INFO in polling mode

**Configuration:** `app/config.py` — single `Settings` class using `pydantic_settings.BaseSettings`, loaded from `.env` file; global singleton `settings` imported everywhere

**Database Sessions:** Two patterns in use — `Depends(get_db)` for REST routers; direct `SessionLocal()` with manual `db.close()` in Telegram command handlers

**Authentication:** Telegram user identity established from `message.from_user.id` (Telegram ID); no separate auth layer

---

_Architecture analysis: 2026-03-28_
