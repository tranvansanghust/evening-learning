# SQLAlchemy Models Quick Reference

## File Locations
```
backend/app/models/
├── __init__.py           # Exports all models
├── user.py               # User model (63 lines)
├── course.py             # Course model (67 lines)
├── user_course.py        # UserCourse model (74 lines)
├── lesson.py             # Lesson model (76 lines)
├── concept.py            # Concept model (62 lines)
├── quiz_session.py       # QuizSession model (89 lines)
├── quiz_answer.py        # QuizAnswer model (74 lines)
└── quiz_summary.py       # QuizSummary model (78 lines)
```

## Quick Import
```python
from app.models import (
    User, Course, UserCourse, Lesson, Concept,
    QuizSession, QuizAnswer, QuizSummary
)
```

## Model Overview Table

| Model | Table | Primary Key | Foreign Keys | Key Fields |
|-------|-------|-------------|--------------|-----------|
| **User** | users | user_id | - | telegram_id (unique), level (0-3) |
| **Course** | courses | course_id | - | source, source_id, total_lessons |
| **UserCourse** | user_courses | user_course_id | user_id, course_id | status, started_at, completed_at |
| **Lesson** | lessons | lesson_id | course_id | sequence_number, content_url |
| **Concept** | concepts | concept_id | lesson_id | name, description |
| **QuizSession** | quiz_sessions | session_id | user_id, lesson_id | status, messages (JSON) |
| **QuizAnswer** | quiz_answers | answer_id | session_id, concept_id | is_correct, engagement_level |
| **QuizSummary** | quiz_summaries | summary_id | session_id, user_course_id | concepts_mastered (JSON), concepts_weak (JSON) |

## Column Types Reference

```python
# Standard Types
Column(Integer)              # Auto-incrementing integers for IDs
Column(String(100))          # Variable-length strings
Column(Text)                 # Large text fields
Column(Boolean)              # True/False values
Column(DateTime(timezone=True))  # Timestamps with timezone support
Column(JSON)                 # JSON document storage

# Constraints
primary_key=True             # Primary key
nullable=False               # Required field
nullable=True                # Optional field
unique=True                  # Unique constraint
default="value"              # Default value
index=True                   # Create index
ForeignKey("table.column")   # Foreign key reference
```

## Common Patterns

### Create Record
```python
from app.database import SessionLocal
from app.models import User

db = SessionLocal()
user = User(telegram_id="123", username="john", level=0)
db.add(user)
db.commit()
db.refresh(user)
```

### Query Single Record
```python
user = db.query(User).filter(User.telegram_id == "123").first()
course = db.query(Course).get(1)  # By primary key
```

### Query Multiple Records
```python
users = db.query(User).filter(User.level >= 1).all()
courses = db.query(Course).filter(Course.source == "udemy").all()
```

### Update Record
```python
user = db.query(User).get(1)
user.level = 2
db.commit()
```

### Delete Record
```python
db.delete(user)
db.commit()
```

### Join Relationships
```python
# Eager load relationship
from sqlalchemy.orm import joinedload
user = db.query(User).options(
    joinedload(User.user_courses)
).get(1)

# Access loaded data without additional queries
for uc in user.user_courses:
    print(uc.course.name)
```

### JSON Field Operations
```python
session = QuizSession(
    messages=[
        {"role": "bot", "content": "Hello"},
        {"role": "user", "content": "Hi"}
    ]
)

# Append message
session.messages.append({"role": "bot", "content": "How are you?"})
db.commit()
```

## Relationship Navigation

### One-to-Many
```python
# Parent to Children
course = db.query(Course).get(1)
lessons = course.lessons  # List of Lesson objects

# Child to Parent
lesson = db.query(Lesson).get(1)
course = lesson.course  # Single Course object
```

### Many-to-Many (via Junction)
```python
# User to Courses
user = db.query(User).get(1)
enrollments = user.user_courses  # List of UserCourse objects
for uc in enrollments:
    print(uc.course.name)

# Course to Users
course = db.query(Course).get(1)
enrollments = course.user_courses
for uc in enrollments:
    print(uc.user.username)
```

### One-to-One
```python
session = db.query(QuizSession).get(1)
summary = session.quiz_summary  # Single QuizSummary object or None
```

## Filtering Examples

