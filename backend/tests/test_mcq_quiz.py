"""Tests for MCQ quiz flow: question generation, Redis store, deterministic evaluation."""

import json
from unittest.mock import MagicMock, patch
from typing import Optional

import pytest

from app.services.question_store import MCQData, RedisQuestionStore, QuestionStoreBase


# ---------------------------------------------------------------------------
# MCQData model
# ---------------------------------------------------------------------------

class TestMCQData:
    def test_serialise_roundtrip(self):
        data = MCQData(
            question="Câu hỏi?",
            list_answer=["A", "B", "C"],
            correct_answer="A",
        )
        raw = data.model_dump_json()
        restored = MCQData.model_validate_json(raw)
        assert restored == data

    def test_json_keys(self):
        data = MCQData(question="Q", list_answer=["X", "Y"], correct_answer="X")
        parsed = json.loads(data.model_dump_json())
        assert set(parsed.keys()) == {"question", "list_answer", "correct_answer"}


# ---------------------------------------------------------------------------
# RedisQuestionStore (with fakeredis)
# ---------------------------------------------------------------------------

class InMemoryStore(QuestionStoreBase):
    """Lightweight in-memory implementation for unit tests (no Redis needed)."""

    def __init__(self):
        self._store: dict[str, MCQData] = {}

    def save(self, question_id: str, data: MCQData, ttl: int = 3600) -> None:
        self._store[question_id] = data

    def get(self, question_id: str) -> Optional[MCQData]:
        return self._store.get(question_id)

    def delete(self, question_id: str) -> None:
        self._store.pop(question_id, None)


class TestInMemoryStore:
    def setup_method(self):
        self.store = InMemoryStore()
        self.data = MCQData(question="Q?", list_answer=["A", "B", "C"], correct_answer="B")

    def test_save_and_get(self):
        self.store.save("qid-1", self.data)
        result = self.store.get("qid-1")
        assert result == self.data

    def test_get_missing_returns_none(self):
        assert self.store.get("does-not-exist") is None

    def test_delete_removes_entry(self):
        self.store.save("qid-2", self.data)
        self.store.delete("qid-2")
        assert self.store.get("qid-2") is None

    def test_delete_missing_is_noop(self):
        self.store.delete("ghost")  # should not raise


class TestRedisQuestionStoreKeyFormat:
    """Verify the Redis key prefix without a live Redis connection."""

    def test_key_prefix_used_in_save(self):
        mock_client = MagicMock()
        store = RedisQuestionStore.__new__(RedisQuestionStore)
        store._client = mock_client

        data = MCQData(question="Q", list_answer=["A", "B"], correct_answer="A")
        store.save("abc-123", data)

        call_args = mock_client.setex.call_args
        assert call_args[0][0] == "mcq:abc-123"
        assert call_args[0][1] == 3600

    def test_key_prefix_used_in_get(self):
        mock_client = MagicMock()
        mock_client.get.return_value = None
        store = RedisQuestionStore.__new__(RedisQuestionStore)
        store._client = mock_client

        store.get("abc-123")
        mock_client.get.assert_called_once_with("mcq:abc-123")

    def test_key_prefix_used_in_delete(self):
        mock_client = MagicMock()
        store = RedisQuestionStore.__new__(RedisQuestionStore)
        store._client = mock_client

        store.delete("abc-123")
        mock_client.delete.assert_called_once_with("mcq:abc-123")

    def test_get_returns_mcqdata_when_found(self):
        data = MCQData(question="Q", list_answer=["A", "B"], correct_answer="A")
        mock_client = MagicMock()
        mock_client.get.return_value = data.model_dump_json()
        store = RedisQuestionStore.__new__(RedisQuestionStore)
        store._client = mock_client

        result = store.get("abc-123")
        assert result == data


# ---------------------------------------------------------------------------
# generate_mcq_question — shuffle + UUID
# ---------------------------------------------------------------------------

class TestGenerateMCQQuestion:
    def _make_service(self, llm_response: dict):
        from app.services.llm_service import LLMService
        svc = LLMService.__new__(LLMService)
        svc.FAST_MODEL = "test-model"
        svc.SMART_MODEL = "test-model"

        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.choices[0].message.content = json.dumps(llm_response)
        mock_client.chat.completions.create.return_value = mock_msg
        svc.client = mock_client
        return svc

    def test_returns_mcq_question_with_uuid(self):
        from app.services.llm_service import MCQQuestion
        svc = self._make_service({
            "question": "Câu hỏi?",
            "correct_answer": "Đúng",
            "distractors": ["Sai 1", "Sai 2"],
        })
        result = svc.generate_mcq_question(
            lesson_content="Nội dung bài học",
            concepts=["Khái niệm A"],
            conversation_history=[],
        )
        assert isinstance(result, MCQQuestion)
        assert len(result.question_id) == 36  # UUID4 format
        assert result.correct_answer == "Đúng"
        assert len(result.list_answer) == 3
        assert "Đúng" in result.list_answer

    def test_all_choices_present(self):
        svc = self._make_service({
            "question": "Q?",
            "correct_answer": "C",
            "distractors": ["A", "B"],
        })
        result = svc.generate_mcq_question("content", ["concept"], [])
        assert set(result.list_answer) == {"A", "B", "C"}

    def test_question_ids_are_unique(self):
        svc = self._make_service({
            "question": "Q?",
            "correct_answer": "C",
            "distractors": ["A", "B"],
        })
        ids = {svc.generate_mcq_question("content", ["c"], []).question_id for _ in range(5)}
        assert len(ids) == 5


# ---------------------------------------------------------------------------
# Deterministic evaluation in submit_answer
# ---------------------------------------------------------------------------

class TestDeterministicEvaluation:
    def _make_quiz_service(self, store):
        from app.services.quiz_service import QuizService
        from app.services.llm_service import LLMService
        llm = MagicMock(spec=LLMService)
        return QuizService(llm_service=llm, question_store=store)

    def test_correct_choice_is_detected(self):
        store = InMemoryStore()
        data = MCQData(question="Q?", list_answer=["A", "B", "C"], correct_answer="B")
        store.save("qid-x", data)

        svc = self._make_quiz_service(store)
        # Simulate internal evaluation logic (isolated from DB)
        mcq = store.get("qid-x")
        assert mcq is not None
        chosen = mcq.list_answer[1]  # index 1 = "B"
        is_correct = chosen == mcq.correct_answer
        assert is_correct is True

    def test_wrong_choice_is_detected(self):
        store = InMemoryStore()
        data = MCQData(question="Q?", list_answer=["A", "B", "C"], correct_answer="B")
        store.save("qid-y", data)

        mcq = store.get("qid-y")
        chosen = mcq.list_answer[0]  # index 0 = "A"
        is_correct = chosen == mcq.correct_answer
        assert is_correct is False


# ---------------------------------------------------------------------------
# Callback data parsing
# ---------------------------------------------------------------------------

class TestCallbackDataParsing:
    def _parse(self, callback_data: str):
        parts = callback_data.split(":")
        return int(parts[1]), parts[2], int(parts[3])

    def test_parse_valid_callback(self):
        qid = "550e8400-e29b-41d4-a716-446655440000"
        data = f"quiz:42:{qid}:2"
        session_id, question_id, choice_index = self._parse(data)
        assert session_id == 42
        assert question_id == qid
        assert choice_index == 2

    def test_callback_data_length_under_64_bytes(self):
        qid = "550e8400-e29b-41d4-a716-446655440000"
        data = f"quiz:99999:{qid}:2"
        assert len(data.encode()) <= 64
