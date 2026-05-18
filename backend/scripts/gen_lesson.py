"""
gen_lesson — Generate a course from a URL and seed it into the database.

Usage:
    cd backend
    source eveninig-learning-venv/bin/activate
    python -m scripts.gen_lesson <url> [options]

Options:
    --lessons N       Number of lessons to generate (default: 5)
    --level 0-3       Learner level: 0=beginner, 3=advanced (default: 0)
    --overwrite       Overwrite existing course with same slug
    --dry-run         Generate files only, skip DB insert
    --out-dir PATH    Directory to write markdown files (default: lessons/<slug>)

Examples:
    python -m scripts.gen_lesson https://go.dev/tour/basics
    python -m scripts.gen_lesson https://go.dev/tour/basics --lessons 10 --level 1
    python -m scripts.gen_lesson https://go.dev/tour/basics --dry-run
"""

import argparse
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _sanitize_filename(title: str) -> str:
    return re.sub(r"[^\w\-]", "-", title.lower().replace(" ", "-"))


def _write_markdown_files(out_dir: str, course_name: str, lessons) -> None:
    os.makedirs(out_dir, exist_ok=True)

    # Write README index
    index_lines = [f"# {course_name}\n\n| # | File | Tiêu đề |\n|---|---|---|\n"]
    for gen in lessons:
        seq = gen.plan.sequence_number
        fname = f"{seq:02d}-{_sanitize_filename(gen.plan.title)}.md"
        index_lines.append(f"| {seq} | [{fname}]({fname}) | {gen.plan.title} |\n")
        fpath = os.path.join(out_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(gen.content_markdown)
        logger.info(f"  Wrote {fpath}")

    readme = os.path.join(out_dir, "README.md")
    with open(readme, "w", encoding="utf-8") as f:
        f.writelines(index_lines)
    logger.info(f"  Wrote {readme}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a course from a URL and seed it into the DB."
    )
    parser.add_argument("url", help="URL of the course to generate from")
    parser.add_argument("--lessons", type=int, default=5, help="Number of lessons (default: 5)")
    parser.add_argument("--level", type=int, default=0, choices=[0, 1, 2, 3],
                        help="Learner level 0-3 (default: 0)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite existing course with same slug")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate markdown files only, skip DB insert")
    parser.add_argument("--out-dir", default=None,
                        help="Output directory for markdown files (default: lessons/<slug>)")
    args = parser.parse_args()

    from app.config import settings
    from app.services.llm_service import LLMService
    from app.services.lesson_generator import LessonGenerator

    llm = LLMService(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        fast_model=settings.llm_fast_model,
        smart_model=settings.llm_smart_model,
    )
    generator = LessonGenerator(client=llm.client, smart_model=settings.llm_smart_model)

    slug = LessonGenerator.url_to_slug(args.url)
    out_dir = args.out_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "lessons",
        slug,
    )

    logger.info(f"Generating course from: {args.url}")
    logger.info(f"  lessons={args.lessons}  level={args.level}  slug={slug}")

    course_name, lessons = generator.run(
        url=args.url,
        num_lessons=args.lessons,
        user_level=args.level,
    )

    logger.info(f"\nGenerated {len(lessons)} lessons for '{course_name}'")
    logger.info(f"Writing markdown files to: {out_dir}")
    _write_markdown_files(out_dir, course_name, lessons)

    if args.dry_run:
        logger.info("\n[dry-run] Skipping DB insert.")
        _print_summary(course_name, lessons)
        return

    from app.database import SessionLocal
    from app.services.course_seeder import CourseSeeder

    db = SessionLocal()
    try:
        seeder = CourseSeeder(db)
        course = seeder.seed(
            course_name=course_name,
            slug=slug,
            lessons=lessons,
            overwrite=args.overwrite,
        )
        logger.info(f"\nSeeded to DB: course_id={course.course_id}")
    finally:
        db.close()

    _print_summary(course_name, lessons)


def _print_summary(course_name: str, lessons) -> None:
    total_concepts = sum(len(g.concepts) for g in lessons)
    logger.info("\n" + "=" * 50)
    logger.info(f"Course   : {course_name}")
    logger.info(f"Lessons  : {len(lessons)}")
    logger.info(f"Concepts : {total_concepts}")
    logger.info("=" * 50)
    for gen in lessons:
        concept_names = ", ".join(c.name for c in gen.concepts) or "—"
        logger.info(f"  {gen.plan.sequence_number:02d}. {gen.plan.title}")
        logger.info(f"      concepts: {concept_names}")


if __name__ == "__main__":
    main()
