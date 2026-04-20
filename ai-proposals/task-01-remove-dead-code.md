# Task 01: Xóa Dead Code

## Mục tiêu
Xóa ~700 dòng code không được sử dụng để giảm confusion khi đọc codebase. Không ảnh hưởng đến bất kỳ chức năng nào đang chạy.

## Tham khảo
Đọc `docs/tech/codebase-health.md` để hiểu toàn cảnh trước khi làm.

## Các file cần thay đổi

- `backend/app/routers/telegram_handlers.py` — xóa class `TelegramHandlers` (dòng 476–1010)
- `backend/app/services/handler_service.py` — xóa toàn bộ file
- `backend/app/services/telegram_service.py` — xóa toàn bộ file (xem lưu ý bên dưới)

## Kế hoạch thực hiện

### Bước 1: Verify dead code trước khi xóa

Chạy grep để xác nhận không có file nào ngoài dead code import những thứ này:

```bash
grep -r "TelegramHandlers" backend/ --include="*.py"
grep -r "HandlerService" backend/ --include="*.py"
grep -r "from app.services.handler_service" backend/ --include="*.py"
grep -r "from app.services.telegram_service" backend/ --include="*.py"
grep -r "ParsedUpdate" backend/ --include="*.py"
grep -r "TelegramService" backend/ --include="*.py"
```

Kết quả mong đợi: chỉ thấy references trong `telegram_handlers.py` (chính file đang xóa) và `telegram_service.py`. Nếu thấy file khác import → dừng lại, báo cáo.

### Bước 2: Xóa class TelegramHandlers trong telegram_handlers.py

Xóa từ dòng bắt đầu `class TelegramHandlers:` đến hết file (dòng 476–1010).

Giữ lại phần imports ở đầu file — nhưng sau khi xóa class, kiểm tra và xóa các imports không còn dùng:
- `from app.services.telegram_service import ParsedUpdate, TelegramService` → xóa
- `from app.models import QuizSummary` → kiểm tra có còn dùng trong router functions không

### Bước 3: Xóa file handler_service.py

```bash
rm backend/app/services/handler_service.py
```

### Bước 4: Xóa file telegram_service.py

Trước khi xóa, verify `InlineButton` và `TelegramService` không dùng ở đâu khác. Nếu xác nhận an toàn:

```bash
rm backend/app/services/telegram_service.py
```

### Bước 5: Dọn imports trong __init__.py nếu có

Kiểm tra `backend/app/services/__init__.py` xem có export HandlerService hay TelegramService không → xóa nếu có.

### Bước 6: Chạy tests

```bash
cd backend && python -m pytest tests/ -v
```

Tất cả tests hiện tại phải pass sau khi xóa.

### Bước 7: Verify bot vẫn khởi động được

```bash
cd backend
source eveninig-learning-venv/bin/activate
python -c "from app.routers.telegram_handlers import router; print('OK')"
python -c "from app.bot_polling import main; print('OK')"
```

## Định nghĩa "Done"

- [ ] Không còn file `handler_service.py`
- [ ] Không còn file `telegram_service.py`  
- [ ] `telegram_handlers.py` không còn class `TelegramHandlers`
- [ ] `telegram_handlers.py` không còn imports của dead classes
- [ ] Tất cả tests pass
- [ ] `from app.routers.telegram_handlers import router` không lỗi

## Rủi ro

Thấp. Dead code đã được verify không được gọi từ bất kỳ đâu trong runtime path.
