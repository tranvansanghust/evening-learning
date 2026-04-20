# Task 04: Fix OnboardingState bị tái dụng cho checkin

## Mục tiêu
Hiện tại khi user gõ `/done`, code tạo lại `OnboardingState` với `step="checkin"` để track trạng thái "đang chờ user mô tả bài học". Đây là hack — dùng bảng onboarding để lưu state quiz checkin. Cần tách riêng.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước, đặc biệt phần "Bug 4".

## Vấn đề hiện tại

```python
# telegram_handlers.py:175–180
onboarding_service = OnboardingService(db)
ob_state = onboarding_service.get_onboarding_state(user.user_id)
if ob_state is None:
    onboarding_service.create_onboarding_state(user.user_id)  # ← tạo mới để hack
onboarding_service.update_onboarding_state(user_id=user.user_id, current_step="checkin")
```

Và trong `handle_text`:
```python
# telegram_handlers.py:246–248
ob_state = onboarding_service.get_onboarding_state(user_id)
if ob_state is not None:
    await _handle_onboarding_step(...)  # ← route cả "checkin" vào đây
```

**Vấn đề:** Logic routing trong `handle_text` không phân biệt "đang onboarding thật" và "đang chờ checkin". Nếu user đang giữa chừng onboarding mà gõ `/done`, flow sẽ bị lẫn lộn.

## Giải pháp

Thêm một cột `is_checkin_pending` vào `quiz_sessions` HOẶC dùng approach đơn giản hơn: thêm cột `checkin_pending` (Boolean) vào bảng `users`.

**Approach được chọn — đơn giản nhất:** Thêm cột `checkin_pending: Boolean` vào `users` table.

- Khi user gõ `/done` → set `user.checkin_pending = True`
- Khi user gửi text và `checkin_pending == True` → xử lý như checkin, set `checkin_pending = False`
- Không cần tạo/xóa OnboardingState nữa cho checkin flow

## Files cần thay đổi

- `backend/app/models/user.py` — thêm column `checkin_pending`
- `backend/alembic/versions/` — tạo migration mới
- `backend/app/routers/telegram_handlers.py` — sửa `cmd_done`, `handle_text`, `_handle_checkin`

## Kế hoạch thực hiện

### Bước 1: Viết test trước (TDD)

Tạo `backend/tests/test_checkin_flow.py`:
```python
# Test: /done set checkin_pending=True, không tạo OnboardingState
# Test: text khi checkin_pending=True → start quiz, set checkin_pending=False
# Test: text khi checkin_pending=False và không có ob_state → fallback message
# Test: /done khi đang onboarding thật (ob_state tồn tại) → không làm gì (hoặc thông báo)
```

### Bước 2: Thêm column vào User model

```python
# app/models/user.py
from sqlalchemy import Boolean
checkin_pending = Column(Boolean, default=False, nullable=False, server_default="0")
```

### Bước 3: Tạo Alembic migration

```bash
cd backend
source eveninig-learning-venv/bin/activate
alembic revision --autogenerate -m "add_checkin_pending_to_users"
```

Kiểm tra file migration được tạo, verify nội dung đúng, chạy:
```bash
alembic upgrade head
```

### Bước 4: Sửa `cmd_done`

Xóa logic tạo OnboardingState hack. Thay bằng:
```python
user.checkin_pending = True
db.commit()
```

Thêm guard: nếu `ob_state` đang tồn tại (user đang onboarding thật) → không xử lý `/done`:
```python
ob_state = onboarding_service.get_onboarding_state(user.user_id)
if ob_state is not None:
    await message.answer("Bạn đang onboarding dở. Hãy hoàn thành onboarding trước!")
    return
```

### Bước 5: Sửa `handle_text` — phân tách routing

Thứ tự ưu tiên mới:
1. Nếu `ob_state` tồn tại VÀ `ob_state.current_step != "checkin"` → onboarding
2. Nếu `user.checkin_pending == True` → checkin
3. Nếu có quiz session active → quiz answer
4. Fallback

```python
# handle_text routing:
ob_state = onboarding_service.get_onboarding_state(user_id)
if ob_state is not None:
    await _handle_onboarding_step(...)
    return

if user and user.checkin_pending:
    await _handle_checkin(message, text, user, db)
    return

active_session = ...
if active_session:
    await _handle_quiz_answer(...)
    return
```

### Bước 6: Sửa `_handle_checkin`

Thay `onboarding_service.clear_state(user_id)` bằng:
```python
user.checkin_pending = False
db.commit()
```

Sửa signature để nhận `user` object thay vì `user_id` (cần user object để set field).

### Bước 7: Chạy tests

```bash
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] `users` table có cột `checkin_pending`
- [ ] Migration chạy được
- [ ] `/done` không tạo OnboardingState nữa
- [ ] Text khi checkin_pending → start quiz đúng
- [ ] Routing trong handle_text rõ ràng, không lẫn lộn onboarding và checkin
- [ ] Tests pass

## Rủi ro

Trung bình. Cần migration DB. Nếu đang có OnboardingState với step="checkin" trong DB thực → cần data migration hoặc handle case cũ.
