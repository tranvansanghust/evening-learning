# Onboarding API Documentation

**Version:** 0.1.0
**Status:** Complete MVP Implementation

---

## Overview

The Onboarding API implements the complete user onboarding flow as specified in `02_onboarding-user-flow.md`. It provides a series of endpoints that guide users through a structured process from signup to personalized curriculum generation.

### Architecture

- **Service Layer:** `app/services/onboarding_service.py` - Business logic
- **Router/API:** `app/routers/onboarding.py` - FastAPI endpoints
- **Data Model:** `app/models/onboarding_state.py` - Temporary state tracking
- **Database:** PostgreSQL with SQLAlchemy ORM

### Key Features

✓ Multi-step form flow with state persistence
✓ Udemy URL detection and curriculum fetching (mock)
✓ Binary tree assessment (Q1 → Q2a/Q2b)
✓ Level determination (0-3)
✓ Curriculum generation and scheduling
✓ Type-safe request/response models
✓ Comprehensive error handling
✓ Request logging for debugging

---

## API Endpoints

### 1. Start Onboarding

**Endpoint:** `POST /api/onboard/start`

**Purpose:** Create a new user and initialize onboarding state.

**Request:**
```json
{
  "telegram_id": "123456789",
  "username": "john_doe"  // optional
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Welcome john_doe! Let's set up your learning journey.",
  "user_id": 1,
  "next_step": "course_input"
}
```

**Errors:**
- `400 Bad Request` - User already exists with this telegram_id
- `500 Internal Server Error` - Database error

**Example:**
```bash
curl -X POST http://localhost:8000/api/onboard/start \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": "123456789",
    "username": "john_doe"
  }'
```

---

### 2. Course Input

**Endpoint:** `POST /api/onboard/course_input`

**Purpose:** Parse user's course input (Udemy URL or topic name).

**Request:**
```json
{
  "user_id": 1,
  "input_text": "https://www.udemy.com/course/react-complete-guide/"
}
```

**Response Options:**

**If Udemy URL detected:**
```json
{
  "success": true,
  "message": "Found: react-complete-guide",
  "detected_type": "udemy",
  "course_name": "react-complete-guide",
  "next_step": "confirm_course"
}
```

**If topic detected:**
```json
{
  "success": true,
  "message": "Topic: Learn Advanced React",
  "detected_type": "topic",
  "course_name": "Learn Advanced React",
  "next_step": "level_q1"
}
```

**Errors:**
- `400 Bad Request` - Invalid URL/topic format
- `404 Not Found` - User onboarding state not found

**Example:**
```bash
curl -X POST http://localhost:8000/api/onboard/course_input \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "input_text": "Learn React"
  }'
```

---

### 3. Level Q1 - Assessment Question 1

**Endpoint:** `POST /api/onboard/level_q1`

**Purpose:** Store Q1 answer and return Q2 (Q2a or Q2b).

**Question:** "Have you built a web app before?"
**Valid Answers:** `"never"` or `"yes"`

**Request:**
```json
{
  "user_id": 1,
  "answer": "yes"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Great! Next question...",
  "question": "Have you used other frameworks (Vue, Angular, etc)?",
  "question_type": "q2b",
  "next_step": "level_q2"
}
```

**Answer Logic:**
- If Q1 = `"never"` → Q2 is Q2a: "Do you know HTML/CSS?" → Level 0 or 1
- If Q1 = `"yes"` → Q2 is Q2b: "Have you used other frameworks?" → Level 2 or 3

**Errors:**
- `400 Bad Request` - Invalid answer (not "never" or "yes")
- `404 Not Found` - User onboarding state not found

**Example:**
```bash
curl -X POST http://localhost:8000/api/onboard/level_q1 \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "answer": "yes"
  }'
```

---

### 4. Level Q2 - Assessment Question 2

**Endpoint:** `POST /api/onboard/level_q2`

**Purpose:** Store Q2 answer and determine user level.

**Valid Answers:** `"no"` or `"yes"`

