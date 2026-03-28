# Codebase Structure
_Last updated: 2026-03-28_

## Summary

Single-backend monorepo. All production code lives under `backend/app/`. A `frontend/` directory exists at root but is currently empty. The backend follows a strict directory-per-layer layout: `routers/`, `services/`, `models/`, `schemas/`, `utils/`, `database/`.

## Directory Layout

```
evening-learning/
├── backend/                        # All Python backend code
│   ├── app/                        # Application package
│   │   ├── main.py                 # FastAPI app entry point, router registration
│   │   ├── config.py               # Pydantic settings, env var loading
│   │   ├── bot_polling.py          # Aiogram polling entry point (dev mode)
│   │   ├── database/               # DB engine, session factory, Base
│   │   │   └── __init__.py         # engine, SessionLocal, Base, get_db
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py         # Re-exports all models
│   │   │   ├── user.py
│   │   │   ├── course.py
│   │   │   ├── lesson.py
│   │   │   ├── concept.py
│   │   │   ├── user_course.py
│   │   │   ├── quiz_session.py
│   │   │   ├── quiz_answer.py
│   │   │   ├── quiz_summary.py
│   │   │   └── onboarding_state.py
│   │   ├── routers/                # FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── telegram.py         # Webhook receiver: POST /webhook/telegram
│   │   │   ├── telegram_handlers.py # Aiogram command handlers (/start, /done, etc.)
│   │   │   ├── onboarding.py       # POST /api/onboard/*
│   │   │   ├── learning.py         # POST /api/learn/*
│   │   │   ├── quiz.py             # POST /api/quiz/*
│   │   │   └── progress.py         # GET /api/progress/*
│   │   ├── services/               # Business logic classes
│   │   │   ├── __init__.py
│   │   │   ├── onboarding_service.py  # OnboardingService — user creation, course setup, level assessment
│   │   │   ├── quiz_service.py        # QuizService — quiz lifecycle, LLM orchestration
│   │   │   ├── llm_service.py         # LLMService — OpenAI-compatible API calls
│   │   │   ├── llm_prompts.py         # LLMPrompts — prompt templates
│   │   │   ├── telegram_service.py    # TelegramService — send messages, parse updates
│   │   │   ├── handler_service.py     # HandlerService — format data for Telegram display
│   │   │   └── progress_service.py    # ProgressService — query and compute learning metrics
│   │   ├── schemas/                # Pydantic schemas (shared API models)
│   │   │   ├── __init__.py
│   │   │   └── progress.py         # UserProgress, QuizSummaryPreview, ConceptDetail
│   │   └── utils/                  # Utility helpers
│   │       ├── __init__.py
│   │       └── http_client.py
│   ├── tests/                      # pytest test suite
│   │   ├── __init__.py
│   │   └── test_message_routing.py
│   ├── alembic/                    # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/               # Migration scripts
│   │       ├── 22d1932ee4e1_initial_schema.py
│   │       ├── d9c5d4750155_new.py
│   │       ├── 87cbb2432c2d_fix_onboarding.py
│   │       └── fa6c6359d5d0_add_course_topic_to_onboarding_state.py
│   ├── alembic.ini                 # Alembic configuration
│   ├── requirements.txt            # Python dependencies
│   ├── bot_dev.py                  # (root-level dev bot script)
│   └── eveninig-learning-venv/     # Virtual environment (intentional typo)
├── docs/                           # Human-readable documentation
│   ├── 01_system-core-features.md
│   ├── 02_onboarding-user-flow.md
│   ├── 03_daily-loop-flow.md
│   ├── 04_knowledge-tracker-and-edge-cases.md
│   ├── 05_technical-architecture.md
│   ├── setup.sql
│   └── tech/                       # Technical reference docs
├── ai-proposals/                   # Feature planning proposals (pre-implementation)
├── .planning/                      # GSD planning documents
│   └── codebase/                   # Auto-generated codebase analysis
├── frontend/                       # Frontend placeholder (currently empty)
├── CLAUDE.md                       # Project rules for Claude
└── README.md
```

## Directory Purposes

**`backend/app/routers/`:**
- Purpose: HTTP and Telegram presentation layer only — no business logic
- Contains: `APIRouter` instances, inline request/response Pydantic models, `Depends` wiring
- Key files: `telegram_handlers.py` (aiogram command handlers), `onboarding.py`, `learning.py`, `quiz.py`, `progress.py`, `telegram.py` (webhook)
- Note: Inline Pydantic request/response models are defined directly in each router file, not in `schemas/`

**`backend/app/services/`:**
- Purpose: All business logic; one class per concern
- Contains: Service classes instantiated per-request (onboarding, quiz) or as singletons (telegram, LLM)
- Key files: `onboarding_service.py`, `quiz_service.py`, `llm_service.py`, `handler_service.py`, `progress_service.py`, `telegram_service.py`

