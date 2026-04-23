# Quiz Quality Issues

## Vấn đề 1 — Câu hỏi không có trong bài học

### Triệu chứng
User báo bot hỏi những thứ không có trong bài học vừa đọc.

### Root Cause (3 tầng)

**Tầng 1 — `fetch_udemy_curriculum()` là mock**
`onboarding_service.py:229-232` trả về generic lessons cho mọi topic:
```
title: "Section 1", description: "Content for section 1"
```
Bất kỳ topic nào (Kubernetes, piano…) đều cho ra "Section 1-5" không có nội dung thật.

**Tầng 2 — `content_markdown` chỉ được generate khi user gõ `/today`**
`lesson_helpers._send_lesson_link()` mới gọi `LLMContentGenerator.get_or_generate()`.
Nếu user chưa gõ `/today`, `content_markdown = NULL`. Khi đó `quiz_service.start_quiz()` rơi vào fallback:
```python
lesson_content = f"Bài học về {course_topic}: {lesson.title}"
# → "Bài học về Kubernetes: Section 1"
```
LLM sinh câu hỏi từ kiến thức chung, không bám vào bài học cụ thể.

**Tầng 3 — Kể cả khi `content_markdown` có, nó vẫn generic**
Content được generate từ title "Section 1" → LLM tự suy luận nội dung section → có thể hỏi khái niệm không nằm trong phần user đã đọc.

### Fix cần làm
- Thay `fetch_udemy_curriculum()` bằng LLM curriculum generation: tạo lesson titles + mô tả cụ thể từ `course_topic`
- Generate `content_markdown` ngay khi tạo course (không lazy), hoặc bắt buộc generate trước khi start quiz

---

## Vấn đề 2 — Câu hỏi lòng vòng, lặp lại cùng chủ đề

### Triệu chứng
Bot hỏi đi hỏi lại cùng 1 câu hỏi với cách diễn đạt khác nhau (ảnh: hỏi 3 lần liên tiếp về "container giao tiếp qua localhost"), không chuyển sang khái niệm mới.

### Root Cause

**Prompt `quiz_question_generation` không track khái niệm đã hỏi rõ ràng**
Prompt yêu cầu "hỏi về khái niệm chưa được đề cập trong lịch sử hội thoại" nhưng:
- Không phân biệt "đã hỏi + user trả lời sai" vs "đã hỏi + user trả lời đúng"
- LLM đọc conversation history thấy user chưa trả lời đúng → tiếp tục hỏi cùng concept
- Không có cơ chế "đã hỏi concept X quá N lần → chuyển sang concept khác"

**`decide_next_action` chọn `followup` quá thoải mái**
Khi user trả lời sai/thiếu → LLM chọn `followup` → sinh câu hỏi tương tự → lặp lại vòng này.
Không có giới hạn số lần followup trên cùng một khái niệm.

### Fix cần làm
- Thêm vào prompt: danh sách các concept đã được hỏi đủ (> 1 lần followup) → không hỏi lại
- Giới hạn `followup` tối đa 1 lần trên cùng concept: lần 2 user sai → chuyển sang `continue` (concept mới) thay vì tiếp tục `followup`
- Thêm explicit instruction vào prompt: "Nếu concept X đã xuất hiện ≥ 2 lần trong history → bắt buộc chuyển sang concept khác"

---

## Vấn đề 3 — Vẫn gửi nhận xét sau khi user muốn kết thúc

### Triệu chứng
User gõ "oke kết thúc" → bot vẫn gửi feedback đánh giá câu trả lời ("Học viên chưa trả lời câu hỏi...") rồi mới hiện tổng kết. Thừa 1 bước, gây khó chịu vì user đã tuyên bố muốn dừng.

### Root Cause
Khi `engagement_level = "low"` (user muốn kết thúc), `submit_answer()` vẫn chạy đủ flow:
1. `evaluate_answer()` → trả về `feedback` ("Học viên chưa trả lời...")
2. `_handle_quiz_answer` gửi `feedback` trước
3. Sau đó mới detect `next_action == "end"` → gửi tổng kết

`_handle_quiz_answer` không phân biệt "end vì hết câu hỏi" vs "end vì user muốn dừng" — cả hai đều gửi feedback trước.

### Fix cần làm
Trong `submit_answer()`, khi `next_action == END` do `engagement_level == "low"`: đặt `evaluation.feedback = ""` hoặc thêm flag `user_requested_end = True` vào result.

Trong `_handle_quiz_answer`: nếu `user_requested_end` hoặc feedback rõ ràng là "chưa trả lời" + `next_action == end` → bỏ qua bước gửi feedback, hiện tổng kết luôn.

---

## Liên kết

- Root cause quiz off-topic: `backend/app/services/onboarding_service.py` (fetch_udemy_curriculum mock)
- Lesson content generation: `backend/app/services/llm_content_generator.py`
- Quiz question prompt: `backend/app/services/llm_prompts.py` (quiz_question_generation, decide_next_action)
- Quiz orchestration: `backend/app/services/quiz_service.py` (start_quiz, submit_answer)
