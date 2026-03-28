# External Integrations
_Last updated: 2026-03-28_

## Summary
The application integrates with three external services: Telegram Bot API (for user messaging), an OpenAI-compatible LLM API (for quiz generation and answer evaluation), and a MySQL database (for persistence). All credentials are injected via environment variables and accessed through the typed `Settings` class in `backend/app/config.py`.

## APIs & External Services

**LLM Provider (OpenAI-compatible):**
- Service: Any OpenAI-compatible API endpoint (default: OpenAI `https://api.openai.com/v1`)
  - SDK/Client: `openai` Python SDK v2.29.0 — `OpenAI(api_key=..., base_url=...)`
  - Auth: `LLM_API_KEY` env var
  - Base URL: `LLM_BASE_URL` env var (supports OpenAI, OpenRouter, local models, etc.)
  - Fast model: `LLM_FAST_MODEL` env var (default: `gpt-4o-mini`) — used for question generation and next-action decisions
  - Smart model: `LLM_SMART_MODEL` env var (default: `gpt-4o`) — used for answer evaluation, summaries, course suggestions
  - Implementation: `backend/app/services/llm_service.py` — `LLMService` class; all LLM calls MUST go through this class
  - Prompts: `backend/app/services/llm_prompts.py` — `LLMPrompts` class with static prompt template methods

**Telegram Bot API:**
- Service: Telegram Bot API
  - SDK/Client: `aiogram` 3.3.0 — `Bot` class from `aiogram`
  - Auth: `TELEGRAM_BOT_TOKEN` env var
  - Webhook URL: `TELEGRAM_WEBHOOK_URL` env var
  - Implementation: `backend/app/services/telegram_service.py` — `TelegramService` class for sending messages and parsing updates
  - Webhook receiver: `backend/app/routers/telegram_handlers.py` — `POST /webhook` endpoint
  - Polling mode: `backend/app/bot_polling.py` and `backend/bot_dev.py`
  - Message routing: `backend/app/services/handler_service.py` — `HandlerService` routes all incoming Telegram messages to the correct business logic

## Data Storage

**Databases:**
- Type: MySQL 5.7+ / 8.x
  - Connection: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` env vars
  - URL format: `mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}?ssl_disabled=true`
  - Client: SQLAlchemy 2.0.23 ORM with pymysql 1.1.0 driver
  - Session management: `backend/app/database/__init__.py` — `get_db()` FastAPI dependency, `SessionLocal` factory
  - Connection pool: QueuePool, pool_size=5, max_overflow=10, pool_pre_ping=True
  - Models: `backend/app/models/` — `User`, `Course`, `Lesson`, `Concept`, `QuizSession`, `QuizAnswer`, `QuizSummary`, `UserCourse`, `OnboardingState`
  - Migrations: alembic, config at `backend/alembic.ini`, scripts at `backend/alembic/versions/`

**File Storage:**
- Local filesystem only — no cloud object storage detected

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- None (no user-facing auth system)
- User identity is derived from Telegram user ID (`telegram_id` field on `User` model)
- No JWT, sessions, or OAuth detected

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry or similar)

**Logs:**
- Python standard `logging` module used throughout services
- Format: `logger = logging.getLogger(__name__)` in each service/router module
- Log SQL queries in debug mode (`echo=settings.debug` on SQLAlchemy engine)

## CI/CD & Deployment

**Hosting:**
- Not explicitly configured (no Dockerfile, docker-compose, or deployment manifests detected)

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- `DB_HOST` — MySQL host (default: `127.0.0.1`)
- `DB_PORT` — MySQL port (default: `3306`)
- `DB_USER` — MySQL user (default: `root`)
- `DB_PASSWORD` — MySQL password (default: empty)
- `DB_NAME` — MySQL database name (default: `evening_learning`)
- `TELEGRAM_BOT_TOKEN` — Bot token from BotFather
- `TELEGRAM_WEBHOOK_URL` — Public URL for webhook (empty = not set, use polling instead)
- `LLM_BASE_URL` — OpenAI-compatible API base URL (default: `https://api.openai.com/v1`)
- `LLM_API_KEY` — API key for LLM provider
- `LLM_FAST_MODEL` — Model for fast/cheap LLM tasks (default: `gpt-4o-mini`)
- `LLM_SMART_MODEL` — Model for complex LLM tasks (default: `gpt-4o`)

**Secrets location:**
- `.env` file in `backend/` (loaded automatically by pydantic-settings)

## Webhooks & Callbacks

**Incoming:**
- `POST /webhook` — Receives Telegram update payloads; handled by `backend/app/routers/telegram_handlers.py`

**Outgoing:**
- Telegram Bot API — Outgoing messages sent via `TelegramService` using aiogram `Bot` client
- LLM API — Outgoing requests for quiz generation, evaluation, summaries, course suggestions

---

*Integration audit: 2026-03-28*
