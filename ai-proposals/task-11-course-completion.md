# Task 11: Course Completion (PASS) Flow

## Mục tiêu
Khi user hoàn thành tất cả lessons → update `UserCourse.status = PASS`, gửi thông báo chúc mừng, và gợi ý 3 chủ đề tiếp theo.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước.

## Files cần thay đổi

- `backend/app/routers/telegram_handlers.py` — sửa `cmd_today`
- `backend/app/services/llm_service.py` — thêm `suggest_next_topics()`

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Thêm vào `backend/tests/test_today_command.py`:

```python
# Test: get_current_lesson trả None + UserCourse.status còn IN_PROGRESS
#   → cmd_today update status=PASS, gửi completion message
# Test: get_current_lesson trả None + UserCourse.status đã là PASS
#   → chỉ gửi thông báo "đã hoàn thành", không update lại
```

### Bước 2: Thêm `suggest_next_topics()` vào `llm_service.py`

Method đơn giản, dùng `fast_model`:

```python
def suggest_next_topics(self, completed_course: str) -> str:
    """Gợi ý 3 chủ đề học tiếp sau khi hoàn thành một khóa."""
    prompt = (
        f"User vừa hoàn thành khóa học: {completed_course}.\n"
        "Gợi ý 3 chủ đề hoặc khóa học tiếp theo phù hợp, "
        "mỗi gợi ý trên một dòng, bắt đầu bằng số thứ tự. "
        "Trả lời bằng tiếng Việt, ngắn gọn."
    )
    response = self.client.chat.completions.create(
        model=self.fast_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()
```

### Bước 3: Sửa `cmd_today` — xử lý khi `lesson is None`

Hiện tại `cmd_today` khi `get_current_lesson()` trả `None` chỉ gửi "chúc mừng". Cần mở rộng:

```python
if not lesson:
    # Kiểm tra status hiện tại
    if enrollment.status != "PASS":
        # Lần đầu complete → update status
        from datetime import datetime
        enrollment.status = "PASS"
        enrollment.completed_at = datetime.utcnow()
        db.commit()

        # Gợi ý chủ đề tiếp theo
        try:
            suggestions = llm_service.suggest_next_topics(course.name)
            next_msg = f"\n\n🎯 <b>Bạn có thể học tiếp:</b>\n{suggestions}"
        except Exception:
            next_msg = ""

        await message.answer(
            f"🎉 <b>Chúc mừng!</b> Bạn đã hoàn thành khoá học <b>{course.name}</b>!\n\n"
            f"Bạn đã làm rất tốt 💪{next_msg}\n\n"
            "Gõ /start để bắt đầu khoá học mới.",
            parse_mode="HTML",
        )
    else:
        # Đã PASS rồi
        await message.answer(
            f"🏆 Bạn đã hoàn thành khoá <b>{course.name}</b> rồi!\n\n"
            "Gõ /start để chọn khoá học mới.",
            parse_mode="HTML",
        )
    return
```

Cần khởi tạo `llm_service` trong `cmd_today` — tương tự cách `_handle_checkin` làm:

```python
from app.config import settings
llm_service = LLMService(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    fast_model=settings.llm_fast_model,
    smart_model=settings.llm_smart_model,
)
```

### Bước 4: Chạy tests

```bash
cd backend && python -m pytest tests/test_today_command.py -v
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] Khi tất cả lessons done → `UserCourse.status = PASS`, `completed_at` được set
- [ ] Bot gửi thông báo chúc mừng + gợi ý chủ đề tiếp
- [ ] Gọi lại `/today` sau khi đã PASS → thông báo khác (không update lại)
- [ ] LLM error không làm crash — fallback gracefully
- [ ] Tests pass

## Lưu ý
`suggest_next_topics()` gọi LLM → có thể chậm. Nếu >2s, cân nhắc gửi "đang gợi ý..." trước rồi gửi kết quả sau.
