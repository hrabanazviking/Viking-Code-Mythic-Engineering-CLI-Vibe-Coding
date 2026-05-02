"""Phase 19.0 / BS-6 (audit remediation 2026-05-02) — cross-process
file lock tests.

Covers ``runtime/cross_process_lock.py`` (new module) and the
opt-in ``cross_process=True`` flag on
``persistence/json_store.py:FileLock``.

Cross-platform: works on POSIX (``fcntl.flock``) and Windows
(``msvcrt.locking``). The CI OS matrix at slice 19.3 will exercise
both paths post-implementation; here we test what runs on the
build platform.
"""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from mythic_vibe_cli.runtime.cross_process_lock import (
    CrossProcessLockTimeoutError,
    DEFAULT_DEADLINE_SECONDS,
    DEFAULT_POLL_INTERVAL,
    cross_process_lock,
)


class CrossProcessLockBasicTests(unittest.TestCase):
    """Basic acquire / release / re-acquire semantics on the
    current platform (auto-detected via os.name)."""

    def test_default_constants(self) -> None:
        self.assertEqual(DEFAULT_DEADLINE_SECONDS, 30.0)
        self.assertEqual(DEFAULT_POLL_INTERVAL, 0.05)

    def test_acquire_release_re_acquire(self) -> None:
        """Sequential lock acquisitions on the same path must
        succeed once the previous holder releases."""
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "test.lock"
            with cross_process_lock(lock_path, deadline=2.0):
                pass  # acquire + release
            # Re-acquire after release: must work.
            with cross_process_lock(lock_path, deadline=2.0):
                pass

    def test_lock_file_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "subdir" / "test.lock"
            self.assertFalse(lock_path.exists())
            with cross_process_lock(lock_path, deadline=2.0):
                self.assertTrue(lock_path.exists())
            # Lock file remains after release (intentional — no
            # need to delete; subsequent acquires reuse it).
            self.assertTrue(lock_path.exists())

    def test_parent_directory_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "deep" / "nested" / "test.lock"
            self.assertFalse(lock_path.parent.exists())
            with cross_process_lock(lock_path, deadline=2.0):
                pass
            self.assertTrue(lock_path.parent.exists())


class CrossProcessLockContentionTests(unittest.TestCase):
    """When one holder has the lock, another acquisition either
    blocks until released or raises CrossProcessLockTimeoutError
    once the deadline expires."""

    def test_thread_contention_blocks_until_release(self) -> None:
        """Thread A acquires, Thread B requests with a generous
        deadline. B blocks until A releases, then completes."""
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "contended.lock"
            sequence: list[str] = []
            release_event = threading.Event()

            def holder():
                with cross_process_lock(lock_path, deadline=5.0):
                    sequence.append("holder-acquired")
                    # Wait for the test to signal release.
                    release_event.wait(timeout=2.0)
                    sequence.append("holder-releasing")

            def waiter():
                # Give the holder a moment to acquire first.
                time.sleep(0.1)
                with cross_process_lock(
                    lock_path, deadline=5.0, poll_interval=0.05
                ):
                    sequence.append("waiter-acquired")

            holder_thread = threading.Thread(target=holder)
            waiter_thread = threading.Thread(target=waiter)
            holder_thread.start()
            waiter_thread.start()
            # Let the waiter spin a bit on contention, then release.
            time.sleep(0.3)
            release_event.set()
            holder_thread.join(timeout=3.0)
            waiter_thread.join(timeout=3.0)

        self.assertEqual(
            sequence,
            ["holder-acquired", "holder-releasing", "waiter-acquired"],
        )

    def test_short_deadline_raises_timeout_error(self) -> None:
        """If the lock is held for longer than the waiter's
        deadline, the waiter raises CrossProcessLockTimeoutError."""
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "timeout.lock"
            release_event = threading.Event()
            timeout_raised = threading.Event()

            def holder():
                with cross_process_lock(lock_path, deadline=5.0):
                    # Hold longer than the waiter's deadline.
                    release_event.wait(timeout=2.0)

            def waiter():
                time.sleep(0.1)  # let holder acquire first
                try:
                    with cross_process_lock(
                        lock_path, deadline=0.3, poll_interval=0.05
                    ):
                        pass
                except CrossProcessLockTimeoutError:
                    timeout_raised.set()

            holder_thread = threading.Thread(target=holder)
            waiter_thread = threading.Thread(target=waiter)
            holder_thread.start()
            waiter_thread.start()
            waiter_thread.join(timeout=3.0)
            self.assertTrue(timeout_raised.is_set())
            release_event.set()
            holder_thread.join(timeout=3.0)

    def test_timeout_error_subclasses_timeout_error(self) -> None:
        """Operators catching ``TimeoutError`` (or its parent
        ``OSError``) get the cross-process timeout naturally."""
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "subclass.lock"
            release_event = threading.Event()

            def holder():
                with cross_process_lock(lock_path, deadline=5.0):
                    release_event.wait(timeout=2.0)

            holder_thread = threading.Thread(target=holder)
            holder_thread.start()
            try:
                time.sleep(0.1)
                # Catch as TimeoutError (parent class) — must work.
                with self.assertRaises(TimeoutError):
                    with cross_process_lock(
                        lock_path, deadline=0.2, poll_interval=0.05
                    ):
                        pass
            finally:
                release_event.set()
                holder_thread.join(timeout=3.0)


