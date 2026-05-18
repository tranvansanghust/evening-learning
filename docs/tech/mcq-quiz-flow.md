# MCQ Quiz Flow

## Tổng quan

Quiz dùng câu hỏi trắc nghiệm (MCQ). LLM sinh câu hỏi + đáp án đúng + 2 distractor trong một lần gọi. Đáp án đúng được lưu vào Redis — không cần gọi LLM khi đánh giá.

---

## Flow

```
User /done
  → cmd_done() sinh content_markdown nếu chưa có
  → QuizService.start_quiz() → LLM sinh MCQ #1
  → Lưu MCQ vào Redis (key: mcq:{question_id}, TTL: 3600s)
  → Bot gửi câu hỏi + đáp án A/B/C trong message text
  → Inline keyboard: [ A ]  [ B ]  [ C ]

User nhấn button
  → handle_quiz_callback() parse callback_data: quiz:{session_id}:{question_id}:{choice_index}
  → QuizService.submit_answer()
      → Redis.get(question_id) → lấy MCQData
      → chosen = list_answer[choice_index]
      → is_correct = (chosen == correct_answer)
      → Redis.delete(question_id)
      → Lưu QuizAnswer vào DB
  → Bot gửi "✅ Đúng!" hoặc "❌ Chưa đúng. Đáp án đúng là: ..."
  → Nếu < 5 câu: sinh MCQ tiếp, gửi tiếp
  → Nếu = 5 câu: kết thúc, sinh summary bằng LLM
```

---

## Các file liên quan

| File | Vai trò |
|------|---------|
| `app/services/question_store.py` | `MCQData`, `QuestionStoreBase`, `RedisQuestionStore` |
| `app/services/llm_prompts.py` | `mcq_question_generation()` — prompt trả JSON |
| `app/services/llm_service.py` | `MCQQuestion`, `generate_mcq_question()` |
| `app/services/quiz_service.py` | `start_quiz()`, `submit_answer()`, `get_or_generate_summary()` |
| `app/routers/telegram_handlers.py` | `cmd_done()`, `handle_quiz_callback()`, `_make_quiz_keyboard()`, `_format_quiz_message()` |
| `app/models/quiz_answer.py` | Thêm `question_id`, `correct_answer`, `choices` |
| `alembic/versions/f1a2b3c4d5e6_...py` | Migration thêm 3 cột mới vào `quiz_answers` |

---

## Redis

- **Key format:** `mcq:{question_id}` (UUID4)
- **Value:** JSON string — `{"question": "", "list_answer": [], "correct_answer": ""}`
- **TTL:** 3600s
- **Client:** sync `redis.Redis` (không phải asyncio) vì service chạy trong `asyncio.to_thread()`
- **Singleton:** `_question_store = make_question_store(settings.redis_url)` tại module level

---

## LLM output format

```json
{
  "question": "Câu hỏi?",
  "correct_answer": "Đáp án đúng",
  "distractors": ["Sai 1", "Sai 2"]
}
```

Server shuffle `[correct_answer] + distractors` trước khi trả về — đảm bảo vị trí ngẫu nhiên mỗi lần.

---

## Telegram

- **Callback data format:** `quiz:{session_id}:{question_id}:{choice_index}` (≤ 64 bytes)
- **Hiển thị đáp án:** trong nội dung message text (`_format_quiz_message`), không dùng button text để tránh truncate
- **Button:** chỉ hiển thị `A`, `B`, `C` trên một hàng ngang

---

## Max questions & summary

- Tối đa **5 câu** mỗi session
- Sau câu thứ 5: `quiz_session.status = "completed"`, gọi LLM sinh `QuizSummary` (mastered/weak concepts)
- Summary lưu DB qua `get_or_generate_summary()`

---

## Edge cases

- **Redis hết TTL hoặc đã xoá:** `submit_answer()` raise `ValueError("Question not found")` — bot báo lỗi
- **Câu hỏi text thay vì button khi đang quiz:** bot trả lời "Hãy chọn đáp án bằng cách nhấn nút 👆"
- **Không có content_markdown:** `cmd_done()` tự generate trước khi quiz bắt đầu
- **Migration:** chạy `alembic upgrade head` trước khi deploy lần đầu
