# Task 03: Implement /progress và /review thật

## Mục tiêu
Hai lệnh `/progress` và `/review` hiện chỉ gửi "đang tải..." mà không trả dữ liệu thật. Cần gọi `ProgressService` và format kết quả để gửi cho user.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước.

## Files cần thay đổi

- `backend/app/routers/telegram_handlers.py` — sửa `cmd_progress` (dòng 196–199) và `cmd_review` (dòng 201–203)

## Không thay đổi ProgressService

`ProgressService` đã có sẵn các methods cần dùng. Không cần sửa. Chỉ cần gọi đúng từ handler.

## API của ProgressService (đọc trước khi code)

```python
# backend/app/services/progress_service.py

class ProgressService:
    def __init__(self, db: Session): ...
    
    def get_user_progress(self, user_id: int, db_session: Session) -> UserProgress:
        # Returns: UserProgress(lessons_completed, total_lessons, concepts_mastered, total_concepts)
        
    def get_quiz_summaries(self, user_id: int, db_session: Session) -> List[QuizSummaryPreview]:
        # Returns: list of QuizSummaryPreview(summary_id, date, lesson_name, concepts_mastered_count, concepts_weak_count)
```

**Lưu ý quan trọng:** `ProgressService` nhận `user_id` (int từ DB), không phải `telegram_id` (string). Cần lookup user từ telegram_id trước.

## Kế hoạch thực hiện

### Bước 1: Viết test trước (TDD)

Tạo `backend/tests/test_progress_review_commands.py`:

```python
# Test: /progress với user có 2/5 bài xong → format đúng số liệu
# Test: /progress với user không tồn tại → trả thông báo "chưa có tài khoản"
# Test: /review với user có 3 quiz summaries → format đúng danh sách
# Test: /review với user chưa có quiz → "chưa có quiz nào"
```

### Bước 2: Tạo helper function `get_user_by_telegram`

Thêm vào `telegram_handlers.py` (hoặc tìm xem đã có chưa):

```python
def _get_user_by_telegram_id(telegram_id: str, db: Session):
    from app.models import User
    return db.query(User).filter(User.telegram_id == telegram_id).first()
```

Kiểm tra xem đã có pattern tương tự trong file chưa (cmd_start, cmd_today đều làm điều này). Nếu lặp lại 3+ lần → extract thành helper.

### Bước 3: Implement `cmd_progress`

```python
@router.message(Command("progress"))
async def cmd_progress(message: Message) -> None:
    from app.models import User
    
    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return
        
        progress_service = ProgressService(db)
        progress = progress_service.get_user_progress(user.user_id, db_session=db)
        
        # Format progress message — tự viết, không dùng HandlerService (dead code)
        # Xem format gợi ý trong handler_service.py:31–94 để tham khảo (nhưng không import)
        msg = _format_progress(progress)
        await message.answer(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_progress: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()
```

Viết `_format_progress(progress)` trực tiếp trong file (private helper function, không class).

### Bước 4: Implement `cmd_review`

```python
@router.message(Command("review"))
async def cmd_review(message: Message) -> None:
    from app.models import User
    
    telegram_id = str(message.from_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Bạn chưa có tài khoản. Gõ /start để bắt đầu!")
            return
        
        progress_service = ProgressService(db)
        summaries = progress_service.get_quiz_summaries(user.user_id, db_session=db)
        
        msg = _format_quiz_list(summaries)
        await message.answer(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_review: {e}", exc_info=True)
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
    finally:
        db.close()
```

### Bước 5: Viết format helpers

Hai private functions đơn giản trong `telegram_handlers.py`:

```python
def _format_progress(progress) -> str:
    # Trả về string với emoji, số liệu, progress bar text
    # Tham khảo logic trong handler_service.py để viết lại (không import)

def _format_quiz_list(summaries) -> str:
    # Trả về danh sách dạng "1. Lesson Name - ngày - X đạt / Y cần ôn"
    # Nếu rỗng: "Chưa có quiz nào. Gõ /done sau khi học xong bài!"
```

### Bước 6: Thêm import ProgressService vào đầu file

```python
from app.services.progress_service import ProgressService
```

### Bước 7: Chạy tests

```bash
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `/progress` trả dữ liệu thật từ DB (lessons completed, concepts mastered)
- [ ] `/progress` xử lý đúng khi user không tìm thấy
- [ ] `/review` trả danh sách quiz summaries thật
- [ ] `/review` trả thông báo phù hợp khi chưa có summary
- [ ] Tests cover cả happy path và edge cases
- [ ] Không import HandlerService (dead code)

## Giới hạn file
Nếu `telegram_handlers.py` sắp vượt 300 dòng sau khi thêm code này → tách `_format_progress` và `_format_quiz_list` vào file `app/services/message_formatter.py` mới.