**Request:**
```json
{
  "user_id": 1,
  "answer": "yes"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Assessment complete!",
  "assessed_level": 3,
  "level_description": "Expert - Framework experience",
  "next_step": "deadline"
}
```

**Level Matrix:**

| Q1 | Q2 | Level | Description |
|----|----|----|---|
| never | no | 0 | Beginner - Starting from basics |
| never | yes | 1 | Intermediate - Know HTML/CSS |
| yes | no | 2 | Advanced - Web app experience |
| yes | yes | 3 | Expert - Framework experience |

**Effects:**
- Updates user's `level` field
- Moves to deadline step

**Errors:**
- `400 Bad Request` - Invalid answer
- `404 Not Found` - User onboarding state or Q1 answer not found

**Example:**
```bash
curl -X POST http://localhost:8000/api/onboard/level_q2 \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "answer": "no"
  }'
```

---

### 5. Deadline

**Endpoint:** `POST /api/onboard/deadline`

**Purpose:** Store target course completion date.

**Request:**
```json
{
  "user_id": 1,
  "deadline_date": "2025-05-31"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Great! Deadline set to May 31, 2025",
  "deadline": "2025-05-31",
  "next_step": "hours_per_day"
}
```

**Validation:**
- Date format: ISO 8601 `YYYY-MM-DD`
- Date must be in the future (> today)

**Errors:**
- `400 Bad Request` - Invalid date format or past date
- `404 Not Found` - User onboarding state not found

**Example:**
```bash
curl -X POST http://localhost:8000/api/onboard/deadline \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "deadline_date": "2025-05-31"
  }'
```

---

### 6. Hours Per Day

**Endpoint:** `POST /api/onboard/hours_per_day`

**Purpose:** Store available daily study hours.

**Request:**
```json
{
  "user_id": 1,
  "hours": 2
}
```

**Response:**
```json
{
  "success": true,
  "message": "Perfect! 2 hour(s) per day is a solid commitment.",
  "hours_per_day": 2,
  "next_step": "reminder_time"
}
```

**Validation:**
- Hours: 1-12 (integer)

**Errors:**
- `400 Bad Request` - Invalid hours (< 1 or > 12)
- `404 Not Found` - User onboarding state not found

**Example:**
```bash
curl -X POST http://localhost:8000/api/onboard/hours_per_day \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "hours": 3
  }'
```

---

### 7. Reminder Time

**Endpoint:** `POST /api/onboard/reminder_time`

**Purpose:** Store reminder time and generate personalized curriculum.

**This is the FINAL step.** After this:
- Curriculum is generated
- UserCourse enrollment is created
- First lesson is returned
- Onboarding state is cleaned up

**Request:**
```json
{
  "user_id": 1,
  "time": "09:00"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Your learning journey is ready!",
  "reminder_time": "09:00",
  "curriculum_generated": true,
  "first_lesson": {
    "lesson_id": 101,
    "sequence_number": 1,
    "title": "Section 1: Getting Started",
    "description": "Introduction to React",
    "estimated_duration_minutes": 45
  },
  "total_lessons": 6,
  "estimated_total_hours": 7.5
}
```

**Validation:**
- Time format: `HH:MM` (24-hour)
- Valid range: 00:00 - 23:59

**Side Effects:**
1. Curriculum generated from course structure
2. `UserCourse` enrollment created with status `IN_PROGRESS`
3. Onboarding state deleted (marked as completed)
4. User's level is finalized

**Errors:**
- `400 Bad Request` - Invalid time format, missing deadline/hours
- `404 Not Found` - User onboarding state not found
- `500 Internal Server Error` - Course not found or curriculum generation failed

**Example:**
```bash
curl -X POST http://localhost:8000/api/onboard/reminder_time \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "time": "21:00"
  }'
```

---

### 8. Get Onboarding Status

**Endpoint:** `GET /api/onboard/status/{user_id}`

**Purpose:** Retrieve current onboarding progress for a user.

