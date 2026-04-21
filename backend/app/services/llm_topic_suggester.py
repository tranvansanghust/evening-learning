"""
LLMTopicSuggester — gợi ý chủ đề học tiếp sau khi hoàn thành khoá học.

Tách riêng khỏi llm_service.py để giữ file size dưới 300 dòng.
"""

import logging

logger = logging.getLogger(__name__)


class LLMTopicSuggester:
    """
    Gợi ý 3 chủ đề hoặc khoá học tiếp theo sau khi user hoàn thành một khoá.

    Dùng fast_model để tiết kiệm chi phí (không cần smart model cho task này).
    """

    def __init__(self, client, fast_model: str):
        """
        Args:
            client: OpenAI-compatible client (đã được khởi tạo với api_key/base_url)
            fast_model: Tên model dùng để generate (fast/cheap)
        """
        self.client = client
        self.fast_model = fast_model

    def suggest_next_topics(self, completed_course: str) -> str:
        """
        Gợi ý 3 chủ đề học tiếp sau khi hoàn thành một khoá học.

        Args:
            completed_course: Tên khoá học vừa hoàn thành

        Returns:
            str: Danh sách 3 gợi ý, mỗi gợi ý trên một dòng (bắt đầu bằng số thứ tự)

        Raises:
            Exception: Bất kỳ lỗi nào từ LLM — caller phải xử lý try/except
        """
        prompt = (
            f"User vừa hoàn thành khóa học: {completed_course}.\n"
            "Gợi ý 3 chủ đề hoặc khóa học tiếp theo phù hợp, "
            "mỗi gợi ý trên một dòng, bắt đầu bằng số thứ tự. "
            "Trả lời bằng tiếng Việt, ngắn gọn."
        )

        response = self.client.chat.completions.create(
            model=self.fast_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        result = response.choices[0].message.content.strip()
        logger.info(f"Generated topic suggestions for course: {completed_course!r}")
        return result
