# Telegram Bot Integration Guide

**Status:** Webhook infrastructure and routing complete. Ready for service layer integration.

---

## Overview

The Telegram integration provides a webhook-based bot interface for the Evening Learning system. It consists of three main components:

### Components Created

1. **`app/services/telegram_service.py`** — Service layer for Telegram API communication
2. **`app/routers/telegram.py`** — Webhook endpoint and request routing
3. **`app/routers/telegram_handlers.py`** — Command handlers and message dispatchers
4. **`app/main.py`** — Updated to include Telegram router

---

## Architecture

```
Telegram Server
      ↓
POST /webhook/telegram (FastAPI endpoint)
      ↓
telegram.py: telegram_webhook()
      ↓
TelegramService.parse_update() — Extract user_id, message_text
      ↓
TelegramHandlers.handle_update() — Route to appropriate handler
      ↓
Handler functions (start, done, progress, resume, review)
      ↓
TelegramService.send_message() — Send response back to user
      ↓
200 OK response to Telegram (immediately)
```

---

## File Descriptions

### 1. `app/services/telegram_service.py`

**Purpose:** Manages all Telegram API communication via aiogram 3.x Bot client.

**Key Classes:**

- **`TelegramService`** — Main service class
  - `__init__(bot_token: str)` — Initialize with bot token
  - `send_message(user_id: str, text: str)` — Send text message
  - `send_message_with_buttons(user_id: str, text: str, buttons: List[InlineButton])` — Send message with inline buttons
  - `parse_update(update_dict: Dict[str, Any])` — Parse Telegram update
  - `close()` — Clean up resources

- **`InlineButton`** — Data class representing a button
  - `text: str` — Button display text
  - `callback_data: str` — Data sent when button pressed

- **`ParsedUpdate`** — Standardized update representation
  - `user_id: str` — Telegram user ID
  - `message_text: Optional[str]` — Message or command text
  - `update_type: str` — "message", "callback_query", or "edited_message"
  - `raw_update: Optional[Update]` — Original aiogram Update object

**Update Parsing:**
- Handles message updates (regular text)
- Handles callback_query updates (button presses)
- Handles edited_message updates
- Returns None for unknown update types

**Error Handling:**
- Invalid user_id format → logged, returns False
- API errors → logged with context, returns False
- Invalid token → ValueError on initialization

---

### 2. `app/routers/telegram.py`

**Purpose:** Defines the webhook endpoint and routes updates to handlers.

**Key Endpoints:**

1. **`POST /webhook/telegram`**
   - Receives Telegram updates
   - Parses update and routes to handlers
   - Returns 200 immediately to Telegram
   - Async processing of actual handling (fire-and-forget)
   - **Note:** All handlers will be called asynchronously; responses happen via separate bot.send_message() calls

2. **`GET /health/telegram`**
   - Health check for Telegram service
   - Verifies bot token configuration
   - Returns webhook URL and status

**How Telegram Webhook Works:**
- Telegram sends POST request with JSON update
- We parse and return 200 OK immediately (Telegram times out after 30 seconds)
- Actual message handling happens in background
- Responses sent via `bot.send_message()` API calls

---

### 3. `app/routers/telegram_handlers.py`

**Purpose:** Command handlers and message router.

**Key Class:**

- **`TelegramHandlers`** — Handler dispatcher
  - `handle_update(update: ParsedUpdate)` — Main router
  - `handle_start(update)` — /start command (onboarding)
  - `handle_done(update)` — /done command (learning complete)
  - `handle_progress(update)` — /progress command (show progress)
  - `handle_resume(update)` — /resume command (continue learning)
  - `handle_review(update, full_message)` — /review command (show summaries)
  - `handle_message(update)` — Regular messages (not commands)

**Handler Status:**
- All handlers are placeholders
- Basic logging in place
- Return template responses (hardcoded)
- Ready for integration with actual service logic

**Command Parsing:**
- Extracts command from "/command" or "/command@botname" format
- Case-insensitive
- Handles messages without commands

---

### 4. `app/main.py` (Updated)

**Changes:**
- Import telegram router: `from app.routers import telegram`
- Include router in `include_routers()`: `app.include_router(telegram.router)`
- Log Telegram configuration in startup event

---

## Configuration

### Environment Variables (in `.env`)

```
TELEGRAM_BOT_TOKEN=<your-bot-token-from-botfather>
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
```

### Getting a Bot Token

1. Open Telegram and find @BotFather
2. Send `/newbot`
3. Follow prompts to create bot
4. Copy token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

---

## Usage Examples

### 1. Sending a Simple Message

```python
from app.services.telegram_service import TelegramService

service = TelegramService(token="...")
await service.send_message("123456789", "Hello!")
```

### 2. Sending Message with Buttons

```python
from app.services.telegram_service import TelegramService, InlineButton

service = TelegramService(token="...")
buttons = [
    InlineButton("Yes", "q_1_yes"),
    InlineButton("No", "q_1_no"),
]
await service.send_message_with_buttons(
    "123456789",
    "Do you agree?",
    buttons,
    rows=2
)
```

