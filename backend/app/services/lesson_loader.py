"""Reads pre-built lesson content from the lessons/ directory on disk."""

from pathlib import Path
from typing import Optional

_LESSONS_DIR = Path(__file__).parent.parent.parent.parent / "lessons"


class LessonLoader:
    def __init__(self, lessons_dir: Path = _LESSONS_DIR):
        self._dir = lessons_dir

    def list_courses(self) -> list[dict]:
        """Return metadata for every course folder found on disk."""
        if not self._dir.exists():
            return []
        courses = []
        for course_dir in sorted(self._dir.iterdir()):
            if not course_dir.is_dir():
                continue
            lesson_files = self._lesson_files(course_dir)
            courses.append({
                "slug": course_dir.name,
                "title": self._course_title(course_dir),
                "total_lessons": len(lesson_files),
            })
        return courses

    def load_course(self, slug: str) -> Optional[dict]:
        """Load a course + all lesson files from disk.

        Returns dict with keys: slug, title, lessons (list of dicts with
        sequence_number, title, description, content_markdown).
        Returns None if slug not found.
        """
        course_dir = self._dir / slug
        if not course_dir.exists():
            return None
        lessons = []
        for i, f in enumerate(self._lesson_files(course_dir), start=1):
            content = f.read_text(encoding="utf-8")
            title = self._md_title(content) or f.stem
            lessons.append({
                "sequence_number": i,
                "title": title,
                "description": title,
                "content_markdown": content,
            })
        return {
            "slug": slug,
            "title": self._course_title(course_dir),
            "lessons": lessons,
        }

    # ------------------------------------------------------------------
    # Internal helpers

    def _lesson_files(self, course_dir: Path) -> list[Path]:
        return sorted(
            f for f in course_dir.iterdir()
            if f.suffix == ".md" and f.name != "README.md"
        )

    def _course_title(self, course_dir: Path) -> str:
        readme = course_dir / "README.md"
        if readme.exists():
            raw = self._md_title(readme.read_text(encoding="utf-8")) or course_dir.name
            return raw.split(" — ")[0].strip()
        return course_dir.name

    def _md_title(self, content: str) -> Optional[str]:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return None
