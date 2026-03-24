# Technical Architecture

> Tài liệu này mô tả kiến trúc kỹ thuật của hệ thống học tập.
> Version: 0.1 — Draft

---

## Tech Stack Overview

| Layer | Công nghệ | Lý do chọn |
|---|---|---|
| **Backend** | Python FastAPI | Async-first, hiệu suất cao, dễ maintain |
| **Database** | MySQL | Structured data, dễ query, phổ biến |
| **Frontend** | React | Lightweight, flexible, tốt cho learning app |
| **LLM** | Claude API (Anthropic) | Conversational intelligence tốt, multi-turn dialogue |
| **Telegram Bot** | aiogram 3.x | Async, phù hợp FastAPI, webhook-based |
| **Session Storage** | MySQL / Redis | Maintain conversation history |
| **External Integration** | Udemy API / Scraping | *(User will try and report back)* |

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                        TELEGRAM USER                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ /start, /done, /progress, etc.
                 │
    ┌────────────▼─────────────┐
    │   TELEGRAM BOT WEBHOOK   │
    │   (aiogram 3.x)          │
    │   - Parse incoming msg   │
    │   - Route to FastAPI     │
    └────────────┬─────────────┘
                 │
     ┌───────────▼──────────────┐
     │   FASTAPI BACKEND        │
     │                          │
     │  Routers:               │
     │  - /onboard             │
     │  - /learn               │
     │  - /quiz                │
     │  - /progress            │
     │                          │
     │  Services:              │
     │  - User service         │
     │  - Curriculum service   │
     │  - Quiz service         │
     │  - LLM service          │
     └───┬──────────┬───────────┘
         │          │
    ┌────▼──┐  ┌───▼─────────────┐
    │ MySQL │  │  CLAUDE API     │
    │  DB   │  │  (LLM)          │
    │       │  │                 │
    │ Users │  │ - Gen questions │
    │ Courses   │ - Evaluate ans  │
    │ Lessons   │ - Gen summary   │
    │ Concepts  │ - Detect engage │
    │ Sessions  │                 │
    └────────┘  └─────────────────┘
         │
         │
    ┌────▼──────────────┐
    │  FRONTEND (React) │
    │                   │
    │  Pages:           │
    │  - Lesson viewer  │
    │  - Dashboard      │
    │  - Progress       │
    └────────────────────┘
```

---

## Database Schema (MySQL)

### Core Tables

```sql
-- Users
users
  - user_id (PK)
  - telegram_id (unique)
  - username
  - level (0-3)
  - created_at
  - updated_at

-- Courses / Curriculum
courses
  - course_id (PK)
  - name
  - description
  - source (udemy / internal)
  - source_id (external ID từ Udemy)
  - total_lessons
  - created_at

-- User Courses (enrollment)
user_courses
  - user_course_id (PK)
  - user_id (FK)
  - course_id (FK)
  - status (PASS / FAIL / IN_PROGRESS)
  - started_at
  - completed_at

-- Lessons
lessons
  - lesson_id (PK)
  - course_id (FK)
  - sequence_number
  - title
  - description
  - content_url (cho Track B frontend)
  - estimated_duration_minutes

-- Concepts
concepts
  - concept_id (PK)
  - lesson_id (FK)
  - name
  - description

-- Quiz Sessions
quiz_sessions
  - session_id (PK)
  - user_id (FK)
  - lesson_id (FK)
  - status (active / completed)
  - messages (JSON) ← conversation history
  - started_at
  - completed_at

-- Quiz Answers
quiz_answers
  - answer_id (PK)
  - session_id (FK)
  - concept_id (FK)
  - question
  - user_answer
  - is_correct
  - engagement_level (low / medium / high)
  - created_at

-- Post-Quiz Summaries
quiz_summaries
  - summary_id (PK)
  - session_id (FK)
  - concepts_mastered (JSON list)
  - concepts_weak (JSON with explanations)
  - created_at
```

---

## FastAPI Routers & Endpoints

### POST /webhook/telegram
Nhận webhook từ Telegram Bot, xử lý incoming messages

```python
@app.post("/webhook/telegram")
async def handle_telegram_webhook(update: Update):
    # Parse incoming message
    # Route to appropriate handler
    # Return response to Telegram
```

### POST /api/onboard/start
Bắt đầu onboarding flow

```python
@app.post("/api/onboard/start")
async def start_onboarding(user_id: str):
    # Tạo user nếu chưa có
    # Return onboarding message
```

### POST /api/onboard/input
User nhập input trong onboarding (course URL, topic, level assessment, deadline, etc.)

```python
@app.post("/api/onboard/input")
async def onboarding_input(
    user_id: str,
    input_type: str,  # course_url, topic, q1, q2, deadline, etc.
    value: str
):
    # Xử lý input, lưu vào DB
    # Return next onboarding message hoặc sinh curriculum
```

### POST /api/learn/start
User bắt đầu học

```python
@app.post("/api/learn/start")
async def start_learning(user_id: str, lesson_id: str):
    # Record timestamp
    # Return learning content (cho Track B)
```

### POST /api/learn/done
User báo học xong

```python
@app.post("/api/learn/done")
async def learning_done(user_id: str, lesson_id: str):
    # Track A: Return check-in message
    # Track B: Return congratulations message + [Start Quiz]
```

### POST /api/quiz/start
Bắt đầu oral-test quiz

```python
@app.post("/api/quiz/start")
async def start_quiz(
    user_id: str,
    lesson_id: str,
    user_checkin: Optional[str]  # Only for Track A
):
    # Create quiz session
    # Call LLM to generate first question
    # Return first quiz message
