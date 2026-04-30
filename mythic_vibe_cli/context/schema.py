"""Knowledge graph schema + migrations (PH-05 slice 5.1).

The graph is a single SQLite file at ``<root>/mythic/graph.sqlite3``.
Stdlib-only — no SQLAlchemy, no peewee. Schema versioning lives in
the ``schema_version`` table; :func:`apply_migrations` is idempotent
and safe across processes via SQLite's own file-level locking.

Schema v1 entities:

- ``module``, ``function``, ``document``, ``decision``, ``phase``,
  ``task``, ``packet``, ``verification``, ``handoff``.

Schema v1 edges:

- ``contains``, ``references``, ``mentions``, ``supersedes``,
  ``targets``, ``validates``, ``resumes``, ``precedes``.

Tags are a free-text relevance substrate the slice 5.3 retriever
uses for tag-overlap ranking.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


CURRENT_SCHEMA_VERSION = 1


# --- Entity / edge kind catalogues --------------------------------------

ENTITY_KINDS: tuple[str, ...] = (
    "module",
    "function",
    "document",
    "decision",
    "phase",
    "task",
    "packet",
    "verification",
    "handoff",
)

EDGE_KINDS: tuple[str, ...] = (
    "contains",
    "references",
    "mentions",
    "supersedes",
    "targets",
    "validates",
    "resumes",
    "precedes",
)


# --- DDL ----------------------------------------------------------------

SCHEMA_V1_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(kind, name)
);

CREATE INDEX IF NOT EXISTS idx_entities_kind ON entities(kind);
CREATE INDEX IF NOT EXISTS idx_entities_path ON entities(path);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    dst_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(src_id, dst_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_id);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_id);
CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);

CREATE TABLE IF NOT EXISTS entity_tags (
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    UNIQUE(entity_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_entity_tags_tag ON entity_tags(tag);
"""


# Future migrations append here. Each entry: (target_version, sql_text).
MIGRATIONS: tuple[tuple[int, str], ...] = (
    (1, SCHEMA_V1_SQL),
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_current_version(conn: sqlite3.Connection) -> int:
    """Return the highest ``version`` recorded in ``schema_version``,
    or 0 if the table does not exist or is empty.

    Robust by design: a brand-new database returns 0 cleanly; a
    half-migrated database raises (so :func:`apply_migrations` can
    surface the failure).
    """
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    if cur.fetchone() is None:
        return 0
    row = conn.execute(
        "SELECT MAX(version) FROM schema_version"
    ).fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply every pending migration up to :data:`CURRENT_SCHEMA_VERSION`.

    Returns the version the database is at after this call. Idempotent:
    re-running on an up-to-date database is a no-op (no rows added,
    no DDL re-executed beyond ``CREATE TABLE IF NOT EXISTS`` clauses
    which SQLite handles cleanly).

    Foreign-key enforcement is enabled per-connection — SQLite needs
    the pragma set on each connection that wants ``ON DELETE CASCADE``
    to work.
    """
    conn.execute("PRAGMA foreign_keys = ON")
    current = get_current_version(conn)
    for target_version, sql in MIGRATIONS:
        if target_version <= current:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version(version, applied_at) VALUES (?, ?)",
            (target_version, _utc_now_iso()),
        )
        conn.commit()
        current = target_version
    return current


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "EDGE_KINDS",
    "ENTITY_KINDS",
    "MIGRATIONS",
    "SCHEMA_V1_SQL",
    "apply_migrations",
    "get_current_version",
]
