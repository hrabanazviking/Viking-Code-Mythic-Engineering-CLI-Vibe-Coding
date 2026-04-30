"""Tests for the voice & multimodal surface (PH-07 slices 7.1-7.4)."""

from __future__ import annotations

import argparse
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS
from mythic_vibe_cli.voice.transcribe import (
    DEFAULT_ENGINE,
    KNOWN_ENGINES,
    MissingExtraError,
    StubTranscriber,
    TranscriptionRequest,
    TranscriptionResult,
    WhisperTranscriber,
    make_transcriber,
    transcribe,
)
from mythic_vibe_cli.voice.tts import (
    DEFAULT_TTS_ENGINE,
    KNOWN_TTS_ENGINES,
    TTS_ENABLED_ENV,
    ChatterboxEngine,
    StubTTSEngine,
    TTSRequest,
    TTSResult,
    is_tts_enabled,
    make_tts_engine,
    say,
)


# ---- StubTranscriber (slice 7.1) -------------------------------------


class StubTranscriberTests(unittest.TestCase):
    def test_text_file_contents_returned_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.txt"
            path.write_text("Refactor router into modules", encoding="utf-8")
            req = TranscriptionRequest(source_path=str(path))
            result = StubTranscriber().transcribe(req)
        self.assertEqual(result.text, "Refactor router into modules")
        self.assertTrue(result.dry_run)
        self.assertEqual(result.engine, "stub")

    def test_md_file_treated_as_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "intent.md"
            path.write_text("# Intent\nShip the router", encoding="utf-8")
            req = TranscriptionRequest(source_path=str(path))
            result = StubTranscriber().transcribe(req)
        self.assertIn("Ship the router", result.text)

    def test_binary_file_returns_basename_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.wav"
            path.write_bytes(b"\x00\x01\x02")
            req = TranscriptionRequest(source_path=str(path))
            result = StubTranscriber().transcribe(req)
        self.assertIn("voice.wav", result.text)
        self.assertIn("stub transcript", result.text)

    def test_missing_file_falls_back_to_placeholder(self) -> None:
        req = TranscriptionRequest(source_path="/nonexistent/voice.wav")
        result = StubTranscriber().transcribe(req)
        self.assertIn("stub transcript", result.text)
        self.assertEqual(result.dry_run, True)


# ---- WhisperTranscriber (slice 7.1) ----------------------------------


class WhisperTranscriberTests(unittest.TestCase):
    def test_missing_whisper_dep_raises_missing_extra(self) -> None:
        # Patch the import to fail; constructor should raise.
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def fake_import(name, *args, **kwargs):
            if name == "whisper":
                raise ImportError("simulated absence")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(MissingExtraError) as ctx:
                WhisperTranscriber()
        self.assertEqual(ctx.exception.extra, "openai-whisper")
        self.assertIn("pip install openai-whisper", ctx.exception.install_hint)

    def test_transcribe_via_mocked_module(self) -> None:
        """Inject a fake whisper module via attribute patching so we
        don't need the real package."""
        fake = mock.MagicMock()
        fake_model = mock.MagicMock()
        fake_model.transcribe.return_value = {"text": "  decoded text  "}
        fake.load_model.return_value = fake_model
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audio.wav"
            path.write_bytes(b"")
            wt = WhisperTranscriber.__new__(WhisperTranscriber)
            wt.name = "whisper"
            wt._module = fake
            req = TranscriptionRequest(source_path=str(path), engine="whisper")
            result = wt.transcribe(req)
        self.assertEqual(result.text, "decoded text")
        self.assertFalse(result.dry_run)
        self.assertEqual(result.engine, "whisper")

    def test_missing_source_file_returns_error_result(self) -> None:
        fake = mock.MagicMock()
        wt = WhisperTranscriber.__new__(WhisperTranscriber)
        wt.name = "whisper"
        wt._module = fake
        req = TranscriptionRequest(source_path="/nope.wav", engine="whisper")
        result = wt.transcribe(req)
        self.assertEqual(result.text, "")
        self.assertIn("not found", result.error)


