# Evening Learning — Project Rules for Claude

## Project Overview

AI-powered learning system với Telegram bot. Users học qua conversational quizzes, track real knowledge (không chỉ streaks).

**Tech Stack:**
- Backend: Python FastAPI
- Database: MySQL (SQLAlchemy ORM)
- LLM: OpenAI-compatible API (configured via `llm_base_url`, mặc định GPT-4o)
- Telegram Bot: aiogram 3.x (webhook + polling)
- Testing: pytest

**Structure:**
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings từ .env
│   ├── models/              # SQLAlchemy models
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   │   ├── handler_service.py   # Telegram message routing
│   │   ├── onboarding_service.py
│   │   ├── quiz_service.py
│   │   ├── llm_service.py       # LLM calls
│   │   └── llm_prompts.py       # Prompt templates
│   ├── schemas/             # Pydantic schemas
│   └── utils/
├── tests/                   # pytest tests (TDD)
└── eveninig-learning-venv/  # Virtual env (typo intentional)
```

---

## Development Commands

```bash
# Activate venv
cd backend
source eveninig-learning-venv/bin/activate

# Run server (dev)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_message_routing.py -v

# Run bot polling (alternative to webhook)
python -m app.bot_polling
```

---

## Planning Pipeline — Tính năng lớn phải lập kế hoạch trước

Với mọi tính năng cần sửa **nhiều hơn 1 file** hoặc có logic phức tạp:

### Bước 1: Tạo file kế hoạch trong `ai-proposals/`

Tên file: `ai-proposals/<feature-name>.md`

Nội dung bắt buộc:
```markdown
# [Tên tính năng]

## Mục tiêu
Mô tả ngắn tính năng cần làm.

## Các file cần thay đổi / tạo mới
- `path/to/file.py` — [tạo mới | sửa] — mô tả thay đổi
- ...

## Kế hoạch thực hiện (từng bước)
1. Bước 1: ...
2. Bước 2: ...
...

## Giải thích thiết kế (nếu phức tạp)
Lý do tại sao làm theo hướng này, các trade-off, dependency giữa các bước.
```

### Bước 2: Đợi xác nhận rồi mới implement

Sau khi tạo file proposal, **dừng lại và hỏi user** trước khi bắt đầu code.

### Bước 3: Đọc lại proposal trước khi implement

**Bắt buộc đọc lại file proposal** ngay trước khi bắt đầu code — user có thể đã chỉnh sửa nội dung sau khi tạo. Implement theo đúng nội dung mới nhất trong file. Nếu cần thay đổi plan, cập nhật file proposal trước.

**Không được bắt đầu implement tính năng lớn khi chưa có proposal được duyệt.**

---

## TDD — Viết test trước, implement sau

Với mọi tính năng mới hoặc bugfix:

1. **Viết test trước** trong `backend/tests/` — test phải fail
2. **Chạy test** để xác nhận fail đúng lý do
3. **Implement** code cho đến khi test pass
4. **Chạy lại toàn bộ test** để đảm bảo không break gì

**Không được implement code mới nếu chưa có test tương ứng.**

---

## Code Conventions

- **Async first**: Tất cả service methods và route handlers dùng `async def`
- **Services chứa business logic**, routers chỉ handle HTTP
- **Config qua `settings`**: Import từ `app.config`, không hardcode credentials
- **LLM calls** đi qua `llm_service.py`, không gọi OpenAI client trực tiếp ở nơi khác
- **Telegram messages** được route qua `handler_service.py`

---

## Code Quality Rules

### OOP — Bắt buộc dùng class

- Logic nghiệp vụ phải được đặt trong class, không viết hàm rời
- Mỗi class có một trách nhiệm rõ ràng (Single Responsibility)
- Dùng kế thừa hoặc composition khi có hành vi chung giữa các class

### Giới hạn độ dài file — Tối đa 300 lines

- Nếu file sắp vượt 300 lines, phải tách ra file/class mới trước khi tiếp tục
- Không được thêm code vào file đã > 300 lines mà không tách trước

### DRY — Không lặp code

- Bất kỳ đoạn logic nào xuất hiện > 1 lần phải được extract thành method hoặc class riêng
- Trước khi viết code mới, kiểm tra xem logic tương tự đã tồn tại chưa

---

## Documentation — Cập nhật sau mỗi thay đổi lớn

Sau mỗi tính năng hoàn thành hoặc thay đổi đáng kể, cập nhật file tương ứng trong `docs/tech/`:

- **Ngắn gọn**: chỉ ghi những ý chính — đủ để đọc và debug khi có lỗi
- **Không viết essay**: bullet points, không giải thích dài dòng
- Nếu chưa có file phù hợp → tạo file mới trong `docs/tech/`

Nội dung cần ghi:
- Tính năng làm gì, hoạt động ra sao (flow tóm tắt)
- Các file liên quan chính
- Edge cases hoặc điều kiện đặc biệt cần lưu ý
- Lỗi thường gặp và cách xử lý (nếu biết)

---

## API Routes

- `POST /webhook` — Telegram webhook receiver
- `POST /api/onboard/*` — Onboarding flow
- `POST /api/learn/*` — Learning flow
- `POST /api/quiz/*` — Quiz flow
- `GET /api/progress/*` — Progress tracking
- `GET /health` — Health check

---

## Environment Variables (`.env`)

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=evening_learning

TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_URL=...

LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=...
LLM_FAST_MODEL=gpt-4o-mini
LLM_SMART_MODEL=gpt-4o
```
