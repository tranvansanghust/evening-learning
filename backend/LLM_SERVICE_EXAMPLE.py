"""
Example: End-to-end LLM Service usage in a quiz flow.

This example shows how the LLMService integrates into a complete quiz flow,
demonstrating all the methods and expected responses.

Note: This is pseudocode showing the integration pattern. In real implementation,
this would be part of QuizService and called from routers.
"""

from app.services.llm_service import LLMService
from app.config import get_settings


async def example_quiz_flow():
    """
    Complete example of a quiz session using LLMService.

    Demonstrates:
    1. Generating first question
    2. Getting user answer
    3. Evaluating answer
    4. Deciding next action
    5. Generating follow-up or next question
    6. Ending quiz and generating summary
    """

    # Initialize service
    settings = get_settings()
    llm = LLMService(api_key=settings.anthropic_api_key)

    # ===== QUIZ SETUP =====
    lesson_content = """
    The SQL WHERE clause is used to filter records based on specified conditions.
    It allows you to select only the rows that meet certain criteria.

    Syntax: SELECT column_name FROM table_name WHERE condition;

    Examples:
    - WHERE age > 18
    - WHERE department = 'Sales'
    - WHERE salary BETWEEN 50000 AND 100000
    - WHERE name LIKE 'A%'

    You can combine conditions with AND, OR, NOT operators.
    """

    concepts = ["WHERE", "filtering", "conditions", "operators"]
    conversation_history = []

    # ===== QUESTION 1: FIRST QUESTION =====
    print("\n=== QUIZ STARTS ===")

    question_1 = await llm.generate_quiz_question(
        lesson_content=lesson_content,
        conversation_history=conversation_history,
        concepts=concepts,
        is_first_question=True
    )

    print(f"\nBot: {question_1}")
    # Expected: "What is the purpose of the WHERE clause in SQL?"

    # Add to conversation
    conversation_history.append({"role": "assistant", "content": question_1})

    # ===== ANSWER 1: USER RESPONDS =====
    user_answer_1 = "The WHERE clause is used to filter rows in a table based on specific conditions."

    print(f"User: {user_answer_1}")
    conversation_history.append({"role": "user", "content": user_answer_1})

    # ===== EVALUATE ANSWER 1 =====
    evaluation_1 = await llm.evaluate_answer(
        question=question_1,
        user_answer=user_answer_1,
        lesson_context=lesson_content,
        concepts=concepts
    )

    print(f"\nEvaluation 1:")
    print(f"  - Correct: {evaluation_1.is_correct}")
    print(f"  - Confidence: {evaluation_1.confidence:.2f}")
    print(f"  - Engagement: {evaluation_1.engagement_level}")
    print(f"  - Covered: {evaluation_1.key_concepts_covered}")
    print(f"  - Missed: {evaluation_1.key_concepts_missed}")
    print(f"  - Feedback: {evaluation_1.feedback}")

    # Expected output:
    # {
    #   "is_correct": true,
    #   "confidence": 0.95,
    #   "engagement_level": "medium",
    #   "key_concepts_covered": ["WHERE", "filtering"],
    #   "key_concepts_missed": [],
    #   "feedback": "Good explanation of the WHERE clause's purpose!"
    # }

    # ===== DECIDE NEXT ACTION 1 =====
    action_1 = await llm.decide_next_action(
        answer_evaluation=evaluation_1,
        question_count=1,
        max_questions=5
    )

    print(f"\nDecision 1: {action_1.action_type}")
    print(f"  - Reason: {action_1.reason}")

    # Expected: action_type = "continue" (student answered well, ask next concept)

    # ===== QUESTION 2: NEXT QUESTION (DIFFERENT CONCEPT) =====
    question_2 = await llm.generate_quiz_question(
        lesson_content=lesson_content,
        conversation_history=conversation_history,
        concepts=concepts,
        is_first_question=False
    )

    print(f"\nBot: {question_2}")
    # Expected: "Can you give an example of how you would use WHERE to filter records?"

    conversation_history.append({"role": "assistant", "content": question_2})

    # ===== ANSWER 2: USER RESPONDS =====
    user_answer_2 = "Um, I guess you would like, put a WHERE somewhere?"

    print(f"User: {user_answer_2}")
    conversation_history.append({"role": "user", "content": user_answer_2})

    # ===== EVALUATE ANSWER 2 =====
    evaluation_2 = await llm.evaluate_answer(
        question=question_2,
        user_answer=user_answer_2,
        lesson_context=lesson_content,
        concepts=concepts
    )

    print(f"\nEvaluation 2:")
    print(f"  - Correct: {evaluation_2.is_correct}")
    print(f"  - Confidence: {evaluation_2.confidence:.2f}")
    print(f"  - Engagement: {evaluation_2.engagement_level}")
    print(f"  - Missed: {evaluation_2.key_concepts_missed}")

    # Expected:
    # {
    #   "is_correct": false,
    #   "confidence": 0.88,
    #   "engagement_level": "low",
    #   "key_concepts_covered": [],
    #   "key_concepts_missed": ["WHERE", "conditions"],
    #   "feedback": "You're on the right track, but let's clarify with a concrete example..."
    # }

    # ===== DECIDE NEXT ACTION 2 =====
    action_2 = await llm.decide_next_action(
        answer_evaluation=evaluation_2,
        question_count=2,
        max_questions=5
    )

    print(f"\nDecision 2: {action_2.action_type}")
    print(f"  - Reason: {action_2.reason}")

    # Expected: action_type = "followup" (student struggled, need to clarify)
    # with follow_up_question = "Let me ask it differently..."

    # ===== QUESTION 3: FOLLOW-UP =====
    if action_2.action_type == "followup":
        question_3 = action_2.follow_up_question
        print(f"\nBot (Follow-up): {question_3}")
        conversation_history.append({"role": "assistant", "content": question_3})

        user_answer_3 = "SELECT * FROM employees WHERE age > 18"
        print(f"User: {user_answer_3}")
        conversation_history.append({"role": "user", "content": user_answer_3})

        evaluation_3 = await llm.evaluate_answer(
            question=question_3,
            user_answer=user_answer_3,
            lesson_context=lesson_content,
            concepts=concepts
        )

        print(f"\nEvaluation 3:")
        print(f"  - Correct: {evaluation_3.is_correct}")
        print(f"  - Engagement: {evaluation_3.engagement_level}")

        # Expected: correct=true, engagement=high

        action_3 = await llm.decide_next_action(
            answer_evaluation=evaluation_3,
            question_count=3,
            max_questions=5
        )

        print(f"\nDecision 3: {action_3.action_type}")

        # After 3 questions with good coverage, might decide to "end"

    # ===== QUIZ SUMMARY =====
    if action_3.action_type == "end":
        print("\n=== GENERATING SUMMARY ===")

        summary = await llm.generate_quiz_summary(
            lesson_name="SQL WHERE Clause",
            lesson_content=lesson_content,
            conversation_history=conversation_history,
            concepts=concepts
        )

        print(f"\nSummary:")
        print(f"  - Mastered: {summary.concepts_mastered}")
        print(f"  - Weak: {[w.concept for w in summary.concepts_weak]}")
        print(f"  - Engagement: {summary.engagement_quality}")
        print(f"  - Summary: {summary.summary_text}")
        print(f"  - Suggestions:")
        for suggestion in summary.suggestions:
            print(f"    • {suggestion}")

        # Expected:
        # {
        #   "concepts_mastered": ["WHERE", "filtering"],
        #   "concepts_weak": [
        #     {
        #       "concept": "conditions",
        #       "user_answer": "I guess you would like, put a WHERE somewhere?",
        #       "correct_explanation": "Conditions use operators like >, <, =, BETWEEN, LIKE..."
        #     }
        #   ],
        #   "engagement_quality": "medium",
        #   "summary_text": "You demonstrated understanding of WHERE's purpose...",
        #   "suggestions": [
        #     "Practice writing WHERE conditions with different operators",
        #     "Review the BETWEEN and LIKE operators with examples"
        #   ]
        # }

        # ===== SUGGEST NEXT COURSES =====
        print("\n=== SUGGESTING NEXT COURSES ===")

        suggestions = await llm.suggest_next_courses(
            completed_course_name="SQL WHERE Clause",
            user_level=1,  # Beginner-Intermediate
            completed_concepts=summary.concepts_mastered
        )

        print(f"\nRecommended next courses:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.course_name}")
            print(f"     → {suggestion.reason}")

        # Expected:
        # [
        #   {
        #     "course_name": "SQL JOINs and Multiple Tables",
        #     "reason": "Natural progression to combine data from multiple sources"
        #   },
        #   {
        #     "course_name": "Advanced WHERE: Subqueries and Complex Conditions",
        #     "reason": "Deepen your understanding of filtering with advanced techniques"
        #   },
        #   {
        #     "course_name": "Database Indexing and Query Optimization",
        #     "reason": "Learn to write efficient WHERE clauses for large datasets"
        #   }
        # ]

        print("\n=== QUIZ COMPLETE ===\n")


