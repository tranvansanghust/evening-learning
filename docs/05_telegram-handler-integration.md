# Telegram Handler Integration Guide

## Quick Reference for Quiz & Learning Endpoints

This guide shows how to integrate the Quiz Service and Learning endpoints into Telegram handlers.

---

## HTTP Client Setup

```python
import aiohttp
import json
from typing import Optional, Dict, Any

class LearningAPIClient:
    """HTTP client for Learning and Quiz endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    # Learning endpoints
    async def start_learning(self, user_id: int, lesson_id: int, track: str):
        """POST /api/learn/start"""
        url = f"{self.base_url}/api/learn/start"
        data = {"user_id": user_id, "lesson_id": lesson_id, "track": track}
        async with self.session.post(url, json=data) as resp:
            return await resp.json()

    async def done_learning(self, user_id: int, lesson_id: int,
                          user_checkin: Optional[str] = None):
        """POST /api/learn/done"""
        url = f"{self.base_url}/api/learn/done"
        data = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "user_checkin": user_checkin
        }
        async with self.session.post(url, json=data) as resp:
            return await resp.json()

    async def get_learning_status(self, user_id: int):
        """GET /api/learn/status/{user_id}"""
        url = f"{self.base_url}/api/learn/status/{user_id}"
        async with self.session.get(url) as resp:
            return await resp.json()

    # Quiz endpoints
    async def start_quiz(self, user_id: int, lesson_id: int,
                        user_checkin: Optional[str] = None):
        """POST /api/quiz/start"""
        url = f"{self.base_url}/api/quiz/start"
        data = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "user_checkin": user_checkin
        }
        async with self.session.post(url, json=data) as resp:
            return await resp.json()

    async def submit_answer(self, session_id: int, user_answer: str):
        """POST /api/quiz/answer"""
        url = f"{self.base_url}/api/quiz/answer"
        data = {"session_id": session_id, "user_answer": user_answer}
        async with self.session.post(url, json=data) as resp:
            return await resp.json()

    async def get_quiz_status(self, session_id: int):
        """GET /api/quiz/status/{session_id}"""
        url = f"{self.base_url}/api/quiz/status/{session_id}"
        async with self.session.get(url) as resp:
            return await resp.json()

    async def get_quiz_summary(self, session_id: int):
        """GET /api/quiz/summary/{session_id}"""
        url = f"{self.base_url}/api/quiz/summary/{session_id}"
        async with self.session.get(url) as resp:
            return await resp.json()
```

---

## Handler Examples

### Example 1: Track B (Internal Content Learning)

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def handle_start_learning_track_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User pressed 'Start Learning' button for Track B (internal content).

    Flow:
    1. Validate user and lesson
    2. Start learning session (Track B)
    3. Send content URL to user
    4. Wait for /done command
    """
    user_id = update.effective_user.id
    lesson_id = context.user_data.get("lesson_id")

    # Call API to start learning
    async with LearningAPIClient() as client:
        result = await client.start_learning(
            user_id=user_id,
            lesson_id=lesson_id,
            track="B"
        )

    if not result.get("success"):
        await update.message.reply_text("❌ Failed to start learning")
        return

    lesson_name = result["lesson_name"]
    content_url = result["content_url"]
    estimated_duration = result["estimated_duration"]

    # Send lesson to user
    message = f"""
📖 *{lesson_name}*

⏱️ Estimated: {estimated_duration} minutes

[Read Lesson]({content_url})

When you're done reading, click *Done Learning ✅* to start the quiz.
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Done Learning ✅", callback_data="done_learning")]
    ])

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    # Store in context for later use
    context.user_data["learning_session"] = {
        "lesson_id": lesson_id,
        "lesson_name": lesson_name,
        "track": "B"
    }


async def handle_done_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User finished learning and ready for quiz.

    Flow:
    1. Mark learning as done
    2. Initialize quiz session
    3. Send first question
    """
    user_id = update.effective_user.id
    lesson_id = context.user_data["learning_session"]["lesson_id"]

    # Call API to finish learning and start quiz
    async with LearningAPIClient() as client:
        result = await client.done_learning(
            user_id=user_id,
            lesson_id=lesson_id,
            user_checkin=None  # Track B doesn't need check-in
        )

    if not result.get("success"):
        await update.message.reply_text("❌ Failed to start quiz")
        return

    session_id = result["session_id"]
    first_question = result["first_question"]

    # Store quiz session ID for answer handling
    context.user_data["quiz_session_id"] = session_id

    # Send first question
    message = f"""
🎯 *Let's test your understanding!*

{first_question}