**Response:**
```json
{
  "success": true,
  "user_id": 1,
  "current_step": "reminder_time",
  "course_id": 5,
  "assessed_level": 2,
  "deadline": "2025-05-31",
  "hours_per_day": 2,
  "reminder_time": "09:00"
}
```

**Use Cases:**
- Check progress if user disconnects
- Resume onboarding from current step
- Debug/admin monitoring

**Errors:**
- `404 Not Found` - No active onboarding for this user
- `500 Internal Server Error` - Database error

**Example:**
```bash
curl http://localhost:8000/api/onboard/status/1
```

---

## Data Models

### OnboardingState

Temporary state record created during onboarding, deleted when complete.

**Fields:**
```python
onboarding_id: int              # Primary key
user_id: int                    # FK to users
current_step: str               # start, course_input, level_q1, level_q2, deadline, hours_per_day, reminder_time, completed
course_id: Optional[int]        # FK to courses (nullable)
q1_answer: Optional[str]        # "never" or "yes"
q2_answer: Optional[str]        # "no" or "yes"
assessed_level: Optional[int]   # 0-3
deadline: Optional[date]        # YYYY-MM-DD
hours_per_day: Optional[int]    # 1-12
reminder_time: Optional[str]    # "HH:MM"
created_at: datetime            # UTC
updated_at: datetime            # UTC
expires_at: datetime            # Auto-expires after 7 days
```

---

## OnboardingService

Core business logic service.

### Main Methods

```python
class OnboardingService:
    # User management
    def create_user(telegram_id: str, username: Optional[str]) -> User
    def create_onboarding_state(user_id: int) -> OnboardingState
    def get_onboarding_state(user_id: int) -> Optional[OnboardingState]

    # Course handling
    def detect_course_from_input(user_input: str) -> Tuple[Optional[str], Optional[str]]
    def fetch_udemy_curriculum(course_slug: str) -> List[dict]
    def create_course_from_curriculum(...) -> Course

    # Assessment
    def assess_level(q1_answer: str, q2_answer: str) -> int

    # Curriculum
    def create_curriculum(course: Course, user_level: int, deadline: date, hours_per_day: int) -> List[Lesson]
    def get_first_lesson(course_id: int) -> Optional[Lesson]

    # State management
    def update_onboarding_state(...) -> OnboardingState
    def save_user_course_enrollment(user_id: int, course_id: int) -> UserCourse
    def complete_onboarding(user_id: int) -> None
```

---

## Flow Diagram

```
POST /start
    ↓
Create User, Initialize State
    ↓
POST /course_input
    ├─ Udemy URL → confirm_course
    └─ Topic → level_q1
    ↓
POST /level_q1
    ├─ "never" → Q2a: "Know HTML/CSS?"
    └─ "yes" → Q2b: "Used other frameworks?"
    ↓
POST /level_q2
    ├─ Level determined (0-3)
    ├─ User.level updated
    └─ deadline
    ↓
POST /deadline
    ├─ Validate future date
    └─ hours_per_day
    ↓
POST /hours_per_day
    ├─ Validate 1-12
    └─ reminder_time
    ↓
POST /reminder_time (FINAL STEP)
    ├─ Validate HH:MM
    ├─ Generate curriculum
    ├─ Create UserCourse enrollment
    ├─ Get first lesson
    ├─ Delete OnboardingState
    └─ Return first lesson + summary
    ↓
Onboarding Complete ✅
```

---

## Integration with Telegram Bot

The endpoints are designed to be called by Telegram handlers. Example handler:

```python
# In app/routers/telegram_handlers.py

async def handle_start(user_id: str, db: Session):
    service = OnboardingService(db)
    user = service.create_user(user_id, username=None)
    await telegram_service.send_message(
        user_id,
        f"Welcome! User ID: {user.user_id}"
    )

async def handle_course_input(user_id: str, course_text: str, db: Session):
    service = OnboardingService(db)
    detected_type, value = service.detect_course_from_input(course_text)

    if detected_type == "udemy":
        # Confirm course with inline buttons
        await telegram_service.send_message_with_buttons(
            user_id,
            f"Found: {value}",
            [InlineButton("Correct ✅", "confirm_yes")]
        )
    else:
        # Move to assessment
        await send_q1(user_id, db)
```

