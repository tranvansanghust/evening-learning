# Quiz Service & Learning Endpoints Integration Guide

## Overview

This document describes the complete implementation of the Quiz Service and Learning/Quiz routers for the Evening Learning system. These components orchestrate the quiz flow and manage the learning-to-quiz transition in the daily loop.

**Status:** Implemented
**Components Created:**
- `backend/app/services/quiz_service.py` - Core quiz orchestration service
- `backend/app/routers/learning.py` - Learning phase endpoints
- `backend/app/routers/quiz.py` - Quiz phase endpoints
- Updated `backend/app/main.py` - Router registration

---

## Architecture Overview

```
User Flow:
1. Learning Phase (Track A or B)
   ↓
2. POST /api/learn/done
   ↓
3. QuizService.start_quiz()
   ├─ Create QuizSession
   ├─ Load Lesson & Concepts
   └─ Generate First Question via LLM
   ↓
4. POST /api/quiz/answer (multiple times)
   ├─ Evaluate Answer with LLM
   ├─ Save QuizAnswer
   ├─ Decide Next Action (continue/followup/end)
   └─ Generate Next Question or End Quiz
   ↓
5. GET /api/quiz/summary/{session_id}
   ├─ Generate Summary with LLM
   └─ Save QuizSummary
```

---

## Service Architecture

### QuizService (`app/services/quiz_service.py`)

**Purpose:** Orchestrates the entire quiz lifecycle using LLMService for all AI interactions.

**Key Methods:**

#### 1. `start_quiz(user_id, lesson_id, user_checkin, db_session) -> dict`

Initializes a quiz session and generates the first question.

