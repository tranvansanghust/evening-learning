# Technical Concerns
_Last updated: 2026-03-28_

## Summary
The codebase has several critical issues: a broken webhook routing path, hardcoded credentials committed to source, and a 1009-line god file violating the project's own 300-line limit. Several handlers are stubs with placeholder values that would cause runtime crashes.

## Known Issues

- **Non-functional webhook routing** — webhook receiver does not correctly route to handlers
- **Hardcoded `user_id=1` placeholder** — progress and review handlers use a hardcoded user ID instead of resolving from Telegram context
- **Broken `settings.anthropic_api_key` attribute** — referenced in `/api/learn` and `/api/quiz` endpoints but the attribute does not exist on the settings object; causes a crash at runtime
- **Stub handlers** — `/resume`, `/progress`, `/review` are not implemented; they return placeholder responses

## Technical Debt

- **Two parallel handler systems in one file** — `telegram_handlers.py` is 1009 lines and contains both the old and new handler routing logic side-by-side
- **9 files exceed the 300-line project limit** — violates the project's own code quality rule; key offenders include `telegram_handlers.py` (1009 lines), `onboarding_service.py`, `quiz_service.py`
- **Missing `watchfiles` from requirements** — uvicorn `--reload` depends on `watchfiles` but it is not in `requirements.txt`
- **Duplicate logic** — onboarding state transitions appear in both the router and the service layer

## Security Concerns

- **Real Telegram bot token committed as default value** in `config.py` — token is visible in git history
- **No webhook signature verification** — the `/webhook` endpoint accepts any POST request without verifying the `X-Telegram-Bot-Api-Secret-Token` header
- **SSL disabled for database** — SQLAlchemy connection string uses `ssl=false`

## Performance Concerns

- **No LLM call timeout** — `llm_service.py` makes OpenAI API calls with no timeout; a hung request will block the handler indefinitely
- **DB session per message** — a new SQLAlchemy session is created for every incoming Telegram message with no connection pooling configured

## Missing / Incomplete

- **No reminder/scheduler** — the learning reminder feature (scheduled daily messages) is not implemented
- **Track B content not implemented** — onboarding references a "Track B" learning path but the content and routing are missing
- **No `.env.example`** — new developers have no reference for required environment variables
- **Empty frontend** — `frontend/` directory exists but contains no code
- **No alembic baseline migration** — two new migration files exist (`87cbb2432c2d`, `fa6c6359d5d0`) but there is no initial schema migration to establish the baseline
