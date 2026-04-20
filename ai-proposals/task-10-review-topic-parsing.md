# Task 10: /review [topic] — Argument Parsing

## Mục tiêu
`/review` hiện luôn trả toàn bộ danh sách quiz. Cần hỗ trợ `/review React` để filter theo topic.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước.

## Files cần thay đổi

- `backend/app/routers/telegram_handlers.py` — sửa `cmd_review`

## Không cần thay đổi ProgressService

`ProgressService.get_review_by_topic(user_id, topic, db_session)` đã có sẵn — filter theo `lesson.title.contains(topic)` case-insensitive.

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Thêm vào `backend/tests/test_progress_review_commands.py`:

```python
# Test: /review không có arg → trả all summaries
# Test: /review React → chỉ trả summaries có lesson_name chứa "React"
# Test: /review TopicKhongTon → trả "Không tìm thấy quiz nào về TopicKhongTon"
```

### Bước 2: Sửa `cmd_review`

```python
@router.message(Command("review"))
async def cmd_review(message: Message) -> None:
    from app.models import User

    telegram_id = str(message.from_user.id)
    # Parse topic argument: "/review React" → topic = "React"
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return

        progress_service = ProgressService(db)

        if topic:
            summaries = progress_service.get_review_by_topic(
                user_id=user.user_id, topic=topic, db_session=db
            )
            if not summaries:
                await message.answer(
                    f"Không tìm thấy quiz nào về <b>{topic}</b>.\n\n"
                    "Gõ /review để xem tất cả.",
                    parse_mode="HTML",
                )
                return
        else:
            summaries = progress_service.get_quiz_summaries(
                user_id=user.user_id, db_session=db
            )

        msg = format_quiz_list(summaries)
        await message.answer(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_review: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()
```

### Bước 3: Chạy tests

```bash
cd backend && python -m pytest tests/test_progress_review_commands.py -v
```

## Định nghĩa "Done"

- [ ] `/review` không có arg → trả all summaries như cũ
- [ ] `/review React` → filter đúng theo topic
- [ ] `/review XYZ` không tìm thấy → thông báo phù hợp
- [ ] Tests pass
