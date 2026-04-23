"""Chart intelligence for Yggdrasil retrieval and cross-category linking."""

from __future__ import annotations

import json
import csv
import importlib
import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ChartRecord:
    """Indexed chart file with optional category and cross-link metadata."""

    file_path: str
    title: str
    categories: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    content_snippet: str = ""
    keywords: List[str] = field(default_factory=list)


class ChartIntelligence:
    """Build and query a resilient index of data/charts and its subfolders."""

    def __init__(self, charts_root: Path):
        self.charts_root = charts_root
        self.records: List[ChartRecord] = []
        self._record_lookup: Dict[str, ChartRecord] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Huginn scouts chart files and catalogs knowledge by category."""
        if not self.charts_root.exists():
            logger.warning("Charts directory missing: %s", self.charts_root)
            return

        supported = {
            ".yaml", ".yml", ".json", ".md", ".txt", ".jsonl", ".csv", ".html", ".htm", ".xml", ".pdf"
        }
        for chart_file in self.charts_root.rglob("*"):
            if not chart_file.is_file() or chart_file.suffix.lower() not in supported:
                continue
            record = self._parse_chart_file(chart_file)
            if record:
                self.records.append(record)
                self._record_lookup[record.file_path] = record

        logger.info("ChartIntelligence indexed %s chart files", len(self.records))

    def _parse_chart_file(self, chart_file: Path) -> ChartRecord | None:
        rel_path = chart_file.relative_to(self.charts_root).as_posix()
        auto_categories = self._categories_from_path(chart_file)
        raw_text = ""
        payload: Any = None

        try:
            if chart_file.suffix.lower() in {".yaml", ".yml"}:
                payload = yaml.safe_load(chart_file.read_text(encoding="utf-8"))
                raw_text = json.dumps(payload, ensure_ascii=False, default=str)
            elif chart_file.suffix.lower() == ".json":
                payload = json.loads(chart_file.read_text(encoding="utf-8"))
                raw_text = json.dumps(payload, ensure_ascii=False, default=str)
            elif chart_file.suffix.lower() in {".csv", ".cvs"}:
                with chart_file.open("r", encoding="utf-8") as handle:
                    payload = [row for row in csv.DictReader(handle)]
                raw_text = json.dumps(payload, ensure_ascii=False, default=str)
            elif chart_file.suffix.lower() == ".pdf":
                raw_text = self._extract_pdf_text(chart_file)
            else:
                raw_text = chart_file.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            logger.warning("Chart parse failed for %s: %s", chart_file, exc)
            return None

        metadata = payload if isinstance(payload, dict) else {}
        declared_categories = metadata.get("categories", []) if metadata else []
        categories = auto_categories + [c for c in declared_categories if isinstance(c, str)]
        categories = sorted(set(c for c in categories if c))

        links = self._extract_links(metadata, raw_text)
        title = metadata.get("title") if isinstance(metadata.get("title"), str) else chart_file.stem
        keywords = self._extract_keywords(raw_text)

        return ChartRecord(
            file_path=rel_path,
            title=title,
            categories=categories,
            links=links,
            content_snippet=raw_text[:1200],
            keywords=keywords,
        )

    def _extract_pdf_text(self, chart_file: Path) -> str:
        module_name = "pypdf" if importlib.util.find_spec("pypdf") else "PyPDF2"
        if not importlib.util.find_spec(module_name):
            logger.warning("No PDF reader installed; skipping PDF chart: %s", chart_file)
            return ""
        pdf_module = importlib.import_module(module_name)
        reader = pdf_module.PdfReader(str(chart_file))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    def _categories_from_path(self, chart_file: Path) -> List[str]:
        rel_parent = chart_file.parent.relative_to(self.charts_root)
        if rel_parent == Path("."):
            return []
        return [part.lower().replace(" ", "_") for part in rel_parent.parts]

    def _extract_links(self, metadata: Dict[str, Any], raw_text: str) -> List[str]:
        links: Set[str] = set()
        for key in ("links", "related_files", "related", "xref"):
            values = metadata.get(key)
            if isinstance(values, str):
                links.add(values)
            elif isinstance(values, list):
                links.update(str(v) for v in values if v)

        for token in raw_text.replace("\n", " ").split():
            if "charts/" in token:
                links.add(token.strip("'\".,()[]{}"))

        return sorted(links)

    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {
            "the", "and", "for", "that", "with", "from", "this", "into", "your",
            "have", "were", "when", "what", "will", "shall", "they", "them",
        }
        words = [w.strip(".,:;!?()[]{}\"'`).-_/").lower() for w in text.split()]
        keywords = [w for w in words if len(w) > 3 and w not in stop_words and w.isascii()]
        return sorted(set(keywords))[:50]

    def query(self, query: str, max_results: int = 8) -> Dict[str, Any]:
        """Return ranked chart knowledge records linked to a query."""
        tokens = set(self._extract_keywords(query))
        scored: List[tuple[int, ChartRecord]] = []

        for record in self.records:
            # Muninn remembers by keyword overlap and category relevance.
            overlap = len(tokens.intersection(set(record.keywords)))
            if overlap == 0 and tokens:
                continue
            score = overlap + len(record.categories)
            scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [item[1] for item in scored[:max_results]]

        return {
            "results": [
                {
                    "file": r.file_path,
                    "title": r.title,
                    "categories": r.categories,
                    "links": r.links,
                    "snippet": r.content_snippet,
                }
                for r in selected
            ],
            "total_matches": len(scored),
            "indexed_files": len(self.records),
        }
