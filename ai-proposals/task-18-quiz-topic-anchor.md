# Task 18: Fix Quiz Topic Anchor — Gắn Quiz với Course Topic

## Vấn đề

User onboard với topic "piano" nhưng khi `/done` gõ nội dung về "chia động từ", quiz đổi chủ đề theo luôn. Bot không nhắc nhở gì, không giữ đúng chủ đề đã đăng ký học.

## Root Cause (đã xác nhận)

### Nguyên nhân 1 — `user_checkin` hoàn toàn override concept

`quiz_service.py:138-140`:
```python
if user_checkin:
    lesson_content = f"Học viên tự mô tả nội dung đã học hôm nay: {user_checkin}..."
    if concept_names == [lesson.title]:
        concept_names = [user_checkin]  # ← user_checkin thay thế hoàn toàn concept
```

Khi lesson không có concepts trong DB (và hiện tại hầu hết lesson đều không có), `concept_names` mặc định về `[lesson.title]`. Khi user gõ bất cứ thứ gì ở `/done`, dòng này thay `concept_names` bằng nội dung user gõ. LLM chỉ biết quiz theo đó.

### Nguyên nhân 2 — Course topic không được truyền vào quiz

`start_quiz()` và `submit_answer()` không load `Course` từ DB. LLM không biết user đang học khóa gì, chỉ biết `lesson.title` (vd: "Section 1") và `user_checkin` — không đủ để giữ đúng chủ đề.

### Nguyên nhân 3 — `lesson_content` rỗng

`lesson.description` thường rỗng. `lesson.content_markdown` (từ task 14) không được dùng. LLM không có context về bài học → dễ bị dẫn dắt bởi user_checkin.

### Nguyên nhân 4 — Prompt `answer_evaluation` không validate topic

Prompt hiện tại chấp nhận bất kỳ câu trả lời nào, không kiểm tra có liên quan đến course topic hay không. Nên dù user trả lời về chia động từ trong quiz piano, LLM vẫn evaluate và generate câu tiếp.

## Giải pháp

### Thay đổi thiết kế

`user_checkin` (nội dung user tự mô tả) là **supplementary context** (gợi ý thêm), KHÔNG phải primary topic. Course topic từ onboarding là **anchor** không thay đổi.

### Fix 1 — Load `course_topic` trong `start_quiz()` và `submit_answer()`

```python
# quiz_service.py — start_quiz()
lesson = db_session.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
course = db_session.query(Course).filter(Course.course_id == lesson.course_id).first()
course_topic = course.name if course else lesson.title
```

Truyền `course_topic` vào tất cả LLM calls.

### Fix 2 — Dùng `content_markdown` làm lesson context chính

```python
# Ưu tiên content_markdown (task 14), fallback về description, rồi title
lesson_content = lesson.content_markdown or lesson.description or f"Bài học về {course_topic}: {lesson.title}"
```

### Fix 3 — Không cho `user_checkin` override `concept_names`

Bỏ dòng 139-140 trong `start_quiz()`:
```python
# TRƯỚC (sai):
if concept_names == [lesson.title]:
    concept_names = [user_checkin]  # ← xóa dòng này

# SAU:
# concept_names giữ nguyên từ DB hoặc [lesson.title]
# user_checkin chỉ được append vào lesson_content
if user_checkin:
    lesson_content = f"{lesson_content}\n\nHọc viên mô tả nội dung học hôm nay: {user_checkin}".strip()
```

Tương tự trong `submit_answer()`.

### Fix 4 — Thêm `course_topic` vào prompt `answer_evaluation`

`llm_prompts.py` — thêm param `course_topic` và thêm validation vào prompt:

```python
@staticmethod
def answer_evaluation(question, user_answer, lesson_context, concepts, course_topic=""):
    ...
    topic_section = f"\nKHÓA HỌC: {course_topic}" if course_topic else ""

    prompt = f"""Đánh giá câu trả lời của học viên.
{topic_section}
NỘI DUNG BÀI HỌC: {lesson_context}
KHÁI NIỆM: {concepts_str}
CÂU HỎI: {question}
CÂU TRẢ LỜI: {user_answer}

QUAN TRỌNG: Nếu câu trả lời không liên quan đến khóa học "{course_topic}",
hãy đặt is_correct=false và feedback nhắc học viên trả lời đúng chủ đề.

Trả về JSON: {{ "is_correct": ..., "feedback": "..." ... }}"""
```

### Fix 5 — Thêm `course_topic` vào prompt `quiz_question_generation`

```python
@staticmethod
def quiz_question_generation(lesson_content, conversation_history, concepts, is_first_question, course_topic=""):
    ...
    prompt = f"""Tạo câu hỏi ôn tập về "{course_topic}" cho bài: {lesson_content}
    
Khái niệm: {concepts_section}
...
Câu hỏi PHẢI liên quan đến chủ đề "{course_topic}"."""
```

## Files cần thay đổi

- `backend/app/services/quiz_service.py` — load Course, fix user_checkin override, truyền course_topic
- `backend/app/services/llm_prompts.py` — thêm course_topic vào 2 prompt methods
- `backend/app/services/llm_service.py` — cập nhật method signatures để truyền course_topic

## Kế hoạch thực hiện

### Bước 1: Viết tests trước

`backend/tests/test_quiz_topic_anchor.py`:

```python
# Test: start_quiz() load Course và lấy course_topic
# Test: user_checkin KHÔNG override concept_names
# Test: lesson_content dùng content_markdown nếu có
# Test: answer_evaluation prompt chứa course_topic
# Test: quiz_question_generation prompt chứa course_topic
# Test: user trả lời off-topic → is_correct=False + feedback nhắc về course_topic
```

### Bước 2: Sửa `quiz_service.py`

1. Trong `start_quiz()`:
   - Load `Course` từ `lesson.course_id`
   - Lấy `course_topic = course.name`
   - Dùng `lesson.content_markdown or lesson.description` làm lesson_content
   - Bỏ block `concept_names = [user_checkin]`
   - Truyền `course_topic` vào `generate_quiz_question()` và `evaluate_answer()`

2. Trong `submit_answer()`:
   - Load `Course` tương tự
   - Cập nhật lesson_content để dùng `content_markdown`
   - Bỏ block `concept_names = [stored_checkin]`
   - Truyền `course_topic` vào tất cả LLM calls

### Bước 3: Sửa `llm_prompts.py`

- `quiz_question_generation()`: thêm param `course_topic`, inject vào prompt
- `answer_evaluation()`: thêm param `course_topic`, thêm validation vào prompt

### Bước 4: Sửa `llm_service.py`

- `generate_quiz_question()`: thêm param `course_topic`, truyền xuống `LLMPrompts`
- `evaluate_answer()`: thêm param `course_topic`, truyền xuống `LLMPrompts`

### Bước 5: Chạy tests

```bash
cd backend && source eveninig-learning-venv/bin/activate && python -m pytest tests/test_quiz_topic_anchor.py -v
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `start_quiz()` load `Course` và truyền `course_topic` vào LLM
- [ ] `user_checkin` chỉ là supplementary context, không override `concept_names`
- [ ] `lesson_content` dùng `content_markdown` nếu có
- [ ] Prompt câu hỏi chứa `course_topic`
- [ ] Prompt đánh giá validate câu trả lời theo `course_topic`
- [ ] Tests pass

## Rủi ro

- Thấp. Không thay đổi DB schema, không thêm LLM call mới.
- Thay đổi signature `generate_quiz_question()` và `evaluate_answer()` — cần update tất cả callers.
- LLM vẫn có thể bị user dẫn dắt nếu prompt không đủ mạnh — logging để monitor.
