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
        is_first_question: bool = True,
        course_topic: str = ""
    ) -> str:
        """
        Generate prompt for creating a new quiz question.

        Args:
            lesson_content: The lesson text the user just learned
            conversation_history: List of previous Q&A pairs
            concepts: List of concept names to test
            is_first_question: Whether this is the first question
            course_topic: The course topic/name (anchor for questions)

        Returns:
            str: The formatted prompt for Claude

        Example:
            >>> prompt = LLMPrompts.quiz_question_generation(
            ...     lesson_content="SQL is...",
            ...     conversation_history=[],
            ...     concepts=["JOIN", "WHERE"],
            ...     is_first_question=True,
            ...     course_topic="SQL Basics"
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
        topic_section = f'về "{course_topic}" ' if course_topic else ""

        if is_first_question:
            prompt = f"""Tạo một câu hỏi ôn tập {topic_section}bằng tiếng Việt cho học viên vừa học xong bài sau:

---
{lesson_content}
---

Khái niệm cần kiểm tra: {concepts_section}

Yêu cầu cho câu hỏi:
- Câu hỏi PHẢI liên quan đến chủ đề "{course_topic}" nếu được cung cấp
- Hỏi về một trong các khái niệm trên
- Câu hỏi mở, không phải trắc nghiệm
- Ngắn gọn, thân thiện
- Bằng tiếng Việt

Chỉ trả về câu hỏi, không thêm bất kỳ text nào khác."""
        else:
            prompt = f"""Tạo câu hỏi ôn tập {topic_section}tiếp theo bằng tiếng Việt.

Nội dung bài học:
---
{lesson_content}
---

Khái niệm cần kiểm tra: {concepts_section}

{history_section}
Yêu cầu:
- Câu hỏi PHẢI liên quan đến chủ đề "{course_topic}" nếu được cung cấp
- Hỏi về khái niệm chưa được đề cập trong lịch sử hội thoại
- Tiếp nối tự nhiên với câu trả lời trước
- Câu hỏi mở, khuyến khích giải thích
- Bằng tiếng Việt

Chỉ trả về câu hỏi, không thêm bất kỳ text nào khác."""

        return prompt

    @staticmethod
    def answer_evaluation(
        question: str,
        user_answer: str,
        lesson_context: str,
        concepts: List[str],
        course_topic: str = ""
    ) -> str:
        """
        Generate prompt for evaluating a user's answer.

        Args:
            question: The question that was asked
            user_answer: The user's response
            lesson_context: The lesson content for context
            concepts: Key concepts being tested
            course_topic: The course topic/name for off-topic validation

        Returns:
            str: The formatted prompt for Claude
        """
        concepts_str = ", ".join(concepts)
        topic_section = f"\nKHÓA HỌC: {course_topic}" if course_topic else ""
        topic_validation = (
            f'\nQUAN TRỌNG: Nếu câu trả lời không liên quan đến khóa học "{course_topic}", '
            f'hãy đặt is_correct=false và feedback nhắc học viên trả lời đúng chủ đề "{course_topic}".'
        ) if course_topic else ""

        prompt = f"""Đánh giá câu trả lời của học viên dựa trên nội dung bài học.{topic_section}

NỘI DUNG BÀI HỌC:
{lesson_context}

KHÁI NIỆM CẦN KIỂM TRA: {concepts_str}

CÂU HỎI:
{question}

CÂU TRẢ LỜI CỦA HỌC VIÊN:
{user_answer}
{topic_validation}
Trả về JSON object:
{{
  "is_correct": <true/false - câu trả lời có đúng về cơ bản không?>,
  "confidence": <số thực 0.0-1.0 - độ chắc chắn của đánh giá>,
  "engagement_level": "<'low' | 'medium' | 'high' - chất lượng và độ sâu của câu trả lời>",
  "key_concepts_covered": <danh sách khái niệm học viên hiểu đúng>,
  "key_concepts_missed": <danh sách khái niệm học viên bỏ sót hoặc hiểu sai>,
  "feedback": "<1-2 câu phản hồi ngắn bằng tiếng Việt, động viên và chỉ ra điều cần ôn>"
}}

Hướng dẫn:
- Chấp nhận hiểu biết một phần là đúng nếu nắm được ý chính
- low = trả lời sơ sài / không liên quan / muốn kết thúc, medium = trả lời đủ ý, high = giải thích chi tiết và sâu
- Nếu học viên tỏ ý muốn kết thúc (ví dụ: "thôi", "kết thúc", "xong rồi", "stop", "enough"): đặt engagement_level="low", is_correct=false
- Phản hồi bằng tiếng Việt
- Chỉ trả về JSON, không có markdown hay text khác

QUAN TRỌNG: Chỉ trả về JSON object."""

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

        prompt = f"""Quyết định bước tiếp theo trong buổi ôn tập kiến thức của học viên.

{eval_summary}

THÔNG TIN:
- Số câu hỏi đã hỏi: {question_count}
- Giới hạn tối đa: {max_questions} câu

Trả về JSON object:
{{
  "action_type": "<'continue' | 'followup' | 'end'>",
  "reason": "<giải thích ngắn gọn lý do quyết định>",
  "follow_up_question": "<nếu action_type là 'followup', đặt câu hỏi bổ sung bằng tiếng Việt. Nếu không, null>"
}}

Hướng dẫn:
- "continue": học viên trả lời tốt → hỏi về khái niệm khác
- "followup": học viên còn nhầm hoặc trả lời sơ sài → hỏi thêm để làm rõ
- "end": học viên hiểu tốt HOẶC đã đạt giới hạn số câu hỏi HOẶC engagement_level="low"
- Nếu engagement_level="low": luôn chọn "end" — học viên không muốn tiếp tục
- Thông thường hỏi 3-5 câu rồi kết thúc
- follow_up_question phải bằng tiếng Việt

QUAN TRỌNG: Chỉ trả về JSON object, không có text khác."""

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

        prompt = f"""Tổng kết buổi ôn tập kiến thức của học viên.

BÀI HỌC: {lesson_name}

NỘI DUNG BÀI HỌC:
{lesson_content}

TẤT CẢ KHÁI NIỆM TRONG BÀI: {concepts_str}

{history_section}

Dựa trên toàn bộ hội thoại trên, tạo JSON tổng kết:
{{
  "concepts_mastered": <danh sách khái niệm học viên nắm rõ>,
  "concepts_weak": [
    {{
      "concept": "<tên khái niệm>",
      "user_answer": "<học viên đã trả lời gì>",
      "correct_explanation": "<giải thích đúng là gì>"
    }}
  ],
  "engagement_quality": "<'low' | 'medium' | 'high' - chất lượng tham gia tổng thể>",
  "summary_text": "<2-3 câu tổng kết bằng tiếng Việt>",
  "suggestions": <danh sách 2-3 gợi ý cụ thể bằng tiếng Việt>
}}

Hướng dẫn:
- concepts_mastered: chỉ ghi nếu học viên trả lời đúng với mức độ tốt
- concepts_weak: ghi các khái niệm sai, nhầm lẫn, hoặc chưa đề cập
- suggestions: cụ thể và có thể thực hiện được
- Toàn bộ text bằng tiếng Việt

QUAN TRỌNG: Chỉ trả về JSON object, không có text khác."""

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
