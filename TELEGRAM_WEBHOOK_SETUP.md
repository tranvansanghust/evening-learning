# Telegram Webhook Setup Instructions

This guide explains how to set up the Telegram webhook so the bot receives updates from Telegram's servers.

---

## Prerequisites

1. **Telegram Bot Token** — From @BotFather on Telegram
   - Command: `/newbot`
   - Save the token: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

2. **Public HTTPS URL** — Where Telegram will send updates
   - Must be HTTPS (not HTTP)
   - Must have valid SSL certificate
   - Example: `https://api.myapp.com/webhook/telegram`

3. **Backend Running** — FastAPI app available at that URL
   - The `/webhook/telegram` endpoint must be accessible

---

## Setting Up the Webhook

### Option 1: Using Telegram Bot API Directly (curl)

```bash
# Replace with your actual values
BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
WEBHOOK_URL="https://api.myapp.com/webhook/telegram"

# Set webhook
curl -X POST https://api.telegram.org/bot${BOT_TOKEN}/setWebhook \
  -d "url=${WEBHOOK_URL}" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Response should be:
# {"ok":true,"result":true,"description":"Webhook was set"}
```

### Option 2: Using Python Script

```python
import requests

BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
WEBHOOK_URL = "https://api.myapp.com/webhook/telegram"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
response = requests.post(url, json={"url": WEBHOOK_URL})

print(response.json())
# Should print: {'ok': True, 'result': True, 'description': 'Webhook was set'}
```

### Option 3: Using FastAPI Client

```python
from app.config import settings
import httpx

async def set_telegram_webhook():
    bot_token = settings.telegram_bot_token
    webhook_url = settings.telegram_webhook_url

    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json={"url": webhook_url})
        print(response.json())
```

---

## Verifying the Webhook

### Check Current Webhook Status

```bash
BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

curl https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo
```

Expected response:
```json
{
  "ok": true,
  "result": {
    "url": "https://api.myapp.com/webhook/telegram",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "ip_address": "1.2.3.4",
    "last_error_date": null,
    "last_error_message": null
  }
}
```

### Remove Webhook (if needed)

```bash
BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

curl -X POST https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook
```

---

## Testing the Webhook

### Test 1: Send Message to Bot

1. Find your bot in Telegram (search for its @username)
2. Send message: `/start`
3. Check backend logs for:
   ```
   INFO: Parsed message update from user 123456789
   INFO: Handling update from user 123456789: type=message, text=/start
   ```

### Test 2: Simulate Webhook Request (curl)

```bash
curl -X POST http://localhost:8000/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "date": 1234567890,
      "chat": {"id": 987654321},
      "from": {
        "id": 987654321,
        "is_bot": false,
        "first_name": "John"
      },
      "text": "/start"
    }
  }'

# Expected response:
# {"ok":true,"message":"Update received"}
```

### Test 3: Check Health Endpoint

```bash
curl http://localhost:8000/health/telegram

# Expected response:
# {
#   "status": "healthy",
#   "service": "telegram-webhook",
#   "bot_token_configured": true,
#   "webhook_url": "https://api.myapp.com/webhook/telegram"
# }
```

---

## Environment Configuration

Add these to `.env` file:

```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_WEBHOOK_URL=https://api.myapp.com/webhook/telegram
```

The webhook URL should:
- Be publicly accessible (test with `curl https://api.myapp.com/webhook/telegram`)
- Support POST requests
- Return 200 status code
- Respond within 30 seconds

---

## Troubleshooting

### Webhook Not Receiving Updates

**Check 1: Is webhook URL correct?**
```bash
curl https://api.myapp.com/webhook/telegram
# Should return 405 (Method Not Allowed) for GET, not 404
```

**Check 2: Is SSL certificate valid?**
- Telegram requires valid HTTPS with recognized certificate
- Self-signed certificates won't work
- Use Let's Encrypt (free) or paid certificate

**Check 3: Check webhook info for errors**
```bash
curl https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo

# If last_error_message is set, it means:
# - Connection failed (check URL accessibility)
# - Server returned non-200 status
# - Server timed out (>30 seconds)
```

**Check 4: Are pending updates stuck?**
```bash
# Clear pending updates
curl -X POST https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook \
  -d "drop_pending_updates=true"

# Then set webhook again
curl -X POST https://api.telegram.org/bot${BOT_TOKEN}/setWebhook \
  -d "url=https://api.myapp.com/webhook/telegram"
```

### 502 Bad Gateway Error

This means:
- Backend is not running
- Backend crashed
- Port is wrong
- Firewall is blocking the connection

Solution:
1. Check backend is running: `ps aux | grep uvicorn`
2. Check logs: `tail -f /var/log/app.log`
3. Verify port: `netstat -tlnp | grep 8000`
4. Test connectivity: `curl -v http://localhost:8000/health`

### Webhook Returns 500 Error

This means the backend code has an error:

1. Check Flask/FastAPI error logs
2. Verify all imports are correct
3. Check that TELEGRAM_BOT_TOKEN is set
4. Try simulating update locally with curl

---

## Webhook Lifecycle

```
User sends message to bot
         ↓
Telegram servers receive message
         ↓
Telegram makes HTTP POST to our webhook URL
    (includes update_id, message, etc.)
         ↓
Our endpoint receives request and parses JSON
         ↓
Return 200 OK to Telegram immediately
         ↓
Process update asynchronously
         ↓
Call bot.send_message() to reply
         ↓
User receives reply
```

**Important:** Always return 200 within 30 seconds, even if processing fails.

---

## Production Considerations

1. **HTTPS Only:** Telegram will only POST to HTTPS URLs
2. **Certificate:** Use valid, recognized SSL certificate
3. **Rate Limiting:** Implement rate limiting on webhook endpoint
4. **Scaling:** Each POST request is independent; safe to run multiple workers
5. **Logging:** Log all webhooks for debugging
6. **Monitoring:** Monitor webhook errors via getWebhookInfo

---

## Reference Links

- Telegram Bot API: https://core.telegram.org/bots/api
- setWebhook method: https://core.telegram.org/bots/api#setwebhook
- getWebhookInfo method: https://core.telegram.org/bots/api#getwebhookinfo
- Aiogram docs: https://docs.aiogram.dev/
