# LLM Service Integration Guide

## Overview

The LLM Service provides a clean interface for all Claude API interactions in the learning system. It handles quiz question generation, answer evaluation, quiz flow decisions, summary generation, and course recommendations.

## Components

### 1. LLMPrompts (`app/services/llm_prompts.py`)

Contains all prompt templates as static methods in the `LLMPrompts` class. Each method generates a formatted prompt for a specific task.

**Available Prompts:**

- `quiz_question_generation()` - Generate quiz questions
- `answer_evaluation()` - Evaluate user answers
- `decide_next_action()` - Decide quiz progression
- `quiz_summary_generation()` - Generate post-quiz summaries
- `suggest_next_courses()` - Recommend next courses

### 2. LLMService (`app/services/llm_service.py`)

Main service class that handles all Claude API calls with error handling, logging, and structured responses.

**Model Selection Strategy:**
- **Fast tasks** (claude-haiku-4-5): Question generation, decision making
- **Complex tasks** (claude-sonnet-4-6): Answer evaluation, summaries, recommendations

**Methods:**

#### `generate_quiz_question()`
Generates a conversational quiz question from lesson content.

```python
question = await service.generate_quiz_question(
    lesson_content="The SQL WHERE clause filters rows...",
    conversation_history=[],
    concepts=["WHERE", "conditions"],
    is_first_question=True
)
# Returns: "What does the WHERE clause do in SQL queries?"
```

#### `evaluate_answer()`
Evaluates if an answer is correct and returns structured feedback.

```python
evaluation = await service.evaluate_answer(
    question="What is a WHERE clause?",
    user_answer="It filters rows based on conditions",
    lesson_context="SQL WHERE clause filters rows...",
    concepts=["WHERE"]
)
# Returns AnswerEvaluation with:
# - is_correct: bool
# - confidence: 0.0-1.0
# - engagement_level: "low" | "medium" | "high"
# - key_concepts_covered: ["WHERE"]
# - key_concepts_missed: []
# - feedback: "Great explanation!"
```

#### `decide_next_action()`
Decides whether to continue quiz, ask follow-up, or end.

```python
action = await service.decide_next_action(
    answer_evaluation=evaluation,
    question_count=2,
    max_questions=5
)
# Returns NextAction with:
# - action_type: "continue" | "followup" | "end"
# - reason: "Student answered well..."
# - follow_up_question: Optional[str]
```

#### `generate_quiz_summary()`
Creates comprehensive post-quiz summary.

```python
summary = await service.generate_quiz_summary(
    lesson_name="SQL Basics",
    lesson_content="SELECT, WHERE, JOIN...",
    conversation_history=[
        {"role": "assistant", "content": "What is...?"},
        {"role": "user", "content": "It is..."}
    ],
    concepts=["SELECT", "WHERE", "JOIN"]
)
# Returns QuizSummary with:
# - concepts_mastered: ["WHERE"]
# - concepts_weak: [{"concept": "JOIN", "user_answer": "...", "correct_explanation": "..."}]
# - engagement_quality: "high"
# - summary_text: "You demonstrated strong understanding..."
# - suggestions: ["Practice JOINs with more examples"]
```

#### `suggest_next_courses()`
Suggests 3 logical next courses for the user.

```python
suggestions = await service.suggest_next_courses(
    completed_course_name="SQL Basics",
    user_level=1,
    completed_concepts=["SELECT", "WHERE"]
)
# Returns List[CourseSuggestion]:
# [
#   {"course_name": "Advanced SQL", "reason": "Builds on your SELECT/WHERE mastery"},
#   ...
# ]
```

## Pydantic Models

All responses are strongly-typed Pydantic models:

### AnswerEvaluation
```python
AnswerEvaluation(
    is_correct: bool,
    confidence: float,  # 0.0-1.0
    engagement_level: EngagementLevel,  # "low" | "medium" | "high"
    key_concepts_covered: List[str],
    key_concepts_missed: List[str],
    feedback: str
)
```

### NextAction
```python
NextAction(
    action_type: ActionType,  # "continue" | "followup" | "end"
    reason: str,
    follow_up_question: Optional[str]
)
```

### QuizSummary
```python
QuizSummary(
    concepts_mastered: List[str],
    concepts_weak: List[WeakConcept],
    engagement_quality: EngagementLevel,
    summary_text: str,
    suggestions: List[str]
)
```

### CourseSuggestion
```python
CourseSuggestion(
    course_name: str,
    reason: str
)
```

## Integration with Quiz Service

The LLMService is meant to be called by a higher-level QuizService. Here's the typical flow:

