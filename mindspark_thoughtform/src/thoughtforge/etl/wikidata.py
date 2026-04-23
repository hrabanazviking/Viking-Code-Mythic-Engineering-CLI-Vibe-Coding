"""
Wikidata streaming ETL for ThoughtForge.

Streams the full Wikidata JSON dump (latest-all.json.gz) into the
SQLite knowledge database using ijson for constant memory usage.

Three strategies supported:
  A. Pure Python streaming (this module) — maximum control, cross-platform
  B. wd2sql (external C++ tool) — fastest, optional
  C. KGTK (subset-friendly) — optional

Usage:
  from thoughtforge.etl.wikidata import WikidataETL
  etl = WikidataETL()
  etl.build(dump_path="/path/to/latest-all.json.gz")
"""

from __future__ import annotations

import gzip
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterator

from tqdm import tqdm

from thoughtforge.etl.schema import get_connection, initialize_schema
from thoughtforge.utils.paths import get_knowledge_db_path

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

DEFAULT_BATCH_SIZE: int = 2000
COMMIT_EVERY_N: int = 50_000        # commit every N entities
MEMORY_CHECK_EVERY_N: int = 10_000  # check RAM usage every N entities

# Entity types to exclude (redirects, disambiguation pages, etc.)
EXCLUDED_INSTANCE_OF: frozenset[str] = frozenset({
    "Q4167410",   # Wikimedia disambiguation page
    "Q4167836",   # Wikimedia category
    "Q11266439",  # Wikimedia template
    "Q4663903",   # Wikimedia portal
    "Q13433827",  # Wikimedia user category
    "Q17442446",  # Wikimedia internal item
})


