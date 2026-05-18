# Task 19 — MCQ Quiz Flow (Câu hỏi trắc nghiệm)

## Mục tiêu

Chuyển quiz từ free-text sang trắc nghiệm (MCQ): LLM sinh câu hỏi kèm đáp án đúng + 2 lựa chọn sai, mỗi câu được cấp 1 `question_id` (UUID), lưu vào Redis dưới dạng JSON string. Sau đó hiển thị 3 nút inline keyboard trên Telegram. User chọn nút → đánh giá deterministic (so sánh với đáp án lưu trong Redis), không cần gọi LLM để evaluate.

## Redis key / value format

```
key:   mcq:{question_id}          # question_id là UUID4
value: JSON string
{
  "question": "...",
  "list_answer": ["A...", "B...", "C..."],   # đã shuffle
  "correct_answer": "A..."                   # text của đáp án đúng
}
TTL: 3600s (1 giờ)
```

Callback data của Telegram button: `quiz:{question_id}:{choice_index}`

## Các file cần thay đổi / tạo mới

| File | Hành động | Nội dung |
|------|-----------|----------|
| `app/services/question_store.py` | Tạo mới | Interface `QuestionStoreBase` (abstract) + `RedisQuestionStore` (implement luôn) |
| `app/services/llm_prompts.py` | Sửa | Thêm `mcq_question_generation()` — prompt JSON trả về `{question, correct_answer, distractors[2]}` |
| `app/services/llm_service.py` | Sửa | Thêm Pydantic model `MCQQuestion` + method `generate_mcq_question()` |
| `app/services/quiz_service.py` | Sửa | Dùng `generate_mcq_question()`, lưu/load qua `QuestionStore`, bỏ LLM evaluate |
| `app/models/quiz_answer.py` | Sửa | Thêm cột `question_id` (String 36, UUID), `correct_answer` (Text), `choices` (JSON) |
| `app/routers/telegram_handlers.py` | Sửa | Gửi inline keyboard 3 nút, thêm callback_query handler cho `quiz:*` |
| `app/config.py` | Sửa | Thêm `REDIS_URL` vào Settings |
| `tests/test_mcq_quiz.py` | Tạo mới | Unit tests: sinh MCQ, Redis store/get, evaluate deterministic, callback parsing |

## Kế hoạch thực hiện (từng bước)

### Bước 1: Thêm Redis config
- `app/config.py`: thêm `REDIS_URL: str = "redis://localhost:6379/0"`
- `.env`: thêm `REDIS_URL=redis://localhost:6379/0`
- Thêm dependency `redis[asyncio]` vào `requirements.txt`

### Bước 2: QuestionStore interface + Redis implementation
- Tạo `app/services/question_store.py`:
  ```python
  class MCQData(BaseModel):
      question: str
      list_answer: list[str]   # shuffled
      correct_answer: str

  class QuestionStoreBase(ABC):
      async def save(self, question_id: str, data: MCQData, ttl: int = 3600) -> None
      async def get(self, question_id: str) -> Optional[MCQData]
      async def delete(self, question_id: str) -> None

  class RedisQuestionStore(QuestionStoreBase):
      # key: mcq:{question_id}
      # value: MCQData.model_dump_json()
      # TTL: 3600s
  ```
- Singleton `redis_question_store` dùng `aioredis` (từ `redis.asyncio`)

### Bước 3: LLM prompt + service cho MCQ
- `llm_prompts.py`: thêm `mcq_question_generation(lesson_content, concepts, conversation_history, course_topic)`:
  - Prompt yêu cầu trả về JSON thuần: `{"question": "...", "correct_answer": "...", "distractors": ["...", "..."]}`
  - Dặn LLM không thêm markdown, chỉ JSON
- `llm_service.py`:
  - Thêm `MCQQuestion(BaseModel)`: `question_id` (UUID str), `question`, `list_answer` (shuffled), `correct_answer`
  - Thêm `generate_mcq_question(...)`:
    1. Gọi LLM với prompt MCQ
    2. Parse JSON → lấy `correct_answer` + `distractors`
    3. Shuffle `[correct_answer] + distractors` → `list_answer`
    4. Tạo `question_id = str(uuid4())`
    5. Return `MCQQuestion`

### Bước 4: Quiz Service refactor
- `start_quiz()`:
  - Gọi `generate_mcq_question()` thay `generate_quiz_question()`
  - Lưu vào Redis: `await question_store.save(question_id, MCQData(...))`
  - Return `{session_id, question_id, question, list_answer, lesson_name, concepts}`
- `submit_answer(session_id, question_id, choice_index, db)`:
  - Load từ Redis: `data = await question_store.get(question_id)`
  - Đánh giá: `is_correct = (data.list_answer[choice_index] == data.correct_answer)`
  - Lưu `QuizAnswer` với `question_id`, `correct_answer`, `choices=data.list_answer`, `user_answer=data.list_answer[choice_index]`
  - Xóa Redis key: `await question_store.delete(question_id)`
  - Sinh MCQ mới → lưu Redis → return `{is_correct, next_question_id, next_question, list_answer}`
  - Kết thúc sau N câu (max_questions) → gọi `generate_quiz_summary()` (LLM vẫn dùng)
- Bỏ `evaluate_answer()` và `decide_next_action()` LLM calls

### Bước 5: Telegram handler — inline keyboard + callback
- Khi gửi câu hỏi (trong `_start_quiz_from_checkin` và sau mỗi câu):
  ```python
  InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(text=choice, callback_data=f"quiz:{question_id}:{i}")
      for i, choice in enumerate(list_answer)
  ]])
  ```
- Thêm `@router.callback_query(lambda c: c.data.startswith("quiz:"))`:
  - Parse `question_id` và `choice_index` từ callback_data
  - Gọi `quiz_service.submit_answer(session_id, question_id, choice_index, db)`
  - `answer_callback_query()` để tắt loading spinner
  - Gửi kết quả (đúng/sai) + câu tiếp theo hoặc summary

### Bước 6: DB migration
- `quiz_answer`: ALTER TABLE thêm `question_id VARCHAR(36)`, `correct_answer TEXT`, `choices JSON`

### Bước 7: Tests
- Test `generate_mcq_question()`: mock LLM, verify shuffle + UUID
- Test `RedisQuestionStore`: save → get → delete (dùng fakeredis)
- Test `submit_answer()`: đúng / sai index
- Test callback_data parse

## Giải thích thiết kế

**Tại sao key là `question_id` (UUID) thay vì `session_id`?**
- Một session có nhiều câu hỏi nối tiếp → nếu key là session_id sẽ overwrite
- `question_id` định danh từng câu, callback Telegram embed luôn `question_id` → không cần DB lookup thêm

**JSON format trong Redis:**
```json
{"question": "...", "list_answer": ["A", "B", "C"], "correct_answer": "A"}
```
- `correct_answer` là text (không phải index) → tránh lỗi khi list thay đổi thứ tự
- Đủ để evaluate và reconstruct nếu cần

**Tại sao vẫn giữ `QuestionStoreBase` abstract?**
- Nếu sau này muốn test với in-memory store hoặc DB fallback → chỉ swap class

**Callback data:** `quiz:{question_id}:{choice_index}` — question_id UUID đủ để lookup Redis, choice_index để biết user chọn gì
