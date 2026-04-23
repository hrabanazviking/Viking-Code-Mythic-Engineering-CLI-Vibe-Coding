"""Optional web search helper for Yggdrasil cognition."""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class WebSearchOracle:
    """Minimal, fault-tolerant web scout for fresh lore and context."""

    def __init__(self, enabled: bool = False, timeout: int = 8, max_results: int = 5):
        self.enabled = enabled
        self.timeout = max(timeout, 2)
        self.max_results = max(max_results, 1)

    def search(self, query: str) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        try:
            import requests
        except Exception as exc:
            logger.warning("Web search dependency unavailable: %s", exc)
            return []

        try:
            response = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                timeout=self.timeout,
                headers={"User-Agent": "NorseSagaEngine/5.0 Yggdrasil"},
            )
            response.raise_for_status()
            return self._parse_results(response.text)
        except Exception as exc:
            logger.warning("Web search failed for '%s': %s", query, exc)
            return []

    def _parse_results(self, page: str) -> List[Dict[str, Any]]:
        pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'(?:<a[^>]*class="result__snippet"[^>]*>(.*?)</a>|<div[^>]*class="result__snippet"[^>]*>(.*?)</div>)?',
            re.S,
        )

        results: List[Dict[str, Any]] = []
        for match in pattern.finditer(page):
            url = html.unescape(match.group(1) or "")
            title_raw = re.sub(r"<[^>]+>", "", match.group(2) or "")
            snippet_raw = re.sub(r"<[^>]+>", "", (match.group(3) or match.group(4) or ""))
            results.append(
                {
                    "title": html.unescape(title_raw).strip(),
                    "url": url.strip(),
                    "snippet": html.unescape(snippet_raw).strip(),
                }
            )
            if len(results) >= self.max_results:
                break

        return results