# ---- make_transcriber + transcribe orchestrator ---------------------


class TranscribeFactoryTests(unittest.TestCase):
    def test_default_engine_returns_stub(self) -> None:
        self.assertEqual(DEFAULT_ENGINE, "stub")
        engine = make_transcriber("")
        self.assertIsInstance(engine, StubTranscriber)

    def test_unknown_engine_raises(self) -> None:
        with self.assertRaises(ValueError):
            make_transcriber("hal9000")

    def test_orchestrator_returns_stub_result_when_no_extra(self) -> None:
        # Default engine is stub; no extras needed.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.txt"
            path.write_text("ship router", encoding="utf-8")
            result = transcribe(TranscriptionRequest(source_path=str(path)))
        self.assertEqual(result.text, "ship router")
        self.assertEqual(result.engine, "stub")

    def test_orchestrator_returns_error_result_for_unknown_engine(
        self,
    ) -> None:
        result = transcribe(
            TranscriptionRequest(source_path="x.txt", engine="hal9000")
        )
        self.assertIn("Unknown transcribe engine", result.error)
        self.assertEqual(result.text, "")

    def test_known_engines_constant(self) -> None:
        for required in {"stub", "whisper"}:
            self.assertIn(required, KNOWN_ENGINES)


# ---- TTS (slice 7.3) -------------------------------------------------


class StubTTSEngineTests(unittest.TestCase):
    def test_say_logs_to_stderr_and_returns_unspoken(self) -> None:
        # Inject a custom stream to capture without actually
        # touching stderr.
        buf = io.StringIO()
        engine = StubTTSEngine(stream=buf)
        result = engine.say(TTSRequest(text="hello"))
        self.assertFalse(result.spoken)
        self.assertIn("[voice-stub]", buf.getvalue())
        self.assertIn("hello", buf.getvalue())


class ChatterboxEngineTests(unittest.TestCase):
    def test_missing_chatterbox_raises_missing_extra(self) -> None:
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def fake_import(name, *args, **kwargs):
            if name == "chatterbox":
                raise ImportError("simulated")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(MissingExtraError) as ctx:
                ChatterboxEngine()
        self.assertEqual(ctx.exception.extra, "chatterbox")

    def test_say_uses_module_speak_when_present(self) -> None:
        fake = mock.MagicMock()
        engine = ChatterboxEngine.__new__(ChatterboxEngine)
        engine.name = "chatterbox"
        engine.voice = ""
        engine._module = fake
        result = engine.say(TTSRequest(text="hi", engine="chatterbox"))
        fake.speak.assert_called_once()
        self.assertTrue(result.spoken)

    def test_say_returns_error_when_module_lacks_speak(self) -> None:
        # A module-shaped object with no `speak` attribute.
        class _NoSpeak:
            pass

        engine = ChatterboxEngine.__new__(ChatterboxEngine)
        engine.name = "chatterbox"
        engine.voice = ""
        engine._module = _NoSpeak()
        result = engine.say(TTSRequest(text="hi", engine="chatterbox"))
        self.assertFalse(result.spoken)
        self.assertIn("speak not callable", result.error)