# ===== INTEGRATION WITH QUIZ SERVICE =====

"""
In a real QuizService, this would look like:

class QuizService:
    def __init__(self, db: Session, llm_service: LLMService):
        self.db = db
        self.llm = llm_service

    async def start_quiz(self, user_id: int, lesson_id: int):
        # Create session
        session = QuizSession(user_id=user_id, lesson_id=lesson_id)
        self.db.add(session)
        self.db.commit()

        # Get lesson
        lesson = self.db.query(Lesson).get(lesson_id)

        # Generate first question
        question = await self.llm.generate_quiz_question(
            lesson_content=lesson.content,
            conversation_history=[],
            concepts=[c.name for c in lesson.concepts],
            is_first_question=True
        )

        # Save to session
        session.messages = [{"role": "assistant", "content": question}]
        self.db.commit()

        return {"session_id": session.session_id, "question": question}

    async def answer_question(self, session_id: int, answer: str):
        session = self.db.query(QuizSession).get(session_id)

        # Get the question that was asked
        last_question = session.messages[-1]["content"]

        # Evaluate answer
        evaluation = await self.llm.evaluate_answer(
            question=last_question,
            user_answer=answer,
            lesson_context=session.lesson.content,
            concepts=[c.name for c in session.lesson.concepts]
        )

        # Save answer to database
        quiz_answer = QuizAnswer(
            session_id=session_id,
            question=last_question,
            user_answer=answer,
            is_correct=evaluation.is_correct,
            engagement_level=evaluation.engagement_level
        )
        self.db.add(quiz_answer)

        # Decide next action
        question_count = len([m for m in session.messages if m["role"] == "assistant"])
        action = await self.llm.decide_next_action(
            answer_evaluation=evaluation,
            question_count=question_count,
            max_questions=5
        )

        # Update conversation
        session.messages.append({"role": "user", "content": answer})

        # Determine next response
        next_question = None
        if action.action_type == "end":
            # Generate summary
            summary = await self.llm.generate_quiz_summary(
                lesson_name=session.lesson.title,
                lesson_content=session.lesson.content,
                conversation_history=session.messages,
                concepts=[c.name for c in session.lesson.concepts]
            )

            # Save summary
            quiz_summary = QuizSummary(
                session_id=session_id,
                concepts_mastered=summary.concepts_mastered,
                concepts_weak=json.dumps([w.model_dump() for w in summary.concepts_weak])
            )
            self.db.add(quiz_summary)

            # Check if PASS or FAIL
            mastery_rate = len(summary.concepts_mastered) / len([c for c in session.lesson.concepts])
            if mastery_rate >= 0.75:
                # PASS flow - suggest next courses
                suggestions = await self.llm.suggest_next_courses(
                    completed_course_name=session.lesson.course.name,
                    user_level=session.user.level,
                    completed_concepts=summary.concepts_mastered
                )
                # Return suggestions to user

            session.status = "completed"
        elif action.action_type == "followup":
            next_question = action.follow_up_question
            session.messages.append({"role": "assistant", "content": next_question})
        else:  # continue
            # Generate next question
            next_question = await self.llm.generate_quiz_question(
                lesson_content=session.lesson.content,
                conversation_history=session.messages,
                concepts=[c.name for c in session.lesson.concepts],
                is_first_question=False
            )
            session.messages.append({"role": "assistant", "content": next_question})

        self.db.commit()

        return {
            "evaluation": evaluation,
            "action": action.action_type,
            "next_question": next_question
        }
"""


if __name__ == "__main__":
    import asyncio

    # Run the example (requires API key in .env)
    asyncio.run(example_quiz_flow())