Please type your answer below.
"""

    await update.message.reply_text(message, parse_mode="Markdown")


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User submitted an answer to a quiz question.

    Flow:
    1. Submit answer to API
    2. Get evaluation and next action
    3. If continue/followup: send next question
    4. If end: send summary prompt
    """
    user_id = update.effective_user.id
    session_id = context.user_data.get("quiz_session_id")
    user_answer = update.message.text

    if not session_id:
        await update.message.reply_text("❌ No active quiz session")
        return

    # Submit answer
    async with LearningAPIClient() as client:
        result = await client.submit_answer(
            session_id=session_id,
            user_answer=user_answer
        )

    if not result.get("success"):
        await update.message.reply_text("❌ Failed to process answer")
        return

    evaluation = result["evaluation"]
    feedback = evaluation["feedback"]
    next_action = result["next_action"]
    question_count = result["question_count"]

    # Build response message
    message = f"💬 *Feedback:*\n{feedback}\n\n"

    if evaluation["is_correct"]:
        message += "✅ *Correct!*\n"
    else:
        message += "⚠️ *Not quite right, but let's move on.*\n"

    message += f"📊 Engagement: {evaluation['engagement_level'].upper()}\n\n"

    # Handle next action
    if next_action == "end":
        message += "🎉 *Quiz Complete!*\n\n"
        message += f"You answered {question_count} questions. Let's see your summary!"

        await update.message.reply_text(message, parse_mode="Markdown")

        # Send summary
        await send_quiz_summary(update, context, session_id)

    else:  # continue or followup
        next_question = result.get("next_question")

        if next_action == "followup":
            message += "📌 *Follow-up question:*\n"
        else:
            message += f"📌 *Question {question_count + 1}:*\n"

        message += f"{next_question}"

        await update.message.reply_text(message, parse_mode="Markdown")


async def send_quiz_summary(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           session_id: int):
    """
    Retrieve and send the quiz summary to the user.
    """
    async with LearningAPIClient() as client:
        result = await client.get_quiz_summary(session_id=session_id)

    if not result.get("success"):
        await update.message.reply_text("❌ Failed to generate summary")
        return

    mastered = result["concepts_mastered"]
    weak = result["concepts_weak"]
    suggestions = result["suggestions"]
    summary_text = result["summary_text"]

    # Build summary message
    message = "📝 *Quiz Summary*\n\n"

    if mastered:
        message += f"✅ *Mastered Concepts:*\n"
        for concept in mastered:
            message += f"  • {concept}\n"
        message += "\n"

    if weak:
        message += f"⚠️ *Concepts to Review:*\n"
        for item in weak:
            message += f"  • *{item['concept']}*\n"
            message += f"    Your answer: {item['user_answer']}\n"
            message += f"    Correct: {item['correct_explanation']}\n\n"

    message += f"📊 *Performance:*\n{summary_text}\n\n"

    if suggestions:
        message += f"💡 *Next Steps:*\n"
        for suggestion in suggestions:
            message += f"  • {suggestion}\n"

    await update.message.reply_text(message, parse_mode="Markdown")
