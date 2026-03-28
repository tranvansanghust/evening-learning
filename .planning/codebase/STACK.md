# Technology Stack
_Last updated: 2026-03-28_

## Summary
Evening Learning is a Python backend application powering an AI-driven Telegram learning bot. It uses FastAPI as the web framework, MySQL as the database, and the OpenAI SDK (pointed at any OpenAI-compatible endpoint) for LLM calls. The bot integration uses aiogram 3.x in both webhook and polling modes.

## Languages

**Primary:**
- Python 3.11 (venv at `backend/eveninig-learning-venv/lib/python3.11`)
  - All backend logic, services, models, and API handlers

**Secondary:**
- None detected

## Runtime

**Environment:**
- Python 3.11 (virtual environment)
- Venv location: `backend/eveninig-learning-venv/` (note: intentional typo)
- Also has a `backend/venv/` directory

**Package Manager:**
- pip (no Poetry or pipenv detected)
- Lockfile: `backend/requirements.txt` (pinned versions, no lock file)

## Frameworks

**Core:**
- FastAPI 0.104.1 — HTTP API framework, entry point at `backend/app/main.py`
- uvicorn 0.24.0 (standard extras) — ASGI server, runs FastAPI app
- Pydantic 2.5.0 — Data validation and settings management
- pydantic-settings 2.1.0 — `.env` file loading via `Settings` class in `backend/app/config.py`

**Bot:**
- aiogram 3.3.0 — Telegram Bot framework, supports both webhook (`backend/app/routers/telegram_handlers.py`) and polling (`backend/app/bot_polling.py`, `backend/bot_dev.py`)

**ORM / Database:**
- SQLAlchemy 2.0.23 — ORM, declarative base in `backend/app/database/__init__.py`
- alembic 1.18.4 (installed) / `>=1.13.0` (required) — Database migrations, config at `backend/alembic.ini`, versions at `backend/alembic/versions/`
- pymysql 1.1.0 — MySQL driver used in connection URL: `mysql+pymysql://`

**LLM:**
- openai 2.29.0 (installed) / `>=1.0.0` (required) — OpenAI-compatible client used in `backend/app/services/llm_service.py`

**Testing:**
- pytest 9.0.2
- pytest-asyncio 1.3.0

**Utilities:**
- httpx 0.25.0 — Async HTTP client (available, used internally by some SDKs)
- python-dotenv 1.0.0 — `.env` file support
- cryptography 46.0.5 (installed) / `>=42.0.0` (required) — Required by aiogram/pymysql SSL

## Key Dependencies

**Critical:**
- `fastapi==0.104.1` — Core web framework; all API routes defined under `backend/app/routers/`
- `aiogram==3.3.0` — Telegram Bot integration; message routing via `backend/app/services/handler_service.py`
- `openai>=1.0.0` — LLM API calls; all calls routed through `backend/app/services/llm_service.py`
- `sqlalchemy==2.0.23` — ORM for all database models in `backend/app/models/`
- `pymysql==1.1.0` — Required for MySQL connectivity; connection URL driver

**Infrastructure:**
- `alembic>=1.13.0` — Manages DB schema migrations; migration scripts in `backend/alembic/versions/`
- `pydantic==2.5.0` — Request/response validation and LLM response parsing
- `pydantic-settings==2.1.0` — Typed config management from `.env`

## Configuration

**Environment:**
- All config loaded from `.env` file (auto-discovered by `pydantic-settings`)
- Typed access via `Settings` class in `backend/app/config.py`
- Global singleton: `from app.config import settings`
- Key config groups: database (MySQL), Telegram bot token + webhook URL, LLM (base URL, API key, model names)

**Build:**
- No build step; pure Python interpreted
- `backend/alembic.ini` — migration configuration
- `backend/alembic/env.py` — migration environment setup

## Platform Requirements

**Development:**
- Python 3.11
- MySQL 5.7+ or 8.x running locally (default: `127.0.0.1:3306`)
- Run server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` from `backend/`
- Run polling bot: `python -m app.bot_polling` from `backend/`

**Production:**
- ASGI server (uvicorn with workers): `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
- Telegram webhook mode via `POST /webhook` endpoint
- MySQL database (connection pooling configured: pool_size=5, max_overflow=10)

---

*Stack analysis: 2026-03-28*
