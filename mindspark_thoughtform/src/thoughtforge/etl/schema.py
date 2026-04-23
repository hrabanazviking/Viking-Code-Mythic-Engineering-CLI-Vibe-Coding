"""
SQLite schema initialization for the ThoughtForge knowledge database.

Creates all tables, indexes, and views needed for SQL + vector hybrid retrieval.
Idempotent — safe to call multiple times (uses IF NOT EXISTS).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from thoughtforge.utils.paths import get_knowledge_db_path

logger = logging.getLogger(__name__)

# ── DDL statements ─────────────────────────────────────────────────────────────

_TABLES = """
-- Core entity table (Wikidata QIDs + labels)
CREATE TABLE IF NOT EXISTS entities (
    qid              TEXT PRIMARY KEY,
    label_en         TEXT,
    description_en   TEXT,
    aliases_en       TEXT,
    instance_of      TEXT,
    popularity_score REAL DEFAULT 0.0,
    source           TEXT DEFAULT 'wikidata'
);

-- Statements / facts
CREATE TABLE IF NOT EXISTS statements (
    statement_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_qid   TEXT NOT NULL,
    property_pid  TEXT NOT NULL,
    object_value  TEXT,
    object_type   TEXT,
    qualifiers    TEXT,
    refs          TEXT,
    source        TEXT DEFAULT 'wikidata',
    FOREIGN KEY (subject_qid) REFERENCES entities(qid)
);

-- Multi-language labels
CREATE TABLE IF NOT EXISTS labels (
    qid      TEXT NOT NULL,
    language TEXT NOT NULL,
    label    TEXT NOT NULL,
    PRIMARY KEY (qid, language)
);

-- Pre-computed embeddings (BLOB = numpy float32 array)
CREATE TABLE IF NOT EXISTS embeddings (
    qid              TEXT PRIMARY KEY,
    text_for_embedding TEXT,
    embedding        BLOB,
    model_name       TEXT DEFAULT 'all-MiniLM-L6-v2'
);

-- ConceptNet nodes (concept, relation, weight)
CREATE TABLE IF NOT EXISTS conceptnet_edges (
    edge_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    uri        TEXT UNIQUE,
    concept1   TEXT NOT NULL,
    relation   TEXT NOT NULL,
    concept2   TEXT NOT NULL,
    weight     REAL DEFAULT 1.0,
    language   TEXT DEFAULT 'en',
    source     TEXT DEFAULT 'conceptnet'
);

-- GeoNames places
CREATE TABLE IF NOT EXISTS geonames_places (
    geonames_id    INTEGER PRIMARY KEY,
    name           TEXT,
    ascii_name     TEXT,
    latitude       REAL,
    longitude      REAL,
    feature_class  TEXT,
    feature_code   TEXT,
    country_code   TEXT,
    population     INTEGER DEFAULT 0,
    elevation      INTEGER,
    timezone       TEXT,
    admin1_code    TEXT,
    admin2_code    TEXT,
    source         TEXT DEFAULT 'geonames'
);

-- DBpedia entries
CREATE TABLE IF NOT EXISTS dbpedia_entities (
    uri          TEXT PRIMARY KEY,
    label_en     TEXT,
    abstract_en  TEXT,
    types        TEXT,
    source       TEXT DEFAULT 'dbpedia'
);

-- Built-in reference documents (chunked)
CREATE TABLE IF NOT EXISTS reference_chunks (
    chunk_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file    TEXT NOT NULL,
    chunk_index    INTEGER NOT NULL,
    title          TEXT,
    content        TEXT NOT NULL,
    tags           TEXT,
    word_count     INTEGER DEFAULT 0,
    source         TEXT DEFAULT 'reference',
    UNIQUE (source_file, chunk_index)
);

-- Reference chunk embeddings
CREATE TABLE IF NOT EXISTS reference_embeddings (
    chunk_id   INTEGER PRIMARY KEY,
    embedding  BLOB,
    model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
    FOREIGN KEY (chunk_id) REFERENCES reference_chunks(chunk_id)
);

-- ETL ingestion log
CREATE TABLE IF NOT EXISTS ingestion_log (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    completed_at TEXT,
    entity_count INTEGER DEFAULT 0,
    status       TEXT DEFAULT 'running',
    notes        TEXT
);
"""

_FTS5 = """
-- Full-text search on entities
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    qid UNINDEXED,
    label_en,
    description_en,
    aliases_en,
    content='entities',
    content_rowid='rowid'
);

