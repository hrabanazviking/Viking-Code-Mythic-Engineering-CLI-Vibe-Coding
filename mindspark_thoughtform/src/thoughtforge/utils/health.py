"""System health checker for MindSpark: ThoughtForge.

Runs non-destructive checks on every major component and returns structured
HealthResult objects.  Never raises — every check returns a result with a
status string so callers can act on it safely.

Usage:
    from thoughtforge.utils.health import HealthChecker
    results = HealthChecker().check_all()
    print(HealthChecker().report())
"""

from __future__ import annotations

import importlib.util
import logging
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from thoughtforge.utils.paths import (
    get_configs_dir,
    get_knowledge_db_path,
    get_memory_dir,
)

logger = logging.getLogger(__name__)

# ── Minimum free disk space (bytes) ───────────────────────────────────────────
_MIN_FREE_BYTES = 500 * 1024 * 1024   # 500 MB

# Required packages: (import_name, pip_name)
_REQUIRED_PACKAGES: list[tuple[str, str]] = [
    ("yaml", "pyyaml"),
    ("sentence_transformers", "sentence-transformers"),
]

_OPTIONAL_PACKAGES: list[tuple[str, str]] = [
    ("llama_cpp", "llama-cpp-python"),
    ("onnxruntime", "onnxruntime"),
    ("torch", "torch"),
]

_REQUIRED_CONFIG_KEYS = {"backend"}


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class HealthResult:
    component: str
    status: str          # "ok" | "degraded" | "fail"
    message: str
    fix_hint: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def failed(self) -> bool:
        return self.status == "fail"


# ── HealthChecker ──────────────────────────────────────────────────────────────

