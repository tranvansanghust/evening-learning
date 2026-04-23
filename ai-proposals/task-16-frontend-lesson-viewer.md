# Task 16: Frontend Lesson Viewer Web App

## Mục tiêu
Xây dựng frontend web app trong `frontend/` để hiển thị nội dung bài học dưới dạng Markdown đẹp, mobile-friendly. User mở link từ Telegram → đọc bài học trên web.

## Tham khảo
Làm **sau task-15** (cần API endpoint `/api/lessons/{lesson_id}/content` hoạt động). Không phụ thuộc task-14 trực tiếp.

## Tech stack lựa chọn

**Vite + React + TypeScript** vì:
- Build nhanh, dev server instant
- `react-markdown` + `remark-gfm` render Markdown đẹp
- Mobile responsive dễ với CSS modules hoặc Tailwind
- Deploy tĩnh được (Vercel, Netlify, hoặc serve từ FastAPI `StaticFiles`)

## Files cần tạo mới

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── pages/
│   │   └── LessonPage.tsx       ← trang chính
│   ├── components/
│   │   ├── MarkdownRenderer.tsx  ← render markdown
│   │   └── LoadingSpinner.tsx
│   └── styles/
│       └── lesson.css
└── .env.example                 ← VITE_API_BASE_URL
```

## Kế hoạch thực hiện

### Bước 1: Khởi tạo project Vite

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install react-markdown remark-gfm
npm install react-router-dom
```

### Bước 2: Cấu hình env

`.env.example`:
```
VITE_API_BASE_URL=http://localhost:8000
```

`.env.local` (gitignored):
```
VITE_API_BASE_URL=http://localhost:8000
```

### Bước 3: Routing — `App.tsx`

URL format: `/lesson/{lesson_id}`

```tsx
// src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import LessonPage from "./pages/LessonPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/lesson/:lessonId" element={<LessonPage />} />
        <Route path="*" element={<div style={{padding: "2rem"}}>Trang không tồn tại</div>} />
      </Routes>
    </BrowserRouter>
  );
}
```

### Bước 4: `LessonPage.tsx` — fetch + render

```tsx
// src/pages/LessonPage.tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import MarkdownRenderer from "../components/MarkdownRenderer";
import LoadingSpinner from "../components/LoadingSpinner";
import "../styles/lesson.css";

interface LessonContent {
  lesson_id: number;
  title: string;
  sequence_number: number;
  content_markdown: string;
  course_name: string;
}

export default function LessonPage() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const [lesson, setLesson] = useState<LessonContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || "";
    fetch(`${apiBase}/api/lessons/${lessonId}/content`)
      .then((r) => {
        if (!r.ok) throw new Error(`Lỗi ${r.status}`);
        return r.json();
      })
      .then(setLesson)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [lessonId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="error-state">Không tải được bài học: {error}</div>;
  if (!lesson) return null;

  return (
    <div className="lesson-container">
      <header className="lesson-header">
        <p className="course-name">{lesson.course_name}</p>
        <h1 className="lesson-title">{lesson.title}</h1>
        <span className="lesson-badge">Bài {lesson.sequence_number}</span>
      </header>
      <main className="lesson-content">
        <MarkdownRenderer content={lesson.content_markdown} />
      </main>
      <footer className="lesson-footer">
        <p>Học trên Telegram bot để làm quiz bài này</p>
      </footer>
    </div>
  );
}
```

### Bước 5: `MarkdownRenderer.tsx`

```tsx
// src/components/MarkdownRenderer.tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
```

### Bước 6: CSS — `lesson.css`

Mobile-first, clean typography, dễ đọc trên điện thoại:

```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f8f9fa;
  color: #212529;
  line-height: 1.6;
}

.lesson-container {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 1rem 3rem;
}

.lesson-header {
  padding: 1.5rem 0 1rem;
  border-bottom: 2px solid #e9ecef;
  margin-bottom: 1.5rem;
}

.course-name { font-size: 0.8rem; color: #6c757d; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
.lesson-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }
.lesson-badge { display: inline-block; background: #0d6efd; color: white; font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 12px; }

.lesson-content { line-height: 1.75; }

.markdown-body h2 { font-size: 1.25rem; margin: 1.5rem 0 0.5rem; color: #343a40; }
.markdown-body h3 { font-size: 1.05rem; margin: 1.25rem 0 0.4rem; color: #495057; }
.markdown-body p { margin-bottom: 1rem; }
.markdown-body ul, .markdown-body ol { padding-left: 1.5rem; margin-bottom: 1rem; }
.markdown-body li { margin-bottom: 0.25rem; }
.markdown-body code { background: #e9ecef; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
.markdown-body pre { background: #212529; color: #f8f9fa; padding: 1rem; border-radius: 6px; overflow-x: auto; margin-bottom: 1rem; }
.markdown-body pre code { background: none; padding: 0; }
.markdown-body blockquote { border-left: 4px solid #0d6efd; padding-left: 1rem; color: #6c757d; margin-bottom: 1rem; }

.lesson-footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e9ecef; color: #6c757d; font-size: 0.85rem; text-align: center; }

.error-state { padding: 2rem; color: #dc3545; text-align: center; }

@media (max-width: 480px) {
  .lesson-title { font-size: 1.25rem; }
}
```

### Bước 7: Vite config — proxy API trong dev

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

Với proxy này, `VITE_API_BASE_URL` có thể để trống trong dev.

### Bước 8: Dev test

```bash
cd frontend
npm run dev
# Mở http://localhost:5173/lesson/1
```

### Bước 9 (optional): Deploy tĩnh từ FastAPI

Sau `npm run build`, serve `frontend/dist/` từ FastAPI:

```python
# backend/app/main.py
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")
```

## Định nghĩa "Done"

- [ ] `frontend/` có package.json, vite.config.ts, tsconfig.json
- [ ] `npm run dev` khởi động được
- [ ] `npm run build` không lỗi
- [ ] `/lesson/{lesson_id}` fetch từ API và render Markdown
- [ ] Loading state khi đang fetch
- [ ] Error state khi 404 hoặc network lỗi
- [ ] Mobile-friendly (test ở 375px width)
- [ ] VITE_API_BASE_URL có trong `.env.example`

## Rủi ro

- CORS: Backend phải allow frontend origin (task-15 đã handle). Trong dev dùng Vite proxy nên không cần lo.
- Markdown XSS: `react-markdown` mặc định sanitize HTML — an toàn.
- First paint chậm nếu content chưa gen và phải chờ LLM (~3-5s). Loading spinner là bắt buộc.
