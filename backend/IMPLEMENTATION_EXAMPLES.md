# Implementation Examples

This document shows practical examples of how to use the integrated Telegram handlers with backend services.

## Handler Initialization

```python
from app.services.telegram_service import TelegramService
from app.routers.telegram_handlers import TelegramHandlers
from app.services.onboarding_service import OnboardingService
from app.services.progress_service import ProgressService
from app.services.quiz_service import QuizService
from app.services.llm_service import LLMService
from app.database import SessionLocal, engine
from app.config import settings

# Initialize services
telegram_service = TelegramService(bot_token=settings.telegram_bot_token)
db = SessionLocal()

onboarding_service = OnboardingService(db)
progress_service = ProgressService()
llm_service = LLMService(api_key=settings.claude_api_key)
quiz_service = QuizService(llm_service=llm_service)

# Initialize handlers with all services
handlers = TelegramHandlers(
    telegram_service=telegram_service,
    onboarding_service=onboarding_service,
    progress_service=progress_service,
    quiz_service=quiz_service,
)
```

## Example 1: User Onboarding Flow

```python
from app.services.telegram_service import ParsedUpdate

# User sends /start
update = ParsedUpdate(
    user_id="123456789",
    message_text="/start",
    update_type="message"
)

# Handler processes it
await handlers.handle_update(update)

# Flow:
# 1. Creates User record via OnboardingService
# 2. Formats welcome message with HandlerService
# 3. Sends: "Chào bạn! Mình là học bạn AI 👋..."
# 4. User is ready to provide course URL or topic
```

## Example 2: Viewing Progress

```python
# User sends /progress
update = ParsedUpdate(
    user_id="123456789",
    message_text="/progress",
    update_type="message"
)

# Handler processes it
await handlers.handle_update(update)

# Flow:
# 1. Gets user progress from ProgressService
# 2. Calculates percentages and progress bars
# 3. Formats with HandlerService using emoji:
#    📊 Tiến độ học tập của bạn
#    📚 Bài học:
#    ████████░░ 3/10 (30%)
#    💡 Khái niệm:
#    ███░░░░░░░ 6/40 (15%)
# 4. Adds motivational message based on progress
# 5. Sends formatted message
```

## Example 3: Quiz Answer Handling

```python
from app.models import QuizSession

# User sends an answer during quiz
update = ParsedUpdate(
    user_id="123456789",
    message_text="useState is a React Hook for managing state in functional components",
    update_type="message"
)

# Get active quiz session for user (would be stored in state)
session_id = 1

# Handler processes answer
await handlers.handle_answer(update, session_id)

# Flow:
# 1. Calls QuizService.submit_answer()
# 2. LLM evaluates answer
# 3. Formats evaluation with HandlerService:
#    ✅ Tuyệt vời!
#    Nhận xét: Great understanding of React hooks!
#    💪 Bạn làm rất tốt! Hãy tiếp tục!
# 4. Decides next action:
#    - If continue: generates and sends next question
#    - If follow-up: sends follow-up question
#    - If end: generates summary and sends it
# 5. Updates session in database
```

## Example 4: Quiz Summary

After quiz completes, handler sends formatted summary:

```python
# QuizSummary data from database
summary = {
    "summary_id": 1,
    "date": datetime.now(),
    "lesson_name": "React Hooks",
    "concepts_mastered": ["useState", "useEffect", "useContext"],
    "concepts_weak": [
        {
            "concept": "useReducer",
            "user_answer": "Similar to useState",
            "correct_explanation": "useReducer is for complex state logic..."
        },
        {
            "concept": "Custom Hooks",
            "user_answer": "Not mentioned",
            "correct_explanation": "Custom Hooks let you reuse stateful logic..."
        }
    ]
}

# HandlerService formats it nicely:
msg = handler_service.format_quiz_detail(summary)

# Output:
# 📊 React Hooks
# 📅 24/03/2026 14:30
#
# ✅ Khái niệm đạt:
#   • useState
#   • useEffect
#   • useContext
#
# ⚠️ Khái niệm cần ôn:
#   • useReducer
#     useReducer is for complex state logic...
#   • Custom Hooks
#     Custom Hooks let you reuse stateful logic...
#
# 💪 Hãy ôn lại những khái niệm này để nắm vững hơn!
```

## Example 5: Review Quiz History

```python
# User sends /review
update = ParsedUpdate(
    user_id="123456789",
    message_text="/review",
    update_type="message"
)

await handlers.handle_update(update)

# Flow:
# 1. Gets all quiz summaries from ProgressService
# 2. Formats with HandlerService:
#
# 📚 Danh sách các quiz của bạn
#
# 1. React Hooks
#    📅 24/03/2026
#    ✅ 3 khái niệm đạt
#    ⚠️ 2 khái niệm cần ôn
#    /review_detail_1
#
# 2. JavaScript Advanced
#    📅 23/03/2026
#    ✅ 5 khái niệm đạt
#    ⚠️ 1 khái niệm cần ôn
#    /review_detail_2
```

## Example 6: Filter Review by Topic

```python
# User sends /review React
update = ParsedUpdate(
    user_id="123456789",
    message_text="/review React",
    update_type="message"
)

await handlers.handle_update(update)

# Flow:
# 1. Extracts topic: "React"
# 2. Calls ProgressService.get_review_by_topic("React")
# 3. Filters summaries where lesson title contains "React"
# 4. Formats and sends filtered list
```

## Example 7: Error Handling