### 3. Handling an Update in Your Service

```python
from app.routers.telegram_handlers import TelegramHandlers
from app.services.telegram_service import TelegramService

service = TelegramService(token="...")
handlers = TelegramHandlers(service)

# When update arrives:
parsed = service.parse_update(update_dict)
if parsed:
    await handlers.handle_update(parsed)
```

---

## Integration Checklist

To complete the Telegram integration, implement the following in service layer:

### Phase 1: Onboarding Service
- [ ] Implement actual `/start` flow (currently placeholder)
- [ ] Course URL parsing (Udemy URLs)
- [ ] Assessment questions (binary tree)
- [ ] Curriculum generation
- [ ] Schedule setup

### Phase 2: Learning Service
- [ ] `/done` command → check-in phase
- [ ] Parse user learning summary
- [ ] Schedule quiz session

### Phase 3: Quiz Service
- [ ] Quiz question generation (via Claude API)
- [ ] Handle quiz answers
- [ ] Generate post-quiz summary

### Phase 4: Progress Service
- [ ] `/progress` command → show progress
- [ ] Fetch user's knowledge tracker
- [ ] Format summary for display

### Phase 5: Review Service
- [ ] `/review` command → show summaries
- [ ] Filter by topic
- [ ] Spaced repetition scheduling

---

## Testing

### Test Webhook Locally

```bash
# 1. Start the backend
cd backend
uvicorn app.main:app --reload

# 2. In another terminal, simulate a Telegram update
curl -X POST http://localhost:8000/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456,
    "message": {
      "message_id": 1,
      "from": {"id": 987654, "first_name": "Test"},
      "text": "/start"
    }
  }'

# Expected response: {"ok": true, "message": "Update received"}
```

### Test Service Directly

```python
from app.services.telegram_service import TelegramService

# Create service (will fail without valid token)
try:
    service = TelegramService("invalid-token")
except ValueError as e:
    print(f"Expected error: {e}")

# Parse update
update_dict = {
    "update_id": 123456,
    "message": {
        "message_id": 1,
        "from": {"id": 987654},
        "text": "/start"
    }
}
parsed = service.parse_update(update_dict)
print(f"User ID: {parsed.user_id}, Text: {parsed.message_text}")
# Output: User ID: 987654, Text: /start
```

---

## Error Handling

### Common Issues

1. **"Telegram bot token not configured"**
   - Check TELEGRAM_BOT_TOKEN in .env
   - Verify it's valid from @BotFather

2. **"Failed to send message"**
   - Check internet connectivity
   - Verify user_id format (should be numeric)
   - Check Telegram API status

3. **Webhook not receiving updates**
   - Verify webhook URL is publicly accessible
   - Check that /webhook/telegram endpoint is registered
   - Confirm Telegram has correct webhook URL set

4. **Update parsing fails**
   - Log raw update and compare to expected format
   - Check that user_id is present in update

---

## Logging

All modules use Python logging with INFO and DEBUG levels:

```python
import logging

logger = logging.getLogger(__name__)
logger.info(f"User {user_id} sent message")
logger.debug("Detailed debug info")
logger.error(f"Error occurred: {error}")
```

### Log Locations

- `telegram_service.py`: Bot initialization, API calls, parsing
- `telegram.py`: Webhook receives, routing
- `telegram_handlers.py`: Command handling, dispatching

---

## Next Steps for Other Agents

1. **Onboarding Service** — Implement full onboarding flow
   - Parse course URLs (Udemy, etc.)
   - Run assessment questions
   - Generate personalized curriculum
   - Call TelegramService to send updates

2. **Learning Service** — Implement daily learning tracking
   - Listen for `/done` command via handlers
   - Check-in: ask what user learned
   - Route to Quiz Service

3. **Quiz Service** — Implement oral test and evaluation
   - Generate questions via Claude API
   - Log answers and confidence levels
   - Generate post-quiz summary
   - Use TelegramService to send results

4. **Progress Service** — Implement knowledge tracking
   - Listen for `/progress` command
   - Fetch user's mastered vs. needs-review concepts
   - Format and send summary

5. **Review Service** — Implement spaced repetition
   - Listen for `/review` command
   - Fetch past quiz summaries
   - Schedule review questions

---

## Key Design Decisions

1. **Webhook (not polling):** Telegram initiates connection; we respond immediately
2. **Service layer separation:** TelegramService handles API, TelegramHandlers routes
3. **Async throughout:** All I/O is non-blocking using asyncio
4. **Stateless handlers:** State stored in database, not in bot code
5. **Logging over raising:** Most errors are logged; returns False/None gracefully
6. **Type hints:** Full type coverage for IDE support and documentation

---

## Resources

- **Aiogram 3.x Docs:** https://docs.aiogram.dev/
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **FastAPI WebHooks:** https://fastapi.tiangolo.com/advanced/behind-a-proxy/
