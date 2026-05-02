r"""Phase 19.3 (audit remediation 2026-05-02) — long-path
compatibility regression test.

The historical Windows MAX_PATH limit (260 chars) bites
cross-platform Python projects. Modern Win10/11 supports long
paths via either per-app manifest, the ``LongPathsEnabled``
registry key, or the ``\\?\`` UNC prefix on each path.

This test verifies that ``runtime/atomic_write.py`` doesn't add
its own length restriction on top of whatever the OS allows. We
deliberately stay under the 260-char total-path limit AND under
the 255-char per-segment limit to keep the test portable across
Windows configurations — operators who hit the limit have
OS-level toggles to enable long paths; that's not the helper's
responsibility.

POSIX has no MAX_PATH issue; the test runs there too as a
sanity check that long names don't trip up the helper's tmp-
file naming or os.replace.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.runtime.atomic_write import atomic_write_text


class LongPathCompatibilityTests(unittest.TestCase):
    """The atomic-write helper handles long but legal paths
    without choking on tmp-file naming or os.replace."""

    def test_long_filename_round_trip(self) -> None:
        """A single 200-char filename. Well under MAX_PATH but
        long enough to surface any per-name-length assumption."""
        with tempfile.TemporaryDirectory() as tmp:
            long_name = "x" * 200 + ".txt"
            target = Path(tmp) / long_name
            atomic_write_text(target, "long-name-content")
            self.assertEqual(
                target.read_text(encoding="utf-8"), "long-name-content"
            )

    def test_long_filename_uses_unique_tmp_suffix(self) -> None:
        """The tmp filename is target.name + .<hex>.tmp — a long
        ``target.name`` plus the 17-char ``.<12-hex>.tmp`` suffix
        should still produce a single-segment legal filename.
        Windows NTFS has a 255-char per-segment limit, so the
        target.name + 17 must stay ≤ 255 — i.e. ≤ 238 chars
        before the suffix. We test at 220 to leave headroom and
        still surface any regression where the suffix lands the
        tmp name over the limit."""
        with tempfile.TemporaryDirectory() as tmp:
            # 220 chars + ".<12-hex>.tmp" = 237 — under the 255
            # per-segment limit on Windows / Linux / macOS.
            long_name = "x" * 220 + ".txt"
            target = Path(tmp) / long_name
            atomic_write_text(target, "ok")
            # Confirm no orphan tmp files.
            tmp_files = list(Path(tmp).glob("*.tmp"))
            self.assertEqual(tmp_files, [])

    def test_nested_directory_path_within_limit(self) -> None:
        """Three nested 50-char directory segments + 50-char
        filename keeps total well under 260 chars on most
        configurations. Exercises the helper's mkdir parents
        logic on a tall tree."""
        with tempfile.TemporaryDirectory() as tmp:
            seg = "y" * 50
            target = Path(tmp) / seg / seg / seg / "out.txt"
            atomic_write_text(target, "nested")
            self.assertEqual(
                target.read_text(encoding="utf-8"), "nested"
            )

    def test_unicode_filename_round_trip(self) -> None:
        """Non-ASCII filename (Norse-themed!) — exercises the
        path encoding side of long-name handling."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ᚱᚢᚾᚨ_seiðkona.txt"
            atomic_write_text(target, "rúnar")
            self.assertEqual(
                target.read_text(encoding="utf-8"), "rúnar"
            )


if __name__ == "__main__":
    unittest.main()
