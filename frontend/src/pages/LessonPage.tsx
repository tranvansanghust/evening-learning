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
  generated_at: string;
}

export default function LessonPage() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const [lesson, setLesson] = useState<LessonContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!lessonId) {
      setError("Không tìm thấy ID bài học");
      setLoading(false);
      return;
    }

    const apiBase = import.meta.env.VITE_API_BASE_URL || "";
    fetch(`${apiBase}/api/lessons/${lessonId}/content`)
      .then((r) => {
        if (!r.ok) throw new Error(`Lỗi ${r.status}`);
        return r.json();
      })
      .then((data: LessonContent) => setLesson(data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [lessonId]);

  if (loading) return <LoadingSpinner />;
  if (error)
    return (
      <div className="error-state">Không tải được bài học: {error}</div>
    );
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