class HealthChecker:
    """
    Non-destructive health checker for all ThoughtForge components.

    Every check method returns a HealthResult; it never raises.
    check_all() runs all checks and returns a flat list.
    """

    def __init__(self) -> None:
        self._user_config_path = get_configs_dir() / "user_config.yaml"
        self._default_config_path = get_configs_dir() / "default.yaml"
        self._knowledge_db_path = get_knowledge_db_path()
        self._memory_dir = get_memory_dir()

    # ── Public API ─────────────────────────────────────────────────────────────

    def check_all(self) -> list[HealthResult]:
        """Run every check and return the full list of results."""
        return [
            self.check_config(),
            self.check_backend(),
            self.check_knowledge_db(),
            self.check_memory_store(),
            self.check_disk_space(),
            self.check_dependencies(),
        ]

    def report(self, verbose: bool = False) -> str:
        """Return a human-readable multi-line health report."""
        results = self.check_all()
        lines: list[str] = [
            "MindSpark: ThoughtForge — System Diagnostics",
            "=" * 45,
        ]
        sections: dict[str, list[HealthResult]] = {}
        for r in results:
            sections.setdefault(r.component, []).append(r)

        for component, comp_results in sections.items():
            lines.append(f"\n[{component}]")
            for r in comp_results:
                icon = "✓" if r.ok else ("!" if r.status == "degraded" else "✗")
                line = f"  {icon} {r.message}"
                lines.append(line)
                if not r.ok and r.fix_hint:
                    lines.append(f"    → {r.fix_hint}")

        overall = all(r.ok or r.status == "degraded" for r in results)
        lines.append("")
        if overall:
            lines.append("All systems operational. Run: python run_thoughtforge.py")
        else:
            failed = [r for r in results if r.failed]
            lines.append(
                f"{len(failed)} issue(s) found. Run: python forge_doctor.py --fix"
            )

        return "\n".join(lines)

    # ── Individual checks ──────────────────────────────────────────────────────

    def check_config(self) -> HealthResult:
        """Check that user_config.yaml exists and contains required keys."""
        path = self._user_config_path
        if not path.exists():
            return HealthResult(
                component="Config",
                status="fail",
                message=f"user_config.yaml not found at {path}",
                fix_hint="Run: python setup_thoughtforge.py",
            )

        try:
            with path.open("r", encoding="utf-8") as f:
                cfg: Any = yaml.safe_load(f)
        except Exception as exc:
            return HealthResult(
                component="Config",
                status="fail",
                message=f"user_config.yaml is not valid YAML: {exc}",
                fix_hint="Run: python forge_doctor.py --fix",
            )

        if not isinstance(cfg, dict):
            return HealthResult(
                component="Config",
                status="fail",
                message="user_config.yaml parsed to a non-dict value",
                fix_hint="Run: python setup_thoughtforge.py to regenerate",
            )

        missing = _REQUIRED_CONFIG_KEYS - set(cfg.keys())
        if missing:
            return HealthResult(
                component="Config",
                status="fail",
                message=f"user_config.yaml missing required key(s): {', '.join(sorted(missing))}",
                fix_hint="Run: python setup_thoughtforge.py",
            )

        backend = str(cfg.get("backend", "none")).strip().lower()
        model_info = ""
        if backend == "ollama":
            model_info = f" ({cfg.get('ollama_model', '')})"
        elif backend in ("lmstudio", "openai_compatible"):
            model_info = f" ({cfg.get('lmstudio_model', '')})"
        elif backend == "turboquant":
            model_info = f" ({Path(cfg.get('gguf_model_path', '')).name})"

        return HealthResult(
            component="Config",
            status="ok",
            message=f"user_config.yaml — valid | backend: {backend}{model_info}",
        )

    def check_backend(self) -> HealthResult:
        """Check that the configured backend is reachable."""
        path = self._user_config_path
        if not path.exists():
            return HealthResult(
                component="Backend",
                status="degraded",
                message="Skipped (user_config.yaml not found)",
            )

        try:
            with path.open("r", encoding="utf-8") as f:
                cfg: Any = yaml.safe_load(f) or {}
        except Exception:
            return HealthResult(
                component="Backend",
                status="degraded",
                message="Skipped (user_config.yaml unreadable)",
            )

        backend = str(cfg.get("backend", "none")).strip().lower()

        if backend in ("none", ""):
            return HealthResult(
                component="Backend",
                status="ok",
                message="No backend configured (knowledge-only mode)",
            )

        try:
            from thoughtforge.inference.unified_backend import load_backend_from_config
            instance = load_backend_from_config(path)
            if instance is None:
                return HealthResult(
                    component="Backend",
                    status="ok",
                    message=f"Backend '{backend}' loaded (health_check skipped for this type)",
                )
            t_start = __import__("time").perf_counter()
            ok = instance.health_check()
            ping_ms = int((__import__("time").perf_counter() - t_start) * 1000)
            if ok:
                return HealthResult(
                    component="Backend",
                    status="ok",
                    message=f"{instance.backend_name()} reachable (ping: {ping_ms}ms)",
                )
            return HealthResult(
                component="Backend",
                status="fail",
                message=f"{backend} health_check returned False",
                fix_hint=f"Ensure your {backend} server is running",
            )
        except Exception as exc:
            return HealthResult(
                component="Backend",
                status="fail",
                message=f"Backend '{backend}' not reachable: {exc}",
                fix_hint=f"Start your {backend} server and retry",
            )

    def check_knowledge_db(self) -> HealthResult:
        """Check knowledge DB exists, is not corrupt, and has WAL mode."""
        db = self._knowledge_db_path
        if not db.exists():
            return HealthResult(
                component="Knowledge DB",
                status="degraded",
                message=f"knowledge.db not found at {db} (empty knowledge base — OK)",
                fix_hint="Run: python forge_memory.py reference  to populate it",
            )

        size_mb = db.stat().st_size / (1024 * 1024)

        try:
            conn = sqlite3.connect(str(db), timeout=5)
            try:
                # Integrity check
                rows = conn.execute("PRAGMA integrity_check").fetchall()
                integrity_ok = len(rows) == 1 and rows[0][0] == "ok"

                # WAL mode
                wal_row = conn.execute("PRAGMA journal_mode").fetchone()
                wal_mode = wal_row[0].lower() == "wal" if wal_row else False

                # FTS5 shadow tables (proxy for FTS health)
                fts_row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='entities_fts'"
                ).fetchone()
                fts_ok = fts_row is not None

                # Row counts
                entity_count_row = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
                entity_count = entity_count_row[0] if entity_count_row else 0

            finally:
                conn.close()
        except Exception as exc:
            return HealthResult(
                component="Knowledge DB",
                status="fail",
                message=f"knowledge.db failed to open: {exc}",
                fix_hint="Run: python forge_doctor.py --fix",
            )

        if not integrity_ok:
            return HealthResult(
                component="Knowledge DB",
                status="fail",
                message=f"knowledge.db failed integrity check ({size_mb:.1f} MB)",
                fix_hint="Run: python forge_doctor.py --fix to repair or rebuild",
            )

        status = "ok"
        notes = []
        if not wal_mode:
            notes.append("WAL mode not enabled")
            status = "degraded"
        if not fts_ok:
            notes.append("FTS5 index missing")
            status = "degraded"

        note_str = " | ".join(notes) if notes else "OK"
        return HealthResult(
            component="Knowledge DB",
            status=status,
            message=(
                f"knowledge.db — {size_mb:.1f} MB, {entity_count:,} entities | "
                f"Integrity: OK | FTS5: {'OK' if fts_ok else 'missing'} | "
                f"WAL: {'enabled' if wal_mode else 'disabled'}"
            ),
            fix_hint="Run: python forge_doctor.py --fix" if status != "ok" else "",
        )

    def check_memory_store(self) -> HealthResult:
        """Check memory store files are present and parseable."""
        mem_dir = self._memory_dir
        if not mem_dir.exists():
            return HealthResult(
                component="Memory Store",
                status="ok",
                message="Memory directory not yet created (normal for fresh install)",
            )

        issues: list[str] = []
        notes: list[str] = []

        # personality_core.yaml
        pc_path = mem_dir / "personality_core.yaml"
        if pc_path.exists():
            try:
                with pc_path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    issues.append("personality_core.yaml: not a YAML mapping")
                else:
                    notes.append("personality_core.yaml — valid")
            except Exception as exc:
                issues.append(f"personality_core.yaml: {exc}")
        else:
            notes.append("personality_core.yaml — not present (OK)")

        # JSONL files
        for fname in ("episodic_store.jsonl", "user_profile_store.jsonl", "response_patterns.jsonl"):
            fpath = mem_dir / fname
            if not fpath.exists():
                notes.append(f"{fname} — not present (OK)")
                continue
            import json
            bad_lines = 0
            total_lines = 0
            try:
                with fpath.open("r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        total_lines += 1
                        try:
                            json.loads(stripped)
                        except json.JSONDecodeError:
                            bad_lines += 1
            except Exception as exc:
                issues.append(f"{fname}: {exc}")
                continue
            if bad_lines:
                issues.append(f"{fname}: {bad_lines}/{total_lines} corrupt lines")
            else:
                notes.append(f"{fname} — {total_lines} records (valid)")

        # active_thread_state.json
        ts_path = mem_dir / "active_thread_state.json"
        if ts_path.exists():
            import json
            try:
                with ts_path.open("r", encoding="utf-8") as f:
                    json.load(f)
                notes.append("active_thread_state.json — valid")
            except Exception as exc:
                issues.append(f"active_thread_state.json: {exc}")
        else:
            notes.append("active_thread_state.json — not present (OK)")

        if issues:
            return HealthResult(
                component="Memory Store",
                status="fail",
                message="Memory store issues: " + "; ".join(issues),
                fix_hint="Run: python forge_doctor.py --fix",
            )

        summary = notes[0] if len(notes) == 1 else f"{len(notes)} files checked (all valid)"
        return HealthResult(
            component="Memory Store",
            status="ok",
            message=summary,
        )

    def check_disk_space(self) -> HealthResult:
        """Check there is at least 500 MB free on the project's disk."""
        try:
            root = get_knowledge_db_path().parent
            usage = shutil.disk_usage(root)
            free_gb = usage.free / (1024 ** 3)
            if usage.free < _MIN_FREE_BYTES:
                return HealthResult(
                    component="Disk",
                    status="fail",
                    message=f"Only {free_gb:.1f} GB free — minimum 500 MB required",
                    fix_hint="Free up disk space before running ThoughtForge",
                )
            return HealthResult(
                component="Disk",
                status="ok",
                message=f"{free_gb:.1f} GB free",
            )
        except Exception as exc:
            return HealthResult(
                component="Disk",
                status="degraded",
                message=f"Could not check disk space: {exc}",
            )

    def check_dependencies(self) -> HealthResult:
        """Check required and optional Python packages are importable."""
        missing_required: list[str] = []
        optional_notes: list[str] = []

        for import_name, pip_name in _REQUIRED_PACKAGES:
            if importlib.util.find_spec(import_name) is None:
                missing_required.append(pip_name)

        for import_name, pip_name in _OPTIONAL_PACKAGES:
            if importlib.util.find_spec(import_name) is None:
                optional_notes.append(f"{pip_name}: not installed (OK — optional)")

        if missing_required:
            return HealthResult(
                component="Dependencies",
                status="fail",
                message=f"Missing required packages: {', '.join(missing_required)}",
                fix_hint=f"Run: pip install {' '.join(missing_required)}",
            )

        note = (
            f"{len(_REQUIRED_PACKAGES)} required packages present"
            + (f"; {len(optional_notes)} optional absent" if optional_notes else "")
        )
        return HealthResult(
            component="Dependencies",
            status="ok",
            message=note,
        )