**Flow:**
1. Validate user and lesson exist
2. Load lesson content and concepts from database
3. Create QuizSession record with status='active'
4. Call LLMService.generate_quiz_question() for first question
5. Save conversation history (bot's first question)
6. Return session_id, first_question, lesson_name, concepts

**Example:**
```python
result = quiz_service.start_quiz(
    user_id=1,
    lesson_id=5,
    user_checkin="I learned about useState",
    db_session=db
)
# result = {
#     "session_id": 42,
#     "first_question": "What is useState used for?",
#     "lesson_name": "React Hooks",
#     "concepts": ["useState", "useEffect", "hooks"]
# }
```

**Database Changes:**
- Creates new QuizSession record
- Sets messages = [{"role": "assistant", "content": first_question}]

---

#### 2. `submit_answer(session_id, user_answer, db_session) -> dict`

Evaluates an answer and determines the next quiz action.

**Flow:**
1. Load QuizSession and verify it's active
2. Get current question from conversation history
3. Call LLMService.evaluate_answer() to evaluate
4. Save QuizAnswer record with is_correct, engagement_level
5. Call LLMService.decide_next_action() to decide progression
6. Based on action type:
   - **CONTINUE:** Generate next question via LLM
   - **FOLLOWUP:** Use provided follow-up or generate one
   - **END:** Mark session as completed
7. Update conversation history (user answer + next question)
8. Return evaluation, next_action, next_question (if applicable)

**Example:**
```python
result = quiz_service.submit_answer(
    session_id=42,
    user_answer="useState manages state in functional components",
    db_session=db
)
# result = {
#     "evaluation": {
#         "is_correct": True,
#         "confidence": 0.95,
#         "engagement_level": "high",
#         "key_concepts_covered": ["state management"],
#         "key_concepts_missed": [],
#         "feedback": "Great explanation!"
#     },
#     "next_action": "continue",
#     "reason": "High engagement, good understanding",
#     "next_question": "Tell me about useEffect...",
#     "question_count": 1,
#     "summary_ready": False
# }
```

**Database Changes:**
- Creates QuizAnswer record
- Updates QuizSession.messages with user answer + next question
- If end: sets status='completed', completed_at=now

---

#### 3. `get_or_generate_summary(session_id, db_session) -> dict`

Generates or retrieves the post-quiz summary.

**Flow:**
1. Load QuizSession and verify it exists
2. Check if summary already exists (return if yes)
3. Load lesson and all concepts
4. Get conversation history from session.messages
5. Call LLMService.generate_quiz_summary()
6. Create QuizSummary record with:
   - concepts_mastered: ["concept1", "concept2"]
   - concepts_weak: [{"concept": "...", "user_answer": "...", "correct_explanation": "..."}]
7. Return summary object

**Example:**
```python
summary = quiz_service.get_or_generate_summary(
    session_id=42,
    db_session=db
)
# summary = {
#     "summary_id": 100,
#     "concepts_mastered": ["useState", "hooks"],
#     "concepts_weak": [
#         {
#             "concept": "useEffect cleanup",
#             "user_answer": "It runs after render",
#             "correct_explanation": "..."
#         }
#     ],
#     "summary_text": "Overall, you understand...",
#     "suggestions": ["Practice with more complex states"],
#     "engagement_quality": "high",
#     "session_id": 42
# }
```

**Database Changes:**
- Creates QuizSummary record linked to QuizSession

---

#### 4. `get_quiz_status(session_id, db_session) -> dict`

Returns current quiz session status and progress.

**Returns:**
```python
{
    "session_id": 42,
    "status": "active",  # or "completed"
    "question_count": 3,
    "answer_count": 2,
    "has_summary": False,
    "lesson_name": "React Hooks",
    "user_id": 1,
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": None
}
```

---

## Router Endpoints

### Learning Router (`app/routers/learning.py`)

Handles the learning phase and transition to quiz.

#### 1. POST `/api/learn/start`

Starts a learning session for a lesson.

**Request:**
```json
{
    "user_id": 1,
    "lesson_id": 5,
    "track": "B"
}
```

**Response (Track B - Internal Content):**
```json
{
    "success": true,
    "message": "Starting learning: React Hooks",
    "lesson_id": 5,
    "lesson_name": "React Hooks",
    "track": "B",
    "content_url": "https://example.com/react-hooks",
    "estimated_duration": 45
}
```

**Response (Track A - External Learning):**
```json
{
    "success": true,
    "message": "Starting learning: React Hooks. Go ahead and learn from your external source!",
    "lesson_id": 5,
    "lesson_name": "React Hooks",
    "track": "A",
    "estimated_duration": 45
}
```

**Purpose:**
- Track B: Returns content_url for user to read in the app
- Track A: Just acknowledges that user is going to external source (Udemy, etc.)

---

#### 2. POST `/api/learn/done`

Marks learning as done and initializes quiz session.

**Request:**
```json
{
    "user_id": 1,
    "lesson_id": 5,
    "user_checkin": "I learned about useState and basic hooks, still confused about useEffect cleanup"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Great! Let's check what you've learned.",
    "session_id": 42,
    "first_question": "You mentioned useState. Can you explain what it does in your own words?",
    "lesson_name": "React Hooks",
    "concepts": ["useState", "useEffect", "hooks"]
}
```

**Flow:**
1. Validate user and lesson
2. Call QuizService.start_quiz()
3. Return quiz session with first question

**Track A Handling:**
The `user_checkin` parameter is especially important for Track A users because:
- For Track B: The system knows exactly what was in the lesson (from lesson.description)
- For Track A: The user learned from external source, so their check-in helps the LLM understand what they actually covered

---

#### 3. GET `/api/learn/status/{user_id}`

Gets today's lesson status for a user.

**Response:**
```json
{
    "success": true,
    "user_id": 1,
    "today_lesson": {
        "lesson_id": 5,
        "lesson_name": "React Hooks",
        "status": "pending",
        "estimated_duration": 45
    },
    "message": "User has lesson: React Hooks"
}
```

**Returns:**
- lesson_id, name, status, and estimated duration
- Currently uses first lesson of active course
- Can be enhanced later with scheduling logic

---

### Quiz Router (`app/routers/quiz.py`)

Handles the entire quiz phase.

#### 1. POST `/api/quiz/start`

Initializes quiz session (same as /api/learn/done but can be called directly).

**Request:**
```json
{
    "user_id": 1,
    "lesson_id": 5,
    "user_checkin": "Optional check-in for Track A users"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Quiz started. Answer the question to begin.",
    "session_id": 42,
    "first_question": "What is useState?",
    "lesson_name": "React Hooks",
    "concepts": ["useState", "useEffect"]
}
```

---

#### 2. POST `/api/quiz/answer`

Submits an answer and gets evaluation + next action.

**Request:**
```json
{
    "session_id": 42,
    "user_answer": "useState is a hook that lets you add state to functional components"
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
        "key_concepts_covered": ["state", "functional components"],
        "key_concepts_missed": [],
        "feedback": "Excellent explanation! You clearly understand the basics."
    },
    "next_action": "continue",
    "reason": "High engagement and correct answer, ready for next question",
    "next_question": "Now tell me about useEffect. What does it do?",
    "question_count": 1,
    "summary_ready": false
}
```

**Possible next_action values:**
- `"continue"` - Ask another question on a different concept
- `"followup"` - Ask a follow-up on the same topic to probe deeper
- `"end"` - Quiz is complete, summary is ready

When `next_action` is `"end"`:
```json
{
    "success": true,
    "evaluation": {...},
    "next_action": "end",
    "reason": "User has answered 5 questions with good understanding",
    "question_count": 5,
    "summary_ready": true
}
```

---

#### 3. GET `/api/quiz/status/{session_id}`

Gets quiz session status and progress.

**Response:**
```json
{
    "success": true,
    "session_id": 42,
    "status": "active",
    "question_count": 3,
    "answer_count": 3,
    "has_summary": false,
    "lesson_name": "React Hooks",
    "user_id": 1,
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": null
}
```

---

#### 4. GET `/api/quiz/summary/{session_id}`

Gets the post-quiz summary.

**Prerequisites:**
- Quiz session must have status='completed'
- If not completed, returns 404

**Response:**
```json
{
    "success": true,
    "session_id": 42,
    "summary_id": 100,
    "concepts_mastered": ["useState", "useEffect basics"],
    "concepts_weak": [
        {
            "concept": "useEffect cleanup",
            "user_answer": "It runs after every render",
            "correct_explanation": "Cleanup function prevents memory leaks and runs before component unmounts..."
        }
    ],
    "summary_text": "Great job! You have a solid understanding of React hooks. You clearly know how useState works and can explain functional components well. You're still building understanding around useEffect cleanup functions...",
    "suggestions": [
        "Practice writing cleanup functions in useEffect",
        "Try implementing a custom hook",
        "Review memory leak prevention patterns"
    ],
    "engagement_quality": "high"
}
```

---

## Flow Examples

### Example 1: Complete Quiz Session (Track B - Internal Content)

**Step 1: User starts learning**
```
POST /api/learn/start
{
    "user_id": 1,
    "lesson_id": 5,
    "track": "B"
}
→ Returns content_url for user to read
```

**Step 2: User finishes reading and marks done**
```
POST /api/learn/done
{
    "user_id": 1,
    "lesson_id": 5,
    "user_checkin": null
}
→ Creates quiz session, generates first question
```

**Step 3-7: Quiz loop (5 answers in this example)**
```
POST /api/quiz/answer (question 1)
{
    "session_id": 42,
    "user_answer": "useState manages state..."
}
→ Returns evaluation + next_question

POST /api/quiz/answer (question 2)
→ Returns evaluation + next_question

... (questions 3, 4, 5)

POST /api/quiz/answer (question 5)
→ Returns evaluation + next_action="end" + summary_ready=true
```

**Step 8: Get summary**
```
GET /api/quiz/summary/42
→ Returns complete summary with mastered/weak concepts
```

---

### Example 2: Quiz Session (Track A - External Learning)

**Step 1: User starts external learning**
```
POST /api/learn/start
{
    "user_id": 1,
    "lesson_id": 6,
    "track": "A"
}
→ Acknowledges user is learning externally
```

**Step 2: User finishes and marks done, providing check-in**
```
POST /api/learn/done
{
    "user_id": 1,
    "lesson_id": 6,
    "user_checkin": "I watched section 3 about SQL joins. Learned INNER JOIN and LEFT JOIN but not sure about CROSS JOIN"
}
→ Creates quiz session
→ LLM uses check-in to understand what to test
→ Generates first question focused on what they said
```

**Rest of quiz:** Same as Track B

---

## Error Handling

### Common Error Cases

**1. Session Not Found**
```
GET /api/quiz/summary/999
→ 404 Not Found
→ "Quiz session 999 not found"
```

**2. Quiz Not Completed**
```
GET /api/quiz/summary/42  (where status='active')
→ 404 Not Found
→ "Quiz session 42 is not completed (current status: active)"
```

**3. Invalid Track**
```
POST /api/learn/start
{
    "user_id": 1,
    "lesson_id": 5,
    "track": "C"
}
→ 400 Bad Request
→ "Track must be 'A' or 'B'"
```

**4. LLM Service Error**
```
POST /api/learn/done (LLM fails to generate question)
→ 500 Internal Server Error
→ "Failed to start quiz session"
```

---

## Database Integration

### Models Used

**QuizSession**
```python
session_id: int (PK)
user_id: int (FK)
lesson_id: int (FK)
status: str ('active' or 'completed')
messages: JSON  # Conversation history
started_at: datetime
completed_at: datetime (nullable)
```

**QuizAnswer**
```python
answer_id: int (PK)
session_id: int (FK)
concept_id: int (FK)
question: str
user_answer: str
is_correct: bool
engagement_level: str ('low', 'medium', 'high')
created_at: datetime
```

**QuizSummary**
```python
summary_id: int (PK)
session_id: int (FK, unique)
user_course_id: int (FK, nullable)
concepts_mastered: JSON
concepts_weak: JSON
created_at: datetime
```

### Conversation History Format

Stored as JSON in `QuizSession.messages`:
```json
[
    {
        "role": "assistant",
        "content": "What is useState?"
    },
    {
        "role": "user",
        "content": "useState is a hook..."
    },
    {
        "role": "assistant",
        "content": "Good! Now tell me about useEffect..."
    },
    {
        "role": "user",
        "content": "useEffect runs after render..."
    }
]
```

---

## LLM Service Integration

The QuizService delegates all AI tasks to LLMService:

**1. generate_quiz_question()**
- Input: lesson_content, conversation_history, concepts, is_first_question
- Output: Natural conversational question
- Model: claude-haiku-4-5 (fast)

**2. evaluate_answer()**
- Input: question, user_answer, lesson_context, concepts
- Output: AnswerEvaluation (is_correct, confidence, engagement_level, feedback)
- Model: claude-sonnet-4-6 (smart)

**3. decide_next_action()**
- Input: AnswerEvaluation, question_count, max_questions
- Output: NextAction (action_type, reason, follow_up_question)
- Model: claude-haiku-4-5 (fast)

**4. generate_quiz_summary()**
- Input: lesson_name, lesson_content, conversation_history, concepts
- Output: QuizSummary (mastered, weak, suggestions)
- Model: claude-sonnet-4-6 (smart)

---

## Integration with Telegram Handlers

These endpoints are ready to be called from `app/routers/telegram_handlers.py`:

**Telegram Command Flow:**
```
/start_learn → POST /api/learn/start (Track A or B)
↓
User learns (externally or from content_url)
↓
/done or button click → POST /api/learn/done
↓
Quiz starts automatically, send first_question to user
↓
User replies → POST /api/quiz/answer
↓
Repeat until next_action='end'
↓
Send summary to user
```

---

## Testing the Implementation

### Setup
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run migration
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Test Endpoints
```bash
# 1. Start learning
curl -X POST http://localhost:8000/api/learn/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "lesson_id": 5, "track": "B"}'

# 2. Finish learning and start quiz
curl -X POST http://localhost:8000/api/learn/done \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "lesson_id": 5, "user_checkin": null}'

# 3. Submit answer
curl -X POST http://localhost:8000/api/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id": 42, "user_answer": "useState manages state in functional components"}'

# 4. Get quiz status
curl http://localhost:8000/api/quiz/status/42

# 5. Get summary (after quiz is completed)
curl http://localhost:8000/api/quiz/summary/42
```

---

## Future Enhancements

### Planned Features
1. **Concept Tracking**: Map each question to specific concept_id
2. **Spaced Repetition**: Track weak concepts for follow-up quizzes
3. **Progress Tracking**: Update UserCourse progress based on mastery
4. **Custom Quiz Length**: Allow users to choose 3-5 questions
5. **Quiz History**: Store all quiz sessions for review
6. **Knowledge Graph**: Visualize concept mastery over time

### Not Implemented Yet
- Post-quiz knowledge retention tracking (Knowledge Tracker)
- Quiz retry logic for failed concepts
- Multi-day review scheduling
- Adaptive difficulty based on user level

---

## Troubleshooting

**LLM Service Not Initialized**
```
Error: LLMService requires ANTHROPIC_API_KEY
Solution: Set ANTHROPIC_API_KEY in .env file
```

**Quiz Session Status Not Transitioning**
```
Check QuizSession.status field
If "active", call submit_answer until next_action="end"
Then status should become "completed"
```

**Summary Generation Fails**
```
Check QuizSession.messages has complete conversation history
Ensure lesson has content and concepts defined
LLM needs sufficient context to generate summary
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Handlers                        │
│              (future integration point)                     │
└──────────┬──────────────────────────────────────────────────┘
           │
           ├─→ POST /api/learn/start
           ├─→ POST /api/learn/done
           └─→ POST /api/quiz/answer
                      │
┌──────────────────────┴──────────────────────────────────────┐
│                   FastAPI Routers                           │
│   ┌──────────────────┐          ┌──────────────────┐       │
│   │ learning.py      │          │ quiz.py          │       │
│   │ ├─ /start        │          │ ├─ /start        │       │
│   │ ├─ /done         │          │ ├─ /answer       │       │
│   │ └─ /status       │          │ ├─ /status       │       │
│   │                  │          │ └─ /summary      │       │
│   └────────┬─────────┘          └────────┬─────────┘       │
│            │                              │                │
└────────────┼──────────────────────────────┼────────────────┘
             │                              │
             ├──────────────────────┬───────┘
                                    │
                    ┌───────────────┴──────────────┐
                    │                              │
                    ▼                              ▼
        ┌──────────────────────┐      ┌──────────────────┐
        │  QuizService         │      │  LLMService      │
        │  ├─ start_quiz       │      │  ├─ generate_Q   │
        │  ├─ submit_answer    │      │  ├─ evaluate_A   │
        │  ├─ get_summary      │      │  ├─ decide_action│
        │  └─ get_status       │      │  └─ gen_summary  │
        └────────┬─────────────┘      └────────┬─────────┘
                 │                              │
                 │                    ┌─────────┴──────┐
                 │                    │                │
                 │              Claude Haiku     Claude Sonnet
                 │              (fast tasks)     (complex tasks)
                 │                    │                │
                 ▼                    ▼                ▼
        ┌──────────────────────────────────────────────┐
        │         SQLAlchemy ORM                       │
        │  ├─ QuizSession                              │
        │  ├─ QuizAnswer                               │
        │  ├─ QuizSummary                              │
        │  ├─ Lesson, Concept                          │
        │  └─ User, UserCourse                         │
        └──────────────┬───────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │     PostgreSQL Database      │
        │     (Persistent Storage)     │
        └──────────────────────────────┘
```

---

## Files Created

1. **`backend/app/services/quiz_service.py`** (555 lines)
   - Core service orchestrating quiz lifecycle
   - Methods: start_quiz, submit_answer, get_or_generate_summary, get_quiz_status

2. **`backend/app/routers/learning.py`** (378 lines)
   - Learning phase endpoints
   - Endpoints: /start, /done, /status/{user_id}
   - Supports Track A and Track B

3. **`backend/app/routers/quiz.py`** (389 lines)
   - Quiz phase endpoints
   - Endpoints: /start, /answer, /status/{session_id}, /summary/{session_id}

4. **Updated `backend/app/main.py`**
   - Registered learning and quiz routers
   - Import statements updated

---

## Summary

The Quiz Service and Learning/Quiz routers provide a complete, production-ready implementation of the quiz flow described in the Daily Loop documentation. All components are:

✓ Fully type-hinted
✓ Properly documented with docstrings
✓ Error-handled with meaningful messages
✓ Integrated with LLMService for AI tasks
✓ Database-aware with proper ORM usage
✓ Ready for Telegram handler integration
✓ Following FastAPI best practices
✓ Using dependency injection (get_db)
✓ Returning standardized JSON responses