class TTSEnvGateTests(unittest.TestCase):
    def test_disabled_by_default(self) -> None:
        previous = os.environ.pop(TTS_ENABLED_ENV, None)
        try:
            self.assertFalse(is_tts_enabled())
        finally:
            if previous is not None:
                os.environ[TTS_ENABLED_ENV] = previous

    def test_truthy_values_enable(self) -> None:
        previous = os.environ.pop(TTS_ENABLED_ENV, None)
        try:
            for raw in ("1", "true", "yes", "on", "TRUE"):
                os.environ[TTS_ENABLED_ENV] = raw
                self.assertTrue(is_tts_enabled(), f"failed for {raw!r}")
        finally:
            os.environ.pop(TTS_ENABLED_ENV, None)
            if previous is not None:
                os.environ[TTS_ENABLED_ENV] = previous

    def test_falsy_values_keep_disabled(self) -> None:
        previous = os.environ.pop(TTS_ENABLED_ENV, None)
        try:
            for raw in ("0", "false", "no", "", "off", "garbage"):
                os.environ[TTS_ENABLED_ENV] = raw
                self.assertFalse(is_tts_enabled(), f"failed for {raw!r}")
        finally:
            os.environ.pop(TTS_ENABLED_ENV, None)
            if previous is not None:
                os.environ[TTS_ENABLED_ENV] = previous


class SayOrchestratorTests(unittest.TestCase):
    def test_default_disabled_skips_engine(self) -> None:
        previous = os.environ.pop(TTS_ENABLED_ENV, None)
        try:
            tts_engine = mock.MagicMock()
            result = say("hello", tts_engine=tts_engine)
        finally:
            if previous is not None:
                os.environ[TTS_ENABLED_ENV] = previous
        self.assertFalse(result.spoken)
        self.assertIn("TTS disabled", result.skipped_reason)
        tts_engine.say.assert_not_called()

    def test_force_overrides_env_gate(self) -> None:
        previous = os.environ.pop(TTS_ENABLED_ENV, None)
        try:
            buf = io.StringIO()
            stub = StubTTSEngine(stream=buf)
            result = say("hello", tts_engine=stub, force=True)
        finally:
            if previous is not None:
                os.environ[TTS_ENABLED_ENV] = previous
        self.assertFalse(result.spoken)  # stub never speaks
        self.assertIn("hello", buf.getvalue())
        # And the gate was not the reason — the stub was invoked.
        self.assertEqual(result.skipped_reason, "stub engine — no audio emitted")

    def test_factory_handles_unknown_engine(self) -> None:
        result = say("hi", engine="hal9000", force=True)
        self.assertIn("Unknown TTS engine", result.error)

    def test_make_tts_engine_default_returns_stub(self) -> None:
        self.assertEqual(DEFAULT_TTS_ENGINE, "stub")
        engine = make_tts_engine("")
        self.assertIsInstance(engine, StubTTSEngine)
        for known in {"stub", "chatterbox"}:
            self.assertIn(known, KNOWN_TTS_ENGINES)


# ---- argparse ---------------------------------------------------------


