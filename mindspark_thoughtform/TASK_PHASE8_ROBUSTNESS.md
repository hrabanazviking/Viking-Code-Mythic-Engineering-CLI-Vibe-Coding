# TASK: Phase 8 — Robustness, Self-Healing, and Production Hardening

**Created:** 2026-03-31
**Completed:** 2026-04-01
**Phase:** 8 of 8 (FINAL)
**Branch:** development
**Status:** COMPLETE — 620 tests passing, tagged v1.2.0
**Depends on:** Phase 7 complete

---

## Goal

Make ThoughtForge production-grade. Every failure should be caught, diagnosed,
and either self-healed or reported clearly. No silent data loss. No cryptic tracebacks.
No half-initialised state. The system should degrade gracefully under any condition
and recover automatically where possible.

---

## Deliverables

| File | Status | Description |
|---|---|---|
| `src/thoughtforge/utils/health.py` | ✅ | System health checker + diagnostic report |
| `src/thoughtforge/utils/self_heal.py` | ✅ | Self-healing: config repair, DB integrity, file recovery |
| `src/thoughtforge/utils/retry.py` | ✅ | Retry decorator with exponential backoff + circuit breaker |
| `src/thoughtforge/utils/errors.py` | ✅ | Typed exception hierarchy |
| `src/thoughtforge/utils/validators.py` | ✅ | Input validation + sanitisation layer |
| `src/thoughtforge/utils/perf.py` | ✅ | Performance profiler + bottleneck reporter |
| `src/thoughtforge/etl/db_integrity.py` | ✅ | SQLite integrity checker + auto-repair |
| `forge_doctor.py` | ✅ | Root-level diagnostic CLI: `python forge_doctor.py` |
| `tests/test_phase8_health.py` | ✅ | Health + self-heal tests |
| `tests/test_phase8_errors.py` | ✅ | Error hierarchy + recovery tests |
| `tests/test_phase8_perf.py` | ✅ | Performance regression tests |

---

## Module Specs

### `src/thoughtforge/utils/errors.py` — Typed Exception Hierarchy

```python
# Base
class ThoughtForgeError(Exception): ...

# Config
class ConfigError(ThoughtForgeError): ...
class ConfigMissingError(ConfigError): ...
class ConfigCorruptError(ConfigError): ...

# Backend
class BackendError(ThoughtForgeError): ...
class BackendUnavailableError(BackendError): ...
class BackendTimeoutError(BackendError): ...
class BackendAuthError(BackendError): ...
class ModelNotFoundError(BackendError): ...

# Knowledge / DB
class KnowledgeError(ThoughtForgeError): ...
class DatabaseCorruptError(KnowledgeError): ...
class DatabaseLockedError(KnowledgeError): ...
class RetrievalError(KnowledgeError): ...

# Memory
class MemoryError(ThoughtForgeError): ...
class MemoryFileCorruptError(MemoryError): ...
class MemoryWriteError(MemoryError): ...

# Pipeline
class PipelineError(ThoughtForgeError): ...
class ScaffoldError(PipelineError): ...
class EnforcementError(PipelineError): ...
```

All exceptions carry: `message`, `context: dict`, `recoverable: bool`,
`suggested_fix: str`.

Replace all bare `except Exception` catches throughout codebase with typed catches.

---

### `src/thoughtforge/utils/retry.py` — Retry + Circuit Breaker

```python
@retry(
    attempts=3,
    backoff=exponential(base=0.5, max=10.0),
    on=(BackendTimeoutError, BackendUnavailableError),
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_timeout=60),
)
def call_backend(...): ...
```

- `@retry(attempts, backoff, on, fallback)` decorator
- `exponential(base, max)` / `linear(step)` / `fixed(seconds)` backoff strategies
- `CircuitBreaker` — opens after N failures, half-opens after recovery timeout
- Jitter on retries to prevent thundering herd
- All retry events logged at WARNING level with attempt count

---

### `src/thoughtforge/utils/health.py` — System Health Checker

```python
@dataclass
class HealthResult:
    component: str
    status: str      # "ok" | "degraded" | "fail"
    message: str
    fix_hint: str

class HealthChecker:
    def check_all(self) -> list[HealthResult]: ...
    def check_config(self) -> HealthResult: ...
    def check_backend(self) -> HealthResult: ...
    def check_knowledge_db(self) -> HealthResult: ...
    def check_memory_store(self) -> HealthResult: ...
    def check_disk_space(self) -> HealthResult: ...
    def check_dependencies(self) -> HealthResult: ...
    def report(self) -> str: ...   # human-readable summary
```

