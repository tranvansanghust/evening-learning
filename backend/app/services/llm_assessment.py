"""
LLMAssessmentGenerator — sinh câu hỏi đánh giá trình độ theo course_topic.

Tách riêng khỏi llm_service.py để giữ file size dưới 300 dòng.
"""

import json
import logging

logger = logging.getLogger(__name__)

FALLBACK_QUESTIONS = {
    "q1": "Bạn đã có kinh nghiệm với chủ đề này chưa?",
    "q2_if_no": "Bạn đã có nền tảng lập trình cơ bản chưa?",
    "q2_if_yes": "Bạn đã từng làm dự án thực tế về chủ đề này chưa?",
}


class LLMAssessmentGenerator:
    """
    Sinh 2 câu hỏi đánh giá trình độ phù hợp với course_topic của user.

    Dùng fast_model để tiết kiệm chi phí. Tự fallback về câu hỏi generic
    nếu LLM lỗi hoặc trả về sai format.
    """

    def __init__(self, client, fast_model: str):
        """
        Args:
            client: OpenAI-compatible client (đã được khởi tạo với api_key/base_url)
            fast_model: Tên model dùng để generate (fast/cheap)
        """
        self.client = client
        self.fast_model = fast_model

    def generate_assessment_questions(self, course_topic: str) -> dict:
        """
        Sinh 2 câu hỏi đánh giá trình độ phù hợp với course_topic.

        Args:
            course_topic: Chủ đề user muốn học (ví dụ: "Python cơ bản", "Machine Learning")

        Returns:
            dict với keys:
                q1: câu hỏi về kinh nghiệm tổng quát với lĩnh vực này
                q2_if_no: câu hỏi nếu Q1 = "chưa có kinh nghiệm"
                q2_if_yes: câu hỏi nếu Q1 = "đã có kinh nghiệm"

        Note:
            Không bao giờ raise exception — luôn fallback về câu hỏi generic nếu LLM lỗi.
        """
        if not course_topic or not course_topic.strip():
            logger.warning("generate_assessment_questions called with empty course_topic, using fallback")
            return self._make_fallback(course_topic or "chủ đề này")

        prompt = (
            f'Bạn là trợ lý đánh giá trình độ học viên.\n'
            f'User muốn học: "{course_topic}"\n\n'
            f'Hãy tạo 2 câu hỏi ngắn để đánh giá trình độ:\n'
            f'1. Q1: Câu hỏi về kinh nghiệm tổng quát với "{course_topic}"\n'
            f'2. Q2_if_no: Nếu user CHƯA CÓ kinh nghiệm → hỏi về kiến thức nền tảng\n'
            f'3. Q2_if_yes: Nếu user ĐÃ CÓ kinh nghiệm → hỏi về mức độ nâng cao hơn\n\n'
            f'Trả về JSON với format:\n'
            f'{{"q1": "...", "q2_if_no": "...", "q2_if_yes": "..."}}\n\n'
            f'Yêu cầu:\n'
            f'- Câu hỏi ngắn gọn (dưới 15 từ)\n'
            f'- Có thể trả lời Có/Chưa\n'
            f'- Liên quan trực tiếp đến "{course_topic}"\n'
            f'- Trả lời bằng tiếng Việt'
        )

        logger.info(f"Calling LLM for assessment questions: topic={course_topic!r}")
        try:
            response = self.client.chat.completions.create(
                model=self.fast_model,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý tạo câu hỏi đánh giá trình độ học viên. Chỉ trả về JSON object theo đúng format yêu cầu."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
            )
            raw = response.choices[0].message.content
            if not raw or not raw.strip():
                logger.warning("generate_assessment_questions: LLM returned empty, using fallback")
                return self._make_fallback(course_topic)

            content = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            logger.debug(f"LLM assessment response: {content[:200]}")
            data = json.loads(content)

            if not all(k in data for k in ("q1", "q2_if_no", "q2_if_yes")):
                logger.warning(
                    f"generate_assessment_questions: missing keys {list(data.keys())}, using fallback"
                )
                return self._make_fallback(course_topic)

            logger.info(f"Generated assessment questions for topic: {course_topic!r}")
            return {
                "q1": data["q1"],
                "q2_if_no": data["q2_if_no"],
                "q2_if_yes": data["q2_if_yes"],
            }

        except Exception as e:
            logger.warning(f"generate_assessment_questions failed ({e}), using fallback")
            return self._make_fallback(course_topic)

    def _make_fallback(self, course_topic: str) -> dict:
        """Trả về câu hỏi generic khi LLM lỗi."""
        return {
            "q1": f"Bạn đã có kinh nghiệm với {course_topic} chưa?",
            "q2_if_no": "Bạn đã có nền tảng lập trình cơ bản chưa?",
            "q2_if_yes": f"Bạn đã từng làm dự án thực tế với {course_topic} chưa?",
        }