```

---

### Example 2: Track A (External Learning with Check-in)

```python
async def handle_start_learning_track_a(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User wants to learn from external source (Udemy, etc).

    Flow:
    1. Start learning session (Track A)
    2. Instruct user where to learn
    3. Wait for /done command with check-in
    """
    user_id = update.effective_user.id
    lesson_id = context.user_data.get("lesson_id")
    lesson_name = context.user_data.get("lesson_name")

    # Call API to start learning
    async with LearningAPIClient() as client:
        result = await client.start_learning(
            user_id=user_id,
            lesson_id=lesson_id,
            track="A"
        )

    if not result.get("success"):
        await update.message.reply_text("❌ Failed to start learning")
        return

    message = f"""
📚 *{lesson_name}*

🎓 Learning from External Source

Please go to Udemy/course website and complete the assigned section.

When you're done, come back and tell me what you learned!

Type /done and then share what you learned (this helps me ask better questions 😊)

Example: "I learned about useState and useEffect. I understand useState but useEffect hooks still confuse me."
"""

    await update.message.reply_text(message, parse_mode="Markdown")

    # Store context
    context.user_data["learning_session"] = {
        "lesson_id": lesson_id,
        "lesson_name": lesson_name,
        "track": "A"
    }


async def handle_done_learning_track_a(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User finished external learning and provides check-in.

    Flow:
    1. Collect user check-in message
    2. Send to API with check-in
    3. Initialize quiz with check-in context
    """
    user_id = update.effective_user.id
    lesson_id = context.user_data["learning_session"]["lesson_id"]

    # Get check-in message (next message after /done)
    # In real implementation, you'd use conversation state to collect this

    await update.message.reply_text(
        "Great! Now tell me what you learned. Share what concepts you covered: 👇"
    )

    # Set state to collect check-in
    context.user_data["waiting_for_checkin"] = True


async def handle_checkin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Received user's check-in message about what they learned.
    """
    if not context.user_data.get("waiting_for_checkin"):
        return

    user_id = update.effective_user.id
    lesson_id = context.user_data["learning_session"]["lesson_id"]
    user_checkin = update.message.text

    # Call API with check-in
    async with LearningAPIClient() as client:
        result = await client.done_learning(
            user_id=user_id,
            lesson_id=lesson_id,
            user_checkin=user_checkin  # Track A uses this!
        )

    if not result.get("success"):
        await update.message.reply_text("❌ Failed to start quiz")
        return

    session_id = result["session_id"]
    first_question = result["first_question"]

    context.user_data["quiz_session_id"] = session_id
    context.user_data["waiting_for_checkin"] = False

    message = f"""
🎯 *Perfect! Now let's see what you understand.*

{first_question}

Type your answer below:
"""

    await update.message.reply_text(message, parse_mode="Markdown")
```

---

## Handler Registration

```python
# In your main handlers setup (telegram_handlers.py or main telegram router)

from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)

def setup_learning_handlers(application: Application):
    """Register all learning and quiz handlers."""

    # Learning flow
    application.add_handler(
        CallbackQueryHandler(
            handle_start_learning_track_b,
            pattern="^start_learn_b$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            handle_start_learning_track_a,
            pattern="^start_learn_a$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            handle_done_learning,
            pattern="^done_learning$"
        )
    )

    # Quiz flow - answer messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND &
            filters.Regex(r".*"),  # Any text message
            handle_quiz_answer
        )
    )

    logger.info("Learning and quiz handlers registered")
```

---

## State Management

Store quiz session IDs in `context.user_data`:

```python
# Starting quiz
context.user_data["quiz_session_id"] = session_id
context.user_data["learning_session"] = {
    "lesson_id": lesson_id,
    "lesson_name": lesson_name,
    "track": "A" or "B"
}
context.user_data["waiting_for_checkin"] = True/False

# Clean up after quiz completes
del context.user_data["quiz_session_id"]
del context.user_data["learning_session"]
```

---

## Error Handling Strategy

```python
async def api_call_with_retry(api_func, *args, max_retries=3, **kwargs):
    """Retry logic for API calls."""
    for attempt in range(max_retries):
        try:
            return await api_func(*args, **kwargs)
        except aiohttp.ClientError as e:
            logger.error(f"API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)  # Wait before retry


async def handle_quiz_answer_with_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quiz answer handler with retry logic."""
    try:
        async with LearningAPIClient() as client:
            result = await api_call_with_retry(
                client.submit_answer,
                session_id=context.user_data["quiz_session_id"],
                user_answer=update.message.text
            )

    except Exception as e:
        logger.error(f"Failed to submit answer: {e}")
        await update.message.reply_text(
            "⚠️ Temporary error processing your answer. Please try again."
        )
        return

    # Continue with normal flow...
```

---

## Complete Minimal Example

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
import aiohttp

class QuizBot:
    def __init__(self, token: str, api_base_url: str):
        self.token = token
        self.api_base_url = api_base_url

    async def start_quiz_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick start quiz flow."""
        user_id = update.effective_user.id
        lesson_id = 5  # Example lesson

        # Start quiz
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base_url}/api/quiz/start",
                json={"user_id": user_id, "lesson_id": lesson_id, "user_checkin": None}
            ) as resp:
                result = await resp.json()

        if result.get("success"):
            context.user_data["quiz_session_id"] = result["session_id"]
            await update.message.reply_text(f"Q: {result['first_question']}")
        else:
            await update.message.reply_text("Failed to start quiz")

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle any message as a quiz answer."""
        session_id = context.user_data.get("quiz_session_id")
        if not session_id:
            return

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base_url}/api/quiz/answer",
                json={"session_id": session_id, "user_answer": update.message.text}
            ) as resp:
                result = await resp.json()

        if result["next_action"] == "end":
            await update.message.reply_text("🎉 Quiz complete!")
        else:
            await update.message.reply_text(f"Q: {result['next_question']}")

    def run(self):
        """Run the bot."""
        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start_quiz_flow))
        app.add_handler(CommandHandler("answer", self.handle_answer))
        app.run_polling()


if __name__ == "__main__":
    bot = QuizBot(
        token="YOUR_TOKEN",
        api_base_url="http://localhost:8000"
    )
    bot.run()
```

---

## Common Patterns

### Pattern 1: Quiz Loop

```python
while True:
    # User sends answer
    answer_result = await client.submit_answer(session_id, answer)

    # Check next action
    if answer_result["next_action"] == "end":
        summary = await client.get_quiz_summary(session_id)
        send_summary(summary)
        break
    else:
        next_question = answer_result["next_question"]
        send_question(next_question)
```

### Pattern 2: Two-Track Learning

```python
# Ask user which track
keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📚 External (Udemy)", callback_data="track_a")],
    [InlineKeyboardButton("📖 Built-in Content", callback_data="track_b")]
])

await update.message.reply_text("How do you want to learn?", reply_markup=keyboard)

# Then route to appropriate handler based on selection
```

### Pattern 3: Session Recovery

```python
# Check if user has active quiz session
status = await client.get_quiz_status(session_id)

if status["status"] == "active":
    await update.message.reply_text(
        f"You have an active quiz with {status['question_count']} questions asked. "
        f"Let's continue!"
    )
else:
    await update.message.reply_text("No active quiz found. Start a new one?")
```

---

## Testing the Integration

```bash
# Start backend server
cd backend
uvicorn app.main:app --reload

# In another terminal, test with curl
curl -X POST http://localhost:8000/api/quiz/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "lesson_id": 5,
    "user_checkin": null
  }'

# Should return:
# {
#   "success": true,
#   "session_id": 42,
#   "first_question": "..."
# }
```

---

This guide provides everything needed to integrate the Quiz Service and Learning endpoints into Telegram handlers!
