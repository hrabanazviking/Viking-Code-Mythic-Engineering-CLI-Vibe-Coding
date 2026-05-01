"""Tests for the voice & multimodal surface (PH-07 slices 7.1-7.4)."""

from __future__ import annotations

import argparse
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
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

    def test_transcribe_argparse_accepts_no_source_then_handler_rejects(self) -> None:
        """PH-07 follow-up: --file is no longer argparse-required so
        --mic can be used instead. The handler enforces "exactly one
        of --file / --mic" and returns USER_INPUT_ERROR otherwise."""
        from mythic_vibe_cli.commands import cmd_voice_transcribe
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        parser = build_parser()
        ns = parser.parse_args(["voice", "transcribe"])
        with redirect_stderr(io.StringIO()):
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_voice_transcribe(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)

    def test_transcribe_mic_flag_parses(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            ["voice", "transcribe", "--mic", "--duration", "3"]
        )
        self.assertTrue(ns.mic)
        self.assertEqual(ns.duration, 3.0)
        self.assertEqual(ns.file, "")

    def test_transcribe_mic_default_duration(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["voice", "transcribe", "--mic"])
        self.assertEqual(ns.duration, 5.0)

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
            mic=False,
            duration=5.0,
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


# ---- Mic capture (PH-07 follow-up) -----------------------------------


@dataclass
class _FakeMicRecorder:
    """Test double for :class:`MicRecorder`. Returns a deterministic
    PCM payload sized to ``duration * sample_rate`` int16 samples."""

    sample_rate: int = 16_000
    channels: int = 1
    last_duration: float = 0.0

    def record(self, duration: float) -> bytes:
        self.last_duration = duration
        # int16 silence — frames * channels * 2 bytes per sample.
        frame_count = int(round(duration * self.sample_rate))
        return b"\x00\x00" * frame_count * self.channels


