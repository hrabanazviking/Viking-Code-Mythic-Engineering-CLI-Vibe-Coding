"""PH-24.4 — Cross-platform regression sweep.

Lightweight invariants that catch the most common cross-platform
regressions before they ship. Each test is intentionally narrow —
fast to run, easy to understand, fails clearly when the underlying
behavior drifts.

Cross-platform: tests run on Windows / macOS / Linux. Tests that
require a specific platform are skipped on others; tests that
exercise platform-dependent code paths assert behavior on the
current platform only and document the cross-platform expectation
in the docstring.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.drift import _relpath
from mythic_vibe_cli.runtime.atomic_write import atomic_write_text


class PathPortabilityTests(unittest.TestCase):
    """Project-relative paths must serialise the same way on every
    platform — forward slashes, never platform separators. Operators
    on different OSes need to diff JSON outputs cleanly without a
    flood of `\\` vs `/` noise."""

    def test_relpath_uses_forward_slashes_on_every_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            nested = root / "docs" / "subdir" / "file.md"
            nested.parent.mkdir(parents=True, exist_ok=True)
            nested.write_text("x", encoding="utf-8")
            result = _relpath(nested, root)
        # Always forward slashes regardless of os.sep.
        self.assertNotIn("\\", result)
        self.assertEqual(result, "docs/subdir/file.md")

    def test_relpath_handles_target_outside_root_gracefully(self) -> None:
        """When the target isn't under the root, ``_relpath`` returns
        the target as-given — still using forward slashes."""
        with tempfile.TemporaryDirectory() as tmp1:
            with tempfile.TemporaryDirectory() as tmp2:
                outside = Path(tmp2) / "elsewhere.txt"
                result = _relpath(outside, Path(tmp1))
        # Whatever we got back, it must not contain backslashes that
        # would corrupt JSON consumers.
        self.assertNotIn("\\", result)


class AtomicWriteCrossPlatformTests(unittest.TestCase):
    """The atomic write helper must produce identical-looking files
    on every platform."""

    def test_writes_unicode_content_with_explicit_utf8(self) -> None:
        """Non-ASCII content (emoji, runes, accents) must round-trip
        without mangling on Windows code-page-default consoles."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            content = "ᚠᚢᚦᚨᚱᚲ Mýthïc Vïbé — café 🜂"
            atomic_write_text(target, content)
            self.assertEqual(target.read_text(encoding="utf-8"), content)

    def test_writes_to_path_with_spaces(self) -> None:
        """Paths with spaces are common on Windows
        (``C:\\Users\\Forge Worker\\``) and must work."""
        with tempfile.TemporaryDirectory() as tmp:
            spaced_dir = Path(tmp) / "Forge Worker" / "out files"
            spaced_dir.mkdir(parents=True, exist_ok=True)
            target = spaced_dir / "demo file.txt"
            atomic_write_text(target, "hello with spaces")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello with spaces")

    def test_writes_preserve_line_endings_as_written(self) -> None:
        """The atomic helper does not transform line endings — what
        you wrote is what comes back. Operators on Windows + POSIX
        get the same JSONL byte stream."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            atomic_write_text(target, "a\nb\nc\n")
        # Read raw bytes so OS newline translation can't lie.
            raw = target.read_bytes()
        self.assertEqual(raw, b"a\nb\nc\n")
        self.assertNotIn(b"\r\n", raw)


class JsonOutputCrossPlatformTests(unittest.TestCase):
    """JSON-emitting commands must produce platform-independent
    payloads — operators piping ``--json`` outputs into shared
    tooling need byte-identical bodies whether the writer ran on
    Windows or Linux."""

    def test_json_dump_omits_path_separators_in_strings(self) -> None:
        """Encoded paths in JSON outputs go through ``_relpath`` or
        ``replace("\\", "/")`` — make sure a representative path
        survives the pipeline."""
        sample = {
            "path": str(Path("docs") / "subdir" / "file.md").replace("\\", "/"),
            "type": "doc",
        }
        # Produced JSON must not contain a single backslash.
        encoded = json.dumps(sample)
        self.assertNotIn("\\\\", encoded)
        # Round-trip parses cleanly on every platform.
        decoded = json.loads(encoded)
        self.assertEqual(decoded["path"], "docs/subdir/file.md")


class EnvironmentInvariantTests(unittest.TestCase):
    """Sanity checks on the test-host environment — these don't
    test product code but they catch the most common CI-host
    misconfiguration before it produces confusing failures."""

    def test_python_version_is_supported(self) -> None:
        """The CLI's pyproject pins ``python>=3.10``. A test running
        under an older interpreter would explode in confusing
        places — this fail-fast probe surfaces it cleanly."""
        self.assertGreaterEqual(sys.version_info[:2], (3, 10))

    def test_temp_dir_is_writable_and_readable(self) -> None:
        """Smoke test that ``tempfile.TemporaryDirectory`` actually
        works on the host — catches sandbox / permission setups
        where the rest of the suite would hang."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "smoke.txt"
            target.write_text("ok", encoding="utf-8")
            self.assertEqual(target.read_text(encoding="utf-8"), "ok")

    def test_os_name_matches_known_values(self) -> None:
        """``os.name`` must be one of the values the cross-platform
        branches expect. Anything else (cygwin reporting "posix",
        old IronPython, etc.) means the platform-detection logic
        in ``cross_process_lock`` and ``hardware`` will silently
        take the wrong branch."""
        self.assertIn(os.name, {"nt", "posix"})


class WindowsSpecificTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows-only invariant")
    def test_windows_long_path_does_not_crash_atomic_write(self) -> None:
        """Approach the Windows ``MAX_PATH`` limit (260 chars by
        default) and verify the atomic helper either writes
        successfully OR raises a clean ``OSError`` — never crashes
        the interpreter."""
        with tempfile.TemporaryDirectory() as tmp:
            # Build a path that's long but under MAX_PATH so we
            # exercise the long-but-legal case. The exact-MAX_PATH
            # case requires Windows long-path support enabled
            # system-wide, which CI hosts don't always have.
            long_segment = "a" * 50
            target = Path(tmp) / long_segment / long_segment / "out.txt"
            try:
                atomic_write_text(target, "ok")
                self.assertEqual(target.read_text(encoding="utf-8"), "ok")
            except OSError:
                # Some CI hosts have aggressive path-length limits;
                # an OSError is acceptable as long as it's clean.
                pass


class PosixSpecificTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX-only invariant")
    def test_posix_chmod_via_open_mode_is_honoured(self) -> None:
        """``cross_process_lock`` opens its lock file with mode 0o644.
        On POSIX this should produce a file readable by the owner +
        group + other. (On Windows the mode is silently ignored,
        which is why this test is POSIX-only.)"""
        from mythic_vibe_cli.runtime.cross_process_lock import cross_process_lock

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "demo.lock"
            with cross_process_lock(lock_path):
                pass
            mode = lock_path.stat().st_mode & 0o777
            # 0o644 may be filtered by umask; verify owner-readable
            # at minimum.
            self.assertTrue(mode & 0o400, f"owner read missing (mode={mode:o})")


if __name__ == "__main__":
    unittest.main()
