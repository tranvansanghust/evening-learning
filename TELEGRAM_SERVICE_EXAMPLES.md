# Telegram Service Integration Examples

This document shows how to use the TelegramService and TelegramHandlers in your service layer code.

---

## Basic Usage

### 1. Initialize Service

```python
from app.services.telegram_service import TelegramService
from app.config import settings

# Create service (typically done once at startup)
service = TelegramService(settings.telegram_bot_token)

# Use service
await service.send_message("123456789", "Hello!")
```

### 2. Send Simple Text Message

```python
await service.send_message(
    user_id="123456789",
    text="Welcome to Evening Learning! 👋"
)
```

### 3. Send Message with Buttons

```python
from app.services.telegram_service import InlineButton

buttons = [
    InlineButton("Yes", "q1_yes"),
    InlineButton("No", "q1_no"),
]

await service.send_message_with_buttons(
    user_id="123456789",
    text="Have you built a web app before?",
    buttons=buttons,
    rows=2  # 2 buttons per row
)
```

### 4. Parse Incoming Update

```python
# Assuming you receive update from webhook as dict
update_dict = {
    "update_id": 123456,
    "message": {
        "message_id": 1,
        "from": {"id": 987654},
        "text": "/done"
    }
}

parsed = service.parse_update(update_dict)
if parsed:
    print(f"User: {parsed.user_id}, Text: {parsed.message_text}")
    # User: 987654, Text: /done
```

---

## Integration with Service Layer

### Example 1: Onboarding Service

```python
from app.services.telegram_service import TelegramService, InlineButton
from app.routers.telegram_handlers import TelegramHandlers

class OnboardingService:
    def __init__(self, telegram_service: TelegramService):
        self.telegram = telegram_service

    async def start_onboarding(self, user_id: str) -> None:
        """Initiate user onboarding."""
        message = (
            "Chào bạn! Mình là học bạn AI 👋\n\n"
            "Bạn đang muốn học gì?\n"
            "(paste link Udemy hoặc gõ tên chủ đề)"
        )
        await self.telegram.send_message(user_id, message)

    async def ask_assessment(self, user_id: str) -> None:
        """Ask first assessment question."""
        buttons = [
            InlineButton("Chưa bao giờ", "q1_no"),
            InlineButton("Rồi", "q1_yes"),
        ]
        await self.telegram.send_message_with_buttons(
            user_id,
            "Bạn đã tự build một web app bằng JavaScript chưa?",
            buttons
        )

    async def ask_deadline(self, user_id: str) -> None:
        """Ask course deadline."""
        buttons = [
            InlineButton("1 tháng", "deadline_1"),
            InlineButton("2 tháng", "deadline_2"),
            InlineButton("3 tháng", "deadline_3"),
        ]
        await self.telegram.send_message_with_buttons(
            user_id,
            "Bạn muốn hoàn thành khoá học khi nào?",
            buttons,
            rows=1
        )
```

### Example 2: Learning Session Service

```python
from app.services.telegram_service import TelegramService, InlineButton
from datetime import datetime

class LearningSessionService:
    def __init__(self, telegram_service: TelegramService):
        self.telegram = telegram_service

    async def start_session(self, user_id: str, lesson_name: str) -> None:
        """Send daily lesson reminder."""
        message = (
            f"🔔 Đến giờ học rồi!\n\n"
            f"Hôm nay: {lesson_name}\n"
            f"Dự kiến: ~45 phút"
        )
        buttons = [
            InlineButton("Bắt đầu học 🚀", "session_start"),
            InlineButton("Hôm nay bận ⏭", "session_skip"),
        ]
        await self.telegram.send_message_with_buttons(
            user_id, message, buttons, rows=1
        )

    async def send_check_in(self, user_id: str) -> None:
        """Ask what user learned."""
        message = (
            "Tốt lắm! 🎉\n\n"
            "Hôm nay bạn học đến đâu rồi?\n"
            "Kể mình nghe bạn tiếp thu được gì nào!"
        )
        await self.telegram.send_message(user_id, message)

    async def confirm_learning_complete(
        self,
        user_id: str,
        lesson_name: str,
        study_duration: int
    ) -> None:
        """Confirm learning session complete."""
        message = (
            f"🎉 Bạn vừa hoàn thành\n"
            f"\"{lesson_name}\"!\n\n"
            f"Thời gian: {study_duration} phút\n\n"
            f"Cùng nhìn lại xem bạn đã nắm được "
            f"những gì trong bài học này nhé 💡"
        )
        buttons = [
            InlineButton("Bắt đầu kiểm tra 🚀", "quiz_start"),
        ]
        await self.telegram.send_message_with_buttons(
            user_id, message, buttons, rows=1
        )
```