class VoiceArgparseTests(unittest.TestCase):
    def test_transcribe_parses(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            ["voice", "transcribe", "--file", "x.txt", "--engine", "stub"]
        )
        self.assertEqual(ns.command, "voice")
        self.assertEqual(ns.voice_command, "transcribe")
        self.assertEqual(ns.file, "x.txt")
        self.assertEqual(ns.engine, "stub")

    def test_transcribe_requires_file(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(["voice", "transcribe"])

    def test_say_parses_text_positional(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["voice", "say", "hello operator"])
        self.assertEqual(ns.text, "hello operator")
        self.assertEqual(ns.engine, "stub")
        self.assertFalse(ns.force)


# ---- cmd_voice_transcribe ---------------------------------------------


class CmdVoiceTranscribeTests(unittest.TestCase):
    def _ns(self, **overrides):
        base = dict(
            path=".",
            file="",
            engine="stub",
            language="en",
            model="base",
            capture_intent=False,
            task="",
            json=True,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_handler_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_dispatch

        self.assertIs(COMMAND_HANDLERS["voice"], cmd_voice_dispatch)

    def test_unknown_subaction(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_dispatch

        ns = argparse.Namespace(voice_command="bogus")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(cmd_voice_dispatch(ns), USER_INPUT_ERROR)

    def test_text_fixture_round_trip(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.txt"
            fixture.write_text("Hello operator", encoding="utf-8")
            ns = self._ns(path=str(root), file=str(fixture))
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_voice_transcribe(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["result"]["text"], "Hello operator")
        self.assertEqual(payload["result"]["engine"], "stub")
        self.assertNotIn("intent_capture", payload)

    def test_capture_intent_requires_task(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.txt"
            fixture.write_text("ship router", encoding="utf-8")
            ns = self._ns(
                path=str(root), file=str(fixture), capture_intent=True
            )
            with redirect_stderr(io.StringIO()):
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_voice_transcribe(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)

    def test_capture_intent_writes_phase_record(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.txt"
            fixture.write_text("Refactor router", encoding="utf-8")
            ns = self._ns(
                path=str(root),
                file=str(fixture),
                capture_intent=True,
                task="Refactor router",
            )
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_voice_transcribe(ns)
            self.assertEqual(exit_code, SUCCESS)
            # The slice 2.3 capture writer drops a file under
            # mythic/checkins/<timestamp>-intent.md.
            intent_dir = root / "mythic" / "checkins"
            records = list(intent_dir.glob("*-intent.md"))
            self.assertEqual(len(records), 1)
            body = records[0].read_text(encoding="utf-8")
            self.assertIn("Refactor router", body)


class CmdVoiceSayTests(unittest.TestCase):
    def test_default_disabled_returns_skipped(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_say

        previous = os.environ.pop(TTS_ENABLED_ENV, None)
        try:
            ns = argparse.Namespace(
                path=".", text="hello", engine="stub", force=False, json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_voice_say(ns)
            payload = json.loads(buf.getvalue())
        finally:
            if previous is not None:
                os.environ[TTS_ENABLED_ENV] = previous
        self.assertEqual(exit_code, SUCCESS)
        self.assertFalse(payload["result"]["spoken"])
        self.assertIn("TTS disabled", payload["result"]["skipped_reason"])
        self.assertFalse(payload["tts_enabled"])

    def test_force_passes_through_to_stub_engine(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_say

        previous = os.environ.pop(TTS_ENABLED_ENV, None)
        try:
            ns = argparse.Namespace(
                path=".", text="hi", engine="stub", force=True, json=True
            )
            stderr = io.StringIO()
            stdout = io.StringIO()
            with redirect_stderr(stderr), redirect_stdout(stdout):
                exit_code = cmd_voice_say(ns)
            payload = json.loads(stdout.getvalue())
        finally:
            if previous is not None:
                os.environ[TTS_ENABLED_ENV] = previous
        self.assertEqual(exit_code, SUCCESS)
        self.assertFalse(payload["result"]["spoken"])  # stub never speaks
        self.assertIn("[voice-stub]", stderr.getvalue())
        self.assertIn("hi", stderr.getvalue())


# ---- TranscriptionResult / TTSResult round-trips ---------------------


class ResultDataclassTests(unittest.TestCase):
    def test_transcription_result_to_dict(self) -> None:
        result = TranscriptionResult(
            text="x",
            source_path="x.txt",
            engine="stub",
            model="base",
            language="en",
        )
        payload = result.to_dict()
        for key in {"text", "source_path", "engine", "model", "language", "dry_run", "error", "metadata"}:
            self.assertIn(key, payload)

    def test_tts_result_to_dict(self) -> None:
        result = TTSResult(text="x", engine="stub", spoken=False, skipped_reason="reason")
        payload = result.to_dict()
        for key in {"text", "engine", "spoken", "skipped_reason", "error", "metadata"}:
            self.assertIn(key, payload)


# ---- Slash catalog + TUI runner --------------------------------------


class VoiceSlashCatalogTests(unittest.TestCase):
    def test_slash_catalog_contains_voice(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("voice", names)

    def test_tui_runner_forwards_path_for_voice(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("voice", project_root=Path(tmp))
        self.assertIn("--path", spec.argv)
        self.assertIn(str(Path(tmp)), spec.argv)


if __name__ == "__main__":
    unittest.main()
