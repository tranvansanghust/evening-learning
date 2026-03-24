# Services Module

This module contains all business logic services for the learning system.

## Services

### 1. LLMService (`llm_service.py`)
**Purpose:** Handle all Claude API interactions for quiz flow

**Key Classes:**
- `LLMService` - Main service class
- `AnswerEvaluation` - Answer evaluation results
- `NextAction` - Quiz flow decision
- `QuizSummary` - Post-quiz summary
- `ConversationMessage` - Conversation message
- `CourseSuggestion` - Suggested course

**Key Methods:**
- `generate_quiz_question()` - Generate quiz questions
- `evaluate_answer()` - Evaluate user answers
- `decide_next_action()` - Decide quiz progression
- `generate_quiz_summary()` - Generate post-quiz summary
- `suggest_next_courses()` - Recommend next courses

**Usage:**
```python
from app.services.llm_service import LLMService
from app.config import get_settings

settings = get_settings()
llm_service = LLMService(api_key=settings.anthropic_api_key)

# Generate first question
question = await llm_service.generate_quiz_question(
    lesson_content="SQL WHERE clause...",
    conversation_history=[],
    concepts=["WHERE", "filtering"]
)
```

### 2. LLMPrompts (`llm_prompts.py`)
**Purpose:** Store prompt templates for Claude API calls

**Key Methods:**
- `quiz_question_generation()` - Prompt for question generation
- `answer_evaluation()` - Prompt for answer evaluation
- `decide_next_action()` - Prompt for quiz decisions
- `quiz_summary_generation()` - Prompt for summary generation
- `suggest_next_courses()` - Prompt for course suggestions

**Note:** These are called internally by LLMService, but can be used standalone for prompt inspection/testing.

### 3. OnboardingService (`onboarding_service.py`)
**Purpose:** Handle user onboarding flow

**Key Methods:**
- `create_user()` - Create new user
- `create_onboarding_state()` - Track onboarding progress
- `get_or_detect_course()` - Find course from URL or topic
- `assess_user_level()` - Determine user skill level
- `generate_curriculum()` - Create course structure

### 4. TelegramService (`telegram_service.py`)
**Purpose:** Handle Telegram Bot communications

**Key Methods:**
- `send_message()` - Send text message
- `send_message_with_buttons()` - Send message with inline buttons
- `parse_update()` - Parse incoming Telegram updates

## Architecture

```
Services
├── LLMService (Claude API)
│   └── uses LLMPrompts for prompt generation
├── QuizService (to be created)
│   └── uses LLMService for quiz flow
├── OnboardingService (User onboarding)
├── TelegramService (Telegram Bot)
└── (Others as needed)
```

## Error Handling

All services include comprehensive error handling:
- Validation errors (ValueError)
- API errors (APIError, RateLimitError, APITimeoutError)
- Database errors (SQLAlchemy exceptions)
- Logging at all levels (DEBUG, INFO, WARNING, ERROR)

## Async Support

The LLMService supports async/await:

```python
# Async usage
question = await llm_service.generate_quiz_question(...)
evaluation = await llm_service.evaluate_answer(...)

# In async context
async def quiz_handler(user_id: int, lesson_id: int):
    llm_service = LLMService(api_key=settings.anthropic_api_key)
    question = await llm_service.generate_quiz_question(...)
    return question
```

## Models

All services use Pydantic models for type safety:
- Request validation
- Response structure
- Automatic serialization to JSON

Example:
```python
from app.services.llm_service import AnswerEvaluation

evaluation = AnswerEvaluation(
    is_correct=True,
    confidence=0.95,
    engagement_level="high",
    key_concepts_covered=["WHERE"],
    key_concepts_missed=[],
    feedback="Great job!"
)

# Serialize to dict/JSON
eval_dict = evaluation.model_dump()
eval_json = evaluation.model_dump_json()
```

## Testing

Services are designed to be testable with mocks:

```python
from unittest.mock import AsyncMock, patch

# Mock LLMService
mock_llm = AsyncMock(spec=LLMService)
mock_llm.generate_quiz_question.return_value = "Test question?"

# Use in test
result = await mock_llm.generate_quiz_question(...)
```

## Logging

All services include detailed logging:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Operation started")
logger.error("Operation failed", exc_info=True)
```

View logs from services for debugging.