### Example 3: Quiz Service

```python
from app.services.telegram_service import TelegramService

class QuizService:
    def __init__(self, telegram_service: TelegramService):
        self.telegram = telegram_service

    async def send_quiz_question(
        self,
        user_id: str,
        question: str,
        question_number: int,
        total_questions: int
    ) -> None:
        """Send a quiz question."""
        message = (
            f"Câu {question_number}/{total_questions}\n\n"
            f"{question}"
        )
        await self.telegram.send_message(user_id, message)

    async def acknowledge_answer(
        self,
        user_id: str,
        is_correct: bool
    ) -> None:
        """Acknowledge quiz answer."""
        if is_correct:
            message = (
                "✅ Giải thích hay đấy!\n\n"
                "Mình ghi nhận rồi nhé."
            )
        else:
            message = (
                "⏸ Mình ghi nhận rồi nhé.\n\n"
                "Sẽ hỏi lại phần này sau để chắc chắn "
                "bạn nắm chắc hơn."
            )
        await self.telegram.send_message(user_id, message)

    async def send_quiz_summary(
        self,
        user_id: str,
        lesson_name: str,
        mastered_concepts: list,
        needs_review_concepts: list
    ) -> None:
        """Send post-quiz summary."""
        summary = f"📝 Tóm tắt buổi học — {lesson_name}\n\n"

        if mastered_concepts:
            summary += "✅ Nắm chắc:\n"
            for concept in mastered_concepts:
                summary += f"• {concept}\n"
            summary += "\n"

        if needs_review_concepts:
            summary += "⚠️ Cần ôn lại:\n"
            for concept in needs_review_concepts:
                summary += f"• {concept}\n"
            summary += "\n"

        summary += "🔁 Mình sẽ hỏi lại sau 3 ngày nhé!"

        await self.telegram.send_message(user_id, summary)
```

### Example 4: Progress Tracking Service

```python
from app.services.telegram_service import TelegramService

class ProgressService:
    def __init__(self, telegram_service: TelegramService):
        self.telegram = telegram_service

    async def send_progress_report(
        self,
        user_id: str,
        course_name: str,
        level: str,
        retention_rate: float,
        mastered_count: int,
        review_count: int
    ) -> None:
        """Send comprehensive progress report."""
        message = (
            f"📊 Tiến độ học tập\n\n"
            f"📚 Khoá học: {course_name}\n"
            f"🎯 Trình độ: {level}\n"
            f"💪 Retention: {retention_rate:.1%}\n\n"
            f"✅ Đã nắm: {mastered_count} concepts\n"
            f"⚠️ Cần ôn: {review_count} concepts"
        )
        await self.telegram.send_message(user_id, message)

    async def send_reminder_to_review(
        self,
        user_id: str,
        concept: str,
        last_review_days: int
    ) -> None:
        """Remind user to review a concept."""
        message = (
            f"🔄 Đã {last_review_days} ngày không ôn lại:\n"
            f"\"{concept}\"\n\n"
            f"Cùng ôn lại nhé! 💪"
        )
        buttons = [
            InlineButton("Bắt đầu ôn", "review_start"),
        ]
        await self.telegram.send_message_with_buttons(
            user_id, message, buttons, rows=1
        )
```

---

## Handling Callback Queries (Button Presses)

When user presses a button, Telegram sends a `callback_query` update:

```python
# In telegram.py webhook handler:
parsed = service.parse_update(update_dict)

# For button presses:
if parsed.update_type == "callback_query":
    callback_data = parsed.message_text  # e.g., "q1_yes"

    # Route based on callback_data
    if callback_data == "q1_yes":
        await onboarding_service.handle_q1_yes(parsed.user_id)
    elif callback_data == "q1_no":
        await onboarding_service.handle_q1_no(parsed.user_id)
```

---

## HTML Formatting in Messages

TelegramService supports HTML formatting:

```python
# Bold, italic, links, etc.
message = (
    "<b>Welcome!</b>\n\n"
    "Visit <a href='https://example.com'>our site</a>\n"
    "<i>Excited to learn with you!</i>"
)
await service.send_message(user_id, message)
```

Supported HTML tags:
- `<b>bold</b>`
- `<strong>bold</strong>`
- `<i>italic</i>`
- `<em>italic</em>`
- `<u>underline</u>`
- `<s>strikethrough</s>`
- `<code>monospace</code>`
- `<pre>code block</pre>`
- `<a href="URL">link</a>`

---

## Error Handling Examples

```python
# Check if message sent successfully
success = await service.send_message(user_id, "Hello")
if not success:
    logger.error(f"Failed to send message to {user_id}")
    # Retry logic, save to queue, etc.

# Parse might return None
parsed = service.parse_update(update_dict)
if parsed is None:
    logger.warning("Could not parse update")
    return  # Skip this update

# Try/except for async operations
try:
    await service.send_message(user_id, text)
except Exception as e:
    logger.error(f"Telegram error: {e}")
```

---

## Full Integration Example

Here's a complete example showing how it all fits together:

```python
# In your service layer
from app.services.telegram_service import TelegramService, InlineButton
from app.config import settings

class MyLearningService:
    def __init__(self):
        self.telegram = TelegramService(settings.telegram_bot_token)

    async def handle_user_message(self, update_dict: dict) -> None:
        """Main handler for incoming Telegram updates."""
        # Parse update
        parsed = self.telegram.parse_update(update_dict)
        if not parsed:
            return

        user_id = parsed.user_id
        text = parsed.message_text or ""

        # Handle different commands
        if text == "/start":
            await self.handle_start(user_id)
        elif text == "/done":
            await self.handle_done(user_id)
        elif text == "/progress":
            await self.handle_progress(user_id)
        elif parsed.update_type == "callback_query":
            await self.handle_button_press(user_id, text)
        else:
            await self.handle_regular_message(user_id, text)

    async def handle_start(self, user_id: str) -> None:
        """Start onboarding."""
        await self.telegram.send_message(
            user_id,
            "Chào bạn! Bạn muốn học gì?"
        )

    async def handle_done(self, user_id: str) -> None:
        """User finished learning."""
        await self.telegram.send_message(
            user_id,
            "Tốt lắm! Bạn học được gì trong hôm nay?"
        )

    async def handle_progress(self, user_id: str) -> None:
        """Show progress."""
        buttons = [
            InlineButton("Overall", "prog_all"),
            InlineButton("This Week", "prog_week"),
        ]
        await self.telegram.send_message_with_buttons(
            user_id,
            "Which progress view?",
            buttons
        )

    async def handle_button_press(self, user_id: str, data: str) -> None:
        """Handle button presses."""
        if data == "prog_all":
            # Fetch overall progress
            # Send comprehensive report
            pass
        elif data == "prog_week":
            # Fetch weekly progress
            # Send weekly report
            pass

    async def handle_regular_message(self, user_id: str, text: str) -> None:
        """Handle regular messages (not commands)."""
        # Check user state
        # Route to appropriate handler based on state
        pass
```

---

## Testing Your Integration

```python
# Unit test example
import pytest
from app.services.telegram_service import TelegramService

@pytest.mark.asyncio
async def test_send_message():
    service = TelegramService("fake-token")

    # Mock the bot
    from unittest.mock import AsyncMock
    service.bot.send_message = AsyncMock()

    # Call method
    result = await service.send_message("123", "Hello")

    # Verify
    assert result == True
    service.bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_parse_update():
    service = TelegramService("fake-token")

    update = {
        "update_id": 1,
        "message": {
            "from": {"id": 123},
            "text": "/start"
        }
    }

    parsed = service.parse_update(update)
    assert parsed.user_id == "123"
    assert parsed.message_text == "/start"
```

---

## Next Steps

Now that the infrastructure is in place:

1. **Implement OnboardingService** — Use examples above
2. **Implement LearningSessionService** — Track daily learning
3. **Implement QuizService** — Generate and score quizzes
4. **Implement ProgressService** — Show knowledge tracking
5. **Add database layer** — Store user state and progress
6. **Connect to Claude API** — Generate quiz questions and summaries
