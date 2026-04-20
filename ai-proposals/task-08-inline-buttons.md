# Task 08: Inline Buttons cho Onboarding

## Mục tiêu
Onboarding Q1/Q2 hiện yêu cầu user gõ text ("có/chưa"). Cần thêm `ReplyKeyboardMarkup` để user chỉ cần bấm button.

## Tham khảo
Đọc `docs/tech/codebase-health.md` trước.

## Files cần thay đổi

- `backend/app/routers/telegram_handlers.py` — sửa `_handle_onboarding_step`

## Không cần thay đổi DB, không cần migration

Logic text parsing vẫn giữ nguyên (phòng trường hợp user gõ tay). Chỉ thêm keyboard gợi ý.

## API aiogram cần dùng

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Tạo keyboard 2 nút nằm ngang
keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Chưa bao giờ"), KeyboardButton(text="Rồi")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# Xóa keyboard
await message.answer("...", reply_markup=ReplyKeyboardRemove())
```

## Kế hoạch thực hiện

### Bước 1: Viết test trước

Thêm vào `backend/tests/test_checkin_flow.py` hoặc tạo file mới:

```python
# Test: bước course_input → message.answer được gọi không có reply_markup đặc biệt
# Test: bước q1 → message.answer được gọi với ReplyKeyboardMarkup có 2 nút
# Test: bước q2 (q1=never) → keyboard ["Chưa", "Có rồi"]
# Test: bước q2 (q1=yes) → keyboard ["Chưa", "Có rồi"]
# Test: bước deadline → ReplyKeyboardRemove() được gọi
```

### Bước 2: Thêm import vào đầu `telegram_handlers.py`

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
```

### Bước 3: Sửa `_handle_onboarding_step`

**Bước `course_input` → hỏi Q1 với keyboard:**
```python
# Sau khi lưu course_topic, chuyển q1:
keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Chưa bao giờ"), KeyboardButton(text="Rồi")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
await message.answer(
    "Bạn đã từng xây dựng web app chưa?",
    reply_markup=keyboard,
)
```

**Bước `q1` → hỏi Q2 với keyboard:**
```python
keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Chưa"), KeyboardButton(text="Có rồi")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
if answer == "never":
    await message.answer("Bạn có biết HTML/CSS chưa?", reply_markup=keyboard)
else:
    await message.answer("Bạn đã dùng framework khác như Vue, Angular chưa?", reply_markup=keyboard)
```

**Bước `q2` → hỏi deadline, xóa keyboard:**
```python
await message.answer(
    "Bạn muốn hoàn thành khoá học trong bao lâu?\n\nVí dụ: 1 month, 3 months, 2026-06-01",
    reply_markup=ReplyKeyboardRemove(),
)
```

**Các bước `deadline`, `hours`, `reminder` giữ nguyên** — không cần keyboard vì là free-text input.

### Bước 4: Logic parsing text đã có vẫn hoạt động

`q1` step đang check: `any(w in text.lower() for w in ["chưa", "không", "never", "no"])` → "Chưa bao giờ" sẽ match "chưa" → hoạt động đúng không cần sửa parser.

`q2` step tương tự → "Chưa" sẽ match "chưa" → đúng.

### Bước 5: Chạy tests

```bash
cd backend && python -m pytest tests/ -v
```

## Định nghĩa "Done"

- [ ] Q1 hiển thị keyboard ["Chưa bao giờ", "Rồi"]
- [ ] Q2 hiển thị keyboard ["Chưa", "Có rồi"]
- [ ] Keyboard biến mất sau khi qua bước deadline
- [ ] Logic parsing text vẫn hoạt động nếu user gõ tay
- [ ] Tests pass
