"""Phase 8 — Error hierarchy, retry decorator, circuit breaker, and validator tests."""

from __future__ import annotations

import time
import threading
import pytest

from thoughtforge.utils.errors import (
    ThoughtForgeError,
    ConfigError,
    ConfigMissingError,
    ConfigCorruptError,
    BackendError,
    BackendUnavailableError,
    BackendTimeoutError,
    BackendAuthError,
    ModelNotFoundError,
    KnowledgeError,
    DatabaseCorruptError,
    DatabaseLockedError,
    RetrievalError,
    MemoryStoreError,
    MemoryFileCorruptError,
    MemoryWriteError,
    PipelineError,
    ScaffoldError,
    EnforcementError,
    ValidationError,
)
from thoughtforge.utils.retry import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    exponential,
    fixed,
    linear,
    retry,
)
from thoughtforge.utils.validators import sanitise_query


# ── Exception hierarchy ────────────────────────────────────────────────────────

class TestExceptionHierarchy:
    def test_base_fields(self):
        exc = ThoughtForgeError("boom", context={"k": "v"}, recoverable=True, suggested_fix="do X")
        assert exc.message == "boom"
        assert exc.context == {"k": "v"}
        assert exc.recoverable is True
        assert exc.suggested_fix == "do X"

    def test_str_includes_fix(self):
        exc = ThoughtForgeError("boom", suggested_fix="try again")
        assert "boom" in str(exc)
        assert "try again" in str(exc)

    def test_str_no_fix(self):
        exc = ThoughtForgeError("boom")
        assert str(exc) == "boom"

    def test_inheritance(self):
        assert issubclass(ConfigMissingError, ConfigError)
        assert issubclass(ConfigCorruptError, ConfigError)
        assert issubclass(ConfigError, ThoughtForgeError)

        assert issubclass(BackendUnavailableError, BackendError)
        assert issubclass(BackendTimeoutError, BackendError)
        assert issubclass(BackendAuthError, BackendError)
        assert issubclass(ModelNotFoundError, BackendError)
        assert issubclass(BackendError, ThoughtForgeError)

        assert issubclass(DatabaseCorruptError, KnowledgeError)
        assert issubclass(DatabaseLockedError, KnowledgeError)
        assert issubclass(RetrievalError, KnowledgeError)
        assert issubclass(KnowledgeError, ThoughtForgeError)

        assert issubclass(MemoryFileCorruptError, MemoryStoreError)
        assert issubclass(MemoryWriteError, MemoryStoreError)
        assert issubclass(MemoryStoreError, ThoughtForgeError)

        assert issubclass(ScaffoldError, PipelineError)
        assert issubclass(EnforcementError, PipelineError)
        assert issubclass(PipelineError, ThoughtForgeError)

    def test_all_carry_recoverable(self):
        for cls in (
            ConfigMissingError, ConfigCorruptError,
            BackendUnavailableError, BackendTimeoutError,
            ModelNotFoundError, DatabaseCorruptError, DatabaseLockedError,
            RetrievalError, MemoryFileCorruptError,
        ):
            exc = cls("test")
            assert isinstance(exc.recoverable, bool)

    def test_all_carry_suggested_fix(self):
        for cls in (
            ConfigMissingError, ConfigCorruptError,
            BackendUnavailableError, BackendTimeoutError,
            ModelNotFoundError, DatabaseCorruptError, DatabaseLockedError,
            RetrievalError, MemoryFileCorruptError,
        ):
            exc = cls("test")
            assert isinstance(exc.suggested_fix, str)

    def test_unrecoverable_types(self):
        assert BackendAuthError("x").recoverable is False
        assert MemoryWriteError("x").recoverable is False
        assert EnforcementError("x").recoverable is False

    def test_recoverable_types(self):
        assert ConfigMissingError("x").recoverable is True
        assert BackendUnavailableError("x").recoverable is True
        assert DatabaseCorruptError("x").recoverable is True


# ── Backoff strategies ─────────────────────────────────────────────────────────

