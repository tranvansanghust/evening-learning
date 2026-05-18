from abc import ABC, abstractmethod
from typing import Optional

import redis
from pydantic import BaseModel


class MCQData(BaseModel):
    question: str
    list_answer: list[str]
    correct_answer: str


class QuestionStoreBase(ABC):
    @abstractmethod
    def save(self, question_id: str, data: MCQData, ttl: int = 3600) -> None: ...

    @abstractmethod
    def get(self, question_id: str) -> Optional[MCQData]: ...

    @abstractmethod
    def delete(self, question_id: str) -> None: ...


class RedisQuestionStore(QuestionStoreBase):
    _KEY_PREFIX = "mcq:"

    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def save(self, question_id: str, data: MCQData, ttl: int = 3600) -> None:
        self._client.setex(f"{self._KEY_PREFIX}{question_id}", ttl, data.model_dump_json())

    def get(self, question_id: str) -> Optional[MCQData]:
        raw = self._client.get(f"{self._KEY_PREFIX}{question_id}")
        return MCQData.model_validate_json(raw) if raw else None

    def delete(self, question_id: str) -> None:
        self._client.delete(f"{self._KEY_PREFIX}{question_id}")


def make_question_store(redis_url: str) -> QuestionStoreBase:
    return RedisQuestionStore(redis_url)
