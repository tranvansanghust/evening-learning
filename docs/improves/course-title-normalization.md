# Course Title Normalization

## Vấn đề

User nhập topic tự do khi onboard: "tôi muốn học về K8s", "học kubernetes cho devops", "piano từ đầu"...

Chuỗi này được dùng trực tiếp làm `course.name` → hiển thị xấu khắp nơi:
- Tin nhắn bot: "Bạn vừa học xong *tôi muốn học về K8s* 🎉"
- Quiz prompt: `course_topic = "tôi muốn học về K8s"`
- LLM sinh câu hỏi với context xấu
- Lesson titles từ curriculum generator cũng kém sát

## Giải pháp

Sau khi user nhập topic, gọi LLM để chuẩn hóa thành tên khóa học ngắn gọn, chuẩn:

| Input | Output |
|---|---|
| "tôi muốn học về K8s" | "Kubernetes Cơ Bản" |
| "học kubernetes cho devops" | "Kubernetes cho DevOps" |
| "piano từ đầu" | "Piano Từ Đầu" |
| "react js" | "React.js" |

Tên này dùng xuyên suốt: `course.name`, tin nhắn bot, quiz prompt, lesson content.

## Files cần thay đổi

- `backend/app/services/llm_prompts.py` — thêm `course_title_normalization(raw_input)`
- `backend/app/services/llm_service.py` — thêm `normalize_course_title(raw_input) -> str`
- `backend/app/routers/telegram_handlers.py` — gọi normalize ngay sau khi user nhập topic (bước `course_input` trong onboarding)

## Kế hoạch thực hiện

### Bước 1 — Prompt

```python
@staticmethod
def course_title_normalization(raw_input: str) -> str:
    return f"""Chuẩn hóa input sau thành tên khóa học ngắn gọn (2-5 từ), tiếng Việt hoặc Anh tùy ngữ cảnh.

Input: "{raw_input}"

Yêu cầu:
- Loại bỏ các cụm thừa: "tôi muốn học", "học về", "từ đầu" nếu không cần thiết
- Viết hoa chữ cái đầu mỗi từ quan trọng
- Giữ tên công nghệ đúng chuẩn: Kubernetes, React.js, Python, v.v.
- Tối đa 5 từ

Chỉ trả về tên khóa học, không có gì khác."""
```

### Bước 2 — LLM method

```python
def normalize_course_title(self, raw_input: str) -> str:
    # Dùng fast_model, max_tokens=30
    # Fallback: title-case của raw_input nếu LLM fail
```

### Bước 3 — Gọi trong onboarding

Trong `_handle_onboarding_step` khi xử lý bước `course_input`:
```python
# Sau khi detect topic, trước khi lưu vào state:
normalized = llm_service.normalize_course_title(text)
onboarding_service.update_onboarding_state(user_id, course_topic=normalized)
# Confirm với user: "Tuyệt! Mình sẽ tạo khóa học **Kubernetes Cơ Bản** cho bạn."
```

## Lưu ý

- Chỉ normalize khi `input_type == "topic"` (không phải Udemy URL)
- Lưu `normalized_title` vào `OnboardingState.course_topic` ngay — downstream code (`complete_onboarding`, curriculum generation, LLM prompts) đều dùng `course_topic` làm source of truth
- Không cần migration DB vì `course.name` vẫn là VARCHAR
