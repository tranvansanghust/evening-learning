# Backend Testing & Setup Guide

> Complete guide to test the backend locally with Telegram + MySQL

---

## Prerequisites

- Python 3.9+
- MySQL 8.0+ (or MariaDB)
- Telegram Bot Token (from BotFather)
- Terminal/Command line access

---

## Step 1: MySQL Setup

### 1.1 Create Database & User

```bash
# Login to MySQL
mysql -u root -p

# In MySQL console:
CREATE DATABASE evening_learning CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'evening_user'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON evening_learning.* TO 'evening_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 1.2 Verify Connection

```bash
mysql -u evening_user -p evening_learning -e "SELECT 1;"
# Should return: 1 (means connection works)
```

---

## Step 2: Python Environment Setup

### 2.1 Create Virtual Environment

```bash
cd /Users/sangtran/Documents/WorkSpace/evening-learning/backend

# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# Should see (venv) in terminal
```

### 2.2 Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt

# Verify key packages
python -c "import fastapi; import sqlalchemy; import aiogram; import anthropic; print('✅ All imports successful')"
```

---

## Step 3: Environment Configuration

### 3.1 Create .env File

```bash
cd /Users/sangtran/Documents/WorkSpace/evening-learning/backend

# Copy from template
cp .env.example .env

# Edit .env with your values
nano .env  # or use your editor
```

### 3.2 Fill in .env Values

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=evening_user
DB_PASSWORD=your_password_here
DB_NAME=evening_learning

# Telegram Bot (from BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram  # Will set up later

# Claude API
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# FastAPI
DEBUG=True
API_HOST=0.0.0.0
API_PORT=8000
```

**Where to get these:**

- **TELEGRAM_BOT_TOKEN**:
  1. Open Telegram, search for @BotFather
  2. Send `/newbot`
  3. Follow prompts, get token
  4. Example: `123456789:ABCDEFGhijklmnopqrstuvwxyz`

- **ANTHROPIC_API_KEY**:
  1. Go to https://console.anthropic.com
  2. Create API key
  3. Copy it

---

## Step 4: Database Schema Creation

### 4.1 Auto-Create Tables

The SQLAlchemy models will auto-create tables on first run. To manually verify:

```bash
cd /Users/sangtran/Documents/WorkSpace/evening-learning/backend

python -c "
from app.database import Base, engine
from app.models import *
Base.metadata.create_all(bind=engine)
print('✅ Tables created successfully')
"
```

### 4.2 Verify Tables Created

```bash
mysql -u evening_user -p evening_learning -e "SHOW TABLES;"

# Should show:
# concepts
# courses
# lessons
# onboarding_states
# quiz_answers
# quiz_sessions
# quiz_summaries
# user_courses
# users
```

---

## Step 5: Run FastAPI Server

### 5.1 Start Server

```bash
cd /Users/sangtran/Documents/WorkSpace/evening-learning/backend

# Make sure venv is activated
source venv/bin/activate

# Start uvicorn server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 5.2 Check Health Endpoint

Open new terminal:

```bash
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

### 5.3 Access API Docs

Open browser:
```
http://localhost:8000/docs
```

You should see Swagger UI with all endpoints listed.

---

## Step 6: Testing Endpoints (Without Telegram)

### 6.1 Test Onboarding Flow

```bash
# 1. Create user
curl -X POST http://localhost:8000/api/onboard/start \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": "123456789",
    "username": "testuser"
  }'

# Should return: {"user_id": "...", "message": "Welcome!"}
```

### 6.2 Test Progress Endpoint

```bash
# Get user progress
curl http://localhost:8000/api/progress/123456789

# Should return:
# {
#   "lessons_completed": 0,
#   "total_lessons": 0,
#   "concepts_mastered": 0,
#   "total_concepts": 0
# }
```

### 6.3 View All Endpoints

```bash
curl http://localhost:8000/docs

# Or just list from terminal:
curl http://localhost:8000/openapi.json | jq '.paths | keys'
```

---

## Step 7: Telegram Integration Setup

### 7.1 Option A: Local Testing (No Webhook)

For local development without ngrok, use **polling** mode:

**Create backend/app/bot_polling.py:**

```python
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from app.config import get_settings
from app.routers import telegram_handlers

async def main():
    settings = get_settings()
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Register handlers
    dp.include_router(telegram_handlers.router)

    # Set commands
    commands = [
        BotCommand(command="start", description="Start onboarding"),
        BotCommand(command="done", description="Finish learning"),
        BotCommand(command="progress", description="View progress"),
        BotCommand(command="review", description="Review past quizzes"),
        BotCommand(command="answer", description="Submit answer"),
    ]
    await bot.set_my_commands(commands)

    print("Bot polling started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python app/bot_polling.py
```

### 7.2 Option B: Webhook (Production)

For production, use webhook. Requires:
1. Public HTTPS domain
2. Ngrok for local testing:

```bash
# Install ngrok (if not already)
brew install ngrok  # Mac
# or download from https://ngrok.com

# Start ngrok
ngrok http 8000

# Copy forwarding URL: https://abc123.ngrok.io

# Update .env
TELEGRAM_WEBHOOK_URL=https://abc123.ngrok.io/webhook/telegram

# Register webhook with Telegram
curl -X POST https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook \
  -F "url=https://abc123.ngrok.io/webhook/telegram"
```

---

## Step 8: Testing via Telegram

### 8.1 With Polling Bot

1. Start polling bot: `python app/bot_polling.py` (in terminal 1)
2. Start FastAPI: `uvicorn app.main:app --reload` (in terminal 2)
3. Open Telegram, find your bot
4. Send `/start`
5. Follow onboarding flow

### 8.2 Test Commands

```
/start              → Begin onboarding
/progress           → View progress
/review             → See past quizzes
/done               → Finish learning
```

---

## Step 9: Troubleshooting

### Issue: "Module not found" error

```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Issue: MySQL connection refused

```bash
# Check if MySQL is running
mysql -u root -p -e "SELECT 1;"

# If not running, start MySQL:
brew services start mysql  # Mac
# or
sudo service mysql start  # Linux
```

### Issue: Telegram bot not responding

```bash
# Check bot token is correct in .env
# Check FastAPI is running on localhost:8000
# Check polling bot script is running

curl http://localhost:8000/health
# Should return 200 OK
```

### Issue: "ANTHROPIC_API_KEY not set"

```bash
# Make sure .env file exists and has the key
cat backend/.env | grep ANTHROPIC_API_KEY

# Should show your key (not empty)
```

---

## Step 10: Next Steps

Once everything works:

1. **Test Quiz Flow:**
   - Create a course via endpoint
   - Create lessons
   - Run through quiz

2. **Test Full Onboarding:**
   - `/start` → Create user
   - Answer level assessment questions
   - Set deadline, hours/day, reminder time

3. **Test Learning Loop:**
   - `/done` → Start quiz
   - `/answer` → Submit answers
   - `/progress` → View results

4. **Check Database:**
   ```bash
   mysql -u evening_user -p evening_learning
   SELECT * FROM users;
   SELECT * FROM quiz_sessions;
   ```

---

## Summary

✅ Database ready
✅ Server running
✅ Endpoints working
✅ Telegram bot responding
✅ Ready to test!

**Quick command to start everything:**

```bash
# Terminal 1: Start FastAPI
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2: Start Telegram bot (polling)
cd backend && source venv/bin/activate && python app/bot_polling.py

# Terminal 3: Test endpoints
curl http://localhost:8000/health
```

Any issues? Check logs in both terminals for error messages.
