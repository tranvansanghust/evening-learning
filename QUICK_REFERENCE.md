# Quiz Service - Quick Reference Card

## 📋 Files Overview

| File | Purpose | Lines |
|------|---------|-------|
| `backend/app/services/quiz_service.py` | Core orchestration | 555 |
| `backend/app/routers/learning.py` | Learning endpoints | 378 |
| `backend/app/routers/quiz.py` | Quiz endpoints | 389 |
| `docs/04_quiz-service-integration.md` | Architecture guide | 450+ |
| `docs/05_telegram-handler-integration.md` | Handler examples | 400+ |

---

## 🔑 Core Methods

### QuizService.start_quiz()
```python
result = quiz_service.start_quiz(
    user_id=1,
    lesson_id=5,
    user_checkin=None,  # For Track A
    db_session=db
)
# Returns: session_id, first_question, lesson_name, concepts
```

### QuizService.submit_answer()
```python
result = quiz_service.submit_answer(
    session_id=42,
    user_answer="User's response",
    db_session=db
)
# Returns: evaluation, next_action, next_question (if applicable)
```

### QuizService.get_or_generate_summary()
```python
summary = quiz_service.get_or_generate_summary(
    session_id=42,
    db_session=db
)
# Returns: concepts_mastered, concepts_weak, summary_text, suggestions
```

### QuizService.get_quiz_status()
```python
status = quiz_service.get_quiz_status(
    session_id=42,
    db_session=db
)
# Returns: status, question_count, answer_count, has_summary
```

---

## 🌐 API Endpoints

### Learning
```
POST /api/learn/start
POST /api/learn/done
GET /api/learn/status/{user_id}
```

### Quiz
```
POST /api/quiz/start
POST /api/quiz/answer
GET /api/quiz/status/{session_id}
GET /api/quiz/summary/{session_id}
```

---

## 🔄 Flow Sequence

```
1. POST /api/learn/start
   ↓
2. User learns (external or via content_url)
   ↓
3. POST /api/learn/done → Calls start_quiz()
   ↓
4. Loop: POST /api/quiz/answer until next_action='end'
   ↓
5. GET /api/quiz/summary/{session_id}
```

---

## 📊 Request/Response Examples

### Start Quiz
**Request:**
```json
{
    "user_id": 1,
    "lesson_id": 5,
    "user_checkin": "I learned about React hooks"
}
```

**Response:**
```json
{
    "success": true,
    "session_id": 42,
    "first_question": "Tell me about useState...",
    "lesson_name": "React Hooks",
    "concepts": ["useState", "useEffect"]
}
```

### Submit Answer
**Request:**
```json
{
    "session_id": 42,
    "user_answer": "useState manages state in functional components"
}
```

**Response:**
```json
{
    "success": true,
    "evaluation": {
        "is_correct": true,
        "confidence": 0.95,
        "engagement_level": "high",
        "feedback": "Excellent!"
    },
    "next_action": "continue",
    "next_question": "Now tell me about useEffect...",
    "question_count": 1
}
```

### Get Summary
**Response:**
```json
{
    "success": true,
    "concepts_mastered": ["useState", "hooks basics"],
    "concepts_weak": [
        {
            "concept": "useEffect cleanup",
            "user_answer": "...",
            "correct_explanation": "..."
        }
    ],
    "summary_text": "You have a solid understanding...",
    "suggestions": ["Practice cleanup functions"]
}
```

---

## 🎯 Integration with Telegram

### Basic Handler
```python
async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_id = context.user_data["quiz_session_id"]
    user_answer = update.message.text

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/quiz/answer",
            json={"session_id": session_id, "user_answer": user_answer}
        ) as resp:
            result = await resp.json()

    if result["next_action"] == "end":
        await send_summary(update, context, session_id)
    else:
        await update.message.reply_text(result["next_question"])
```

---

## 🔐 Error Handling

### Common Errors
```python
# User not found
404: "User 999 not found"

# Quiz not completed
404: "Quiz session 42 is not completed (current status: active)"

# Invalid track
400: "Track must be 'A' or 'B'"

# LLM error
500: "Failed to start quiz session"
```

---

## 🗄️ Database Models

### QuizSession
- session_id (PK)
- user_id, lesson_id (FK)
- status: 'active' | 'completed'
- messages: JSON (conversation history)
- started_at, completed_at

### QuizAnswer
- answer_id (PK)
- session_id (FK)
- concept_id (FK)
- is_correct: bool
- engagement_level: 'low'|'medium'|'high'

### QuizSummary
- summary_id (PK)
- session_id (FK, unique)
- concepts_mastered: JSON
- concepts_weak: JSON
- created_at

---

## 🚀 Quick Start

### Setup
```bash
cd backend
pip install -r requirements.txt
```

### Run
```bash
uvicorn app.main:app --reload
```

### Test
```bash
curl -X POST http://localhost:8000/api/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "lesson_id": 5, "user_checkin": null}'
```

---

## 📈 Progress Tracking

### Check Status
```bash
curl http://localhost:8000/api/quiz/status/42
```

### Get Summary (after completion)
```bash
curl http://localhost:8000/api/quiz/summary/42
```

---

## 🎓 Track Differences

### Track A (External Learning)
- User learns from Udemy/external source
- Provides `user_checkin` (what they learned)
- LLM uses check-in for context
- Quiz is personalized to their learning

### Track B (Internal Content)
- User reads `content_url` from system
- No check-in needed
- Quiz based on lesson description
- Standard assessment

---

## 🔗 Key Integration Points

1. **LLMService**
   - generate_quiz_question()
   - evaluate_answer()
   - decide_next_action()
   - generate_quiz_summary()

2. **Database (ORM)**
   - QuizSession, QuizAnswer, QuizSummary
   - Lesson, Concept, User, UserCourse

3. **Telegram Handlers**
   - Store session_id in context.user_data
   - Call endpoints via HTTP
   - Send responses as messages

---

## 📚 Documentation

- **04_quiz-service-integration.md** - Full architecture
- **05_telegram-handler-integration.md** - Handler examples
- **Docstrings** - Every method has detailed documentation

---

## ✅ Checklist for Integration

- [ ] Deploy backend service
- [ ] Set ANTHROPIC_API_KEY
- [ ] Create HTTP client for endpoints
- [ ] Implement Telegram handlers
- [ ] Test learning flow (Track A & B)
- [ ] Test quiz flow with answers
- [ ] Verify summary generation
- [ ] Deploy to production

---

## 🐛 Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Database
```sql
SELECT * FROM quiz_sessions WHERE session_id = 42;
SELECT * FROM quiz_answers WHERE session_id = 42;
SELECT * FROM quiz_summaries WHERE session_id = 42;
```

### Verify Conversation History
```python
session = db.query(QuizSession).get(42)
print(session.messages)  # See full Q&A history
```

---

## 📞 Support

Check documentation files for:
- Architecture diagrams
- Complete code examples
- Error handling strategies
- State management patterns
- Performance considerations

---

**Ready to integrate!** See documentation for complete details.
