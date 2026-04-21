# Task 12: LLM-Generated Contextual Assessment Questions

## Mục tiêu
Q1/Q2 hiện hardcode câu hỏi về "web app" và "HTML/CSS" dù user có thể học bất kỳ chủ đề nào (Python, Machine Learning, DevOps...). Cần LLM sinh câu hỏi phù hợp với `course_topic` của user.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước.

## Vấn đề cụ thể

```python
# telegram_handlers.py — hardcoded, không liên quan đến course_topic
await message.answer("Bạn đã từng xây dựng web app chưa?")  # ← luôn hỏi về web app
await message.answer("Bạn có biết HTML/CSS chưa?")           # ← luôn hỏi về HTML/CSS
```

Nếu user muốn học "Machine Learning" → câu hỏi về "web app" hoàn toàn vô nghĩa.

## Approach

Giữ nguyên cấu trúc 2 câu hỏi binary (Q1/Q2) và inline buttons. Chỉ thay text câu hỏi bằng LLM-generated text phù hợp với `course_topic`.

**Không thay đổi:**
- Số lượng câu hỏi (vẫn 2)
- Cấu trúc binary answers ("Chưa"/"Rồi")
- Logic `assess_level()` trong `onboarding_service.py`
- Inline keyboard buttons

**Thay đổi:**
- Text câu hỏi Q1 và Q2 được LLM sinh dựa trên `course_topic`
- Lưu text câu hỏi vào `OnboardingState` để dùng lại khi cần

## Files cần thay đổi

- `backend/app/services/llm_service.py` — thêm `generate_assessment_questions()`
- `backend/app/models/onboarding_state.py` — thêm `q1_text`, `q2_text` columns
- `backend/alembic/versions/` — migration mới
- `backend/app/services/onboarding_service.py` — update `update_onboarding_state()` để nhận q1_text/q2_text
- `backend/app/routers/telegram_handlers.py` — sửa bước `course_input` và `q1`

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Tạo `backend/tests/test_llm_assessment_questions.py`:

```python
# Test: generate_assessment_questions trả dict với q1, q2_if_no, q2_if_yes
# Test: q1 chứa "Python" khi course_topic = "Python cơ bản"
# Test: q1 chứa "Machine Learning" khi course_topic = "ML với scikit-learn"
# Test: LLM trả output sai format → fallback về câu hỏi generic
```

Tạo `backend/tests/test_onboarding_llm_questions.py`:

```python
# Test: bước course_input → gọi LLM generate questions → hiển thị q1 từ LLM
# Test: bước q1 → hiển thị q2 từ LLM (không phải hardcoded HTML/CSS)
# Test: LLM lỗi → fallback về câu hỏi generic, onboarding vẫn tiếp tục
```

### Bước 2: Thêm `generate_assessment_questions()` vào `llm_service.py`

```python
def generate_assessment_questions(self, course_topic: str) -> dict:
    """
    Sinh 2 câu hỏi đánh giá trình độ phù hợp với course_topic.

    Returns:
        dict với keys:
            q1: câu hỏi về kinh nghiệm tổng quát với lĩnh vực này
            q2_if_no: câu hỏi nếu Q1 = "chưa có kinh nghiệm"
            q2_if_yes: câu hỏi nếu Q1 = "đã có kinh nghiệm"

    Fallback nếu LLM lỗi: trả dict với câu hỏi generic
    """
    prompt = f"""Bạn là trợ lý đánh giá trình độ học viên.
User muốn học: "{course_topic}"

Hãy tạo 2 câu hỏi ngắn để đánh giá trình độ của họ:
1. Q1: Câu hỏi về kinh nghiệm tổng quát với lĩnh vực "{course_topic}" (ví dụ: "Bạn đã từng làm việc với X chưa?")
2. Q2_if_no: Nếu user trả lời CHƯA CÓ kinh nghiệm → hỏi về kiến thức nền tảng cần thiết
3. Q2_if_yes: Nếu user trả lời ĐÃ CÓ kinh nghiệm → hỏi về mức độ nâng cao hơn

Trả về JSON với format:
{{"q1": "...", "q2_if_no": "...", "q2_if_yes": "..."}}

Câu hỏi phải:
- Ngắn gọn (dưới 15 từ)
- Có thể trả lời Có/Chưa
- Liên quan trực tiếp đến "{course_topic}"
"""
    try:
        response = self.client.chat.completions.create(
            model=self.fast_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(response.choices[0].message.content)
        # Validate keys
        assert "q1" in data and "q2_if_no" in data and "q2_if_yes" in data
        return data
    except Exception as e:
        logger.warning(f"generate_assessment_questions failed, using fallback: {e}")
        return {
            "q1": f"Bạn đã có kinh nghiệm với {course_topic} chưa?",
            "q2_if_no": "Bạn đã có nền tảng lập trình cơ bản chưa?",
            "q2_if_yes": f"Bạn đã từng làm dự án thực tế với {course_topic} chưa?",
        }
```