Checks:
- `user_config.yaml` exists and is valid YAML with required keys
- Configured backend is reachable (health_check())
- Knowledge DB exists, is not corrupt (PRAGMA integrity_check)
- Memory store files are valid JSON/JSONL/YAML
- Disk space ≥ 500 MB free
- All required Python packages importable at correct versions
- No zombie log file handles

---

### `src/thoughtforge/utils/self_heal.py` — Self-Healing

```python
class SelfHealer:
    def heal_config(self) -> bool: ...
    def heal_memory_store(self) -> bool: ...
    def heal_knowledge_db(self) -> bool: ...
    def heal_all(self) -> dict[str, bool]: ...
```

**Config healing:**
- If `user_config.yaml` is missing → copy from `configs/default_user_config.yaml`
- If corrupt YAML → rebuild from defaults, warn user
- If unknown backend → reset to `none`, prompt reconfigure

**Memory store healing:**
- Validate each JSONL line — drop malformed lines, log count
- Validate YAML personality_core — reset to template if unparseable
- Validate JSON thread_state — reset to empty if corrupt
- Never silently discard data — write broken lines to `memory/corrupt_backup_<ts>.jsonl`

**Knowledge DB healing:**
- `PRAGMA integrity_check` — if corrupt, rename to `.corrupt_<ts>.db`, rebuild schema
- WAL mode enabled to prevent mid-write corruption
- Check FTS5 index consistency — rebuild if shadow tables missing
- Vacuum on startup if DB > 2× expected size

**File healing (general):**
- All file writes use atomic write-then-rename pattern
- Temp file → flush → sync → rename (prevents partial writes)

---

### `src/thoughtforge/etl/db_integrity.py` — Database Integrity

```python
class DBIntegrityChecker:
    def check(self, db_path: Path) -> IntegrityReport: ...
    def repair(self, db_path: Path) -> RepairResult: ...
    def enable_wal(self, db_path: Path) -> None: ...
    def optimize(self, db_path: Path) -> None: ...

@dataclass
class IntegrityReport:
    ok: bool
    errors: list[str]
    row_counts: dict[str, int]
    db_size_mb: float
    fts_ok: bool
    wal_mode: bool
```

Run automatically on first import if DB exists and was last checked > 24h ago.
Result cached in `data/.last_integrity_check` (timestamp + ok/fail).

---

### `src/thoughtforge/utils/validators.py` — Input Validation

```python
def sanitise_query(text: str) -> str:
    """Strip null bytes, excessive whitespace, control characters.
    Truncate to MAX_QUERY_CHARS (4096). Never raises — always returns str."""

def validate_config(config: dict) -> list[str]:
    """Returns list of validation error strings. Empty = valid."""

def validate_model_path(path: str | Path) -> Path:
    """Raises ModelNotFoundError with helpful message if path doesn't exist."""

def validate_api_key(key: str, provider: str) -> bool:
    """Format-check only — does not make network calls."""
```

Applied at all system boundaries:
- `ThoughtForgeCore.think()` — sanitise_query on entry
- `setup_thoughtforge.py` — validate_config before writing
- All file loads — validate schema before use

---

### `src/thoughtforge/utils/perf.py` — Performance Profiler

```python
class PerfTracker:
    def record(self, event: str, duration_ms: float, metadata: dict = {}) -> None: ...
    def summary(self, last_n: int = 100) -> PerfSummary: ...
    def bottleneck_report(self) -> str: ...

@dataclass
class PerfSummary:
    events: dict[str, EventStats]   # event_name → {mean, p50, p95, p99, count}
    slowest_events: list[tuple[str, float]]
    total_tracked: int
```

Instrumented at:
- `ThoughtForgeCore.think()` — total, retrieval, scaffold, generation, salvage, enforcement
- `UnifiedBackend.generate()` — per backend
- `MemoryForge.retrieve()` — per retrieval path
- Knowledge DB queries

Lightweight ring buffer (1000 events max). Reported in `--debug` mode and `/stats`
chat command.

---

### `forge_doctor.py` — Diagnostic CLI

