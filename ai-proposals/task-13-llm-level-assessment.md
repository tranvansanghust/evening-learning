# Task 13: LLM-Based Level Assessment from Free-Text Answers

## Mục tiêu
Hiện tại level được tính bằng binary tree cứng (Q1=never+Q2=no → level 0). Cần LLM đánh giá trình độ từ câu trả lời free-text của user, cho kết quả chính xác hơn và tự nhiên hơn.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước. **Nên làm sau task-12** (task-12 thêm LLM questions, task-13 thêm LLM evaluation).

## Sự khác biệt so với task-12

- **Task 12:** LLM sinh câu hỏi, user vẫn trả lời bằng button (Chưa/Rồi) binary
- **Task 13:** User trả lời free-text, LLM đánh giá toàn bộ context → level 0-3

Với task-13, buttons sẽ bị bỏ và user gõ câu trả lời tự do như:
> "Mình đã học Python được 1 năm, làm vài script nhỏ nhưng chưa làm dự án thật sự"

LLM đọc context này cùng với `course_topic` → đưa ra level phù hợp.

## Files cần thay đổi

- `backend/app/services/llm_service.py` — thêm `assess_level_from_answers()`
- `backend/app/routers/telegram_handlers.py` — bỏ buttons Q1/Q2, xử lý free-text, gọi LLM assess
- `backend/app/services/onboarding_service.py` — `complete_onboarding()` dùng assessed_level từ LLM thay vì `assess_level()`

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Tạo `backend/tests/test_llm_level_assessment.py`:

```python
# Test: "Mình chưa biết gì về Python" → level 0
# Test: "Mình biết Python cơ bản, đã làm vài script" → level 1 hoặc 2
# Test: "Mình đã dùng Django 2 năm, deploy production" → level 3
# Test: LLM lỗi → fallback về level 0 (beginner)
# Test: LLM trả level ngoài range 0-3 → clamp về 0-3
```

### Bước 2: Thêm `assess_level_from_answers()` vào `llm_service.py`

```python
def assess_level_from_answers(
    self,
    course_topic: str,
    q1_question: str,
    q1_answer: str,
    q2_question: str,
    q2_answer: str,
) -> int:
    """
    Đánh giá trình độ user dựa trên câu trả lời free-text.

    Returns:
        int: Level 0-3
            0 = Hoàn toàn mới, chưa có nền tảng
            1 = Biết cơ bản, chưa làm dự án thật
            2 = Đã có kinh nghiệm, chưa chuyên sâu
            3 = Có kinh nghiệm thực tế, biết framework/tool nâng cao

    Fallback: trả 0 nếu LLM lỗi
    """
    prompt = f"""Đánh giá trình độ học viên muốn học "{course_topic}".

Câu hỏi 1: {q1_question}
Trả lời: {q1_answer}

Câu hỏi 2: {q2_question}
Trả lời: {q2_answer}

Dựa trên câu trả lời, xác định trình độ từ 0-3:
- 0: Hoàn toàn mới với {course_topic}, chưa có kiến thức nền
- 1: Biết cơ bản (lý thuyết hoặc thực hành nhỏ), chưa có dự án thực tế
- 2: Đã có kinh nghiệm thực tế, hiểu khái niệm chính nhưng chưa chuyên sâu
- 3: Kinh nghiệm vững, đã làm dự án thực tế, biết tool/framework nâng cao

Chỉ trả về một số nguyên duy nhất (0, 1, 2, hoặc 3). Không giải thích thêm.
"""
    try:
        response = self.client.chat.completions.create(
            model=self.fast_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
        )
        raw = response.choices[0].message.content.strip()
        level = int(raw)
        return max(0, min(3, level))  # clamp 0-3
    except Exception as e:
        logger.warning(f"assess_level_from_answers failed, defaulting to 0: {e}")
        return 0
```

### Bước 3: Sửa Q1/Q2 trong `telegram_handlers.py` — bỏ buttons, dùng free-text

**Bước `q1` — không cần parse binary nữa, lưu raw text:**

```python
elif step == "q1":
    # Lưu raw answer thay vì parse binary
    onboarding_service.update_onboarding_state(
        user_id=user_id, q1_answer=text, current_step="q2"
    )
    ob_state = onboarding_service.get_onboarding_state(user_id)
    q2_text = getattr(ob_state, "q2_text_if_no", None) or "Bạn đã có nền tảng lập trình cơ bản chưa? Kể thêm nhé!"

    # KHÔNG có keyboard — free-text
    await message.answer(q2_text)
```

**Bước `q2` — gọi LLM assess thay vì binary tree:**

```python
elif step == "q2":
    onboarding_service.update_onboarding_state(
        user_id=user_id, q2_answer=text, current_step="deadline"
    )

    # Lấy state để có đủ context
    ob_state = onboarding_service.get_onboarding_state(user_id)

    # LLM assess level
    from app.config import settings
    llm = LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )
    assessed_level = llm.assess_level_from_answers(
        course_topic=ob_state.course_topic or "",
        q1_question=getattr(ob_state, "q1_text", "") or "Bạn đã có kinh nghiệm chưa?",
        q1_answer=ob_state.q1_answer or "",
        q2_question=getattr(ob_state, "q2_text_if_no", "") or "Bạn có nền tảng không?",
        q2_answer=text,
    )
    onboarding_service.update_onboarding_state(
        user_id=user_id, assessed_level=assessed_level
    )

    await message.answer(
        "Bạn muốn hoàn thành khoá học trong bao lâu?\n\nVí dụ: 1 month, 3 months, 2026-06-01",
        reply_markup=ReplyKeyboardRemove(),
    )
```

### Bước 4: Sửa `complete_onboarding()` trong `onboarding_service.py`

Hiện tại:
```python
if state.q1_answer and state.q2_answer:
    level = self.assess_level(state.q1_answer, state.q2_answer)
```

Thay bằng:
```python
# Dùng assessed_level từ LLM nếu có, fallback về assess_level() cho backward compat
if state.assessed_level is not None:
    level = state.assessed_level
elif state.q1_answer and state.q2_answer:
    try:
        level = self.assess_level(state.q1_answer, state.q2_answer)
    except ValueError:
        level = 0
```

**Lưu ý:** `assess_level()` cũ expect "never"/"yes"/"no" — với free-text answers sẽ raise ValueError. Fallback về `assessed_level` từ LLM là đúng.

### Bước 5: Chạy tests

```bash
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `assess_level_from_answers()` có trong `llm_service.py`
- [ ] LLM lỗi → fallback về level 0, không crash
- [ ] Level được clamp về 0-3
- [ ] Q1/Q2 không có keyboard — user gõ free-text
- [ ] `complete_onboarding()` dùng `assessed_level` từ LLM
- [ ] `assess_level()` cũ vẫn tồn tại (không xóa) để backward compat
- [ ] Tests pass

## Rủi ro

- Trung bình. Free-text thay vì buttons làm UX khác đi — cần monitor xem user có confused không.
- LLM assess từ 2 câu ngắn có thể không chính xác — level sai ảnh hưởng đến curriculum.
- Nên có logging rõ ràng để debug: `logger.info(f"Assessed level {level} for topic {course_topic}")`

## Gợi ý thêm (không bắt buộc)

Có thể thêm bước "xác nhận level" trước khi hoàn thành:
> "Dựa trên câu trả lời của bạn, mình đánh giá bạn ở **level 2** (đã có kinh nghiệm). Đúng không?"
> [Đúng rồi] [Điều chỉnh lại]