### Bước 3: Thêm columns vào `OnboardingState`

```python
# app/models/onboarding_state.py
q1_text = Column(String(300), nullable=True)
q2_text = Column(String(300), nullable=True)  # text thực tế hiển thị cho q2 (tùy q1 answer)
```

### Bước 4: Tạo Alembic migration

```bash
cd backend
source eveninig-learning-venv/bin/activate
alembic revision --autogenerate -m "add_q1_text_q2_text_to_onboarding_state"
alembic upgrade head
```

### Bước 5: Update `update_onboarding_state()` trong `onboarding_service.py`

Thêm params `q1_text` và `q2_text` vào method signature và body.

### Bước 6: Sửa `_handle_onboarding_step` trong `telegram_handlers.py`

**Bước `course_input` — sau khi lưu topic, gọi LLM gen questions:**

```python
elif step == "course_input":
    onboarding_service.update_onboarding_state(
        user_id=user_id, course_topic=text, current_step="q1"
    )

    # Gen questions từ LLM
    from app.config import settings
    llm = LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )
    questions = llm.generate_assessment_questions(text)

    # Lưu questions vào state
    onboarding_service.update_onboarding_state(
        user_id=user_id,
        q1_text=questions["q1"],
        # Lưu cả q2_if_no và q2_if_yes — sẽ chọn đúng cái ở bước q1
        # Dùng separator để lưu 1 field: "q2_if_no|||q2_if_yes"
        # Hoặc dùng 2 columns riêng (preferred)
    )

    q1_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Chưa"), KeyboardButton(text="Rồi")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(questions["q1"], reply_markup=q1_keyboard)
```

**Lưu ý:** Cần lưu cả `q2_if_no` và `q2_if_yes` vào state. Options:
- 2 columns riêng: `q2_text_if_no`, `q2_text_if_yes` (preferred, rõ ràng hơn)
- Hoặc 1 column `q2_texts` dưới dạng JSON string

**Bước `q1` — dùng q2_text từ state thay vì hardcode:**

```python
elif step == "q1":
    answer = "never" if any(w in text.lower() for w in ["chưa", "không", "never", "no"]) else "yes"
    onboarding_service.update_onboarding_state(
        user_id=user_id, q1_answer=answer, current_step="q2"
    )

    # Lấy q2 question từ state
    ob_state = onboarding_service.get_onboarding_state(user_id)
    if answer == "never":
        q2_text = getattr(ob_state, "q2_text_if_no", None) or "Bạn có nền tảng lập trình cơ bản chưa?"
    else:
        q2_text = getattr(ob_state, "q2_text_if_yes", None) or "Bạn đã làm dự án thực tế chưa?"

    q2_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Chưa"), KeyboardButton(text="Rồi")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(q2_text, reply_markup=q2_keyboard)
```

### Bước 7: Chạy tests

```bash
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `generate_assessment_questions(course_topic)` có trong `llm_service.py`
- [ ] LLM lỗi → fallback câu hỏi generic, không crash
- [ ] `OnboardingState` có `q1_text`, `q2_text_if_no`, `q2_text_if_yes`
- [ ] Migration chạy được
- [ ] Q1 hiển thị câu hỏi từ LLM (liên quan đến course_topic)
- [ ] Q2 hiển thị câu hỏi đúng context (if_no hoặc if_yes)
- [ ] `assess_level()` vẫn hoạt động bình thường (không thay đổi)
- [ ] Tests pass

## Rủi ro

- Trung bình. LLM call trong onboarding làm chậm response ~1-2s → cần loading indicator hoặc async.
- `response_format={"type": "json_object"}` cần model support. Nếu không support → parse text thủ công.
