"""Self-healing utilities for MindSpark: ThoughtForge.

Attempts to automatically repair common failure modes:
  - Missing or corrupt user_config.yaml → restore from template
  - Corrupt JSONL memory files → quarantine bad lines, keep good ones
  - Corrupt SQLite knowledge DB → rename .corrupt, rebuild empty schema
  - All file writes use atomic write-then-rename to prevent partial writes

Usage:
    from thoughtforge.utils.self_heal import SelfHealer
    results = SelfHealer().heal_all()
    # results = {"config": True, "memory": True, "db": False}
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from thoughtforge.utils.errors import (
    ConfigCorruptError,
    ConfigMissingError,
    DatabaseCorruptError,
    MemoryFileCorruptError,
)
from thoughtforge.utils.paths import (
    get_configs_dir,
    get_knowledge_db_path,
    get_memory_dir,
)

logger = logging.getLogger(__name__)


# ── Atomic write helper ────────────────────────────────────────────────────────

def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to path atomically via a temp file + rename.

    Prevents partial writes from corrupting the destination file.
    Safe on both POSIX and Windows.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding=encoding)
        tmp.replace(path)   # atomic on POSIX; best-effort on Windows
    except Exception:
        # Clean up temp file if rename fails
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ── SelfHealer ─────────────────────────────────────────────────────────────────

class SelfHealer:
    """
    Attempts to repair ThoughtForge components that are in a degraded or
    failed state.  Each heal_*() method returns True on success, False if
    healing was not possible.  Errors are logged, never re-raised.
    """

    def __init__(self) -> None:
        self._configs_dir = get_configs_dir()
        self._user_config_path = self._configs_dir / "user_config.yaml"
        self._default_config_path = self._configs_dir / "default.yaml"
        self._memory_dir = get_memory_dir()
        self._knowledge_db_path = get_knowledge_db_path()

    # ── Public API ─────────────────────────────────────────────────────────────

    def heal_all(self) -> dict[str, bool]:
        """Run all healers.  Returns a dict of component → success."""
        return {
            "config":   self.heal_config(),
            "memory":   self.heal_memory_store(),
            "database": self.heal_knowledge_db(),
        }

    # ── Config healing ─────────────────────────────────────────────────────────

    def heal_config(self) -> bool:
        """Ensure user_config.yaml exists and is valid YAML with required keys.

        - Missing → copy built-in template
        - Corrupt YAML → rebuild from template, warn user
        - Unknown backend → reset to 'none'

        Returns True if config is healthy after healing (or was already OK).
        """
        path = self._user_config_path

        # 1. Missing config
        if not path.exists():
            logger.warning(
                "user_config.yaml not found — restoring from template"
            )
            return self._restore_config_from_template(path)

        # 2. Parse existing config
        cfg: Any = None
        try:
            with path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
        except Exception as exc:
            logger.error(
                "user_config.yaml is corrupt (%s) — rebuilding from template", exc
            )
            return self._restore_config_from_template(path)

        if not isinstance(cfg, dict):
            logger.error(
                "user_config.yaml parsed to %s (not dict) — rebuilding", type(cfg).__name__
            )
            return self._restore_config_from_template(path)

        # 3. Ensure required keys exist
        changed = False
        if "backend" not in cfg:
            cfg["backend"] = "none"
            changed = True
            logger.warning("user_config.yaml missing 'backend' — defaulting to 'none'")

        # 4. Unknown backend → reset
        valid_backends = {
            "none", "", "ollama", "lmstudio", "openai_compatible",
            "huggingface", "turboquant",
        }
        backend = str(cfg.get("backend", "none")).strip().lower()
        if backend not in valid_backends:
            logger.warning(
                "Unknown backend '%s' in user_config.yaml — resetting to 'none'", backend
            )
            cfg["backend"] = "none"
            changed = True

        if changed:
            try:
                atomic_write(path, yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
                logger.info("user_config.yaml repaired and saved")
            except Exception as exc:
                logger.error("Failed to save repaired config: %s", exc)
                return False

        return True

    def _restore_config_from_template(self, dest: Path) -> bool:
        """Copy the built-in user_config.yaml template to dest."""
        # Template is in the same configs/ directory (checked in)
        template = self._configs_dir / "user_config.yaml"
        if dest == template:
            # We're trying to restore the template itself — write minimal default
            minimal = "backend: none\nollama_url: \"http://localhost:11434\"\nollama_model: \"\"\n"
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(dest, minimal)
                logger.info("Wrote minimal user_config.yaml to %s", dest)
                return True
            except Exception as exc:
                logger.error("Could not write minimal config: %s", exc)
                return False

        if template.exists() and template != dest:
            try:
                shutil.copy2(str(template), str(dest))
                logger.info("Restored user_config.yaml from template at %s", template)
                return True
            except Exception as exc:
                logger.error("Could not copy config template: %s", exc)
                return False

        # No template available — write minimal defaults
        minimal = "backend: none\nollama_url: \"http://localhost:11434\"\nollama_model: \"\"\n"
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(dest, minimal)
            logger.info("Wrote minimal user_config.yaml defaults to %s", dest)
            return True
        except Exception as exc:
            logger.error("Could not write minimal config: %s", exc)
            return False

    # ── Memory store healing ───────────────────────────────────────────────────

    def heal_memory_store(self) -> bool:
        """Validate and repair memory store files.

        - JSONL files: drop malformed lines, quarantine them to corrupt_backup_<ts>.jsonl
        - personality_core.yaml: reset to template if unparseable
        - active_thread_state.json: reset to empty if corrupt
        - Never silently discards data — broken lines are backed up first

        Returns True if all files are healthy after healing.
        """
        mem_dir = self._memory_dir
        if not mem_dir.exists():
            return True   # Nothing to heal

        all_ok = True

        # personality_core.yaml
        pc_path = mem_dir / "personality_core.yaml"
        if pc_path.exists():
            ok = self._heal_yaml_file(pc_path, reset_content="{}\n")
            all_ok = all_ok and ok

        # JSONL stores
        for fname in ("episodic_store.jsonl", "user_profile_store.jsonl", "response_patterns.jsonl"):
            fpath = mem_dir / fname
            if fpath.exists():
                ok = self._heal_jsonl_file(fpath)
                all_ok = all_ok and ok

        # active_thread_state.json
        ts_path = mem_dir / "active_thread_state.json"
        if ts_path.exists():
            ok = self._heal_json_file(ts_path, reset_content="{}\n")
            all_ok = all_ok and ok

        return all_ok

    def _heal_jsonl_file(self, path: Path) -> bool:
        """Remove corrupt lines from a JSONL file.  Backs up bad lines first."""
        good_lines: list[str] = []
        bad_lines: list[str] = []

        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.rstrip("\n")
                    if not stripped.strip():
                        continue   # skip blank lines
                    try:
                        json.loads(stripped)
                        good_lines.append(stripped)
                    except json.JSONDecodeError:
                        bad_lines.append(stripped)
        except Exception as exc:
            logger.error("Could not read %s for healing: %s", path, exc)
            return False

        if not bad_lines:
            return True   # Already healthy

        logger.warning(
            "%s: %d corrupt line(s) found out of %d — quarantining",
            path.name, len(bad_lines), len(good_lines) + len(bad_lines),
        )

        # Back up corrupt lines
        backup_path = path.parent / f"corrupt_backup_{_timestamp()}.jsonl"
        try:
            backup_path.write_text("\n".join(bad_lines) + "\n", encoding="utf-8")
            logger.info("Quarantined %d bad line(s) to %s", len(bad_lines), backup_path)
        except Exception as exc:
            logger.error("Could not write corrupt backup: %s", exc)
            return False

        # Rewrite file with only good lines
        try:
            atomic_write(path, "\n".join(good_lines) + "\n" if good_lines else "")
            logger.info("%s: repaired (%d good lines retained)", path.name, len(good_lines))
            return True
        except Exception as exc:
            logger.error("Could not rewrite %s: %s", path, exc)
            return False

    def _heal_yaml_file(self, path: Path, reset_content: str = "{}\n") -> bool:
        """Validate a YAML file; reset to reset_content if unparseable."""
        try:
            with path.open("r", encoding="utf-8") as f:
                yaml.safe_load(f)
            return True   # Already valid
        except Exception as exc:
            logger.warning(
                "%s is corrupt (%s) — resetting to default template", path.name, exc
            )
            try:
                backup = path.parent / f"{path.stem}_corrupt_{_timestamp()}{path.suffix}"
                shutil.copy2(str(path), str(backup))
                atomic_write(path, reset_content)
                logger.info("Reset %s (backup: %s)", path.name, backup.name)
                return True
            except Exception as write_exc:
                logger.error("Could not reset %s: %s", path.name, write_exc)
                return False

    def _heal_json_file(self, path: Path, reset_content: str = "{}\n") -> bool:
        """Validate a JSON file; reset to reset_content if unparseable."""
        try:
            with path.open("r", encoding="utf-8") as f:
                json.load(f)
            return True
        except Exception as exc:
            logger.warning(
                "%s is corrupt (%s) — resetting to empty state", path.name, exc
            )
            try:
                backup = path.parent / f"{path.stem}_corrupt_{_timestamp()}.json"
                shutil.copy2(str(path), str(backup))
                atomic_write(path, reset_content)
                logger.info("Reset %s (backup: %s)", path.name, backup.name)
                return True
            except Exception as write_exc:
                logger.error("Could not reset %s: %s", path.name, write_exc)
                return False

    # ── Knowledge DB healing ───────────────────────────────────────────────────

    def heal_knowledge_db(self) -> bool:
        """Check knowledge DB integrity; if corrupt, rename and rebuild empty schema.

        - Enables WAL mode if not already set
        - Runs VACUUM if DB is over-large
        - Returns True if DB is healthy after healing

        Note: rebuilding only recreates the empty schema — all data is lost.
        Use forge_memory.py to re-ingest after a DB rebuild.
        """
        db_path = self._knowledge_db_path
        if not db_path.exists():
            return True   # No DB yet — nothing to heal

        # 1. Check integrity
        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            try:
                rows = conn.execute("PRAGMA integrity_check").fetchall()
                integrity_ok = len(rows) == 1 and rows[0][0] == "ok"
            finally:
                conn.close()
        except Exception as exc:
            logger.error("Could not open knowledge.db for integrity check: %s", exc)
            integrity_ok = False

        if not integrity_ok:
            logger.error(
                "knowledge.db failed integrity check — renaming to .corrupt and rebuilding schema"
            )
            corrupt_path = db_path.with_suffix(f".corrupt_{_timestamp()}.db")
            try:
                db_path.rename(corrupt_path)
                logger.info("Renamed corrupt DB to %s", corrupt_path.name)
            except Exception as exc:
                logger.error("Could not rename corrupt DB: %s", exc)
                return False
            return self._rebuild_empty_schema(db_path)

        # 2. Enable WAL mode if needed
        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            try:
                wal_row = conn.execute("PRAGMA journal_mode").fetchone()
                if wal_row and wal_row[0].lower() != "wal":
                    conn.execute("PRAGMA journal_mode = WAL")
                    conn.commit()
                    logger.info("Enabled WAL mode on knowledge.db")
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Could not enable WAL mode: %s", exc)

        # 3. Vacuum if DB is suspiciously large (> 500 MB with zero entities)
        try:
            size_mb = db_path.stat().st_size / (1024 * 1024)
            conn = sqlite3.connect(str(db_path), timeout=10)
            try:
                entity_count_row = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
                entity_count = entity_count_row[0] if entity_count_row else 0
                if size_mb > 500 and entity_count == 0:
                    logger.info("Vacuuming oversized empty knowledge.db (%.1f MB)", size_mb)
                    conn.execute("VACUUM")
                    conn.commit()
            except Exception:
                pass   # entities table might not exist — skip
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Could not check/vacuum knowledge.db: %s", exc)

        return True

    def _rebuild_empty_schema(self, db_path: Path) -> bool:
        """Create a fresh empty knowledge.db with the correct schema."""
        try:
            from thoughtforge.etl.schema import initialize_schema
            initialize_schema(db_path)
            logger.info("Rebuilt empty knowledge.db schema at %s", db_path)
            return True
        except Exception as exc:
            logger.error("Could not rebuild knowledge.db schema: %s", exc)
            return False
