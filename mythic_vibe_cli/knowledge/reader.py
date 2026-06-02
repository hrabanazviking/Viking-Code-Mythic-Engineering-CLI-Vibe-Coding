"""Read-only private knowledge reader.

Phase 6 connects the companion shell to private coding knowledge
without making that knowledge part of the project graph. Sources are
configured in JSON config under ``knowledge.sources`` or via
``MYTHIC_KNOWLEDGE_SQLITE_PATH``. SQLite is supported first and opened
read-only; PostgreSQL sources are reported as configured but not
queried until a dependency-free/explicit adapter is added.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import sqlite3
from typing import Any
from urllib.parse import quote

from ..config import ConfigStore


DEFAULT_LIMIT = 5
MAX_LIMIT = 20
TEXT_TYPES = ("TEXT", "CHAR", "CLOB", "VARCHAR")
TITLE_NAMES = ("title", "name", "heading", "subject")
BODY_NAMES = ("body", "content", "text", "summary", "notes", "description")
SOURCE_NAMES = ("source", "path", "url", "origin")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class KnowledgeSource:
    name: str
    type: str
    path: str = ""
    host: str = ""
    table: str = ""
    title_column: str = ""
    body_column: str = ""
    source_column: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display_location(self) -> str:
        if self.host and self.path:
            return f"{self.host}:{self.path}"
        return self.path or self.host or "(not configured)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "path": self.path,
            "host": self.host,
            "table": self.table,
            "title_column": self.title_column,
            "body_column": self.body_column,
            "source_column": self.source_column,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class KnowledgeSourceStatus:
    source: KnowledgeSource
    configured: bool
    searchable: bool
    details: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "configured": self.configured,
            "searchable": self.searchable,
            "details": list(self.details),
        }


@dataclass(frozen=True)
class KnowledgeResult:
    source_name: str
    table: str
    title: str
    snippet: str
    source_ref: str = ""
    score: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "table": self.table,
            "title": self.title,
            "snippet": self.snippet,
            "source_ref": self.source_ref,
            "score": self.score,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class KnowledgeSearchResult:
    query: str
    results: tuple[KnowledgeResult, ...]
    statuses: tuple[KnowledgeSourceStatus, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "statuses": [status.to_dict() for status in self.statuses],
        }


def load_knowledge_sources(root: Path) -> list[KnowledgeSource]:
    loaded = ConfigStore(root).load()
    sources: list[KnowledgeSource] = []
    for index, raw in enumerate(loaded.config.knowledge_sources, start=1):
        source_type = str(raw.get("type", "sqlite") or "sqlite").strip().lower()
        name = str(raw.get("name", "") or f"{source_type}-{index}").strip()
        sources.append(
            KnowledgeSource(
                name=name,
                type=source_type,
                path=str(raw.get("path", "") or "").strip(),
                host=str(raw.get("host", "") or "").strip(),
                table=str(raw.get("table", "") or "").strip(),
                title_column=str(raw.get("title_column", raw.get("title", "")) or "").strip(),
                body_column=str(raw.get("body_column", raw.get("body", "")) or "").strip(),
                source_column=str(raw.get("source_column", raw.get("source_ref", "")) or "").strip(),
                metadata={
                    str(key): value
                    for key, value in raw.items()
                    if key
                    not in {
                        "name",
                        "type",
                        "path",
                        "host",
                        "table",
                        "title_column",
                        "title",
                        "body_column",
                        "body",
                        "source_column",
                        "source_ref",
                    }
                },
            )
        )
    return sources


def knowledge_status(root: Path) -> list[KnowledgeSourceStatus]:
    sources = load_knowledge_sources(root)
    if not sources:
        return [
            KnowledgeSourceStatus(
                source=KnowledgeSource(name="(none)", type="sqlite"),
                configured=False,
                searchable=False,
                details=("No knowledge sources configured.",),
            )
        ]
    return [_status_for_source(root, source) for source in sources]


def search_knowledge(root: Path, query: str, *, limit: int = DEFAULT_LIMIT) -> KnowledgeSearchResult:
    statuses = knowledge_status(root)
    capped = max(1, min(MAX_LIMIT, int(limit or DEFAULT_LIMIT)))
    results: list[KnowledgeResult] = []
    for status in statuses:
        if not status.searchable:
            continue
        if status.source.type == "sqlite":
            results.extend(_search_sqlite(root, status.source, query, capped))
    results.sort(key=lambda item: item.score, reverse=True)
    return KnowledgeSearchResult(
        query=query,
        results=tuple(results[:capped]),
        statuses=tuple(statuses),
    )


def render_status(statuses: list[KnowledgeSourceStatus]) -> str:
    lines = ["Knowledge sources"]
    for status in statuses:
        marker = "searchable" if status.searchable else "not searchable"
        configured = "configured" if status.configured else "not configured"
        lines.append(
            f"  {status.source.name}: {configured}, {marker} "
            f"({status.source.type}; {status.source.display_location})"
        )
        for detail in status.details:
            lines.append(f"    - {detail}")
    return "\n".join(lines)


def render_sources(root: Path) -> str:
    sources = load_knowledge_sources(root)
    if not sources:
        return "Knowledge sources\n  none configured"
    lines = ["Knowledge sources"]
    for source in sources:
        lines.append(f"  {source.name}: {source.type} at {source.display_location}")
        if source.table:
            lines.append(f"    table: {source.table}")
    return "\n".join(lines)


def render_search(search: KnowledgeSearchResult) -> str:
    lines = [f"Knowledge search: {search.query}"]
    if not search.results:
        lines.append("  No matching private knowledge found.")
        return "\n".join(lines)
    for result in search.results:
        title = result.title or "(untitled)"
        ref = f" [{result.source_ref}]" if result.source_ref else ""
        lines.append(f"  - {title}{ref}")
        lines.append(f"    source: {result.source_name}/{result.table}")
        lines.append(f"    {result.snippet}")
    return "\n".join(lines)


def _status_for_source(root: Path, source: KnowledgeSource) -> KnowledgeSourceStatus:
    if source.type == "sqlite":
        path = _resolve_source_path(root, source)
        if not source.path:
            return KnowledgeSourceStatus(source, False, False, ("SQLite path is empty.",))
        if not path.is_file():
            return KnowledgeSourceStatus(source, False, False, (f"SQLite file not found: {path}",))
        try:
            with _connect_sqlite_readonly(path) as conn:
                tables = _discover_tables(conn)
        except sqlite3.Error as exc:
            return KnowledgeSourceStatus(source, True, False, (f"Could not open read-only SQLite: {exc}",))
        if source.table and source.table not in tables:
            return KnowledgeSourceStatus(source, True, False, (f"Configured table not found: {source.table}",))
        if not tables:
            return KnowledgeSourceStatus(source, True, False, ("No readable user tables found.",))
        table_count = len(tables)
        return KnowledgeSourceStatus(source, True, True, (f"{table_count} readable table(s).",))
    if source.type in {"postgres", "postgresql"}:
        configured = bool(source.host or source.path)
        return KnowledgeSourceStatus(
            source,
            configured,
            False,
            ("PostgreSQL source configured; adapter not enabled in this stdlib Phase 6 slice.",),
        )
    return KnowledgeSourceStatus(source, False, False, (f"Unsupported source type: {source.type}",))


def _resolve_source_path(root: Path, source: KnowledgeSource) -> Path:
    path = Path(source.path).expanduser()
    if not path.is_absolute():
        path = Path(root) / path
    return path.resolve()


def _connect_sqlite_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{quote(str(path), safe='/:%')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _valid_identifier(name: str) -> bool:
    return bool(IDENTIFIER_RE.match(name))


def _quote_identifier(name: str) -> str:
    if not _valid_identifier(name):
        raise ValueError(f"unsafe identifier: {name!r}")
    return f'"{name}"'


def _discover_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row["name"]) for row in rows if _valid_identifier(str(row["name"]))]


def _table_columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    rows = conn.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()
    columns: list[tuple[str, str]] = []
    for row in rows:
        name = str(row["name"])
        column_type = str(row["type"] or "").upper()
        if _valid_identifier(name):
            columns.append((name, column_type))
    return columns


def _text_columns(columns: list[tuple[str, str]]) -> list[str]:
    selected: list[str] = []
    for name, column_type in columns:
        if not column_type or any(token in column_type for token in TEXT_TYPES):
            selected.append(name)
    return selected


def _pick_column(configured: str, names: tuple[str, ...], text_columns: list[str]) -> str:
    if configured and configured in text_columns:
        return configured
    lowered = {name.lower(): name for name in text_columns}
    for candidate in names:
        if candidate in lowered:
            return lowered[candidate]
    return text_columns[0] if text_columns else ""


def _search_sqlite(root: Path, source: KnowledgeSource, query: str, limit: int) -> list[KnowledgeResult]:
    path = _resolve_source_path(root, source)
    try:
        with _connect_sqlite_readonly(path) as conn:
            tables = [source.table] if source.table else _discover_tables(conn)
            results: list[KnowledgeResult] = []
            for table in tables:
                if not _valid_identifier(table):
                    continue
                results.extend(_search_sqlite_table(conn, source, table, query, limit))
                if len(results) >= limit:
                    break
            return results[:limit]
    except (sqlite3.Error, ValueError, OSError):
        return []


def _search_sqlite_table(
    conn: sqlite3.Connection,
    source: KnowledgeSource,
    table: str,
    query: str,
    limit: int,
) -> list[KnowledgeResult]:
    columns = _table_columns(conn, table)
    text_columns = _text_columns(columns)
    if not text_columns:
        return []
    title_column = _pick_column(source.title_column, TITLE_NAMES, text_columns)
    body_column = _pick_column(source.body_column, BODY_NAMES, text_columns)
    source_column = _pick_column(source.source_column, SOURCE_NAMES, text_columns)
    search_columns = list(dict.fromkeys([title_column, body_column, *text_columns]))
    terms = [term for term in query.split() if term.strip()]
    patterns = [f"%{query}%"]
    patterns.extend(f"%{term}%" for term in terms)
    clauses: list[str] = []
    params: list[str] = []
    for column in search_columns:
        quoted = _quote_identifier(column)
        for pattern in patterns:
            clauses.append(f"{quoted} LIKE ?")
            params.append(pattern)
    where = " OR ".join(clauses)
    select_columns = list(dict.fromkeys([title_column, body_column, source_column]))
    select_expr = ", ".join(_quote_identifier(column) for column in select_columns if column)
    if not select_expr:
        return []
    sql = (
        f"SELECT {select_expr} FROM {_quote_identifier(table)} "
        f"WHERE {where} LIMIT ?"
    )
    rows = conn.execute(sql, (*params, limit)).fetchall()
    results: list[KnowledgeResult] = []
    score_terms = [term.lower() for term in terms]
    for row in rows:
        title = _row_value(row, title_column)
        body = _row_value(row, body_column)
        source_ref = _row_value(row, source_column)
        snippet = _snippet(body or title, score_terms)
        score = _score_text(" ".join([title, body]), score_terms)
        results.append(
            KnowledgeResult(
                source_name=source.name,
                table=table,
                title=title,
                snippet=snippet,
                source_ref=source_ref,
                score=score,
                metadata={"location": source.display_location},
            )
        )
    return results


def _row_value(row: sqlite3.Row, column: str) -> str:
    if not column:
        return ""
    try:
        value = row[column]
    except (KeyError, IndexError):
        return ""
    return str(value or "").strip()


def _score_text(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    if not terms:
        return 0
    return sum(lowered.count(term) for term in terms)


def _snippet(text: str, terms: list[str], *, size: int = 240) -> str:
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= size:
        return cleaned
    lowered = cleaned.lower()
    first = min((lowered.find(term) for term in terms if lowered.find(term) >= 0), default=0)
    start = max(0, first - 60)
    end = min(len(cleaned), start + size)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(cleaned) else ""
    return f"{prefix}{cleaned[start:end]}{suffix}"


__all__ = [
    "KnowledgeResult",
    "KnowledgeSearchResult",
    "KnowledgeSource",
    "KnowledgeSourceStatus",
    "knowledge_status",
    "load_knowledge_sources",
    "render_search",
    "render_sources",
    "render_status",
    "search_knowledge",
]
