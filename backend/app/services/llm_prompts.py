"""
LLM prompt templates for the learning system.

This module contains all prompt templates used for Claude API calls.
Each prompt is designed for a specific task in the quiz flow:
- Generating quiz questions
- Evaluating answers
- Making decisions about quiz progression
- Generating summaries
- Suggesting next courses
"""

from typing import List, Dict, Any


class LLMPrompts:
    """Container class for all LLM prompt templates."""

    @staticmethod
    def quiz_question_generation(
        lesson_content: str,
        conversation_history: List[Dict[str, str]],
        concepts: List[str],
        is_first_question: bool = True
    ) -> str:
        """
        Generate prompt for creating a new quiz question.

        Args:
            lesson_content: The lesson text the user just learned
            conversation_history: List of previous Q&A pairs
            concepts: List of concept names to test
            is_first_question: Whether this is the first question

        Returns:
            str: The formatted prompt for Claude

        Example:
            >>> prompt = LLMPrompts.quiz_question_generation(
            ...     lesson_content="SQL is...",
            ...     conversation_history=[],
            ...     concepts=["JOIN", "WHERE"],
            ...     is_first_question=True
            ... )
        """
        history_section = ""
        if conversation_history:
            history_section = "Previous conversation:\n"
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_section += f"{role}: {msg['content']}\n"
            history_section += "\n"

        concepts_section = ", ".join(concepts)

        if is_first_question:
            prompt = f"""You are an expert AI tutor conducting an oral test for a student who just completed a lesson.

The student just learned:
{lesson_content}

Key concepts they should understand: {concepts_section}

Generate a natural, conversational first quiz question that:
1. Tests one of the key concepts they should have learned
2. Is open-ended (not multiple choice)
3. Encourages them to demonstrate understanding
4. Is appropriate for their level of learning (just completed the lesson)
5. Avoids being too complex or too trivial

Keep the question concise and friendly in tone.

IMPORTANT: Return ONLY the question text, no preamble or explanation."""
        else:
            prompt = f"""You are an expert AI tutor conducting an oral test for a student.

Lesson content being tested:
{lesson_content}

Key concepts to test: {concepts_section}

{history_section}

Based on the conversation history above, generate the next follow-up quiz question that:
1. Tests a different concept or aspect not yet covered
2. Builds naturally on what was discussed
3. Is conversational and flows from the previous exchange
4. Probes deeper into understanding if the student answered well
5. Is open-ended and encourages detailed response

Keep the question concise and maintain a friendly, encouraging tone.

IMPORTANT: Return ONLY the question text, no preamble or explanation."""

        return prompt

    @staticmethod
    def answer_evaluation(
        question: str,
        user_answer: str,
        lesson_context: str,
        concepts: List[str]
    ) -> str:
        """
        Generate prompt for evaluating a user's answer.

        Args:
            question: The question that was asked
            user_answer: The user's response
            lesson_context: The lesson content for context
            concepts: Key concepts being tested

        Returns:
            str: The formatted prompt for Claude
        """
        concepts_str = ", ".join(concepts)

        prompt = f"""You are an expert educator evaluating a student's understanding of lesson content.

LESSON CONTENT:
{lesson_context}

CONCEPTS BEING TESTED: {concepts_str}

QUESTION ASKED:
{question}

STUDENT'S ANSWER:
{user_answer}

Evaluate this answer and respond with a JSON object containing:
{{
  "is_correct": <boolean - is the answer fundamentally correct?>,
  "confidence": <float between 0.0 and 1.0 - how confident are you in this evaluation?>,
  "engagement_level": "<'low' | 'medium' | 'high' - quality and depth of response>",
  "key_concepts_covered": <list of concepts from the lesson that the student demonstrated understanding of>,
  "key_concepts_missed": <list of concepts they failed to address or misunderstood>,
  "feedback": "<brief, constructive feedback (1-2 sentences) encouraging them or pointing out what to review>"
}}

Guidelines:
- Accept partial understanding as correct if they got the main idea
- Consider engagement level: low = minimal/vague response, medium = adequate response, high = thoughtful/detailed
- Be encouraging but honest
- Return valid JSON only, no markdown formatting

IMPORTANT: Return ONLY the JSON object, no other text."""

        return prompt

    @staticmethod
    def decide_next_action(
        answer_evaluation: Dict[str, Any],
        question_count: int,
        max_questions: int = 5
    ) -> str:
        """
        Generate prompt for deciding the next quiz action.

        Args:
            answer_evaluation: The evaluation result from answer_evaluation prompt
            question_count: Number of questions asked so far
            max_questions: Maximum number of questions before ending quiz

        Returns:
            str: The formatted prompt for Claude
        """
        eval_summary = f"""
Current answer evaluation:
- Is correct: {answer_evaluation.get('is_correct', False)}
- Confidence: {answer_evaluation.get('confidence', 0.5)}
- Engagement level: {answer_evaluation.get('engagement_level', 'medium')}
- Concepts covered: {', '.join(answer_evaluation.get('key_concepts_covered', []))}
- Concepts missed: {', '.join(answer_evaluation.get('key_concepts_missed', []))}
"""

        prompt = f"""You are an AI tutor deciding whether to continue or end a quiz session.

{eval_summary}

CONTEXT:
- Questions asked so far: {question_count}
- Maximum questions per session: {max_questions}

Decide what to do next and respond with a JSON object:
{{
  "action_type": "<'continue' | 'followup' | 'end'>",
  "reason": "<brief explanation of the decision>",
  "follow_up_question": "<if action_type is 'followup', provide the follow-up question here. Otherwise, null>"
}}

Guidelines for decision:
- "continue": The student answered well and understands the concept. Ask about a different concept next.
- "followup": The student struggled or showed low engagement. Ask a follow-up to clarify or reinforce.
- "end": Student has demonstrated good understanding OR we've hit the question limit (5 questions).
- Generally, aim for 3-5 questions total before ending.
- If a student answers incorrectly, use "followup" to give them a chance to clarify.
- If engagement is "high" and answer is "correct" after 4+ questions, consider "end".

IMPORTANT: Return ONLY the JSON object, no other text."""

        return prompt

    @staticmethod
    def quiz_summary_generation(
        lesson_name: str,
        lesson_content: str,
        conversation_history: List[Dict[str, str]],
        concepts: List[str]
    ) -> str:
        """
        Generate prompt for creating a post-quiz summary.

        Args:
            lesson_name: Name of the lesson
            lesson_content: The lesson text
            conversation_history: Complete Q&A history from the quiz
            concepts: List of all concepts in the lesson

        Returns:
            str: The formatted prompt for Claude
        """
        history_section = "Quiz Q&A History:\n"
        for i, msg in enumerate(conversation_history):
            if msg["role"] == "assistant":
                history_section += f"Q{(i//2)+1}: {msg['content']}\n"
            else:
                history_section += f"A{(i//2)+1}: {msg['content']}\n"

        concepts_str = ", ".join(concepts)

        prompt = f"""You are an expert educator creating a summary of a student's quiz performance.

LESSON: {lesson_name}

LESSON CONTENT:
{lesson_content}

ALL CONCEPTS IN LESSON: {concepts_str}

{history_section}

Based on the entire quiz conversation above, generate a comprehensive JSON summary:
{{
  "concepts_mastered": <list of concepts the student clearly understands>,
  "concepts_weak": <list of concepts the student struggled with or didn't understand>,
  "engagement_quality": "<'low' | 'medium' | 'high' - overall engagement throughout quiz>",
  "summary_text": "<2-3 sentence summary of overall performance and key takeaways>",
  "suggestions": <list of 2-3 concrete suggestions for next steps in learning>
}}

Guidelines:
- "concepts_mastered": Only include if student answered questions about them correctly with good engagement
- "concepts_weak": Include concepts they got wrong, struggled with, or didn't address
- "suggestions": Be specific and actionable (e.g., "Review JOIN syntax with more examples", not "Study harder")
- Be encouraging while honest about areas needing improvement
- Consider the overall quality and depth of responses

IMPORTANT: Return ONLY the JSON object, no other text."""

        return prompt

    @staticmethod
    def suggest_next_courses(
        completed_course_name: str,
        user_level: int,
        completed_concepts: List[str]
    ) -> str:
        """
        Generate prompt for suggesting next courses.

        Args:
            completed_course_name: Name of the course just completed
            user_level: User's skill level (0-3)
            completed_concepts: Concepts mastered in completed course

        Returns:
            str: The formatted prompt for Claude
        """
        level_description = {
            0: "Beginner - just starting to learn programming",
            1: "Beginner-Intermediate - comfortable with basics",
            2: "Intermediate - can write simple programs",
            3: "Advanced - experienced programmer"
        }

        level_desc = level_description.get(user_level, "Unknown")
        concepts_str = ", ".join(completed_concepts) if completed_concepts else "various concepts"

        prompt = f"""You are an expert learning path designer.

A student just completed a course and demonstrated mastery of:
COURSE: {completed_course_name}
CONCEPTS LEARNED: {concepts_str}

STUDENT PROFILE:
- Experience level: {user_level} ({level_desc})

Suggest exactly 3 logical next courses that:
1. Build on the concepts they just mastered
2. Are appropriate for their experience level
3. Progress their learning in a natural sequence
4. Cover different but complementary topics

Respond with a JSON object:
{{
  "suggestions": [
    {{
      "course_name": "<course title>",
      "reason": "<brief explanation of why this is a good next step>"
    }},
    {{
      "course_name": "<course title>",
      "reason": "<brief explanation>"
    }},
    {{
      "course_name": "<course title>",
      "reason": "<brief explanation>"
    }}
  ]
}}

Be specific with course names and make them sound realistic and educational.

IMPORTANT: Return ONLY the JSON object, no other text."""

        return prompt