class TestBackoffStrategies:
    def test_exponential_grows(self):
        f = exponential(base=0.5, max_wait=100.0, jitter=False)
        assert f(0) == pytest.approx(0.5)
        assert f(1) == pytest.approx(1.0)
        assert f(2) == pytest.approx(2.0)

    def test_exponential_capped(self):
        f = exponential(base=1.0, max_wait=3.0, jitter=False)
        assert f(10) == pytest.approx(3.0)

    def test_linear_grows(self):
        f = linear(step=1.0, max_wait=100.0)
        assert f(0) == pytest.approx(1.0)
        assert f(1) == pytest.approx(2.0)
        assert f(9) == pytest.approx(10.0)

    def test_fixed_constant(self):
        f = fixed(seconds=2.5)
        assert f(0) == pytest.approx(2.5)
        assert f(5) == pytest.approx(2.5)


# ── @retry decorator ──────────────────────────────────────────────────────────

class TestRetryDecorator:
    def test_succeeds_first_try(self):
        calls = []

        @retry(attempts=3, backoff=fixed(0), on=(ValueError,))
        def fn():
            calls.append(1)
            return "ok"

        assert fn() == "ok"
        assert len(calls) == 1

    def test_retries_then_succeeds(self):
        calls = []

        @retry(attempts=3, backoff=fixed(0), on=(ValueError,))
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "done"

        assert fn() == "done"
        assert len(calls) == 3

    def test_exhausts_and_raises(self):
        @retry(attempts=3, backoff=fixed(0), on=(ValueError,))
        def fn():
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            fn()

    def test_fallback_returned_on_exhaustion(self):
        @retry(attempts=2, backoff=fixed(0), on=(ValueError,), fallback="fallback_val")
        def fn():
            raise ValueError("fail")

        assert fn() == "fallback_val"

    def test_unregistered_exception_not_caught(self):
        @retry(attempts=3, backoff=fixed(0), on=(ValueError,))
        def fn():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            fn()

    def test_retry_count_logged(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="thoughtforge.utils.retry"):
            @retry(attempts=2, backoff=fixed(0), on=(RuntimeError,))
            def fn():
                raise RuntimeError("boom")

            with pytest.raises(RuntimeError):
                fn()

        assert any("attempt" in r.message.lower() for r in caplog.records)


# ── CircuitBreaker ────────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_half_opens_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        # Access .state to trigger transition
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_on_half_open_success(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        _ = cb.state   # trigger HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._failures == 0

    def test_reopens_on_half_open_failure(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        _ = cb.state   # trigger HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_circuit_open_error_raised(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=999)
        cb.record_failure()

        @retry(attempts=1, backoff=fixed(0), on=(ValueError,), circuit_breaker=cb)
        def fn():
            return "ok"

        with pytest.raises(CircuitOpenError):
            fn()

    def test_thread_safety(self):
        cb = CircuitBreaker(failure_threshold=50, recovery_timeout=60)
        errors = []

        def hammer():
            try:
                for _ in range(20):
                    cb.record_failure()
                    cb.record_success()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=hammer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# ── sanitise_query ────────────────────────────────────────────────────────────

class TestSanitiseQuery:
    def test_strips_null_bytes(self):
        assert "\x00" not in sanitise_query("hello\x00world")

    def test_strips_control_chars(self):
        result = sanitise_query("hello\x01\x02\x03world")
        for ch in "\x01\x02\x03":
            assert ch not in result

    def test_preserves_newlines(self):
        # Newlines are preserved (multiline queries); tabs are normalised to spaces
        text = "line1\nline2"
        result = sanitise_query(text)
        assert "\n" in result

    def test_truncates_at_4096(self):
        long_text = "x" * 5000
        assert len(sanitise_query(long_text)) <= 4096

    def test_strips_whitespace(self):
        assert sanitise_query("  hello  ") == "hello"

    def test_collapses_runs_of_spaces(self):
        result = sanitise_query("hello    world")
        assert "  " not in result

    def test_non_string_coerced(self):
        result = sanitise_query(42)  # type: ignore[arg-type]
        assert result == "42"

    def test_empty_string_ok(self):
        assert sanitise_query("") == ""

    def test_unicode_normalised(self):
        # NFC: composed form
        import unicodedata
        result = sanitise_query("caf\u00e9")  # é precomposed
        assert unicodedata.is_normalized("NFC", result)
