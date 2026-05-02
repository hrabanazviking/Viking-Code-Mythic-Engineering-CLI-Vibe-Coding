"""Tests for PH-17 Slice 17.2 — narrow-layout detection."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from mythic_vibe_cli.surfaces.narrow_layout import (
    FORCE_NARROW_ENV,
    NARROW_LAYOUT_THRESHOLD,
    detect_columns,
    is_force_narrow_env,
    should_use_narrow_layout,
)


class DetectColumnsTests(unittest.TestCase):
    def test_returns_int(self) -> None:
        cols = detect_columns()
        self.assertIsInstance(cols, int)
        self.assertGreater(cols, 0)

    def test_fallback_used_on_oserror(self) -> None:
        with mock.patch(
            "shutil.get_terminal_size", side_effect=OSError("no terminal")
        ):
            self.assertEqual(detect_columns(fallback=42), 42)


class IsForceNarrowEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(FORCE_NARROW_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(FORCE_NARROW_ENV, None)
        if self._previous is not None:
            os.environ[FORCE_NARROW_ENV] = self._previous

    def test_default_false(self) -> None:
        self.assertFalse(is_force_narrow_env())

    def test_truthy_values(self) -> None:
        for raw in ("1", "true", "yes", "on", "TRUE"):
            os.environ[FORCE_NARROW_ENV] = raw
            self.assertTrue(is_force_narrow_env(), f"failed for {raw!r}")

    def test_falsy_values(self) -> None:
        for raw in ("0", "false", "no", "off", "garbage"):
            os.environ[FORCE_NARROW_ENV] = raw
            self.assertFalse(is_force_narrow_env(), f"failed for {raw!r}")


class ShouldUseNarrowLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(FORCE_NARROW_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(FORCE_NARROW_ENV, None)
        if self._previous is not None:
            os.environ[FORCE_NARROW_ENV] = self._previous

    def test_below_threshold_returns_true(self) -> None:
        self.assertTrue(should_use_narrow_layout(columns=40))
        self.assertTrue(should_use_narrow_layout(columns=NARROW_LAYOUT_THRESHOLD - 1))

    def test_at_or_above_threshold_returns_false(self) -> None:
        self.assertFalse(should_use_narrow_layout(columns=NARROW_LAYOUT_THRESHOLD))
        self.assertFalse(should_use_narrow_layout(columns=120))

    def test_force_env_overrides_wide_terminal(self) -> None:
        os.environ[FORCE_NARROW_ENV] = "1"
        self.assertTrue(should_use_narrow_layout(columns=200))

    def test_custom_threshold(self) -> None:
        self.assertTrue(should_use_narrow_layout(columns=50, threshold=60))
        self.assertFalse(should_use_narrow_layout(columns=70, threshold=60))


class ConstantsTests(unittest.TestCase):
    def test_threshold_is_78(self) -> None:
        # Tuned for mobile SSH clients leaving room for a 2-col gutter.
        self.assertEqual(NARROW_LAYOUT_THRESHOLD, 78)


# ---- Phase 19.0 / L-8 (audit remediation 2026-05-02) -----------------
#
# should_use_narrow_layout used to be exported in __all__ and tested
# but never imported by any production module — a dead integration
# point per the audit. It's now wired into MythicTuiApp.__init__ so
# the TUI knows at startup whether to render its narrow / mobile
# variant. These tests lock the wire-up.


textual_unavailable = False
try:
    import textual  # noqa: F401
except ImportError:
    textual_unavailable = True


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiAppNarrowModeWireUpTests(unittest.TestCase):
    """``MythicTuiApp.__init__`` calls ``should_use_narrow_layout``
    and stores the result as ``self.narrow_mode``."""

    def test_narrow_mode_attribute_present(self) -> None:
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.tui.app import MythicTuiApp

        with tempfile.TemporaryDirectory() as tmp:
            app = MythicTuiApp(Path(tmp))
        self.assertIsInstance(app.narrow_mode, bool)

    def test_force_narrow_env_sets_narrow_mode_true(self) -> None:
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.tui.app import MythicTuiApp

        with mock.patch.dict(os.environ, {FORCE_NARROW_ENV: "1"}, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
        self.assertTrue(app.narrow_mode)

    def test_force_narrow_env_off_consults_terminal_size(self) -> None:
        """When the env override is off, narrow_mode reflects the
        live terminal-size probe. We patch should_use_narrow_layout
        to a known value to make the assertion deterministic."""
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.tui.app import MythicTuiApp

        with mock.patch.dict(os.environ, {FORCE_NARROW_ENV: ""}, clear=False), \
             mock.patch(
            "mythic_vibe_cli.surfaces.narrow_layout.should_use_narrow_layout",
            return_value=True,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
            self.assertTrue(app.narrow_mode)

        with mock.patch.dict(os.environ, {FORCE_NARROW_ENV: ""}, clear=False), \
             mock.patch(
            "mythic_vibe_cli.surfaces.narrow_layout.should_use_narrow_layout",
            return_value=False,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
            self.assertFalse(app.narrow_mode)


if __name__ == "__main__":
    unittest.main()