**`backend/app/models/`:**
- Purpose: SQLAlchemy ORM models mapping to MySQL tables
- Contains: One model class per file, relationships defined with `relationship()`
- Key files: `user.py`, `course.py`, `lesson.py`, `concept.py`, `onboarding_state.py`, `quiz_session.py`, `quiz_summary.py`
- Import pattern: Always import from `app.models` (the package `__init__.py`), not individual files

**`backend/app/database/`:**
- Purpose: Database connection configuration
- Contains: `engine` (QueuePool, 5 connections), `SessionLocal`, `Base` (declarative base), `get_db` generator
- Key files: `__init__.py` — everything is in a single file

**`backend/app/schemas/`:**
- Purpose: Pydantic schemas shared across multiple routers/services
- Contains: Complex response schemas that are reused (`UserProgress`, `QuizSummaryPreview`)
- Note: Simple one-off request/response models are defined inline in their router file

**`backend/app/services/llm_prompts.py`:**
- Purpose: Centralized prompt templates for all LLM interactions
- Contains: `LLMPrompts` class with methods/constants for quiz, evaluation, curriculum, and assessment prompts

**`backend/alembic/versions/`:**
- Purpose: Database schema migration history
- Generated: Yes (via `alembic revision`)
- Committed: Yes

**`docs/`:**
- Purpose: Human-readable documentation of system design and flows
- Not consumed by the application at runtime

**`ai-proposals/`:**
- Purpose: Pre-implementation feature planning documents
- Format: Markdown with goals, files to change, and step-by-step plan
- Required before implementing any feature touching more than 1 file (per CLAUDE.md)

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app — `uvicorn app.main:app`
- `backend/app/bot_polling.py`: Aiogram polling — `python -m app.bot_polling`

**Configuration:**
- `backend/app/config.py`: All settings; import `from app.config import settings`
- `backend/.env`: Environment variables (not committed; see CLAUDE.md for required vars)
- `backend/alembic.ini`: Alembic migration config

**Core Business Logic:**
- `backend/app/services/onboarding_service.py`: User onboarding state machine
- `backend/app/services/quiz_service.py`: Quiz session lifecycle
- `backend/app/services/llm_service.py`: LLM API gateway
- `backend/app/services/llm_prompts.py`: All prompt templates

**Telegram Integration:**
- `backend/app/routers/telegram_handlers.py`: Aiogram command handlers (polling mode)
- `backend/app/routers/telegram.py`: Webhook receiver (prod mode)
- `backend/app/services/telegram_service.py`: Bot messaging and update parsing

**Database:**
- `backend/app/database/__init__.py`: Engine, session, Base
- `backend/app/models/__init__.py`: All model imports

**Testing:**
- `backend/tests/test_message_routing.py`: Current test file

## Naming Conventions

**Files:**
- Snake_case for all Python files: `onboarding_service.py`, `quiz_session.py`
- One class per file; file named after the class (snake_case of class name)

**Directories:**
- Plural nouns for layer directories: `routers/`, `services/`, `models/`, `schemas/`

**Classes:**
- PascalCase: `OnboardingService`, `QuizService`, `LLMService`
- Suffix indicates layer: `*Service`, `*Router` (implicit), `*Request`/`*Response` (Pydantic)

## Where to Add New Code

**New Feature (business logic):**
- Primary service class: `backend/app/services/<feature>_service.py`
- Corresponding router: `backend/app/routers/<feature>.py`
- Register router in: `backend/app/main.py` → `include_routers()`
- Telegram commands: `backend/app/routers/telegram_handlers.py`
- Tests: `backend/tests/test_<feature>.py`

**New Database Model:**
- Implementation: `backend/app/models/<model_name>.py`
- Register: Add import to `backend/app/models/__init__.py` and `__all__` list
- Migration: `alembic revision --autogenerate -m "description"` → `alembic upgrade head`

**New LLM Prompt:**
- Add to: `backend/app/services/llm_prompts.py` in the `LLMPrompts` class

**New Shared Schema:**
- Add to: `backend/app/schemas/progress.py` or create `backend/app/schemas/<domain>.py`

**Utilities:**
- Shared helpers: `backend/app/utils/`

## Special Directories

**`backend/eveninig-learning-venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No (in .gitignore)
- Note: Intentional typo in directory name — do not rename

**`backend/alembic/versions/`:**
- Purpose: Database migration files, auto-generated by Alembic
- Generated: Partially (scaffolded by alembic, modified manually)
- Committed: Yes

**`.planning/codebase/`:**
- Purpose: GSD auto-generated codebase analysis documents
- Generated: Yes (by `/gsd:map-codebase` command)
- Committed: Yes

---

_Structure analysis: 2026-03-28_
