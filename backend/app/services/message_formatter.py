"""Format helpers for Telegram messages."""

from typing import List


def format_progress(progress) -> str:
    lesson_pct = int(progress.lessons_completed / max(progress.total_lessons, 1) * 100)
    concept_pct = int(progress.concepts_mastered / max(progress.total_concepts, 1) * 100)
    return (
        "📊 <b>Tiến độ học tập</b>\n\n"
        f"📚 Bài học: {progress.lessons_completed}/{progress.total_lessons} ({lesson_pct}%)\n"
        f"{_progress_bar(lesson_pct)}\n\n"
        f"🧠 Khái niệm: {progress.concepts_mastered}/{progress.total_concepts} ({concept_pct}%)\n"
        f"{_progress_bar(concept_pct)}"
    )


def format_quiz_list(summaries: List) -> str:
    if not summaries:
        return "Chưa có quiz nào. Gõ /done sau khi học xong bài!"
    lines = ["📖 <b>Danh sách quiz đã làm:</b>\n"]
    for i, s in enumerate(summaries, 1):
        date_str = s.date.strftime("%d/%m/%Y") if hasattr(s.date, "strftime") else str(s.date)
        lines.append(
            f"{i}. {s.lesson_name} — {date_str}\n"
            f"   ✅ {s.concepts_mastered_count} đạt / ⚠️ {s.concepts_weak_count} cần ôn"
        )
    return "\n".join(lines)


def _progress_bar(pct: int, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)