class RecordToTempWavTests(unittest.TestCase):
    def test_returns_path_to_existing_wav(self) -> None:
        from mythic_vibe_cli.voice.transcribe import record_to_temp_wav

        recorder = _FakeMicRecorder()
        path = record_to_temp_wav(0.5, recorder=recorder)
        try:
            self.assertTrue(Path(path).is_file())
            self.assertTrue(path.endswith(".wav"))
            self.assertEqual(recorder.last_duration, 0.5)
            # Verify it's a valid WAV: stdlib wave should open it.
            import wave

            with wave.open(path, "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getframerate(), 16_000)
                # 0.5s * 16k = 8000 frames.
                self.assertEqual(wav.getnframes(), 8000)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_sounddevice_raises_missing_extra(self) -> None:
        """SoundDeviceRecorder constructor should raise
        :class:`MissingExtraError` when sounddevice can't be imported."""
        from mythic_vibe_cli.voice.transcribe import (
            MissingExtraError,
            SoundDeviceRecorder,
        )

        real_import = (
            __builtins__["__import__"]
            if isinstance(__builtins__, dict)
            else __builtins__.__import__
        )

        def fake_import(name, *args, **kwargs):
            if name == "sounddevice":
                raise ImportError("simulated absence")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(MissingExtraError) as ctx:
                SoundDeviceRecorder()
        self.assertEqual(ctx.exception.extra, "sounddevice")
        self.assertIn("pip install sounddevice", ctx.exception.install_hint)

    def test_duration_must_be_positive(self) -> None:
        """The fake recorder is permissive, but the real recorder
        guards against zero/negative durations."""
        from mythic_vibe_cli.voice.transcribe import SoundDeviceRecorder

        # Build a SoundDeviceRecorder without invoking __post_init__
        # (we don't have sounddevice installed in the test env here).
        rec = SoundDeviceRecorder.__new__(SoundDeviceRecorder)
        rec.sample_rate = 16_000
        rec.channels = 1
        rec._module = mock.MagicMock()
        rec._numpy = mock.MagicMock()
        with self.assertRaises(ValueError):
            rec.record(0.0)
        with self.assertRaises(ValueError):
            rec.record(-1.0)


class CmdVoiceTranscribeMicTests(unittest.TestCase):
    """Integration: cmd_voice_transcribe with --mic uses a recorded
    temp WAV and cleans up afterwards."""

    def _ns(self, **overrides):
        base = dict(
            path=".",
            file="",
            engine="stub",
            language="en",
            model="base",
            capture_intent=False,
            task="",
            mic=False,
            duration=5.0,
            json=True,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_mic_records_and_pipes_through_stub(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe
        from mythic_vibe_cli.voice import transcribe as voice_transcribe

        recorder = _FakeMicRecorder()
        # Patch record_to_temp_wav to inject our fake recorder.
        original = voice_transcribe.record_to_temp_wav

        def patched(duration: float, **kwargs):
            return original(duration, recorder=recorder)

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._ns(path=tmp, mic=True, duration=0.25)
            buf = io.StringIO()
            with mock.patch.object(voice_transcribe, "record_to_temp_wav", patched):
                with redirect_stdout(buf):
                    exit_code = cmd_voice_transcribe(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(recorder.last_duration, 0.25)
        # The stub transcriber on a binary WAV returns a placeholder
        # mentioning the basename ("[stub transcript of mythic-mic-...wav]").
        self.assertIn("stub transcript", payload["result"]["text"])
        # Temp file must be cleaned up.
        source_path = payload["request"]["source_path"]
        self.assertFalse(Path(source_path).exists())

    def test_mic_missing_dep_returns_operational_failure(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe
        from mythic_vibe_cli.exit_codes import OPERATIONAL_FAILURE
        from mythic_vibe_cli.voice.transcribe import MissingExtraError
        from mythic_vibe_cli.voice import transcribe as voice_transcribe

        def raising_record(duration: float, **kwargs):
            raise MissingExtraError(
                "sounddevice", "Install with `pip install sounddevice numpy`."
            )

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._ns(path=tmp, mic=True, duration=1.0)
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(
                voice_transcribe, "record_to_temp_wav", raising_record
            ):
                from contextlib import redirect_stderr
                with redirect_stderr(stderr), redirect_stdout(stdout):
                    exit_code = cmd_voice_transcribe(ns)
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)
        self.assertIn("sounddevice", stderr.getvalue())
        self.assertIn("pip install sounddevice", stderr.getvalue())

    def test_file_and_mic_mutually_exclusive(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "x.txt"
            fixture.write_text("hi", encoding="utf-8")
            ns = self._ns(path=tmp, file=str(fixture), mic=True)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_voice_transcribe(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("mutually exclusive", stderr.getvalue())

    def test_neither_file_nor_mic_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        ns = self._ns()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_voice_transcribe(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)

    def test_mic_negative_duration_rejected(self) -> None:
        from mythic_vibe_cli.commands import cmd_voice_transcribe
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        ns = self._ns(mic=True, duration=-1.0)
        with redirect_stderr(io.StringIO()):
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_voice_transcribe(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)


# ---- TTS phase-transition hook (PH-07 follow-up) --------------------


class ComposePhaseMessageTests(unittest.TestCase):
    def test_known_preset_returned(self) -> None:
        from mythic_vibe_cli.voice.notify import compose_phase_message

        self.assertEqual(
            compose_phase_message("intent", "captured"),
            "Intent captured.",
        )
        self.assertEqual(
            compose_phase_message("verify", "pass"),
            "Verification passed.",
        )
        self.assertEqual(
            compose_phase_message("verify", "fail"),
            "Verification failed.",
        )
        self.assertEqual(
            compose_phase_message("handoff", "written"),
            "Handoff written.",
        )

    def test_unknown_phase_falls_back_to_generic_format(self) -> None:
        from mythic_vibe_cli.voice.notify import compose_phase_message

        line = compose_phase_message("hypernova", "ignited")
        self.assertEqual(line, "Hypernova ignited.")

    def test_override_short_circuits_lookup(self) -> None:
        from mythic_vibe_cli.voice.notify import compose_phase_message

        self.assertEqual(
            compose_phase_message("intent", "captured", override="Custom line"),
            "Custom line",
        )

    def test_blank_override_ignored(self) -> None:
        from mythic_vibe_cli.voice.notify import compose_phase_message

        self.assertEqual(
            compose_phase_message("intent", "captured", override="   "),
            "Intent captured.",
        )


class NotifyPhaseGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(TTS_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(TTS_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[TTS_ENABLED_ENV] = self._previous

    def test_disabled_env_is_no_op(self) -> None:
        from mythic_vibe_cli.voice.notify import notify_phase

        engine = mock.MagicMock()
        result = notify_phase("intent", "captured", tts_engine=engine)
        self.assertFalse(result.fired)
        self.assertIsNone(result.tts_result)
        self.assertEqual(result.message, "Intent captured.")
        engine.say.assert_not_called()

    def test_enabled_env_dispatches_through_engine(self) -> None:
        from mythic_vibe_cli.voice.notify import notify_phase

        os.environ[TTS_ENABLED_ENV] = "1"
        buf = io.StringIO()
        stub = StubTTSEngine(stream=buf)
        result = notify_phase("verify", "pass", tts_engine=stub)
        self.assertTrue(result.fired)
        self.assertIsNotNone(result.tts_result)
        self.assertIn("Verification passed.", buf.getvalue())

    def test_force_overrides_disabled_env(self) -> None:
        from mythic_vibe_cli.voice.notify import notify_phase

        buf = io.StringIO()
        stub = StubTTSEngine(stream=buf)
        result = notify_phase(
            "handoff", "written", tts_engine=stub, force=True
        )
        self.assertTrue(result.fired)
        self.assertIn("Handoff written.", buf.getvalue())

    def test_engine_exception_contained(self) -> None:
        """An engine that raises must not break the parent command —
        the hook should swallow the exception and surface it via the
        TTSResult.error field."""
        from mythic_vibe_cli.voice.notify import notify_phase

        class _Boom:
            name = "boom"

            def say(self, request):
                raise RuntimeError("explosion")

        os.environ[TTS_ENABLED_ENV] = "1"
        result = notify_phase("intent", "captured", tts_engine=_Boom())
        self.assertTrue(result.fired)
        self.assertIsNotNone(result.tts_result)
        self.assertFalse(result.tts_result.spoken)
        self.assertEqual(result.tts_result.error, "explosion")


class PhaseRecordNotifyIntegrationTests(unittest.TestCase):
    """When MYTHIC_VOICE_TTS_ENABLED is set, the phase capture
    handler should call notify_phase. We patch notify_phase to
    capture invocation rather than asserting on the stub stderr
    stream so the test stays decoupled from the TTS layer."""

    def test_capture_intent_fires_notify(self) -> None:
        from mythic_vibe_cli.commands import cmd_intent_capture

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = argparse.Namespace(
                path=str(root),
                task="Refactor router",
                summary="Move routing into its own module.",
                note=[],
                confidence="high",
                risk="",
                next_step="",
                operator="tester",
                json=True,
                dry_run=False,
            )
            calls: list[tuple[str, str]] = []

            def spy(phase, status, **kwargs):  # noqa: ANN001 — test spy
                calls.append((phase, status))
                from mythic_vibe_cli.voice.notify import NotifyResult
                return NotifyResult(fired=False, tts_result=None, message="")

            with mock.patch(
                "mythic_vibe_cli.voice.notify.notify_phase", side_effect=spy
            ):
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_intent_capture(ns)
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn(("intent", "captured"), calls)


class HandoffNotifyIntegrationTests(unittest.TestCase):
    def test_create_handoff_fires_notify(self) -> None:
        from mythic_vibe_cli.commands import _create_handoff

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls: list[tuple[str, str]] = []

            def spy(phase, status, **kwargs):  # noqa: ANN001
                calls.append((phase, status))
                from mythic_vibe_cli.voice.notify import NotifyResult
                return NotifyResult(fired=False, tts_result=None, message="")

            with mock.patch(
                "mythic_vibe_cli.voice.notify.notify_phase", side_effect=spy
            ):
                _create_handoff(
                    root,
                    objective="Sub-slice 3 sanity",
                    session_type="reflect",
                )
        self.assertIn(("handoff", "written"), calls)


class VerifyNotifyIntegrationTests(unittest.TestCase):
    def test_cmd_verify_fires_notify_with_result_status(self) -> None:
        """cmd_verify forwards the verification's pass/fail/blocked
        result string straight into notify_phase."""
        from mythic_vibe_cli.commands import cmd_verify

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = argparse.Namespace(
                path=str(root),
                commands=False,
                changed_files=False,
                docs=False,
                invariants=False,
                json=True,
                record=False,
            )
            calls: list[tuple[str, str]] = []

            def spy(phase, status, **kwargs):  # noqa: ANN001
                calls.append((phase, status))
                from mythic_vibe_cli.voice.notify import NotifyResult
                return NotifyResult(fired=False, tts_result=None, message="")

            with mock.patch(
                "mythic_vibe_cli.voice.notify.notify_phase", side_effect=spy
            ):
                with redirect_stdout(io.StringIO()):
                    cmd_verify(ns)

        # Exactly one verify-phase call.
        verify_calls = [c for c in calls if c[0] == "verify"]
        self.assertEqual(len(verify_calls), 1)
        # status must be one of {pass, fail, blocked}.
        self.assertIn(verify_calls[0][1], {"pass", "fail", "blocked"})


if __name__ == "__main__":
    unittest.main()