```python
# User not found error
try:
    # Handler tries to get progress for non-existent user
    progress = progress_service.get_user_progress(999, db_session=db)
except ValueError:
    # Handler catches and sends user-friendly message
    msg = (
        "⚠️ Không tìm thấy tài khoản\n\n"
        "Bạn chưa hoàn thành onboarding.\n"
        "Hãy sử dụng /start để bắt đầu!"
    )
    await service.send_message(update.user_id, msg)
```

## Example 8: Complete Learning Session

```python
# User sends /done
update = ParsedUpdate(
    user_id="123456789",
    message_text="/done",
    update_type="message"
)

await handlers.handle_update(update)

# Flow:
# 1. Handler responds with check-in prompt
# 2. User provides check-in message (what they learned)
# 3. Handler could route to:
#    - Track A: Save check-in and prepare for quiz
#    - Track B: Auto-start quiz based on lesson
# 4. Next handler processes user's learning summary
```

## Example 9: Using HandlerService Directly

```python
from app.schemas.progress import UserProgress
from app.services.handler_service import HandlerService

handler_service = HandlerService()

# Format progress
progress = UserProgress(
    lessons_completed=3,
    total_lessons=10,
    concepts_mastered=15,
    total_concepts=40
)

msg = handler_service.format_progress_message(progress)
# Output: Nicely formatted message with progress bars and emoji

# Format error
error_msg = handler_service.format_error_message("not_found")
# Output: "❌ Không tìm thấy..."

# Format question
question_msg = handler_service.format_quiz_question(
    "What is the difference between useState and useReducer?"
)
# Output: "❓ Câu hỏi:\n\nWhat is the difference..."
```

## Example 10: Using HTTPClient for API Calls

```python
from app.utils.http_client import HTTPClient

client = HTTPClient(base_url="http://localhost:8000")

# Call quiz start endpoint
result = await client.post(
    "/api/quiz/start",
    {
        "user_id": 1,
        "lesson_id": 5,
        "user_checkin": "I learned about useState"
    }
)

if result:
    session_id = result["session_id"]
    first_question = result["first_question"]
    # Use in handler
else:
    # Handle error
    pass

# Call progress endpoint
progress = await client.get("/api/progress/user/1")

if progress:
    # Use progress data
    msg = handler_service.format_progress_message(progress)
```

## Example 11: State-Based Message Routing

```python
# Full implementation would track user state:

async def handle_message(self, update: ParsedUpdate) -> None:
    db = SessionLocal()
    try:
        # Look up user
        user = db.query(User).filter(
            User.telegram_id == update.user_id
        ).first()
        if not user:
            await self.service.send_message(
                update.user_id,
                "❌ Người dùng không tìm thấy. Hãy sử dụng /start"
            )
            return

        # Get user's current state
        onboarding_state = db.query(OnboardingState).filter(
            OnboardingState.user_id == user.user_id
        ).first()

        if onboarding_state:
            # Route to onboarding handler
            await self.handle_onboarding_input(update, user, onboarding_state)

        else:
            # Check for active quiz session
            active_quiz = db.query(QuizSession).filter(
                QuizSession.user_id == user.user_id,
                QuizSession.status == "active"
            ).first()

            if active_quiz:
                # Route to quiz answer handler
                await self.handle_answer(update, active_quiz.session_id)
            else:
                # Send instruction message
                await self.service.send_message(
                    update.user_id,
                    "Use /progress, /review, or /done"
                )
    finally:
        db.close()
```

## Example 12: Database Transaction Handling

```python
async def handle_complex_operation(self, update: ParsedUpdate) -> None:
    db = SessionLocal()
    try:
        # Multiple database operations
        user = db.query(User).filter(
            User.telegram_id == update.user_id
        ).first()

        if user:
            # Get progress
            progress = ProgressService.get_user_progress(user.user_id, db)

            # Get summaries
            summaries = ProgressService.get_quiz_summaries(user.user_id, db)

            # Format combined message
            msg = (
                handler_service.format_progress_message(progress) +
                "\n\n" +
                handler_service.format_quiz_summaries(summaries)
            )

            await self.service.send_message(update.user_id, msg)

            # db.commit() happens automatically on successful completion
    finally:
        db.close()
```

## Testing Handlers

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_handle_start():
    # Mock services
    mock_telegram_service = MagicMock()
    mock_telegram_service.send_message = AsyncMock()

    mock_onboarding = MagicMock()
    mock_user = MagicMock(user_id=1, username="user_123456789")
    mock_onboarding.create_user.return_value = mock_user

    # Create handlers
    handlers = TelegramHandlers(
        telegram_service=mock_telegram_service,
        onboarding_service=mock_onboarding
    )

    # Test
    update = ParsedUpdate("123456789", "/start", "message")
    await handlers.handle_update(update)

    # Assert
    mock_onboarding.create_user.assert_called_once()
    mock_telegram_service.send_message.assert_called_once()
```

## Key Takeaways

1. **Handlers are Thin**: They route to services, format responses, and send messages
2. **Services Do Work**: Business logic lives in service classes
3. **HandlerService Formats**: All formatting happens in HandlerService
4. **Error Handling is Consistent**: Three-level error handling in all handlers
5. **Database Sessions Managed**: Proper cleanup with try/finally blocks
6. **Async Throughout**: All handlers and services are async
7. **Logging is Comprehensive**: Debug at every step
8. **Type Hints**: All parameters and returns are type-hinted
