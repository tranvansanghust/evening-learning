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


def format_quiz_detail(
    lesson_name: str,
    concepts_mastered: list,
    concepts_weak: list,
) -> str:
    lines = [f"📝 <b>Kết quả quiz: {lesson_name}</b>\n"]

    if concepts_mastered:
        lines.append("✅ <b>Nắm chắc:</b>")
        for c in concepts_mastered:
            lines.append(f"  • {c}")
        lines.append("")

    if concepts_weak:
        lines.append("⚠️ <b>Cần ôn lại:</b>")
        for w in concepts_weak:
            if isinstance(w, dict):
                concept = w.get("concept", "")
                explanation = w.get("correct_explanation", "")
                lines.append(f"  • <b>{concept}</b>")
                if explanation:
                    if len(explanation) > 150:
                        explanation = explanation[:147] + "..."
                    lines.append(f"    <i>{explanation}</i>")
            else:
                lines.append(f"  • {w}")
        lines.append("")

    if not concepts_mastered and not concepts_weak:
        lines.append("Quiz hoàn thành!")

    lines.append("💪 Gõ /today để học bài tiếp theo!")
    return "\n".join(lines)


def build_reengagement_message(days_inactive: int, course_name: str) -> str | None:
    """Trả về Telegram message hoặc None nếu không cần nhắc."""
    if days_inactive == 1:
        return (
            f"👋 Hôm qua bạn bận à?\n\n"
            f"Khoá <b>{course_name}</b> đang chờ bạn 📚\n"
            "Gõ /today để tiếp tục!"
        )
    elif days_inactive == 3:
        return (
            f"📚 Bạn chưa học <b>{days_inactive} ngày</b> rồi!\n"
            f"Khoá: <b>{course_name}</b>\n\n"
            "Gõ /today để học tiếp nhé! 💪"
        )
    elif days_inactive == 5:
        return (
            f"🤔 Bạn đã dừng học <b>{days_inactive} ngày</b>.\n\n"
            "Bạn có muốn tiếp tục không?\n"
            "• Gõ /today để học tiếp\n"
            "• Gõ /start nếu muốn đổi khoá học"
        )
    return None


def _progress_bar(pct: int, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)
