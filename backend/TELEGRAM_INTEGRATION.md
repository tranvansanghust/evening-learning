# Telegram Integration Guide

This document explains how the Telegram bot handlers are integrated with the FastAPI backend services.

## Architecture Overview

```
Telegram Bot
    ↓
TelegramService (Message parsing & sending)
    ↓
TelegramHandlers (Command routing)
    ↓
Service Layer (Business logic)
    ├─ OnboardingService (User creation, assessment)
    ├─ ProgressService (Progress tracking)
    ├─ QuizService (Quiz management)
    └─ LLMService (AI-powered questions & evaluation)
    ↓
Database Layer (SQLAlchemy ORM)
```

## Handler Integration Pattern

Each Telegram handler follows this pattern:

```python
async def handle_command(self, update: ParsedUpdate) -> None:
    """Handle specific command."""
    try:
        # Get database session
        db = SessionLocal()

        try:
            # Call relevant service method
            result = self.service_name.method(user_id, db_session=db)

            # Format response using HandlerService
            msg = self.handler_service.format_response(result)

            # Send to user
            await self.service.send_message(update.user_id, msg)

        finally:
            db.close()

    except ValueError as e:
        # Handle not found errors
        logger.warning(f"Validation error: {e}")
        await self.service.send_message(update.user_id, error_msg)

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error: {e}")
        await self.service.send_message(update.user_id, error_msg)
```

## Implemented Handlers

### 1. `/start` - Onboarding
- **Service**: `OnboardingService.create_user()`
- **Response**: Welcome message with HandlerService
- **Database**: Creates User record

```python
user = onboarding_service.create_user(
    telegram_id=update.user_id,
    username=f"user_{update.user_id}"
)
msg = handler_service.format_welcome_message(user.username)
```

### 2. `/progress` - Show Learning Progress
- **Service**: `ProgressService.get_user_progress()`
- **Response**: Formatted progress with emoji and progress bars
- **Database**: Queries lessons, concepts, quiz summaries

```python
progress = progress_service.get_user_progress(user_id, db_session=db)
msg = handler_service.format_progress_message(progress)
```

### 3. `/review` - Show Quiz Summaries
- **Service**: `ProgressService.get_quiz_summaries()` or `get_review_by_topic()`
- **Response**: List of quiz summaries with summary IDs
- **Database**: Queries quiz summaries, lesson names

```python
summaries = progress_service.get_quiz_summaries(user_id, db_session=db)
msg = handler_service.format_quiz_summaries(summaries)
```

### 4. `/done` - Complete Learning Session
- **Service**: Checks user state (simplified for now)
- **Response**: Asks what user learned
- **Database**: Would update user session status

```python
msg = (
    "Tốt lắm! 🎉\n\n"
    "Hôm nay bạn học đến đâu rồi?\n"
    "Kể mình nghe bạn tiếp thu được gì nào!"
)
```

### 5. `/resume` - Resume Learning
- **Service**: State management (simplified for now)
- **Response**: Resumption message
- **Database**: Would fetch last session and reschedule

```python
msg = "Quay lại học tiếp thôi! 💪"
```

### 6. `/answer` - Submit Quiz Answer
- **Service**: `QuizService.submit_answer()`
- **Response**: Formatted answer evaluation and next question
- **Database**: Saves answer, generates next question

```python
result = quiz_service.submit_answer(session_id, user_answer, db_session=db)
eval_msg = handler_service.format_evaluation(result["evaluation"])

if result["next_action"] == "end":
    summary = quiz_service.get_or_generate_summary(session_id, db_session=db)
    msg = handler_service.format_quiz_detail(summary)
else:
    msg = handler_service.format_quiz_question(result["next_question"])
```

## Helper Services

### HandlerService - Response Formatting
Formats backend data into user-friendly Telegram messages with emoji:

```python
format_progress_message(progress)          # Progress with bars
format_quiz_summaries(summaries)           # Quiz list
format_quiz_detail(summary)                # Detailed summary
format_quiz_question(question)             # Question formatting
format_evaluation(evaluation)              # Answer feedback
format_welcome_message(username)           # Welcome message
format_error_message(error_type)          # Error messages
```

### HTTPClient - Internal API Calls
Makes HTTP calls to local FastAPI endpoints (optional, for advanced use):

```python
client = HTTPClient()
result = await client.post("/api/quiz/submit", {"session_id": 1, "answer": "text"})
```

## Database Session Management

All handlers follow proper database session management:

```python
db = SessionLocal()
try:
    # Use db_session in service calls
    result = service.method(user_id, db_session=db)
finally:
    db.close()
```

This ensures:
- Connections are properly closed
- No connection leaks
- Transactions are committed/rolled back appropriately

## Error Handling Strategy

Each handler includes three-level error handling:

1. **ValueError** - User/resource not found errors
   - Log as warning
   - Send user-friendly message
   - Suggest corrective action

2. **Expected Exceptions** - Service-specific errors
   - Log with context
   - Send appropriate error message

3. **Unexpected Exceptions** - Catch-all
   - Log full error
   - Send generic error message
   - No sensitive info to user

## User ID Mapping

**Important**: Current implementation uses placeholder user_id=1 for service calls.

For production, handlers need to:
1. Store telegram_id to user_id mapping in User model
2. Look up user_id from telegram_id before calling services:

```python
user = db.query(User).filter(User.telegram_id == update.user_id).first()
if not user:
    # New user, create via onboarding
    user = onboarding_service.create_user(update.user_id)

# Now use user.user_id for service calls
progress = progress_service.get_user_progress(user.user_id, db_session=db)
```

## Integration Checklist

- [x] HandlerService created with formatting methods
- [x] HTTPClient created for internal API calls
- [x] `/start` handler integrated with OnboardingService
- [x] `/progress` handler integrated with ProgressService
- [x] `/review` handler integrated with ProgressService
- [x] `/done` handler with check-in message
- [x] `/resume` handler with resumption message
- [x] `/answer` handler integrated with QuizService
- [x] Error handling in all handlers
- [x] Database session management in all handlers
- [x] Logging in all handlers
- [ ] User ID mapping (telegram_id → user_id)
- [ ] User state tracking (onboarding, learning, quiz)
- [ ] Session management (active learning sessions)
- [ ] Quiz session state tracking
- [ ] Reminder scheduling

## Next Steps

1. **User State Tracking**: Implement state machine for user progress
2. **Session Management**: Track active learning and quiz sessions
3. **Quiz Integration**: Wire quiz questions and answer submission
4. **Progress Persistence**: Save user progress on each interaction
5. **Reminder System**: Schedule and send learning reminders
6. **Analytics**: Log user interactions for analytics

## Testing

To test handlers locally:

```python
from app.routers.telegram_handlers import TelegramHandlers
from app.services.telegram_service import TelegramService, ParsedUpdate
from app.services.onboarding_service import OnboardingService
from app.database import SessionLocal

# Initialize services
telegram_service = TelegramService(bot_token="YOUR_TOKEN")
db = SessionLocal()
onboarding_service = OnboardingService(db)
handlers = TelegramHandlers(telegram_service, onboarding_service)

# Test /start command
update = ParsedUpdate("123456789", "/start", "message")
await handlers.handle_update(update)
```

## References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- aiogram (Telegram Bot Library): https://docs.aiogram.dev/
- Pydantic: https://docs.pydantic.dev/