```
python forge_doctor.py

MindSpark: ThoughtForge — System Diagnostics
=============================================

[Config]
  ✓ user_config.yaml — valid
  ✓ backend: ollama (llama3.2:3b)

[Backend]
  ✓ Ollama reachable at http://localhost:11434
  ✓ Model llama3.2:3b loaded (ping: 42ms)

[Knowledge DB]
  ✓ thoughtforge.db — 42 MB, 89,412 entities
  ✓ Integrity: OK
  ✓ FTS5 index: OK
  ✓ WAL mode: enabled

[Memory Store]
  ✓ personality_core.yaml — valid
  ✓ episodic_memory.jsonl — 0 records (empty — OK)
  ✓ active_thread_state.json — valid

[Disk]
  ✓ 142 GB free

[Dependencies]
  ✓ thoughtforge 1.0.1
  ✓ sentence-transformers 2.x
  ✓ sqlalchemy OK
  ✗ llama-cpp-python: not installed (OK — using Ollama backend)

[Self-Heal]
  No issues found. Nothing to repair.

All systems operational. Run: python run_thoughtforge.py
```

Flags:
- `--fix` — run self-healer on any detected issues
- `--json` — machine-readable output
- `--verbose` — show all checks including passing

---

## Code Quality Audit (to run during Phase 8)

### Bare except sweeps
- Replace all `except Exception as e: logger.warning(...)` with typed catches
- Every catch either re-raises, returns a typed error result, or self-heals

### Resource leak audit
- All SQLite connections wrapped in context managers or explicit close
- All file handles use `with open(...)` — no unclosed handles
- TurboQuantEngine model properly unloaded when context manager exits

### Efficiency audit
- Identify any O(n²) loops in knowledge retrieval scoring
- Remove redundant JSON re-serialisation in hot paths
- Profile memory usage in knowledge store (JSONL full-load vs streaming)
- LRU cache on personality_core load (doesn't change per turn)

### Config redundancy
- `configs/default.yaml` and `configs/user_config.yaml` merged cleanly
- No duplicated config keys read from different places
- Single `load_config()` function used everywhere (no ad-hoc yaml.safe_load)

### Test coverage gaps
- Identify any public methods with 0 test coverage
- Add targeted tests for any found gaps
- Mutation testing pass on critical path (salvage, enforcement, routing)

---

## Self-Healing Integration Points

| Location | Current Behaviour | Phase 8 Behaviour |
|---|---|---|
| `ThoughtForgeCore.__init__()` | Logs warning if DB missing | Calls `SelfHealer.heal_all()` — repairs what it can |
| `MemoryForge.retrieve()` | Returns empty bundle on error | Typed `RetrievalError`, tries alternate path |
| `store.py` file loads | `except Exception` → returns default | Validates + heals corrupt files before returning |
| `TurboQuantEngine.load()` | Raises raw exception | `ModelNotFoundError` with suggested fix |
| `forge_memory.py` ETL | Crashes on bad data | Skips + logs bad records, continues |
| `run_thoughtforge.py` main | Unhandled exception → traceback | Catches `ThoughtForgeError` → user-friendly message + fix hint |

---

## Atomic Write Pattern (applied everywhere)

```python
def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.flush()
    os.fsync(tmp.fileno())
    tmp.replace(path)   # atomic on POSIX + Windows
```

Used for: all JSONL appends (write to temp, merge), YAML writes, JSON state writes.

---

## Test Strategy

### `tests/test_phase8_health.py`
- `HealthChecker.check_all()` returns list of HealthResult
- Each check returns valid status string
- `check_knowledge_db()` on missing DB → fail with fix_hint
- `check_backend()` on unavailable backend → fail not raise
- `SelfHealer.heal_config()` on missing config → creates default
- `SelfHealer.heal_memory_store()` on corrupt JSONL → drops bad lines, keeps good
- Atomic write: partial write simulation → original file intact

### `tests/test_phase8_errors.py`
- All exception types carry `recoverable` + `suggested_fix`
- `@retry` decorator: 3 failures → raises after 3 attempts
- `@retry` with fallback: returns fallback on exhaustion
- `CircuitBreaker` opens after threshold failures
- `CircuitBreaker` half-opens after recovery timeout
- `sanitise_query` strips null bytes, control chars, truncates at 4096

### `tests/test_phase8_perf.py`
- `PerfTracker.record()` + `summary()` correct event stats
- `think()` total latency < 5000ms (knowledge-only, no model)
- `retrieve()` latency < 500ms on empty DB
- Memory store load < 100ms for 1000 episodic records
- No memory growth over 10 consecutive `think()` calls (no leak)

---

## Release Target

After Phase 8: tag `v1.2.0` — "Production-Grade" milestone.
Benchmark report + self-heal report added to release notes.
