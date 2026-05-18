# task-20 — `/gen-lesson` CLI Command

## Mục tiêu

Tạo lệnh CLI `python -m scripts.gen_lesson <url>` để tự động:
1. Lấy nội dung khoá học từ URL (dùng LLM nếu trang JS-rendered)
2. Dùng LLM chia thành curriculum (N bài, tiêu đề + mô tả)
3. Tạo thư mục `lessons/<slug>/` với các file Markdown
4. Extract concepts cho từng bài (dùng LLM)
5. Seed vào DB: Course + Lessons + Concepts

## Các file cần thay đổi / tạo mới

- `backend/scripts/gen_lesson.py` — [tạo mới] — entry point CLI, parse args, orchestrate flow
- `backend/app/services/lesson_generator.py` — [tạo mới] — class `LessonGenerator`: fetch → curriculum → content → concepts → seed
- `backend/app/services/llm_prompts.py` — [sửa] — thêm 2 prompt: `concept_extraction()` và `curriculum_from_url()`
- `backend/app/services/course_seeder.py` — [tạo mới] — class `CourseSeeder`: insert Course + Lessons + Concepts vào DB

## Kế hoạch thực hiện

### Bước 1: Thêm 2 prompt vào `llm_prompts.py`

**`curriculum_from_url(url, page_content)`** — nhận URL + raw text của trang (có thể rỗng nếu JS-rendered), trả JSON:
```json
[
  {"sequence_number": 1, "title": "...", "description": "..."},
  ...
]
```

**`concept_extraction(lesson_title, lesson_content)`** — nhận tiêu đề + markdown content của 1 bài, trả JSON:
```json
[
  {"name": "var keyword", "description": "..."},
  {"name": "zero value", "description": "..."}
]
```

### Bước 2: Tạo `LessonGenerator` service

```
LessonGenerator
  ├── fetch_page(url) → str          # requests + BeautifulSoup, fallback: rỗng
  ├── generate_curriculum(url, content) → List[LessonPlan]   # gọi LLM prompt
  ├── generate_lesson_content(course, lesson_plan) → str     # gọi LLMContentGenerator
  ├── extract_concepts(title, content) → List[ConceptData]   # gọi LLM prompt
  └── save_markdown(slug, seq, title, content)               # ghi file lessons/<slug>/
```

Cấu trúc data class:
```python
@dataclass
class LessonPlan:
    sequence_number: int
    title: str
    description: str

@dataclass
class ConceptData:
    name: str
    description: str
```

### Bước 3: Tạo `CourseSeeder` service

```
CourseSeeder(db)
  └── seed(course_name, slug, lessons, concepts_per_lesson)
        → Course (tạo mới hoặc skip nếu đã tồn tại)
        → Lesson[] (với content_markdown đã điền)
        → Concept[] (từ concepts_per_lesson)
```

Dùng `course.name` làm unique key — nếu đã tồn tại thì hỏi user có muốn overwrite không.

### Bước 4: Tạo `gen_lesson.py` entry point

```
Usage: python -m scripts.gen_lesson <url> [--lessons N] [--level 0-3] [--dry-run]

Flow:
  1. fetch_page(url)
  2. generate_curriculum(url, page_content) → N bài
  3. Với mỗi bài:
     a. generate_lesson_content() → markdown
     b. extract_concepts() → concepts
     c. save_markdown() → lessons/<slug>/XX-title.md
  4. CourseSeeder.seed() → insert DB
  5. In ra summary: "Created course X with N lessons, M concepts"
```

Options:
- `--lessons N` — số bài (default: 5)
- `--level 0-3` — trình độ học viên (default: 0)
- `--dry-run` — chỉ tạo file md, không insert DB

## Giải thích thiết kế

**Tại sao tách `LessonGenerator` và `CourseSeeder`?**
- `LessonGenerator` = pure logic (fetch + LLM) — testable, không phụ thuộc DB
- `CourseSeeder` = DB side effect — tách ra để `--dry-run` hoạt động sạch

**Xử lý JS-rendered pages (như Go Tour):**
- `fetch_page()` dùng `requests` + `BeautifulSoup` — lấy được text nếu SSR
- Nếu trang trả về HTML rỗng/nav only: `curriculum_from_url` vẫn chạy được vì prompt hỏi LLM sinh curriculum **dựa trên URL + tên khoá học** (LLM biết nội dung Go Tour, MDN, v.v.)
- Fallback này đủ tốt cho các khoá học well-known

**Slug generation:**
- URL `https://go.dev/tour/basics` → slug `go-tour-basics`
- Dùng để đặt tên thư mục `lessons/go-tour-basics/` và làm course identifier

**Không dùng Playwright/Selenium** — quá nặng cho CLI tool, LLM fallback đủ tốt.
