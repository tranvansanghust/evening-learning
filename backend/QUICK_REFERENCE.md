# Quick Reference: Telegram Integration

## File Structure

```
app/
├── routers/
│   ├── telegram_handlers.py      ✓ Updated - All handlers integrated
│   ├── telegram.py               (Webhook endpoint)
│   ├── onboarding.py             (REST endpoints)
│   ├── learning.py               (REST endpoints)
│   ├── quiz.py                   (REST endpoints)
│   └── progress.py               (REST endpoints)
│
├── services/
│   ├── handler_service.py        ✓ NEW - Response formatting
│   ├── telegram_service.py       (Message sending)
│   ├── onboarding_service.py     (User creation, assessment)
│   ├── progress_service.py       (Progress tracking)
│   ├── quiz_service.py           (Quiz management)
│   └── llm_service.py            (AI-powered questions)
│
└── utils/
    ├── __init__.py               ✓ NEW - Exports
    └── http_client.py            ✓ NEW - Internal API calls
```

## Handler Methods Summary

| Handler | Service | Method | Purpose |
|---------|---------|--------|---------|
| `/start` | OnboardingService | `create_user()` | Register new user |
| `/progress` | ProgressService | `get_user_progress()` | Show learning stats |
| `/review` | ProgressService | `get_quiz_summaries()` | List all quizzes |
| `/review [topic]` | ProgressService | `get_review_by_topic()` | Filter by topic |
| `/done` | (State check) | (none) | Mark lesson complete |
| `/resume` | (State check) | (none) | Resume learning |
| `/answer` | QuizService | `submit_answer()` | Process quiz answer |

## HandlerService Methods

### Formatting Methods

```python
format_progress_message(progress)      # Progress with emoji bars
format_quiz_summaries(summaries)       # List of quiz summaries
format_quiz_detail(summary)            # Full quiz details
format_quiz_question(question)         # Format quiz question
format_evaluation(evaluation)          # Answer feedback
format_welcome_message(username)       # Welcome greeting
format_error_message(error_type)       # Error messages
```

### Error Types

```python
"general"           # Generic error
"not_found"        # Resource not found
"invalid_input"    # Bad input format
"quiz_incomplete"  # Quiz incomplete
```

## HTTPClient Usage

```python
from app.utils.http_client import HTTPClient

client = HTTPClient(base_url="http://localhost:8000")

# GET request
result = await client.get("/api/progress/user/1")

# POST request
result = await client.post("/api/quiz/submit", {"session_id": 1, "answer": "text"})

# PUT request
result = await client.put("/api/user/1", {"username": "new_name"})

# DELETE request
result = await client.delete("/api/session/1")

# Generic call
result = await client.call_endpoint("POST", "/api/path", {"key": "value"})
```

## Common Patterns

### Pattern 1: Service Call with Formatting

```python
db = SessionLocal()
try:
    result = service_name.method(user_id, db_session=db)
    msg = handler_service.format_response(result)
    await telegram_service.send_message(user_id, msg)
finally:
    db.close()
```

### Pattern 2: Error Handling

```python
try:
    # Do work
except ValueError as e:
    logger.warning(f"Validation error: {e}")
    msg = format_error_message("not_found")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    msg = format_error_message("general")
finally:
    if db:
        db.close()
```

### Pattern 3: State-Based Routing

```python
# Check user state from database
if onboarding_active:
    await handle_onboarding_input(update, user, state)
elif quiz_active:
    await handle_answer(update, session_id)
else:
    await send_instruction_message(update)
```

## Database Session Management

```python
from app.database import SessionLocal

# Always use try/finally
db = SessionLocal()
try:
    # Pass db_session to service methods
    result = service.method(param, db_session=db)
    # Changes auto-commit on success
finally:
    db.close()  # Always close
```

## Logging Patterns

```python
logger.info(f"User {user_id} initiated {command}")      # Command start
logger.warning(f"User {user_id} not found")             # Validation errors
logger.error(f"Error in {handler}: {error}")            # Exception errors
logger.debug(f"Routing message for user {user_id}")     # Debug info
```

## Type Hints

```python
from typing import Optional, List, Dict, Any
from app.services.telegram_service import ParsedUpdate

async def handle_command(self, update: ParsedUpdate) -> None:
    """Handler method signature."""
    pass

def format_message(data: Dict[str, Any]) -> str:
    """Formatting method signature."""
    return ""
```

## Environment Variables Needed

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/api/telegram/webhook

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=evening_learning
DB_USER=user
DB_PASSWORD=password

# Claude API
CLAUDE_API_KEY=your_api_key

# App
DEBUG=True
```

## Testing a Handler

```bash
cd /path/to/backend

# Check syntax
python3 -m py_compile app/routers/telegram_handlers.py

# Test import
python3 -c "from app.routers.telegram_handlers import TelegramHandlers; print('OK')"

# Run with pytest
pytest tests/test_telegram_handlers.py -v
```

## Common Imports for Handlers

```python
from app.services.telegram_service import ParsedUpdate, TelegramService
from app.services.handler_service import HandlerService
from app.services.onboarding_service import OnboardingService
from app.services.progress_service import ProgressService
from app.services.quiz_service import QuizService
from app.database import SessionLocal
from app.models import User, QuizSummary
import logging

logger = logging.getLogger(__name__)
```

## Database Queries Used

```python
from sqlalchemy.orm import Session
from app.models import User, QuizSummary, QuizSession

db = SessionLocal()

# Get user by telegram_id
user = db.query(User).filter(User.telegram_id == "123456789").first()

# Get user by user_id
user = db.query(User).filter(User.user_id == 1).first()

# Get active quiz session
quiz = db.query(QuizSession).filter(
    QuizSession.user_id == user_id,
    QuizSession.status == "active"
).first()

# Get quiz summary
summary = db.query(QuizSummary).filter(
    QuizSummary.summary_id == summary_id
).first()
```

## Response Format in Telegram

All messages use HTML formatting:

```python
# Bold
<b>Bold text</b>

# Italic
<i>Italic text</i>

# Code
<code>code</code>

# Pre-formatted (for blocks)
<pre>pre-formatted text</pre>
```

## Next Steps Priority

1. **User ID Mapping** - Map telegram_id to user_id in handlers
2. **State Tracking** - Implement user state in database
3. **Session Management** - Track active learning/quiz sessions
4. **Quiz Integration** - Connect quiz flow end-to-end
5. **Progress Persistence** - Save progress on each interaction
6. **Reminder System** - Schedule learning reminders
7. **Analytics** - Log interactions for analytics

## Troubleshooting

### Handler not responding?
- Check if telegram_service is initialized
- Verify bot token is valid
- Check logs for exceptions
- Verify user_id format

### Database errors?
- Ensure db.close() is called in finally block
- Check connection string in config
- Verify migrations are run
- Check if user exists before operations

### Service returns None?
- Check if service is initialized
- Verify service method exists
- Check db_session parameter is passed
- Look at service logs for errors

### Message not formatted?
- Check if handler_service is initialized
- Verify formatter method exists
- Check method parameters match data structure
- Test formatter method directly
