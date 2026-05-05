"""Tests for the session-scope leak guard in tests/conftest.py.

PH-23.2 (additive 2026-05-05). The conftest fixtures defend
against tests that leak absolute-path-treated-as-relative debris
into the repo working tree. These tests verify the guard's
detection logic without actually triggering a session failure.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONFTEST = REPO_ROOT / "tests" / "conftest.py"


def _load_conftest():
    """Load tests/conftest.py via importlib so we can inspect its
    private helpers + constants without running the fixtures."""
    spec = importlib.util.spec_from_file_location(
        "_conftest_under_test", str(CONFTEST)
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load {CONFTEST}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LeakNamesCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            CONFTEST.is_file(),
            f"conftest.py missing at {CONFTEST}",
        )
        self.module = _load_conftest()

    def test_users_in_leak_names(self) -> None:
        # The original 2026-05-02 audit-cycle debris was under
        # `Users/volma/AppData/...` — the guard must catch any
        # recurrence.
        self.assertIn("Users", self.module.ABSOLUTE_PATH_LEAK_NAMES)

    def test_covers_posix_absolute_path_leaks(self) -> None:
        # POSIX equivalents of the same class of bug.
        for name in ("private", "var", "tmp"):
            self.assertIn(
                name, self.module.ABSOLUTE_PATH_LEAK_NAMES,
                f"POSIX leak name missing: {name}",
            )

    def test_covers_windows_specific_paths(self) -> None:
        # Other Windows abs-path roots a buggy test might leak.
        for name in ("AppData", "ProgramData"):
            self.assertIn(
                name, self.module.ABSOLUTE_PATH_LEAK_NAMES,
                f"Windows leak name missing: {name}",
            )


class EnumerateLeakDirsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_conftest()

    def test_returns_empty_when_no_leaks(self) -> None:
        # In a clean working tree (which the conftest ensures via
        # the cleanup fixture before tests run), the enumerator
        # returns no findings.
        leaks = self.module._enumerate_leak_dirs()
        self.assertEqual(
            leaks, [],
            f"unexpected leak dirs detected: {leaks}",
        )


class FixtureDecoratorsTests(unittest.TestCase):
    """Smoke that the fixtures are decorated correctly so pytest
    actually applies them session-wide as autouse.

    pytest's internal fixture metadata isn't stable across versions;
    the most reliable structural check is to read the conftest
    source and assert the decorator literal is present at the
    expected position above each fixture function. That stays
    correct regardless of pytest version.
    """

    def setUp(self) -> None:
        self.raw = CONFTEST.read_text(encoding="utf-8")

    def test_detect_fixture_has_session_autouse_decorator(self) -> None:
        # The decorator must appear immediately above the function
        # def. We check both the scope + autouse arguments are
        # present in the decorator line.
        idx = self.raw.find("def detect_absolute_path_leaks(")
        self.assertGreater(
            idx, 0, "detect_absolute_path_leaks function missing",
        )
        # Look for the decorator within the 200 chars before the def.
        prefix = self.raw[max(0, idx - 200): idx]
        self.assertIn('@pytest.fixture', prefix)
        self.assertIn('scope="session"', prefix)
        self.assertIn("autouse=True", prefix)

    def test_cleanup_fixture_has_session_autouse_decorator(self) -> None:
        idx = self.raw.find("def remove_stale_test_debris(")
        self.assertGreater(
            idx, 0, "remove_stale_test_debris function missing",
        )
        prefix = self.raw[max(0, idx - 200): idx]
        self.assertIn('@pytest.fixture', prefix)
        self.assertIn('scope="session"', prefix)
        self.assertIn("autouse=True", prefix)


if __name__ == "__main__":
    unittest.main()