class CrossProcessLockExceptionSafetyTests(unittest.TestCase):
    """The lock must release even when the body raises."""

    def test_lock_released_when_body_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "exception.lock"

            class _BodyError(Exception):
                pass

            with self.assertRaises(_BodyError):
                with cross_process_lock(lock_path, deadline=2.0):
                    raise _BodyError("simulated body failure")

            # If the lock didn't release, this would block / time out.
            with cross_process_lock(lock_path, deadline=2.0):
                pass


class FileLockCrossProcessOptInTests(unittest.TestCase):
    """The ``persistence/json_store.py:FileLock`` gained an
    additive ``cross_process=True`` opt-in (Phase 19.0 / BS-6).
    Default behaviour (legacy O_EXCL lockfile) is unchanged for
    existing callers."""

    def test_default_uses_legacy_o_excl_path(self) -> None:
        from mythic_vibe_cli.persistence.json_store import FileLock

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "legacy.lock"
            with FileLock(lock_path) as lock:
                # Legacy mode: file handle stored.
                self.assertIsNotNone(lock._handle)
                self.assertIsNone(lock._cross_process_cm)
            # Legacy mode unlinks the lockfile on release.
            self.assertFalse(lock_path.exists())

    def test_opt_in_uses_cross_process_lock(self) -> None:
        from mythic_vibe_cli.persistence.json_store import FileLock

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "modern.lock"
            with FileLock(lock_path, cross_process=True) as lock:
                # OS-lock mode: cm stored, no file handle.
                self.assertIsNotNone(lock._cross_process_cm)
                self.assertIsNone(lock._handle)
            # OS-lock mode does NOT unlink (subsequent acquires
            # reuse the file).
            self.assertTrue(lock_path.exists())

    def test_opt_in_acquire_release_re_acquire(self) -> None:
        from mythic_vibe_cli.persistence.json_store import FileLock

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "reuse.lock"
            with FileLock(lock_path, cross_process=True):
                pass
            with FileLock(lock_path, cross_process=True):
                pass

    def test_opt_in_timeout_surfaces_cross_process_timeout(self) -> None:
        """When the opt-in mode times out, the underlying
        CrossProcessLockTimeoutError propagates."""
        from mythic_vibe_cli.persistence.json_store import FileLock

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "timeout.lock"
            release_event = threading.Event()

            def holder():
                with FileLock(
                    lock_path, cross_process=True, timeout_seconds=5.0
                ):
                    release_event.wait(timeout=2.0)

            holder_thread = threading.Thread(target=holder)
            holder_thread.start()
            try:
                time.sleep(0.1)
                with self.assertRaises(CrossProcessLockTimeoutError):
                    with FileLock(
                        lock_path, cross_process=True, timeout_seconds=0.2
                    ):
                        pass
            finally:
                release_event.set()
                holder_thread.join(timeout=3.0)


class ForgeLedgerCrossProcessIntegrationTests(unittest.TestCase):
    """forge_ledger.py was rewired in BS-6 to use
    ``cross_process_lock`` alongside the existing
    ``file_mutation_queue``. Verify the integration."""

    def test_ledger_creates_sidecar_lock_file(self) -> None:
        from mythic_vibe_cli.forge_ledger import ForgeLedger
        from tests.test_forge_ledger import _make_entry

        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry())
            # Lock sidecar file created.
            self.assertTrue(ledger._lock_path.exists())
            # Lock path is target + .lock suffix.
            self.assertEqual(
                str(ledger._lock_path),
                str(ledger.path) + ".lock",
            )

    def test_concurrent_appends_still_serialize(self) -> None:
        """The cross-process lock layered on top of the existing
        file_mutation_queue must not break intra-process
        concurrent appends. All entries should land."""
        from mythic_vibe_cli.forge_ledger import ForgeLedger
        from tests.test_forge_ledger import _make_entry

        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            errors: list[Exception] = []

            def writer(i: int) -> None:
                try:
                    ledger.append(_make_entry(step_id=f"step-{i:04d}"))
                except Exception as exc:  # noqa: BLE001 — test surface
                    errors.append(exc)

            threads = [
                threading.Thread(target=writer, args=(i,))
                for i in range(15)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            entries = ledger.load()
            self.assertEqual(len(entries), 15)


if __name__ == "__main__":
    unittest.main()
