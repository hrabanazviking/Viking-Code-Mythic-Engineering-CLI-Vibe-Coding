"""Phase 19.0 / L-10 (audit remediation 2026-05-02) — atomic_write
helper tests.

Covers ``runtime/atomic_write.py:atomic_write_text`` — the helper
that artifact-writing call-sites in verify/, handoff.py, and
forge_reflection.py now route through to avoid kill-mid-write
truncation.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.runtime.atomic_write import atomic_write_text
import mythic_vibe_cli.runtime.atomic_write as _mod


class AtomicWriteHappyPathTests(unittest.TestCase):
    def test_writes_text_to_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            atomic_write_text(path, "hello world")
            self.assertEqual(path.read_text(encoding="utf-8"), "hello world")

    def test_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deep" / "nested" / "out.txt"
            self.assertFalse(path.parent.exists())
            atomic_write_text(path, "ok")
            self.assertTrue(path.exists())

    def test_overwrites_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            path.write_text("original", encoding="utf-8")
            atomic_write_text(path, "replacement")
            self.assertEqual(
                path.read_text(encoding="utf-8"), "replacement"
            )

    def test_supports_alternative_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            atomic_write_text(path, "café", encoding="latin-1")
            self.assertEqual(
                path.read_text(encoding="latin-1"), "café"
            )


class AtomicWriteAtomicityTests(unittest.TestCase):
    def test_uses_unique_tmp_suffix(self) -> None:
        """Each write produces a unique .tmp filename so two
        sequential writes never collide on a stale handle."""
        seen_tmp_paths: list[str] = []

        os_replace_real = _mod.os.replace

        def _capturing_replace(src, dst):
            seen_tmp_paths.append(str(src))
            os_replace_real(src, dst)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            with mock.patch.object(
                _mod.os, "replace", side_effect=_capturing_replace
            ):
                atomic_write_text(path, "a")
                atomic_write_text(path, "b")
                atomic_write_text(path, "c")

        self.assertEqual(len(seen_tmp_paths), 3)
        self.assertEqual(len(set(seen_tmp_paths)), 3)
        for tmp_path in seen_tmp_paths:
            self.assertTrue(tmp_path.endswith(".tmp"))

    def test_kill_mid_write_preserves_prior_file(self) -> None:
        """Simulate a kill between tmp write and os.replace. The
        prior good file must remain intact and readable."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            atomic_write_text(path, "version-1")
            prior = path.read_text(encoding="utf-8")

            with mock.patch.object(
                _mod.os, "replace", side_effect=KeyboardInterrupt
            ):
                with self.assertRaises(KeyboardInterrupt):
                    atomic_write_text(path, "version-2")

            after = path.read_text(encoding="utf-8")
            self.assertEqual(after, prior)
            self.assertEqual(after, "version-1")

    def test_tmp_file_cleaned_up_on_failure(self) -> None:
        """Failed writes should not leave .tmp orphans behind."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"

            with mock.patch.object(
                _mod.os, "replace", side_effect=KeyboardInterrupt
            ):
                with self.assertRaises(KeyboardInterrupt):
                    atomic_write_text(path, "data")

            tmp_files = list(Path(tmp).glob("out.txt.*.tmp"))
            self.assertEqual(
                tmp_files, [],
                f"Found orphan tmp files: {tmp_files!r}",
            )


class AtomicWriteRetryTests(unittest.TestCase):
    """The Windows-specific PermissionError retry loop."""

    def test_retries_on_permission_error_and_eventually_succeeds(self) -> None:
        attempt_count = {"n": 0}
        succeeded = {"v": False}

        def _flaky_replace(src, dst):
            attempt_count["n"] += 1
            if attempt_count["n"] < 3:
                raise PermissionError("simulated antivirus contention")
            succeeded["v"] = True

        with mock.patch.object(_mod.os, "replace", side_effect=_flaky_replace):
            with tempfile.TemporaryDirectory() as tmp:
                atomic_write_text(
                    Path(tmp) / "out.txt", "data",
                    retries=5, base_delay=0.001,
                )

        self.assertEqual(attempt_count["n"], 3)
        self.assertTrue(succeeded["v"])

    def test_gives_up_after_retries_exhausted(self) -> None:
        with mock.patch.object(
            _mod.os, "replace",
            side_effect=PermissionError("persistent"),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(PermissionError):
                    atomic_write_text(
                        Path(tmp) / "out.txt", "data",
                        retries=3, base_delay=0.001,
                    )

    def test_non_permission_error_propagates_immediately(self) -> None:
        """Errors other than PermissionError should NOT trigger
        the retry loop — they propagate immediately."""
        attempt_count = {"n": 0}

        def _failing_replace(src, dst):
            attempt_count["n"] += 1
            raise OSError("disk full")

        with mock.patch.object(
            _mod.os, "replace", side_effect=_failing_replace
        ):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(OSError):
                    atomic_write_text(
                        Path(tmp) / "out.txt", "data",
                        retries=5, base_delay=0.001,
                    )

        # Only 1 attempt — no retry on non-PermissionError.
        self.assertEqual(attempt_count["n"], 1)


# ---------------------------------------------------------------------------
# PH-24.3 hardening — exercise the cleanup branch when ``tmp.unlink``
# itself fails after a write failure. The OSError on unlink is silently
# swallowed (tmp file is best-effort), but the original write error must
# still propagate.
# ---------------------------------------------------------------------------


class AtomicWriteCleanupHardeningTests(unittest.TestCase):
    def test_unlink_failure_is_swallowed_but_original_error_propagates(self) -> None:
        """When the write fails AND the .tmp unlink also fails, the
        original write error must still surface. The OSError from
        unlink is best-effort cleanup and must not mask the cause."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"

            def _failing_replace(src, dst):  # noqa: ANN001
                raise PermissionError("disk full mid-replace")

            def _failing_unlink(self):  # noqa: ANN001
                raise OSError("simulated unlink failure")

            with mock.patch.object(
                _mod.os, "replace", side_effect=_failing_replace
            ):
                with mock.patch.object(Path, "unlink", _failing_unlink):
                    with self.assertRaises(PermissionError) as cm:
                        atomic_write_text(
                            target, "data",
                            retries=1, base_delay=0.001,
                        )
            # The original PermissionError, not the swallowed OSError.
            self.assertIn("disk full", str(cm.exception))

    def test_write_failure_cleans_up_tmp_when_unlink_succeeds(self) -> None:
        """When write fails, the .tmp file should not be left behind."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"

            def _failing_replace(src, dst):  # noqa: ANN001
                raise OSError("disk full")

            with mock.patch.object(
                _mod.os, "replace", side_effect=_failing_replace
            ):
                with self.assertRaises(OSError):
                    atomic_write_text(
                        target, "data",
                        retries=1, base_delay=0.001,
                    )
            # No leftover .tmp files in the directory.
            leftover = list(Path(tmp).glob("*.tmp"))
            self.assertEqual(leftover, [])


if __name__ == "__main__":
    unittest.main()
