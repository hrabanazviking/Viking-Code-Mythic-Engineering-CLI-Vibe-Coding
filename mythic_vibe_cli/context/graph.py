"""GraphStore — CRUD over the knowledge-graph SQLite (PH-05 slice 5.2).

Stdlib-only wrapper around :mod:`sqlite3`. The store opens
``<root>/mythic/graph.sqlite3``, applies any pending schema
migrations, and exposes idempotent upsert + query primitives over
the entities/edges/entity_tags tables defined in
:mod:`mythic_vibe_cli.context.schema`.

Public surface:

- :class:`GraphStore` — context-manager-friendly wrapper.
- :class:`Entity` / :class:`Edge` — frozen dataclasses returned by
  query methods.

Design choices:

- **Idempotent upserts** — re-inserting the same ``(kind, name)``
  pair updates ``updated_at`` and ``metadata`` instead of raising.
  Matches how the slice 5.7 packet retriever and slice 5.8 drift
  wiring re-scan on every refresh.
- **Best-effort serialisation** — metadata round-trips through JSON
  text. Non-JSON-serialisable values raise at write time, not at
  read time.
- **No connection pooling** — one connection per ``GraphStore``,
  closed by the context manager. SQLite's per-process locking is
  sufficient for the project's single-operator model.
- **Cross-platform path handling** — paths are stored as forward-
  slash strings so JSON output is stable across OSes.

Cross-platform: pure stdlib; no platform branches.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any, Iterable

from .schema import apply_migrations


DEFAULT_GRAPH_FILENAME = "graph.sqlite3"


def graph_path_for(root: Path) -> Path:
    """Canonical location of the graph SQLite for a project root."""
    return Path(root) / "mythic" / DEFAULT_GRAPH_FILENAME


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Entity:
    id: int
    kind: str
    name: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "path": self.path,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class Edge:
    id: int
    src_id: int
    dst_id: int
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "src_id": self.src_id,
            "dst_id": self.dst_id,
            "kind": self.kind,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


def _parse_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    return decoded


def _row_to_entity(row: sqlite3.Row | tuple[Any, ...]) -> Entity:
    return Entity(
        id=int(row[0]),
        kind=str(row[1]),
        name=str(row[2]),
        path=str(row[3]) if row[3] is not None else "",
        metadata=_parse_metadata(row[4]),
        created_at=str(row[5]) if row[5] is not None else "",
        updated_at=str(row[6]) if row[6] is not None else "",
    )


def _row_to_edge(row: sqlite3.Row | tuple[Any, ...]) -> Edge:
    return Edge(
        id=int(row[0]),
        src_id=int(row[1]),
        dst_id=int(row[2]),
        kind=str(row[3]),
        metadata=_parse_metadata(row[4]),
        created_at=str(row[5]) if row[5] is not None else "",
    )


class GraphStore:
    """SQLite-backed knowledge graph.

    Use as a context manager:

    .. code-block:: python

        with GraphStore.open(root) as store:
            entity = store.upsert_entity("module", "mythic_vibe_cli.app")
            store.add_tag(entity.id, "cli")
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ---- lifecycle -----------------------------------------------------

    @classmethod
    def open(cls, root: Path) -> "GraphStore":
        """Open (or create) the graph at ``<root>/mythic/graph.sqlite3``
        and apply any pending migrations."""
        path = graph_path_for(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = None  # tuple rows — explicit indexing in helpers
        apply_migrations(conn)
        return cls(conn)

    @classmethod
    def open_in_memory(cls) -> "GraphStore":
        """Open an in-memory store. Used by tests and ephemeral consumers
        that don't want to materialise a file."""
        conn = sqlite3.connect(":memory:")
        apply_migrations(conn)
        return cls(conn)

    def close(self) -> None:
        try:
            self._conn.commit()
        except sqlite3.Error:
            pass
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    def __enter__(self) -> "GraphStore":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # ---- entities ------------------------------------------------------

    def upsert_entity(
        self,
        kind: str,
        name: str,
        *,
        path: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        """Insert or update an entity keyed by ``(kind, name)``.

        On insert, ``created_at`` and ``updated_at`` are set to the
        current UTC instant; on update only ``updated_at`` is bumped.
        ``metadata`` is JSON-serialised — any non-serialisable value
        raises at write time.
        """
        now = _utc_now_iso()
        meta_text = json.dumps(metadata or {}, sort_keys=True)
        cur = self._conn.execute(
            "SELECT id, created_at FROM entities WHERE kind=? AND name=?",
            (kind, name),
        )
        existing = cur.fetchone()
        if existing is None:
            cur = self._conn.execute(
                "INSERT INTO entities(kind, name, path, metadata, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (kind, name, path or "", meta_text, now, now),
            )
            self._conn.commit()
            entity_id = int(cur.lastrowid or 0)
        else:
            entity_id = int(existing[0])
            self._conn.execute(
                "UPDATE entities SET path=?, metadata=?, updated_at=? WHERE id=?",
                (path or "", meta_text, now, entity_id),
            )
            self._conn.commit()
        return self._fetch_entity(entity_id)

    def _fetch_entity(self, entity_id: int) -> Entity:
        row = self._conn.execute(
            "SELECT id, kind, name, path, metadata, created_at, updated_at "
            "FROM entities WHERE id=?",
            (entity_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"entity id {entity_id} not found")
        return _row_to_entity(row)

    def find_entity(self, kind: str, name: str) -> Entity | None:
        row = self._conn.execute(
            "SELECT id, kind, name, path, metadata, created_at, updated_at "
            "FROM entities WHERE kind=? AND name=?",
            (kind, name),
        ).fetchone()
        return _row_to_entity(row) if row else None

    def find_entities(
        self,
        *,
        kind: str | None = None,
        name_like: str | None = None,
        path_like: str | None = None,
    ) -> list[Entity]:
        """Return every entity matching the supplied filters. All
        arguments AND together; substring filters use ``LIKE`` with
        ``%`` wildcards on both ends."""
        clauses: list[str] = []
        params: list[Any] = []
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        if name_like is not None:
            clauses.append("name LIKE ?")
            params.append(f"%{name_like}%")
        if path_like is not None:
            clauses.append("path LIKE ?")
            params.append(f"%{path_like}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            "SELECT id, kind, name, path, metadata, created_at, updated_at "
            f"FROM entities{where} ORDER BY kind, name"
        )
        return [_row_to_entity(row) for row in self._conn.execute(sql, params)]

    # ---- edges ---------------------------------------------------------

    def upsert_edge(
        self,
        src_id: int,
        dst_id: int,
        kind: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Edge:
        """Insert or update an edge keyed by ``(src_id, dst_id, kind)``.
        Existing edges keep their ``created_at``; metadata is replaced.
        """
        now = _utc_now_iso()
        meta_text = json.dumps(metadata or {}, sort_keys=True)
        existing = self._conn.execute(
            "SELECT id FROM edges WHERE src_id=? AND dst_id=? AND kind=?",
            (src_id, dst_id, kind),
        ).fetchone()
        if existing is None:
            cur = self._conn.execute(
                "INSERT INTO edges(src_id, dst_id, kind, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (src_id, dst_id, kind, meta_text, now),
            )
            self._conn.commit()
            edge_id = int(cur.lastrowid or 0)
        else:
            edge_id = int(existing[0])
            self._conn.execute(
                "UPDATE edges SET metadata=? WHERE id=?",
                (meta_text, edge_id),
            )
            self._conn.commit()
        return self._fetch_edge(edge_id)

    def _fetch_edge(self, edge_id: int) -> Edge:
        row = self._conn.execute(
            "SELECT id, src_id, dst_id, kind, metadata, created_at "
            "FROM edges WHERE id=?",
            (edge_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"edge id {edge_id} not found")
        return _row_to_edge(row)

    def find_edges(
        self,
        *,
        src_id: int | None = None,
        dst_id: int | None = None,
        kind: str | None = None,
    ) -> list[Edge]:
        clauses: list[str] = []
        params: list[Any] = []
        if src_id is not None:
            clauses.append("src_id = ?")
            params.append(src_id)
        if dst_id is not None:
            clauses.append("dst_id = ?")
            params.append(dst_id)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            "SELECT id, src_id, dst_id, kind, metadata, created_at "
            f"FROM edges{where} ORDER BY id"
        )
        return [_row_to_edge(row) for row in self._conn.execute(sql, params)]

    def entity_neighbours(
        self,
        entity_id: int,
        *,
        kind: str | None = None,
        direction: str = "both",
    ) -> list[Entity]:
        """Return entities one hop away. ``direction`` is one of
        ``"out"`` (entity → neighbour), ``"in"`` (neighbour → entity),
        or ``"both"`` (the union, deduplicated)."""
        if direction not in {"in", "out", "both"}:
            raise ValueError(f"direction must be in/out/both, got {direction!r}")

        out_clause = "src_id = ?"
        in_clause = "dst_id = ?"
        # Qualify `kind` with the edge alias — both `entities.kind`
        # and `edges.kind` exist, so an unqualified column name here
        # raises sqlite3.OperationalError("ambiguous column name").
        kind_clause = " AND ed.kind = ?" if kind else ""

        rows: list[tuple[Any, ...]] = []
        if direction in {"out", "both"}:
            params: list[Any] = [entity_id]
            if kind:
                params.append(kind)
            rows.extend(
                self._conn.execute(
                    "SELECT e.id, e.kind, e.name, e.path, e.metadata, "
                    "e.created_at, e.updated_at "
                    f"FROM entities e JOIN edges ed ON ed.dst_id = e.id "
                    f"WHERE ed.{out_clause}{kind_clause}",
                    params,
                ).fetchall()
            )
        if direction in {"in", "both"}:
            params = [entity_id]
            if kind:
                params.append(kind)
            rows.extend(
                self._conn.execute(
                    "SELECT e.id, e.kind, e.name, e.path, e.metadata, "
                    "e.created_at, e.updated_at "
                    f"FROM entities e JOIN edges ed ON ed.src_id = e.id "
                    f"WHERE ed.{in_clause}{kind_clause}",
                    params,
                ).fetchall()
            )

        seen: set[int] = set()
        result: list[Entity] = []
        for row in rows:
            entity = _row_to_entity(row)
            if entity.id in seen:
                continue
            seen.add(entity.id)
            result.append(entity)
        return result

    # ---- tags ----------------------------------------------------------

    def add_tag(self, entity_id: int, tag: str, *, weight: float = 1.0) -> None:
        """Tag an entity for the slice-5.3 retriever's tag-overlap
        ranking. Re-tagging the same ``(entity, tag)`` pair updates the
        weight rather than raising."""
        existing = self._conn.execute(
            "SELECT 1 FROM entity_tags WHERE entity_id=? AND tag=?",
            (entity_id, tag),
        ).fetchone()
        if existing is None:
            self._conn.execute(
                "INSERT INTO entity_tags(entity_id, tag, weight) VALUES (?, ?, ?)",
                (entity_id, tag, weight),
            )
        else:
            self._conn.execute(
                "UPDATE entity_tags SET weight=? WHERE entity_id=? AND tag=?",
                (weight, entity_id, tag),
            )
        self._conn.commit()

    def tags_for(self, entity_id: int) -> list[tuple[str, float]]:
        return [
            (str(row[0]), float(row[1]))
            for row in self._conn.execute(
                "SELECT tag, weight FROM entity_tags "
                "WHERE entity_id=? ORDER BY weight DESC, tag",
                (entity_id,),
            )
        ]

    def entities_with_tags(self, tags: Iterable[str]) -> list[tuple[Entity, float]]:
        """Return every entity that has at least one matching tag,
        paired with its summed weight across the matching tags. Used
        by the slice 5.3 retriever's first-pass scoring."""
        tag_list = [t for t in tags if t]
        if not tag_list:
            return []
        placeholders = ",".join("?" for _ in tag_list)
        rows = self._conn.execute(
            "SELECT e.id, e.kind, e.name, e.path, e.metadata, "
            "e.created_at, e.updated_at, SUM(t.weight) AS score "
            "FROM entities e JOIN entity_tags t ON t.entity_id = e.id "
            f"WHERE t.tag IN ({placeholders}) "
            "GROUP BY e.id ORDER BY score DESC, e.kind, e.name",
            tag_list,
        ).fetchall()
        return [(_row_to_entity(row[:7]), float(row[7])) for row in rows]

    # ---- introspection -------------------------------------------------

    def entity_count(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        )

    def edge_count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0])


__all__ = [
    "DEFAULT_GRAPH_FILENAME",
    "Edge",
    "Entity",
    "GraphStore",
    "graph_path_for",
]
