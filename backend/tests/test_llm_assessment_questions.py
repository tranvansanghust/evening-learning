"""
Tests for LLMAssessmentGenerator.

Tests:
- generate_assessment_questions trả dict với q1, q2_if_no, q2_if_yes
- q1 chứa "Python" khi course_topic = "Python cơ bản"
- q1 chứa "Machine Learning" khi course_topic = "ML với scikit-learn"
- LLM trả output sai format → fallback về câu hỏi generic
- LLM raise exception → fallback, không crash
- course_topic rỗng → fallback, không crash
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.llm_assessment import LLMAssessmentGenerator


def make_llm_client(response_content: str) -> MagicMock:
    """Tạo fake OpenAI client trả về response_content."""
    client = MagicMock()
    choice = MagicMock()
    choice.message.content = response_content
    client.chat.completions.create.return_value = MagicMock(choices=[choice])
    return client


class TestLLMAssessmentGeneratorReturnShape:
    """Kiểm tra shape/keys của dict trả về."""

    def test_returns_dict_with_required_keys(self):
        payload = json.dumps({
            "q1": "Bạn đã từng làm việc với Python chưa?",
            "q2_if_no": "Bạn đã biết lập trình cơ bản chưa?",
            "q2_if_yes": "Bạn đã xây dựng dự án thực tế với Python chưa?",
        })
        client = make_llm_client(payload)
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("Python cơ bản")

        assert isinstance(result, dict)
        assert "q1" in result
        assert "q2_if_no" in result
        assert "q2_if_yes" in result

    def test_q1_contains_topic_python(self):
        payload = json.dumps({
            "q1": "Bạn đã từng làm việc với Python chưa?",
            "q2_if_no": "Bạn đã biết lập trình cơ bản chưa?",
            "q2_if_yes": "Bạn đã xây dựng ứng dụng với Python chưa?",
        })
        client = make_llm_client(payload)
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("Python cơ bản")

        assert "Python" in result["q1"]

    def test_q1_contains_topic_machine_learning(self):
        payload = json.dumps({
            "q1": "Bạn đã từng học Machine Learning chưa?",
            "q2_if_no": "Bạn đã biết Python cơ bản chưa?",
            "q2_if_yes": "Bạn đã train model thực tế chưa?",
        })
        client = make_llm_client(payload)
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("ML với scikit-learn")

        assert "Machine Learning" in result["q1"]

    def test_values_are_non_empty_strings(self):
        payload = json.dumps({
            "q1": "Bạn đã dùng Python chưa?",
            "q2_if_no": "Bạn có biết lập trình không?",
            "q2_if_yes": "Bạn đã làm dự án Python chưa?",
        })
        client = make_llm_client(payload)
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("Python")

        assert result["q1"] and isinstance(result["q1"], str)
        assert result["q2_if_no"] and isinstance(result["q2_if_no"], str)
        assert result["q2_if_yes"] and isinstance(result["q2_if_yes"], str)


class TestLLMAssessmentGeneratorFallback:
    """Kiểm tra fallback khi LLM lỗi hoặc trả sai format."""

    def test_fallback_when_llm_raises_exception(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("LLM API down")
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        # Không được raise — phải fallback
        result = generator.generate_assessment_questions("Python cơ bản")

        assert isinstance(result, dict)
        assert "q1" in result
        assert "q2_if_no" in result
        assert "q2_if_yes" in result

    def test_fallback_contains_topic_in_q1(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("timeout")
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("DevOps")

        assert "DevOps" in result["q1"]

    def test_fallback_when_json_missing_keys(self):
        """LLM trả JSON hợp lệ nhưng thiếu keys."""
        payload = json.dumps({"q1": "Bạn có biết Python không?"})  # thiếu q2_if_no, q2_if_yes
        client = make_llm_client(payload)
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("Python")

        # Phải fallback về generic questions
        assert "q1" in result
        assert "q2_if_no" in result
        assert "q2_if_yes" in result

    def test_fallback_when_json_invalid(self):
        """LLM trả text không phải JSON hợp lệ."""
        client = make_llm_client("Đây là văn bản thông thường, không phải JSON")
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("React")

        assert "q1" in result
        assert "q2_if_no" in result
        assert "q2_if_yes" in result

    def test_fallback_when_course_topic_empty(self):
        """course_topic rỗng → không crash, trả fallback."""
        client = MagicMock()
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        result = generator.generate_assessment_questions("")

        assert isinstance(result, dict)
        assert "q1" in result

    def test_no_exception_raised_on_any_llm_error(self):
        """Với bất kỳ loại exception nào từ LLM, không được raise."""
        import requests

        for exc in [RuntimeError("err"), ValueError("val"), ConnectionError("conn")]:
            client = MagicMock()
            client.chat.completions.create.side_effect = exc
            generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

            result = generator.generate_assessment_questions("SQL")
            assert "q1" in result, f"Failed for exception: {exc}"


class TestLLMAssessmentGeneratorLLMCall:
    """Kiểm tra LLM được gọi đúng cách."""

    def test_calls_llm_with_fast_model(self):
        payload = json.dumps({
            "q1": "Câu hỏi 1",
            "q2_if_no": "Câu hỏi 2a",
            "q2_if_yes": "Câu hỏi 2b",
        })
        client = make_llm_client(payload)
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        generator.generate_assessment_questions("Django")

        client.chat.completions.create.assert_called_once()
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("model") == "gpt-4o-mini" or call_kwargs.args[0] == "gpt-4o-mini" if call_kwargs.args else call_kwargs.kwargs.get("model") == "gpt-4o-mini"

    def test_prompt_contains_course_topic(self):
        """Prompt gửi đến LLM phải chứa course_topic."""
        payload = json.dumps({
            "q1": "Câu hỏi",
            "q2_if_no": "Q2 no",
            "q2_if_yes": "Q2 yes",
        })
        client = make_llm_client(payload)
        generator = LLMAssessmentGenerator(client=client, fast_model="gpt-4o-mini")

        generator.generate_assessment_questions("Kubernetes DevOps")

        call_kwargs = client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else []
        # Lấy tất cả content từ messages
        all_content = " ".join(m.get("content", "") for m in messages)
        assert "Kubernetes DevOps" in all_content
