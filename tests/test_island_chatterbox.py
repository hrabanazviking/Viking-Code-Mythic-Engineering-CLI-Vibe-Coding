"""Tests for Island E (Chatterbox) — PH-09 Slice 9.4 formalisation.

Locks in the new per-island feature flag and parity with Islands
B / C / D. Existing PH-07 chatterbox tests live in test_voice.py
and continue to pass unchanged (the stub engine path was not
affected).
"""

from __future__ import annotations

import io
import os
import unittest
from unittest import mock

from mythic_vibe_cli.voice.tts import (
    CHATTERBOX_ISLAND_ENV,
    TTS_ENABLED_ENV,
    StubTTSEngine,
    is_chatterbox_island_enabled,
    say,
)


class IsIslandEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(CHATTERBOX_ISLAND_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(CHATTERBOX_ISLAND_ENV, None)
        if self._previous is not None:
            os.environ[CHATTERBOX_ISLAND_ENV] = self._previous

    def test_default_off(self) -> None:
        self.assertFalse(is_chatterbox_island_enabled())

    def test_truthy_values(self) -> None:
        for raw in ("1", "true", "yes", "on", "TRUE"):
            os.environ[CHATTERBOX_ISLAND_ENV] = raw
            self.assertTrue(
                is_chatterbox_island_enabled(), f"failed for {raw!r}"
            )

    def test_falsy_values(self) -> None:
        for raw in ("0", "false", "no", "", "off"):
            os.environ[CHATTERBOX_ISLAND_ENV] = raw
            self.assertFalse(
                is_chatterbox_island_enabled(), f"failed for {raw!r}"
            )


class SayChatterboxGatingTests(unittest.TestCase):
    """The chatterbox engine emits audio only when BOTH the broader
    TTS flag and the per-island flag are on. Stub engine behaviour
    is unchanged."""

    def setUp(self) -> None:
        self._previous_tts = os.environ.pop(TTS_ENABLED_ENV, None)
        self._previous_island = os.environ.pop(CHATTERBOX_ISLAND_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(TTS_ENABLED_ENV, None)
        os.environ.pop(CHATTERBOX_ISLAND_ENV, None)
        if self._previous_tts is not None:
            os.environ[TTS_ENABLED_ENV] = self._previous_tts
        if self._previous_island is not None:
            os.environ[CHATTERBOX_ISLAND_ENV] = self._previous_island

    def test_stub_engine_unaffected_by_island_flag(self) -> None:
        """Stub engine still works with only the broader TTS flag —
        the new island flag does not gate stub."""
        os.environ[TTS_ENABLED_ENV] = "1"
        # Island flag intentionally NOT set.
        buf = io.StringIO()
        stub = StubTTSEngine(stream=buf)
        result = say("hello", tts_engine=stub)
        self.assertIn("hello", buf.getvalue())
        # Stub never spoken=True, but it was invoked (no skip).
        self.assertNotIn("disabled", result.skipped_reason)

    def test_chatterbox_blocked_when_island_flag_off(self) -> None:
        """Broader flag on, island flag off → chatterbox skips."""
        os.environ[TTS_ENABLED_ENV] = "1"
        # Use a mock chatterbox engine to confirm say() never reaches it.
        mock_engine = mock.MagicMock()
        result = say("hi", engine="chatterbox", tts_engine=mock_engine)
        self.assertFalse(result.spoken)
        self.assertIn("Chatterbox island disabled", result.skipped_reason)
        self.assertIn(CHATTERBOX_ISLAND_ENV, result.skipped_reason)
        mock_engine.say.assert_not_called()

    def test_chatterbox_blocked_when_broader_flag_off(self) -> None:
        """Broader flag off → chatterbox skips with the broader-flag
        message, regardless of island flag."""
        os.environ[CHATTERBOX_ISLAND_ENV] = "1"  # island on but broader off
        mock_engine = mock.MagicMock()
        result = say("hi", engine="chatterbox", tts_engine=mock_engine)
        self.assertFalse(result.spoken)
        self.assertIn(TTS_ENABLED_ENV, result.skipped_reason)
        mock_engine.say.assert_not_called()

    def test_chatterbox_dispatches_when_both_flags_on(self) -> None:
        """Both flags on → orchestrator reaches the engine."""
        os.environ[TTS_ENABLED_ENV] = "1"
        os.environ[CHATTERBOX_ISLAND_ENV] = "1"

        # Inject a fake engine to confirm it was called.
        mock_engine = mock.MagicMock()
        from mythic_vibe_cli.voice.tts import TTSResult

        mock_engine.say.return_value = TTSResult(
            text="hi", engine="chatterbox", spoken=True
        )
        result = say("hi", engine="chatterbox", tts_engine=mock_engine)

        mock_engine.say.assert_called_once()
        self.assertTrue(result.spoken)

    def test_force_bypasses_both_flags(self) -> None:
        """force=True bypasses both gates — used by ad-hoc CLI calls
        that need to test the engine path directly."""
        # Both flags off.
        mock_engine = mock.MagicMock()
        from mythic_vibe_cli.voice.tts import TTSResult

        mock_engine.say.return_value = TTSResult(
            text="hi", engine="chatterbox", spoken=True
        )
        result = say(
            "hi", engine="chatterbox", force=True, tts_engine=mock_engine
        )

        mock_engine.say.assert_called_once()
        self.assertTrue(result.spoken)


class BackwardsCompatTests(unittest.TestCase):
    """Make sure the formalisation didn't break the PH-07 stub-only
    workflow that operators may already be using."""

    def setUp(self) -> None:
        self._previous_tts = os.environ.pop(TTS_ENABLED_ENV, None)
        self._previous_island = os.environ.pop(CHATTERBOX_ISLAND_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(TTS_ENABLED_ENV, None)
        os.environ.pop(CHATTERBOX_ISLAND_ENV, None)
        if self._previous_tts is not None:
            os.environ[TTS_ENABLED_ENV] = self._previous_tts
        if self._previous_island is not None:
            os.environ[CHATTERBOX_ISLAND_ENV] = self._previous_island

    def test_stub_engine_no_island_flag_required(self) -> None:
        """Stub engine should never need the island flag, broader
        flag or force=True alone is enough."""
        # Force path
        buf = io.StringIO()
        stub = StubTTSEngine(stream=buf)
        result = say("test", engine="stub", force=True, tts_engine=stub)
        self.assertIn("test", buf.getvalue())
        self.assertNotIn("disabled", result.skipped_reason or "")

    def test_default_disabled_message_unchanged(self) -> None:
        """When everything is off, the default skip message still
        names the broader flag (the operator's first lever)."""
        result = say("hi", engine="stub")
        self.assertFalse(result.spoken)
        self.assertIn(TTS_ENABLED_ENV, result.skipped_reason)


if __name__ == "__main__":
    unittest.main()