-- Full-text search on reference chunks
CREATE VIRTUAL TABLE IF NOT EXISTS reference_fts USING fts5(
    chunk_id UNINDEXED,
    title,
    content,
    tags,
    content='reference_chunks',
    content_rowid='rowid'
);

-- Full-text search on ConceptNet
CREATE VIRTUAL TABLE IF NOT EXISTS conceptnet_fts USING fts5(
    edge_id UNINDEXED,
    concept1,
    relation,
    concept2,
    content='conceptnet_edges',
    content_rowid='rowid'
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_statements_subject ON statements(subject_qid);
CREATE INDEX IF NOT EXISTS idx_statements_property ON statements(property_pid);
CREATE INDEX IF NOT EXISTS idx_statements_object ON statements(object_value);
CREATE INDEX IF NOT EXISTS idx_entities_label ON entities(label_en);
CREATE INDEX IF NOT EXISTS idx_entities_instance ON entities(instance_of);
CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source);
CREATE INDEX IF NOT EXISTS idx_labels_qid ON labels(qid);
CREATE INDEX IF NOT EXISTS idx_conceptnet_concept1 ON conceptnet_edges(concept1);
CREATE INDEX IF NOT EXISTS idx_conceptnet_concept2 ON conceptnet_edges(concept2);
CREATE INDEX IF NOT EXISTS idx_conceptnet_relation ON conceptnet_edges(relation);
CREATE INDEX IF NOT EXISTS idx_geonames_country ON geonames_places(country_code);
CREATE INDEX IF NOT EXISTS idx_geonames_name ON geonames_places(name);
CREATE INDEX IF NOT EXISTS idx_dbpedia_label ON dbpedia_entities(label_en);
CREATE INDEX IF NOT EXISTS idx_reference_file ON reference_chunks(source_file);
CREATE INDEX IF NOT EXISTS idx_reference_tags ON reference_chunks(tags);
"""

_PRAGMAS_WRITE = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
PRAGMA temp_store   = MEMORY;
PRAGMA mmap_size    = 536870912;
PRAGMA cache_size   = -32000;
"""

_PRAGMAS_READ = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
PRAGMA temp_store   = MEMORY;
PRAGMA mmap_size    = 536870912;
PRAGMA cache_size   = -16000;
PRAGMA query_only   = ON;
"""


def get_connection(db_path: Path | None = None, read_only: bool = False) -> sqlite3.Connection:
    """Return a SQLite connection with performance pragmas applied."""
    path = db_path or get_knowledge_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    pragmas = _PRAGMAS_READ if read_only else _PRAGMAS_WRITE
    for pragma in pragmas.strip().split(";"):
        pragma = pragma.strip()
        if pragma:
            conn.execute(pragma)
    return conn


def initialize_schema(db_path: Path | None = None) -> None:
    """Create all tables, FTS5 virtual tables, and indexes. Idempotent."""
    path = db_path or get_knowledge_db_path()
    logger.info("Initializing schema at %s", path)
    conn = get_connection(path)
    try:
        # Tables first
        conn.executescript(_TABLES)
        conn.commit()
        logger.debug("Core tables created/verified")

        # FTS5 virtual tables
        conn.executescript(_FTS5)
        conn.commit()
        logger.debug("FTS5 virtual tables created/verified")

        # Indexes
        conn.executescript(_INDEXES)
        conn.commit()
        logger.info("Schema initialization complete — %s", path)
    finally:
        conn.close()


def rebuild_fts_indexes(db_path: Path | None = None) -> None:
    """Rebuild all FTS5 content indexes from their base tables."""
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
        conn.execute("INSERT INTO reference_fts(reference_fts) VALUES('rebuild')")
        conn.execute("INSERT INTO conceptnet_fts(conceptnet_fts) VALUES('rebuild')")
        conn.commit()
        logger.info("FTS5 indexes rebuilt")
    except sqlite3.OperationalError as e:
        logger.warning("FTS5 rebuild warning: %s", e)
    finally:
        conn.close()


def get_entity_count(db_path: Path | None = None) -> dict[str, int]:
    """Return row counts for all major tables."""
    conn = get_connection(db_path, read_only=True)
    try:
        counts = {}
        tables = [
            "entities", "statements", "labels", "embeddings",
            "conceptnet_edges", "geonames_places", "dbpedia_entities",
            "reference_chunks",
        ]
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                counts[table] = row[0] if row else 0
            except sqlite3.OperationalError:
                counts[table] = -1
        return counts
    finally:
        conn.close()