class WikidataETL:
    """Streams the Wikidata JSON dump into the ThoughtForge SQLite knowledge DB."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_knowledge_db_path()

    def build(
        self,
        dump_path: Path | str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        limit: int | None = None,
        languages: list[str] | None = None,
        instance_of_filter: set[str] | None = None,
    ) -> dict[str, int]:
        """
        Stream the Wikidata dump into SQLite.

        Args:
            dump_path:            Path to latest-all.json.gz (or .json)
            batch_size:           Entities per insert batch
            limit:                Stop after this many entities (useful for testing)
            languages:            Language codes to load labels for (default: ["en"])
            instance_of_filter:   If set, only include entities with these P31 values

        Returns:
            Dict with entity/statement/label counts.
        """
        dump_path = Path(dump_path)
        languages = languages or ["en"]

        if not dump_path.exists():
            raise FileNotFoundError(f"Wikidata dump not found: {dump_path}")

        logger.info("Initializing schema")
        initialize_schema(self.db_path)

        log_id = self._start_log("wikidata")
        stats: dict[str, int] = {"entities": 0, "statements": 0, "labels": 0, "skipped": 0}

        try:
            conn = get_connection(self.db_path)
            # Disable synchronous during bulk load for speed; WAL mode keeps it safe
            conn.execute("PRAGMA synchronous = OFF")
            conn.execute("PRAGMA journal_mode = WAL")

            entity_batch: list[tuple[Any, ...]] = []
            statement_batch: list[tuple[Any, ...]] = []
            label_batch: list[tuple[Any, ...]] = []

            t_start = time.time()

            for item in tqdm(
                self._stream_entities(dump_path),
                desc="Wikidata ETL",
                unit=" entities",
                mininterval=5.0,
            ):
                if limit and stats["entities"] >= limit:
                    break

                qid = item.get("id", "")
                if not qid.startswith("Q"):
                    stats["skipped"] += 1
                    continue

                # Parse entity fields
                label_en = self._get_label(item, "en")
                desc_en = self._get_description(item, "en")
                aliases_en = self._get_aliases(item, "en")
                instance_of = self._get_instance_of(item)
                popularity = self._estimate_popularity(item)

                # Skip excluded types
                if EXCLUDED_INSTANCE_OF.intersection(instance_of.split(",") if instance_of else []):
                    stats["skipped"] += 1
                    continue

                # Apply optional instance_of filter
                if instance_of_filter:
                    entity_types = set(instance_of.split(",")) if instance_of else set()
                    if not entity_types.intersection(instance_of_filter):
                        stats["skipped"] += 1
                        continue

                entity_batch.append((qid, label_en, desc_en, aliases_en, instance_of, popularity))
                stats["entities"] += 1

                # Parse labels for all requested languages
                for lang in languages:
                    lbl = self._get_label(item, lang)
                    if lbl:
                        label_batch.append((qid, lang, lbl))
                        stats["labels"] += 1

                # Parse claims/statements
                for pid, claims_list in item.get("claims", {}).items():
                    for claim in claims_list:
                        if claim.get("rank") == "deprecated":
                            continue
                        snak = claim.get("mainsnak", {})
                        obj_value, obj_type = self._parse_snak(snak)
                        if obj_value is None:
                            continue
                        qualifiers = json.dumps(claim.get("qualifiers", {}), ensure_ascii=False)
                        refs = json.dumps(claim.get("references", [])[:2], ensure_ascii=False)
                        statement_batch.append((qid, pid, obj_value, obj_type, qualifiers, refs))
                        stats["statements"] += 1

                # Batch flush
                if len(entity_batch) >= batch_size:
                    self._flush_entities(conn, entity_batch)
                    entity_batch.clear()
                if len(statement_batch) >= batch_size * 3:
                    self._flush_statements(conn, statement_batch)
                    statement_batch.clear()
                if len(label_batch) >= batch_size * len(languages):
                    self._flush_labels(conn, label_batch)
                    label_batch.clear()

                # Periodic commit
                if stats["entities"] % COMMIT_EVERY_N == 0:
                    conn.commit()
                    elapsed = time.time() - t_start
                    rate = stats["entities"] / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Progress: %d entities | %d statements | %.0f ent/s",
                        stats["entities"], stats["statements"], rate,
                    )

                # RAM check (if psutil available)
                if stats["entities"] % MEMORY_CHECK_EVERY_N == 0:
                    self._check_memory(conn)

            # Final flush
            if entity_batch:
                self._flush_entities(conn, entity_batch)
            if statement_batch:
                self._flush_statements(conn, statement_batch)
            if label_batch:
                self._flush_labels(conn, label_batch)

            conn.commit()
            conn.close()

            logger.info("ETL complete: %s", stats)
            self._finish_log(log_id, stats["entities"], "complete")

        except Exception as e:
            logger.error("Wikidata ETL failed: %s", e)
            self._finish_log(log_id, stats.get("entities", 0), f"failed: {e}")
            raise

        return stats

    # ── Streaming ──────────────────────────────────────────────────────────────

    def _stream_entities(self, dump_path: Path) -> Iterator[dict[str, Any]]:
        """Stream entities from a .json.gz or .json Wikidata dump."""
        try:
            import ijson
        except ImportError as e:
            raise RuntimeError("ijson not installed. Run: pip install ijson") from e

        open_fn = gzip.open if dump_path.suffix == ".gz" else open
        with open_fn(str(dump_path), "rb") as f:
            for item in ijson.items(f, "item"):
                yield item

    # ── Field parsers ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_label(item: dict[str, Any], lang: str) -> str | None:
        return item.get("labels", {}).get(lang, {}).get("value")

    @staticmethod
    def _get_description(item: dict[str, Any], lang: str) -> str | None:
        return item.get("descriptions", {}).get(lang, {}).get("value")

    @staticmethod
    def _get_aliases(item: dict[str, Any], lang: str) -> str | None:
        aliases = item.get("aliases", {}).get(lang, [])
        return ", ".join(a["value"] for a in aliases[:5]) if aliases else None

    @staticmethod
    def _get_instance_of(item: dict[str, Any]) -> str | None:
        claims = item.get("claims", {}).get("P31", [])
        qids = []
        for claim in claims:
            snak = claim.get("mainsnak", {})
            dv = snak.get("datavalue", {})
            if dv.get("type") == "wikibase-entityid":
                qids.append(dv.get("value", {}).get("id", ""))
        return ",".join(q for q in qids if q) or None

    @staticmethod
    def _estimate_popularity(item: dict[str, Any]) -> float:
        """Rough popularity proxy: number of sitelinks / 100, capped at 1.0."""
        return min(len(item.get("sitelinks", {})) / 100.0, 1.0)

    @staticmethod
    def _parse_snak(snak: dict[str, Any]) -> tuple[str | None, str | None]:
        """Extract (value_string, value_type) from a mainsnak."""
        snak_type = snak.get("snaktype")
        if snak_type == "novalue":
            return "novalue", "novalue"
        if snak_type == "somevalue":
            return "somevalue", "somevalue"

        dv = snak.get("datavalue", {})
        dv_type = dv.get("type", "")
        value = dv.get("value")

        if dv_type == "wikibase-entityid":
            return value.get("id") if isinstance(value, dict) else None, "wikibase-item"
        if dv_type == "string":
            return str(value)[:1024], "string"
        if dv_type == "monolingualtext":
            return str(value.get("text", ""))[:1024] if isinstance(value, dict) else None, "monolingualtext"
        if dv_type == "quantity":
            return str(value.get("amount", "")) if isinstance(value, dict) else None, "quantity"
        if dv_type == "time":
            return str(value.get("time", "")) if isinstance(value, dict) else None, "time"
        if dv_type == "globecoordinate":
            if isinstance(value, dict):
                return f"{value.get('latitude')},{value.get('longitude')}", "coordinate"
        return None, None

    # ── Batch flush helpers ────────────────────────────────────────────────────

    @staticmethod
    def _flush_entities(conn: sqlite3.Connection, batch: list[tuple[Any, ...]]) -> None:
        conn.executemany(
            "INSERT OR REPLACE INTO entities "
            "(qid, label_en, description_en, aliases_en, instance_of, popularity_score, source) "
            "VALUES (?, ?, ?, ?, ?, ?, 'wikidata')",
            batch,
        )

    @staticmethod
    def _flush_statements(conn: sqlite3.Connection, batch: list[tuple[Any, ...]]) -> None:
        conn.executemany(
            "INSERT INTO statements "
            "(subject_qid, property_pid, object_value, object_type, qualifiers, refs, source) "
            "VALUES (?, ?, ?, ?, ?, ?, 'wikidata')",
            batch,
        )

    @staticmethod
    def _flush_labels(conn: sqlite3.Connection, batch: list[tuple[Any, ...]]) -> None:
        conn.executemany(
            "INSERT OR REPLACE INTO labels (qid, language, label) VALUES (?, ?, ?)",
            batch,
        )

    # ── Ingestion log helpers ──────────────────────────────────────────────────

    def _start_log(self, source: str) -> int:
        from datetime import datetime, timezone
        conn = get_connection(self.db_path)
        try:
            cur = conn.execute(
                "INSERT INTO ingestion_log (source, started_at, status) VALUES (?, ?, 'running')",
                (source, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            conn.close()

    def _finish_log(self, log_id: int, entity_count: int, status: str) -> None:
        from datetime import datetime, timezone
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                "UPDATE ingestion_log SET completed_at=?, entity_count=?, status=? WHERE log_id=?",
                (datetime.now(timezone.utc).isoformat(), entity_count, status, log_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Memory guard ──────────────────────────────────────────────────────────

    @staticmethod
    def _check_memory(conn: sqlite3.Connection) -> None:
        """Commit early if RAM pressure is high (requires psutil)."""
        try:
            import psutil
            if psutil.virtual_memory().percent > 85:
                conn.commit()
                logger.warning("High memory usage — forced commit")
        except ImportError:
            pass  # psutil optional