```python
from app.services.llm_service import LLMService
from app.config import get_settings

settings = get_settings()
llm_service = LLMService(api_key=settings.anthropic_api_key)

# Quiz flow example:
class QuizService:
    def __init__(self, db: Session, llm_service: LLMService):
        self.db = db
        self.llm = llm_service

    async def start_quiz(self, user_id: int, lesson_id: int):
        # Create session
        session = QuizSession(user_id=user_id, lesson_id=lesson_id)
        self.db.add(session)
        self.db.commit()

        # Generate first question
        lesson = self.db.query(Lesson).get(lesson_id)
        question = await self.llm.generate_quiz_question(
            lesson_content=lesson.content,
            conversation_history=[],
            concepts=[c.name for c in lesson.concepts],
            is_first_question=True
        )

        # Save and return
        session.messages = [{"role": "assistant", "content": question}]
        self.db.commit()
        return question

    async def answer_question(self, session_id: int, answer: str):
        session = self.db.query(QuizSession).get(session_id)

        # Evaluate answer
        evaluation = await self.llm.evaluate_answer(
            question=session.messages[-1]["content"],
            user_answer=answer,
            lesson_context=session.lesson.content,
            concepts=[c.name for c in session.lesson.concepts]
        )

        # Save answer
        quiz_answer = QuizAnswer(
            session_id=session_id,
            question=session.messages[-1]["content"],
            user_answer=answer,
            is_correct=evaluation.is_correct,
            engagement_level=evaluation.engagement_level
        )

        # Decide next action
        action = await self.llm.decide_next_action(
            answer_evaluation=evaluation,
            question_count=len(session.quiz_answers) + 1
        )

        if action.action_type == "end":
            # Generate summary
            summary = await self.llm.generate_quiz_summary(
                lesson_name=session.lesson.title,
                lesson_content=session.lesson.content,
                conversation_history=session.messages,
                concepts=[c.name for c in session.lesson.concepts]
            )
            # Save summary...
            session.status = "completed"
        elif action.action_type == "followup":
            # Use the follow_up_question
            question = action.follow_up_question
        else:
            # Generate next question
            question = await self.llm.generate_quiz_question(...)

        # Update session and return
        session.messages.append({"role": "user", "content": answer})
        session.messages.append({"role": "assistant", "content": question})
        self.db.commit()

        return {
            "evaluation": evaluation,
            "next_question": question if action.action_type != "end" else None
        }
```

## Error Handling

The LLMService includes comprehensive error handling:

```python
from anthropic import APIError, RateLimitError, APITimeoutError

try:
    question = await llm_service.generate_quiz_question(...)
except RateLimitError:
    # Handle rate limiting - implement backoff
    pass
except APITimeoutError:
    # Handle timeout - retry or fail gracefully
    pass
except APIError as e:
    # Handle other API errors
    logger.error(f"API error: {e}")
except ValueError as e:
    # Handle validation errors (empty inputs, etc.)
    logger.error(f"Validation error: {e}")
```

## Configuration

Requires `anthropic_api_key` in environment variables or `.env` file:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

The LLMService initializes with config:

```python
from app.config import get_settings

settings = get_settings()
llm_service = LLMService(api_key=settings.anthropic_api_key)
```

## Logging

All operations are logged at INFO and ERROR levels:

```
INFO - LLMService initialized with Anthropic API
INFO - Generated quiz question (first=True, concepts=2)
INFO - Evaluated answer (correct=True, engagement=high, concepts_covered=1)
INFO - Decision made: continue (q2/5)
ERROR - API error when generating question: Connection timeout
```

## Models Used

- **claude-haiku-4-5-20251001** - Fast model for simple tasks
  - Quiz question generation
  - Next action decisions

- **claude-sonnet-4-6-20250514** - Smart model for complex analysis
  - Answer evaluation with detailed feedback
  - Quiz summary generation
  - Course recommendations

## Response Examples

### Quiz Question
```
"Can you explain what a JOIN does in SQL and why it's useful?"
```

### Answer Evaluation
```json
{
  "is_correct": true,
  "confidence": 0.92,
  "engagement_level": "high",
  "key_concepts_covered": ["JOIN", "relationship"],
  "key_concepts_missed": [],
  "feedback": "Excellent explanation! You clearly understand how JOINs combine tables."
}
```

### Next Action
```json
{
  "action_type": "continue",
  "reason": "Student answered well and engaged deeply. Ready for next concept.",
  "follow_up_question": null
}
```

### Quiz Summary
```json
{
  "concepts_mastered": ["SELECT", "WHERE"],
  "concepts_weak": [
    {
      "concept": "JOIN",
      "user_answer": "It combines tables with similar columns",
      "correct_explanation": "JOINs combine rows from multiple tables based on matching conditions"
    }
  ],
  "engagement_quality": "high",
  "summary_text": "You demonstrated solid understanding of basic SQL queries. Your grasp of WHERE clauses is particularly strong. JOIN operations need more practice to fully master.",
  "suggestions": ["Practice different JOIN types with real datasets", "Review the relationship between tables in the lesson"]
}
```

### Course Suggestions
```json
{
  "suggestions": [
    {
      "course_name": "Intermediate SQL: JOINs and Subqueries",
      "reason": "Natural progression after SQL Basics, builds on SELECT/WHERE mastery"
    },
    {
      "course_name": "Database Design Fundamentals",
      "reason": "Complements your SQL knowledge with design principles"
    },
    {
      "course_name": "Advanced SQL: Performance Optimization",
      "reason": "Next step after mastering queries, focuses on efficiency"
    }
  ]
}
```

## Testing

The service is designed to be testable with mock API responses:

```python
from unittest.mock import AsyncMock, patch

async def test_generate_question():
    service = LLMService(api_key="test-key")

    with patch.object(service.client.messages, 'create') as mock_create:
        mock_create.return_value = AsyncMock(
            content=[AsyncMock(text="Test question?")]
        )

        result = await service.generate_quiz_question(
            lesson_content="Test",
            conversation_history=[],
            concepts=["test"]
        )

        assert result == "Test question?"
```

## Next Steps

1. Create QuizService that uses LLMService
2. Create quiz routers (POST /api/quiz/start, /api/quiz/answer)
3. Add integration tests with Anthropic API
4. Implement rate limiting and retry logic
5. Add monitoring and performance metrics