```

### POST /api/quiz/answer
User trả lời câu hỏi

```python
@app.post("/api/quiz/answer")
async def submit_answer(
    user_id: str,
    session_id: str,
    answer: str
):
    # Save answer to session
    # Call LLM to evaluate
    # Detect engagement
    # Decide: continue quiz or end
    # If continue: gen follow-up question
    # If end: gen summary
    # Return next action
```

### POST /api/quiz/summary
Lấy post-quiz summary

```python
@app.post("/api/quiz/summary")
async def get_quiz_summary(session_id: str):
    # Return stored summary
    # Or generate if not done yet
```

### GET /api/progress
Lấy progress của user

```python
@app.get("/api/progress")
async def get_progress(user_id: str):
    # Query DB
    # Return: completed_lessons / total_lessons, mastered_concepts / total_concepts
```

### GET /api/review
Review post-quiz summaries

```python
@app.get("/api/review")
async def get_review(user_id: str, topic: Optional[str] = None):
    # Return all summaries or filtered by topic
```

### GET /api/lesson/{lesson_id}
Lấy nội dung bài học (cho frontend React)

```python
@app.get("/api/lesson/{lesson_id}")
async def get_lesson(lesson_id: str):
    # Return lesson content để frontend render
```

---

## LLM Service — Prompts & Integration

### LLM Service Class

```python
class LLMService:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def generate_quiz_question(
        self,
        lesson_content: str,
        conversation_history: List[Message],
        previous_answers: Optional[List[dict]]
    ) -> str:
        """Generate next quiz question"""

    def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        lesson_context: str
    ) -> AnswerEvaluation:
        """Evaluate answer (correct/incorrect, engagement, etc.)"""

    def generate_quiz_summary(
        self,
        quiz_session: QuizSession
    ) -> QuizSummary:
        """Generate post-quiz summary with explanations"""

    def suggest_next_courses(
        self,
        completed_course: Course,
        user_level: int
    ) -> List[str]:
        """Suggest 3 next courses for PASS flow"""
```

### Prompt Templates

**Template 1: Generate Quiz Question**
```
You are an AI tutor conducting an oral test.
The user just learned: [LESSON_CONTENT or USER_CHECKIN]

Conversation history:
[PREVIOUS_MESSAGES]

Generate the next quiz question that:
- Tests one key concept they should have learned
- Is conversational (not multiple choice)
- Builds on previous answers if applicable

Question:
```

**Template 2: Evaluate Answer**
```
Question: [QUESTION]
User's answer: [USER_ANSWER]
Lesson context: [LESSON_CONTENT]

Evaluate this answer as JSON:
{
  "is_correct": bool,
  "engagement": "low" | "medium" | "high",
  "should_continue_quiz": bool,
  "key_concepts_covered": [strings],
  "key_concepts_missed": [strings]
}
```

**Template 3: Generate Summary**
```
Quiz session for lesson: [LESSON_NAME]

All Q&A pairs:
[FULL_CONVERSATION]

Generate a summary as JSON:
{
  "concepts_mastered": [...],
  "concepts_weak": [
    {
      "concept": "...",
      "user_answer": "...",
      "correct_explanation": "..."
    }
  ]
}
```

---

## Frontend (React) Architecture

### Pages

```
/dashboard          → Home, progress overview
/lesson/:id         → Lesson viewer (text content render)
/progress           → Detailed progress tracker
```

### Components

```
LessonViewer
  - Render markdown/HTML content
  - Button [Hoàn thành] to trigger API call

ProgressCard
  - Display: lessons_completed / total, concepts_mastered / total

ChatInterface
  - Display Telegram-style chat (for debugging / replay)
```

### API Communication

```javascript
// Call FastAPI endpoints
const api = axios.create({
  baseURL: 'http://localhost:8000/api'
})

api.get('/lesson/:id')      // Fetch lesson content
api.post('/learn/done')     // Notify lesson completion
api.get('/progress')        // Fetch progress
```

---

## Conversation State Management

### Session Storage (MySQL)

```python
# Mỗi quiz session lưu toàn bộ conversation history
quiz_session.messages = [
    {
        "role": "bot",
        "content": "Question 1: ...?"
    },
    {
        "role": "user",
        "content": "User answer here"
    },
    ...
]
```

### Flow

```
1. User /done → Create quiz_session
2. User submit answer → Load session from DB
3. Append user answer to messages
4. Send all messages to Claude API
5. Save Claude response + evaluation to DB
6. Decide next action
7. If quiz ends, generate summary from all messages
```

---

## Udemy Integration (To be determined)

User sẽ try và báo lại về:
- Udemy API availability / Scraping approach
- Curriculum data structure (lessons, duration, etc.)
- Rate limiting concerns

**Current assumption:** Có cách để fetch course curriculum từ Udemy (via API hoặc scraping) và map thành `lessons` table.

---

## Deployment

```
Development:
  - Backend: localhost:8000
  - Frontend: localhost:3000
  - DB: localhost:3306 (MySQL)

Production:
  - FastAPI: deployed on cloud (AWS/GCP/Azure)
  - React: deployed on CDN (Vercel/Netlify)
  - MySQL: managed database service
  - Telegram Webhook: HTTPS public URL pointing to FastAPI
```

---

## Những gì chưa được thiết kế (sẽ bàn tiếp)

- **Authentication/Authorization:** User chỉ có telegram_id, có cần extra auth?
- **Spaced repetition logic:** Exact algorithm để quyết định khi nào quiz lại concept nào
- **Error handling & retry logic:** Khi Telegram/Claude API fail
- **Rate limiting:** Udemy, Claude API, Telegram
- **Monitoring & logging:** Để track issues
