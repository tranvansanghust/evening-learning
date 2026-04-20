# Task 09: Quiz Summary Formatted Display

## Mục tiêu
Khi quiz kết thúc, bot hiện gửi text thô. Cần format đẹp với ✅/⚠️, bold, danh sách rõ ràng.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước.

## Files cần thay đổi

- `backend/app/services/message_formatter.py` — thêm `format_quiz_detail()`
- `backend/app/routers/telegram_handlers.py` — sửa `_handle_quiz_answer` dùng formatter mới

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Tạo `backend/tests/test_message_formatter.py`:

```python
# Test: format_quiz_detail với concepts_mastered + concepts_weak đầy đủ
# Test: format_quiz_detail không có weak concepts → không hiển thị section ⚠️
# Test: format_quiz_detail không có mastered → không hiển thị section ✅
# Test: weak concept với correct_explanation dài → truncate ở 150 chars
```

### Bước 2: Thêm `format_quiz_detail` vào `message_formatter.py`

```python
def format_quiz_detail(
    lesson_name: str,
    concepts_mastered: list,
    concepts_weak: list,
) -> str:
    """Format quiz result khi kết thúc session."""
    lines = [f"📝 <b>Kết quả quiz: {lesson_name}</b>\n"]

    if concepts_mastered:
        lines.append("✅ <b>Nắm chắc:</b>")
        for c in concepts_mastered:
            lines.append(f"  • {c}")
        lines.append("")

    if concepts_weak:
        lines.append("⚠️ <b>Cần ôn lại:</b>")
        for w in concepts_weak:
            if isinstance(w, dict):
                concept = w.get("concept", "")
                explanation = w.get("correct_explanation", "")
                lines.append(f"  • <b>{concept}</b>")
                if explanation:
                    # Truncate dài
                    if len(explanation) > 150:
                        explanation = explanation[:147] + "..."
                    lines.append(f"    <i>{explanation}</i>")
            else:
                lines.append(f"  • {w}")
        lines.append("")

    if not concepts_mastered and not concepts_weak:
        lines.append("Quiz hoàn thành!")

    lines.append("💪 Gõ /today để học bài tiếp theo!")
    return "\n".join(lines)
```

### Bước 3: Sửa `_handle_quiz_answer` trong `telegram_handlers.py`

Import thêm:
```python
from app.services.message_formatter import format_progress, format_quiz_list, format_quiz_detail
```

Khi `next_action == "end"`, thay vì gửi `summary` string thô:

```python
if next_action == "end":
    summary_text = result.get("summary", "")
    concepts_mastered = result.get("concepts_mastered", [])
    concepts_weak = result.get("concepts_weak", [])

    # Lấy lesson name từ active_session
    lesson_name = active_session.lesson.title if active_session.lesson else "Bài học"

    if concepts_mastered or concepts_weak:
        msg = format_quiz_detail(lesson_name, concepts_mastered, concepts_weak)
    else:
        msg = f"Quiz hoàn thành! ✅\n\n{summary_text}\n\nGõ /today để học bài tiếp 📚"

    await message.answer(msg, parse_mode="HTML")
```

**Lưu ý:** `QuizService.submit_answer()` khi `action == END` đã trả `result["summary"]` (text) nhưng không trả `concepts_mastered`/`concepts_weak` riêng. Cần check và bổ sung nếu thiếu — hoặc parse từ `QuizSummary` object.

Kiểm tra `quiz_service.py:submit_answer()` — nếu `result["summary"]` là string thô từ LLM, cần gọi thêm `quiz_service.get_or_generate_summary(session_id, db)` để lấy structured data.

### Bước 4: Chạy tests

```bash
cd backend && python -m pytest tests/test_message_formatter.py -v
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `format_quiz_detail()` có trong `message_formatter.py`
- [ ] Khi quiz kết thúc, bot gửi message đẹp với ✅ và ⚠️ sections
- [ ] Explanation dài được truncate
- [ ] Fallback hợp lý khi không có concepts data
- [ ] Tests pass, không break tests cũ
