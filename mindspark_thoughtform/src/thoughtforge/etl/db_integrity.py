"""SQLite database integrity checker and optimizer for ThoughtForge.

Runs PRAGMA integrity_check, verifies FTS5 shadow tables, reports row counts,
enables WAL mode, and optionally runs VACUUM.  Results are cached in
data/.last_integrity_check so the check is not repeated within 24 hours.

Usage:
    from thoughtforge.etl.db_integrity import DBIntegrityChecker
    checker = DBIntegrityChecker()
    report = checker.check()
    if not report.ok:
        result = checker.repair()
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thoughtforge.utils.paths import get_data_dir, get_knowledge_db_path

logger = logging.getLogger(__name__)

_CACHE_FILE_NAME = ".last_integrity_check"
_CACHE_TTL_SECONDS = 86400   # 24 hours

# FTS5 virtual tables we expect to exist
_EXPECTED_FTS_TABLES = {"entities_fts", "reference_fts", "conceptnet_fts"}

# Core tables we expect to exist
_EXPECTED_TABLES = {"entities", "statements", "labels", "embeddings", "reference_chunks"}


# ── Result dataclasses ─────────────────────────────────────────────────────────

@dataclass
class IntegrityReport:
    ok: bool
    errors: list[str]
    row_counts: dict[str, int]
    db_size_mb: float
    fts_ok: bool
    wal_mode: bool
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def summary(self) -> str:
        status = "OK" if self.ok else f"FAIL ({len(self.errors)} errors)"
        return (
            f"Integrity: {status} | "
            f"Size: {self.db_size_mb:.1f} MB | "
            f"FTS5: {'OK' if self.fts_ok else 'missing'} | "
            f"WAL: {'enabled' if self.wal_mode else 'disabled'} | "
            f"Entities: {self.row_counts.get('entities', 0):,}"
        )


@dataclass
class RepairResult:
    success: bool
    actions: list[str]
    db_renamed: bool = False
    schema_rebuilt: bool = False


# ── DBIntegrityChecker ─────────────────────────────────────────────────────────

class DBIntegrityChecker:
    """
    Checks, optimizes, and repairs the ThoughtForge knowledge database.

    Results of check() are cached for 24 hours to avoid repeated expensive
    integrity scans on every startup.  Call check(force=True) to bypass cache.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_knowledge_db_path()
        self._cache_path = get_data_dir() / _CACHE_FILE_NAME

    # ── Public API ─────────────────────────────────────────────────────────────

    def check(self, force: bool = False) -> IntegrityReport:
        """Run integrity checks against the knowledge database.

        Args:
            force: Skip cache and re-run even if checked recently.

        Returns:
            IntegrityReport with all check results.
        """
        if not force:
            cached = self._load_cache()
            if cached is not None:
                logger.debug("DB integrity: serving from cache (checked at %s)", cached.checked_at)
                return cached

        if not self._db_path.exists():
            report = IntegrityReport(
                ok=True,
                errors=[],
                row_counts={},
                db_size_mb=0.0,
                fts_ok=False,
                wal_mode=False,
            )
            logger.debug("knowledge.db does not exist — skipping integrity check")
            return report

        size_mb = self._db_path.stat().st_size / (1024 * 1024)
        errors: list[str] = []
        row_counts: dict[str, int] = {}
        fts_ok = False
        wal_mode = False

        try:
            conn = sqlite3.connect(str(self._db_path), timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                # Integrity check
                rows = conn.execute("PRAGMA integrity_check").fetchall()
                if not (len(rows) == 1 and rows[0][0] == "ok"):
                    errors.extend(row[0] for row in rows)

                # WAL mode
                wal_row = conn.execute("PRAGMA journal_mode").fetchone()
                wal_mode = bool(wal_row and wal_row[0].lower() == "wal")

                # Row counts for core tables
                existing_tables = {
                    row[0] for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                for table in _EXPECTED_TABLES:
                    if table in existing_tables:
                        count_row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                        row_counts[table] = count_row[0] if count_row else 0
                    else:
                        row_counts[table] = 0
                        errors.append(f"Expected table '{table}' not found")

                # FTS5 tables
                fts_present = _EXPECTED_FTS_TABLES & existing_tables
                fts_ok = fts_present == _EXPECTED_FTS_TABLES
                if not fts_ok:
                    missing_fts = _EXPECTED_FTS_TABLES - fts_present
                    errors.append(f"Missing FTS5 tables: {', '.join(sorted(missing_fts))}")

            finally:
                conn.close()
        except sqlite3.DatabaseError as exc:
            errors.append(f"SQLite error: {exc}")
        except Exception as exc:
            errors.append(f"Unexpected error: {exc}")

        report = IntegrityReport(
            ok=len(errors) == 0,
            errors=errors,
            row_counts=row_counts,
            db_size_mb=size_mb,
            fts_ok=fts_ok,
            wal_mode=wal_mode,
        )
        self._save_cache(report)
        return report

    def repair(self, db_path: Path | None = None) -> RepairResult:
        """Repair the database.

        If integrity check fails:
          - Renames the corrupt DB to .corrupt_<ts>.db
          - Rebuilds an empty schema

        If integrity passes but WAL is disabled, enables WAL.
        If integrity passes but FTS5 tables are missing, rebuilds schema idempotently.

        Returns:
            RepairResult describing what was done.
        """
        target = db_path or self._db_path
        actions: list[str] = []
        db_renamed = False
        schema_rebuilt = False

        if not target.exists():
            return RepairResult(success=True, actions=["DB does not exist — nothing to repair"])

        report = self.check(force=True)

        if not report.ok and any("integrity" in e.lower() or "SQLite" in e for e in report.errors):
            # Corrupt DB — rename and rebuild
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            corrupt_path = target.with_suffix(f".corrupt_{ts}.db")
            try:
                target.rename(corrupt_path)
                actions.append(f"Renamed corrupt DB to {corrupt_path.name}")
                db_renamed = True
            except Exception as exc:
                return RepairResult(
                    success=False,
                    actions=[f"Could not rename corrupt DB: {exc}"],
                    db_renamed=False,
                )

            try:
                from thoughtforge.etl.schema import initialize_schema
                initialize_schema(target)
                actions.append("Rebuilt empty schema")
                schema_rebuilt = True
                self._invalidate_cache()
            except Exception as exc:
                return RepairResult(
                    success=False,
                    actions=actions + [f"Could not rebuild schema: {exc}"],
                    db_renamed=db_renamed,
                )
            return RepairResult(
                success=True, actions=actions,
                db_renamed=db_renamed, schema_rebuilt=schema_rebuilt,
            )

        # Enable WAL if needed
        if not report.wal_mode:
            ok = self.enable_wal(target)
            actions.append("Enabled WAL mode" if ok else "Failed to enable WAL mode")

        # Rebuild FTS5 if missing (schema is idempotent)
        if not report.fts_ok:
            try:
                from thoughtforge.etl.schema import initialize_schema
                initialize_schema(target)
                actions.append("Ran initialize_schema to repair FTS5 tables")
                schema_rebuilt = True
                self._invalidate_cache()
            except Exception as exc:
                actions.append(f"Could not repair FTS5 tables: {exc}")

        if not actions:
            actions.append("No repairs needed")

        return RepairResult(
            success=True, actions=actions,
            db_renamed=db_renamed, schema_rebuilt=schema_rebuilt,
        )

    def enable_wal(self, db_path: Path | None = None) -> bool:
        """Enable WAL journal mode on the database."""
        target = db_path or self._db_path
        if not target.exists():
            return False
        try:
            conn = sqlite3.connect(str(target), timeout=5)
            try:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.commit()
                logger.info("Enabled WAL mode on %s", target.name)
                return True
            finally:
                conn.close()
        except Exception as exc:
            logger.error("Could not enable WAL on %s: %s", target.name, exc)
            return False

    def optimize(self, db_path: Path | None = None) -> None:
        """Run VACUUM and PRAGMA optimize on the database."""
        target = db_path or self._db_path
        if not target.exists():
            return
        try:
            conn = sqlite3.connect(str(target), timeout=60)
            try:
                logger.info("Running VACUUM on %s ...", target.name)
                conn.execute("VACUUM")
                conn.execute("PRAGMA optimize")
                conn.commit()
                logger.info("VACUUM + optimize complete on %s", target.name)
            finally:
                conn.close()
            self._invalidate_cache()
        except Exception as exc:
            logger.error("optimize() failed on %s: %s", target.name, exc)

    # ── Cache helpers ──────────────────────────────────────────────────────────

    def _load_cache(self) -> IntegrityReport | None:
        """Load a cached IntegrityReport if it is still fresh."""
        if not self._cache_path.exists():
            return None
        try:
            with self._cache_path.open("r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            checked_at_str = data.get("checked_at", "")
            if checked_at_str:
                checked_dt = datetime.fromisoformat(checked_at_str)
                age = (datetime.now(timezone.utc) - checked_dt).total_seconds()
                if age > _CACHE_TTL_SECONDS:
                    return None
            return IntegrityReport(
                ok=data.get("ok", False),
                errors=data.get("errors", []),
                row_counts=data.get("row_counts", {}),
                db_size_mb=data.get("db_size_mb", 0.0),
                fts_ok=data.get("fts_ok", False),
                wal_mode=data.get("wal_mode", False),
                checked_at=checked_at_str,
            )
        except Exception as exc:
            logger.debug("Could not load integrity cache: %s", exc)
            return None

    def _save_cache(self, report: IntegrityReport) -> None:
        """Persist an IntegrityReport to the cache file."""
        try:
            data = {
                "ok": report.ok,
                "errors": report.errors,
                "row_counts": report.row_counts,
                "db_size_mb": report.db_size_mb,
                "fts_ok": report.fts_ok,
                "wal_mode": report.wal_mode,
                "checked_at": report.checked_at,
            }
            self._cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Could not save integrity cache: %s", exc)

    def _invalidate_cache(self) -> None:
        """Delete the cached check result so the next check runs fresh."""
        try:
            self._cache_path.unlink(missing_ok=True)
        except Exception:
            pass