---

## Error Handling

All endpoints return standardized error responses:

```json
{
  "success": false,
  "error": "Validation error",
  "detail": "Invalid time format. Use HH:MM (24-hour)"
}
```

**HTTP Status Codes:**
- `201 Created` - Successful user creation
- `200 OK` - Successful step completion
- `400 Bad Request` - Validation error
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Database or logic error

---

## Testing

### Quick Start

1. **Create User**
```bash
curl -X POST http://localhost:8000/api/onboard/start \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "999", "username": "testuser"}'
```

2. **Course Input (Topic)**
```bash
curl -X POST http://localhost:8000/api/onboard/course_input \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "input_text": "Learn React"}'
```

3. **Q1 Answer**
```bash
curl -X POST http://localhost:8000/api/onboard/level_q1 \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "answer": "yes"}'
```

4. **Q2 Answer**
```bash
curl -X POST http://localhost:8000/api/onboard/level_q2 \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "answer": "no"}'
```

5. **Deadline**
```bash
curl -X POST http://localhost:8000/api/onboard/deadline \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "deadline_date": "2025-06-30"}'
```

6. **Hours Per Day**
```bash
curl -X POST http://localhost:8000/api/onboard/hours_per_day \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "hours": 2}'
```

7. **Reminder Time (Final)**
```bash
curl -X POST http://localhost:8000/api/onboard/reminder_time \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "time": "09:00"}'
```

8. **Check Status**
```bash
curl http://localhost:8000/api/onboard/status/1
```

---

## Mock Data

For MVP development, the service includes mock Udemy curriculum data:

**Supported course slugs:**
- `react-complete-guide` - 6 lessons
- `javascript-advanced` - 4 lessons
- Others - Generic 5-lesson structure

To add real Udemy API integration:
1. Replace `fetch_udemy_curriculum()` with actual API call
2. Parse Udemy course structure
3. Store lessons with actual duration data

---

## Future Enhancements

- [ ] Real Udemy API integration
- [ ] Curriculum personalization by level
- [ ] Schedule optimization (spread lessons across deadline)
- [ ] Pre-onboarding validation (check prerequisites)
- [ ] Onboarding analytics (completion rate, common dropoff points)
- [ ] Retry logic for failed curriculum generation
- [ ] Manual curriculum editing UI
- [ ] Course recommendations based on assessment

---

## Database Schema Changes

The OnboardingState table uses MySQL/PostgreSQL:

```sql
CREATE TABLE onboarding_states (
    onboarding_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    current_step VARCHAR(50) NOT NULL,
    course_id INT,
    q1_answer VARCHAR(50),
    q2_answer VARCHAR(50),
    assessed_level INT,
    deadline DATE,
    hours_per_day INT,
    reminder_time VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE SET NULL,
    INDEX idx_onboarding_user_id (user_id),
    INDEX idx_onboarding_current_step (current_step)
);
```

Run migrations to create table before deploying.

---

## Logging

All operations are logged to `app.services.onboarding_service`:

```
INFO: Created user: 1 (telegram_id=123456789)
INFO: Created onboarding state for user 1
INFO: Detected Udemy course: react-complete-guide
INFO: Fetched 6 lessons for course: react-complete-guide
INFO: Assessed user level: 3 (Q1=yes, Q2=yes)
INFO: Updated onboarding state for user 1: reminder_time
INFO: Generated curriculum for user 1: 6 lessons, 7.5 hours
```

Monitor logs for:
- User creation errors (duplicate telegram_id)
- Assessment logic issues
- Curriculum generation failures

---

## Summary

The Onboarding API provides a complete, type-safe, well-documented implementation of the onboarding flow. It's ready for:
- Direct HTTP testing
- Telegram bot integration
- Frontend consumption
- Production deployment (with Udemy API setup)
