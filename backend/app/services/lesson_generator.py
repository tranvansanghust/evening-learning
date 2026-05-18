"""
LessonGenerator — fetch a course URL, generate curriculum + lesson content + concepts via LLM.

Does NOT touch the database — pure generation logic, testable in isolation.
Use CourseSeeder to persist results.
"""

import json
import logging
import re
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List

from app.services.llm_content_generator import LLMContentGenerator
from app.services.llm_prompts import LLMPrompts

logger = logging.getLogger(__name__)


@dataclass
class LessonPlan:
    sequence_number: int
    title: str
    description: str


@dataclass
class ConceptData:
    name: str
    description: str


@dataclass
class GeneratedLesson:
    plan: LessonPlan
    content_markdown: str
    concepts: List[ConceptData] = field(default_factory=list)


class _TextExtractor(HTMLParser):
    """Minimal HTML → plain text extractor using stdlib only."""

    _SKIP_TAGS = {"script", "style", "noscript", "head"}

    def __init__(self):
        super().__init__()
        self._parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


class LessonGenerator:
    """
    Orchestrates: fetch URL → generate curriculum → generate content → extract concepts.

    Args:
        client: OpenAI-compatible API client
        smart_model: Model to use for all LLM calls
    """

    def __init__(self, client, smart_model: str):
        self.client = client
        self.smart_model = smart_model
        self._content_generator = LLMContentGenerator(client=client, smart_model=smart_model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        url: str,
        num_lessons: int = 5,
        user_level: int = 0,
    ) -> tuple[str, List[GeneratedLesson]]:
        """
        Full pipeline: URL → (course_name, list of GeneratedLesson).

        Returns:
            course_name: Inferred from URL path
            lessons: List of GeneratedLesson with content + concepts filled in
        """
        page_text = self.fetch_page(url)
        course_name = self._slug_to_name(self._url_to_slug(url))

        plans = self.generate_curriculum(url, page_text, num_lessons)
        total = len(plans)

        lessons: List[GeneratedLesson] = []
        for plan in plans:
            logger.info(f"  [{plan.sequence_number}/{total}] Generating: {plan.title}")
            content = self._content_generator.generate_lesson_content(
                course_topic=course_name,
                lesson_title=plan.title,
                lesson_sequence=plan.sequence_number,
                total_lessons=total,
                user_level=user_level,
            )
            concepts = self.extract_concepts(plan.title, content)
            lessons.append(GeneratedLesson(plan=plan, content_markdown=content, concepts=concepts))

        return course_name, lessons

    def fetch_page(self, url: str) -> str:
        """Fetch URL and return plain text. Returns '' on any error or JS-only pages."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; evening-learning-bot/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            parser = _TextExtractor()
            parser.feed(html)
            text = parser.get_text()
            # Heuristic: if text is very short the page is likely JS-rendered
            return text if len(text) > 200 else ""
        except Exception as e:
            logger.warning(f"fetch_page({url}) failed: {e}")
            return ""

    def generate_curriculum(
        self, url: str, page_text: str, num_lessons: int
    ) -> List[LessonPlan]:
        """Call LLM to generate a list of LessonPlan from URL + page text."""
        prompt = LLMPrompts.curriculum_from_url(url, page_text, num_lessons)
        raw = self._call_llm(prompt)
        data = self._parse_json(raw)
        if not isinstance(data, list):
            raise ValueError(f"curriculum_from_url returned non-list: {raw[:200]}")
        return [
            LessonPlan(
                sequence_number=item["sequence_number"],
                title=item["title"],
                description=item.get("description", ""),
            )
            for item in data
        ]

    def extract_concepts(self, title: str, content: str) -> List[ConceptData]:
        """Call LLM to extract key concepts from lesson content."""
        prompt = LLMPrompts.concept_extraction(title, content)
        raw = self._call_llm(prompt)
        data = self._parse_json(raw)
        if not isinstance(data, list):
            logger.warning(f"concept_extraction returned non-list, skipping: {raw[:100]}")
            return []
        return [
            ConceptData(
                name=item.get("name", ""),
                description=item.get("description", ""),
            )
            for item in data
            if item.get("name")
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def url_to_slug(url: str) -> str:
        """'https://go.dev/tour/basics' → 'go-tour-basics'"""
        return LessonGenerator._url_to_slug(url)

    @staticmethod
    def _url_to_slug(url: str) -> str:
        url = re.sub(r"https?://", "", url)
        url = re.sub(r"[^\w/]", "-", url)
        parts = [p for p in url.split("/") if p and p not in ("www",)]
        slug = "-".join(parts)
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug.lower()

    @staticmethod
    def _slug_to_name(slug: str) -> str:
        """'go-tour-basics' → 'Go Tour Basics'"""
        return " ".join(w.capitalize() for w in slug.split("-"))

    def _call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.smart_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        return (response.choices[0].message.content or "").strip()

    @staticmethod
    def _parse_json(raw: str):
        """Strip markdown code fences then parse JSON."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n", 1)
            text = lines[1] if len(lines) > 1 else ""
            text = text.removesuffix("```").strip()
        return json.loads(text)