```python
# Exact match
db.query(User).filter(User.level == 2)

# Range
db.query(UserCourse).filter(UserCourse.started_at >= some_date)

# Multiple conditions (AND)
db.query(QuizSession).filter(
    (QuizSession.status == "completed") &
    (QuizSession.user_id == user_id)
)

# Multiple conditions (OR)
db.query(Course).filter(
    (Course.source == "udemy") |
    (Course.source == "internal")
)

# NOT
db.query(User).filter(User.level != 0)

# IN list
db.query(Course).filter(Course.course_id.in_([1, 2, 3]))

# LIKE (contains)
db.query(Lesson).filter(Lesson.title.like("%python%"))

# IS NULL
db.query(UserCourse).filter(UserCourse.completed_at == None)
```

## Ordering and Limiting

```python
# Order by ascending
db.query(Lesson).filter(
    Lesson.course_id == 1
).order_by(Lesson.sequence_number).all()

# Order by descending
db.query(QuizSession).order_by(
    QuizSession.started_at.desc()
).all()

# Limit and offset
db.query(User).limit(10).offset(20).all()  # Page 3 with 10 per page

# Count
count = db.query(User).count()
```

## Error Handling

```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

try:
    db.add(record)
    db.commit()
except IntegrityError as e:
    db.rollback()
    # Handle unique constraint, foreign key violation, etc.
except SQLAlchemyError as e:
    db.rollback()
    # Handle other database errors
```

## Session Management

```python
from app.database import SessionLocal, get_db
from fastapi import Depends

# Manual session
db = SessionLocal()
try:
    # Use db
finally:
    db.close()

# FastAPI dependency (auto-closes)
@app.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User).get(user_id)
```

## Performance Tips

1. **Use indexes**: ForeignKey, status, timestamp columns
2. **Eager load**: Use `joinedload()` to prevent N+1 queries
3. **Lazy load**: Use `lazy="select"` for large collections
4. **Limit results**: Use `.limit()` for large queries
5. **Batch operations**: Group inserts/updates in transactions
6. **Avoid loading unnecessary data**: Use `.only()` to select specific columns

## Testing Models

```python
from app.models import User
from app.database import Base, engine

# Create test tables
Base.metadata.create_all(bind=engine)

# Use in tests
def test_user_creation():
    db = SessionLocal()
    user = User(telegram_id="test", username="test", level=0)
    db.add(user)
    db.commit()
    
    result = db.query(User).filter(User.telegram_id == "test").first()
    assert result is not None
    assert result.username == "test"
    
    db.close()
```

## Common Mistakes to Avoid

1. **Not committing**: Changes must be committed to persist
   ```python
   db.add(user)
   db.commit()  # Don't forget!
   ```

2. **Accessing relationships after session close**: Load them first
   ```python
   user = db.query(User).options(joinedload(User.user_courses)).get(1)
   db.close()
   print(user.user_courses)  # OK - already loaded
   ```

3. **Modifying lazy-loaded collections outside session**:
   ```python
   db.close()
   user.user_courses.append(uc)  # Error!
   ```

4. **Forgetting about cascade deletes**: Can delete more than intended
   ```python
   db.delete(user)  # Also deletes user_courses, quiz_sessions, quiz_answers
   ```

5. **Not using indexes for frequent queries**: Makes queries slow

## Database Setup

### Using Alembic (Recommended)
```bash
cd backend
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### Direct Creation
```python
from app.database import Base, engine
from app.models import *

Base.metadata.create_all(bind=engine)
```

### Database URL Format
```
mysql+pymysql://user:password@localhost:3306/dbname
```

## Useful Snippets

### Get user with all data loaded
```python
user = db.query(User).options(
    joinedload(User.user_courses).joinedload(UserCourse.course),
    joinedload(User.quiz_sessions).joinedload(QuizSession.lesson),
).filter(User.user_id == user_id).first()
```

### Get recent quiz sessions
```python
sessions = db.query(QuizSession).filter(
    QuizSession.status == "completed"
).order_by(QuizSession.completed_at.desc()).limit(10).all()
```

### Get user's mastered concepts
```python
mastered = []
for summary in db.query(QuizSummary).filter(
    QuizSummary.session_id.in_(
        db.query(QuizSession.session_id).filter(
            QuizSession.user_id == user_id
        )
    )
).all():
    mastered.extend(summary.concepts_mastered or [])
```

### Bulk insert
```python
users = [
    User(telegram_id=f"user_{i}", username=f"user{i}", level=0)
    for i in range(100)
]
db.add_all(users)
db.commit()
```

## Related Documentation
- See `MODELS_DOCUMENTATION.md` for detailed model descriptions
- See `MODELS_RELATIONSHIP_DIAGRAM.txt` for visual relationships
- SQLAlchemy docs: https://docs.sqlalchemy.org/

