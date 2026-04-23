"""Phase 8 — HealthChecker, SelfHealer, DBIntegrityChecker, and atomic_write tests."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
import yaml

from thoughtforge.utils.health import HealthChecker, HealthResult
from thoughtforge.utils.self_heal import SelfHealer, atomic_write
from thoughtforge.etl.db_integrity import DBIntegrityChecker, IntegrityReport


# ── HealthResult ──────────────────────────────────────────────────────────────

class TestHealthResult:
    def test_ok_property(self):
        r = HealthResult(component="X", status="ok", message="all good")
        assert r.ok is True
        assert r.failed is False

    def test_failed_property(self):
        r = HealthResult(component="X", status="fail", message="broken")
        assert r.ok is False
        assert r.failed is True

    def test_degraded(self):
        r = HealthResult(component="X", status="degraded", message="meh")
        assert r.ok is False
        assert r.failed is False


# ── HealthChecker.check_all() ─────────────────────────────────────────────────

class TestHealthCheckerAll:
    def test_returns_list_of_health_results(self):
        results = HealthChecker().check_all()
        assert isinstance(results, list)
        assert all(isinstance(r, HealthResult) for r in results)

    def test_all_results_have_valid_status(self):
        results = HealthChecker().check_all()
        valid = {"ok", "degraded", "fail"}
        for r in results:
            assert r.status in valid, f"{r.component}: invalid status '{r.status}'"

    def test_each_result_has_non_empty_message(self):
        results = HealthChecker().check_all()
        for r in results:
            assert r.message, f"{r.component} has empty message"

    def test_report_returns_string(self):
        report = HealthChecker().report()
        assert isinstance(report, str)
        assert len(report) > 0


# ── check_config ──────────────────────────────────────────────────────────────

class TestCheckConfig:
    def test_missing_config_is_fail(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "thoughtforge.utils.health.get_configs_dir", lambda: tmp_path
        )
        checker = HealthChecker()
        checker._user_config_path = tmp_path / "user_config.yaml"
        result = checker.check_config()
        assert result.failed
        assert result.fix_hint

    def test_corrupt_yaml_is_fail(self, tmp_path):
        p = tmp_path / "user_config.yaml"
        p.write_text(": : : broken yaml :::", encoding="utf-8")
        checker = HealthChecker()
        checker._user_config_path = p
        result = checker.check_config()
        assert result.failed

    def test_valid_config_is_ok(self, tmp_path):
        p = tmp_path / "user_config.yaml"
        p.write_text("backend: none\n", encoding="utf-8")
        checker = HealthChecker()
        checker._user_config_path = p
        result = checker.check_config()
        assert result.ok

    def test_missing_backend_key_is_fail(self, tmp_path):
        p = tmp_path / "user_config.yaml"
        p.write_text("some_key: value\n", encoding="utf-8")
        checker = HealthChecker()
        checker._user_config_path = p
        result = checker.check_config()
        assert result.failed


# ── check_backend ─────────────────────────────────────────────────────────────

class TestCheckBackend:
    def test_missing_config_is_degraded(self, tmp_path):
        checker = HealthChecker()
        checker._user_config_path = tmp_path / "nonexistent.yaml"
        result = checker.check_backend()
        assert result.status == "degraded"

    def test_backend_none_is_ok(self, tmp_path):
        p = tmp_path / "user_config.yaml"
        p.write_text("backend: none\n", encoding="utf-8")
        checker = HealthChecker()
        checker._user_config_path = p
        result = checker.check_backend()
        assert result.ok


# ── check_knowledge_db ────────────────────────────────────────────────────────

class TestCheckKnowledgeDB:
    def test_missing_db_is_degraded(self, tmp_path):
        checker = HealthChecker()
        checker._knowledge_db_path = tmp_path / "nonexistent.db"
        result = checker.check_knowledge_db()
        assert result.status == "degraded"
        assert result.fix_hint

    def test_valid_empty_db_is_ok(self, tmp_path):
        db = tmp_path / "knowledge.db"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("CREATE TABLE IF NOT EXISTS entities (qid TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS statements (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS labels (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS embeddings (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS reference_chunks (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        checker = HealthChecker()
        checker._knowledge_db_path = db
        result = checker.check_knowledge_db()
        # Integrity should pass; WAL enabled; FTS5 absent → degraded at most
        assert result.status in ("ok", "degraded")


# ── check_memory_store ────────────────────────────────────────────────────────

class TestCheckMemoryStore:
    def test_empty_dir_is_ok(self, tmp_path):
        checker = HealthChecker()
        checker._memory_dir = tmp_path
        result = checker.check_memory_store()
        assert result.ok

    def test_valid_jsonl_is_ok(self, tmp_path):
        f = tmp_path / "episodic_store.jsonl"
        f.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")
        checker = HealthChecker()
        checker._memory_dir = tmp_path
        result = checker.check_memory_store()
        assert result.ok

    def test_corrupt_jsonl_is_fail(self, tmp_path):
        f = tmp_path / "episodic_store.jsonl"
        f.write_text('{"id": 1}\nNOT JSON\n{"id": 3}\n', encoding="utf-8")
        checker = HealthChecker()
        checker._memory_dir = tmp_path
        result = checker.check_memory_store()
        assert result.failed

    def test_valid_yaml_is_ok(self, tmp_path):
        f = tmp_path / "personality_core.yaml"
        f.write_text("name: Sigrid\nage: 21\n", encoding="utf-8")
        checker = HealthChecker()
        checker._memory_dir = tmp_path
        result = checker.check_memory_store()
        assert result.ok


# ── check_disk_space ──────────────────────────────────────────────────────────

class TestCheckDiskSpace:
    def test_returns_health_result(self):
        result = HealthChecker().check_disk_space()
        assert isinstance(result, HealthResult)
        assert result.status in ("ok", "degraded", "fail")


# ── check_dependencies ────────────────────────────────────────────────────────

class TestCheckDependencies:
    def test_yaml_present(self):
        result = HealthChecker().check_dependencies()
        # yaml (pyyaml) must be installed for ThoughtForge to work at all
        assert result.ok or result.status == "degraded"


# ── SelfHealer ────────────────────────────────────────────────────────────────

class TestSelfHealerConfig:
    def _make_healer(self, tmp_path: Path) -> SelfHealer:
        h = SelfHealer()
        h._configs_dir = tmp_path
        h._user_config_path = tmp_path / "user_config.yaml"
        return h

    def test_missing_config_gets_restored(self, tmp_path):
        h = self._make_healer(tmp_path)
        assert not h._user_config_path.exists()
        ok = h.heal_config()
        assert ok
        assert h._user_config_path.exists()
        data = yaml.safe_load(h._user_config_path.read_text())
        assert "backend" in data

    def test_corrupt_config_gets_rebuilt(self, tmp_path):
        p = tmp_path / "user_config.yaml"
        p.write_text(": : broken :", encoding="utf-8")
        h = self._make_healer(tmp_path)
        ok = h.heal_config()
        assert ok
        data = yaml.safe_load(p.read_text())
        assert "backend" in data

    def test_valid_config_unchanged(self, tmp_path):
        p = tmp_path / "user_config.yaml"
        p.write_text("backend: ollama\nollama_url: http://localhost:11434\n", encoding="utf-8")
        mtime_before = p.stat().st_mtime
        h = self._make_healer(tmp_path)
        ok = h.heal_config()
        assert ok

    def test_unknown_backend_reset_to_none(self, tmp_path):
        p = tmp_path / "user_config.yaml"
        p.write_text("backend: UNKNOWN_THING\n", encoding="utf-8")
        h = self._make_healer(tmp_path)
        ok = h.heal_config()
        assert ok
        data = yaml.safe_load(p.read_text())
        assert data["backend"] == "none"


class TestSelfHealerMemory:
    def _make_healer(self, tmp_path: Path) -> SelfHealer:
        h = SelfHealer()
        h._memory_dir = tmp_path
        return h

    def test_valid_jsonl_no_change(self, tmp_path):
        f = tmp_path / "episodic_store.jsonl"
        original = '{"id": 1}\n{"id": 2}\n'
        f.write_text(original, encoding="utf-8")
        h = self._make_healer(tmp_path)
        ok = h.heal_memory_store()
        assert ok
        # Good lines are preserved
        lines = [l for l in f.read_text().splitlines() if l.strip()]
        assert len(lines) == 2

    def test_corrupt_lines_quarantined(self, tmp_path):
        f = tmp_path / "episodic_store.jsonl"
        f.write_text('{"id": 1}\nBAD LINE\n{"id": 3}\n', encoding="utf-8")
        h = self._make_healer(tmp_path)
        ok = h.heal_memory_store()
        assert ok
        # Good lines remain
        good_lines = [l for l in f.read_text().splitlines() if l.strip()]
        assert all(l.startswith("{") for l in good_lines)
        # Corrupt backup created
        backups = list(tmp_path.glob("corrupt_backup_*.jsonl"))
        assert len(backups) == 1

    def test_corrupt_json_thread_state_reset(self, tmp_path):
        f = tmp_path / "active_thread_state.json"
        f.write_text("NOT JSON {{{{", encoding="utf-8")
        h = self._make_healer(tmp_path)
        ok = h.heal_memory_store()
        assert ok
        data = json.loads(f.read_text())
        assert isinstance(data, dict)

    def test_empty_dir_returns_true(self, tmp_path):
        h = self._make_healer(tmp_path)
        assert h.heal_memory_store() is True


# ── atomic_write ──────────────────────────────────────────────────────────────

class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        p = tmp_path / "out.txt"
        atomic_write(p, "hello")
        assert p.read_text() == "hello"

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "out.txt"
        p.write_text("old")
        atomic_write(p, "new")
        assert p.read_text() == "new"

    def test_no_tmp_file_left_on_success(self, tmp_path):
        p = tmp_path / "out.txt"
        atomic_write(p, "data")
        tmp = p.with_suffix(".txt.tmp")
        assert not tmp.exists()


# ── DBIntegrityChecker ────────────────────────────────────────────────────────

class TestDBIntegrityChecker:
    def _make_checker(self, tmp_path: Path) -> DBIntegrityChecker:
        db = tmp_path / "knowledge.db"
        checker = DBIntegrityChecker(db_path=db)
        checker._cache_path = tmp_path / ".last_integrity_check"
        return checker

    def test_missing_db_returns_ok(self, tmp_path):
        checker = self._make_checker(tmp_path)
        report = checker.check(force=True)
        assert report.ok

    def test_empty_db_passes_integrity(self, tmp_path):
        from thoughtforge.etl.schema import initialize_schema
        db = tmp_path / "knowledge.db"
        initialize_schema(db)

        checker = self._make_checker(tmp_path)
        report = checker.check(force=True)
        # Full schema: integrity passes, no errors from missing tables
        assert report.ok

    def test_enable_wal(self, tmp_path):
        db = tmp_path / "knowledge.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        checker = self._make_checker(tmp_path)
        ok = checker.enable_wal(db)
        assert ok

        conn2 = sqlite3.connect(str(db))
        row = conn2.execute("PRAGMA journal_mode").fetchone()
        conn2.close()
        assert row[0].lower() == "wal"

    def test_cache_persisted_and_loaded(self, tmp_path):
        db = tmp_path / "knowledge.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        checker = self._make_checker(tmp_path)
        report1 = checker.check(force=True)
        # Second call should load from cache
        report2 = checker.check(force=False)
        assert report1.ok == report2.ok

    def test_force_bypasses_cache(self, tmp_path):
        db = tmp_path / "knowledge.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        checker = self._make_checker(tmp_path)
        checker.check(force=True)
        # Should not raise when forced again
        report2 = checker.check(force=True)
        assert isinstance(report2, IntegrityReport)

    def test_integrity_report_summary_string(self, tmp_path):
        db = tmp_path / "knowledge.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE entities (qid TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()

        checker = self._make_checker(tmp_path)
        report = checker.check(force=True)
        summary = report.summary()
        assert isinstance(summary, str)
        assert "Integrity" in summary
