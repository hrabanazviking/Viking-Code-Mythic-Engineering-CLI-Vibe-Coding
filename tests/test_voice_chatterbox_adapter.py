"""Tests for the additive Chatterbox modern-API adapter (Phase A.1
of the 2026-05-02 audit remediation).

The audit (AUDIT_PSEUDOCODE_DEEP_2026-05-02.md, finding #1) showed
that the previous ChatterboxEngine.say() implementation probed for a
top-level ``chatterbox.speak()`` function which the real package does
not export. The real package exposes ``ChatterboxTTS`` (and
``ChatterboxMultilingualTTS``) with a ``from_pretrained(device=...)``
classmethod and a ``generate(text)`` instance method that returns a
torch waveform tensor; saving requires ``torchaudio.save(path, wav, sr)``.

These tests mock the modern API at the module + class level so they
exercise the adapter logic without requiring the heavyweight
``torch`` / ``torchaudio`` / ``chatterbox`` runtime deps. The legacy
``speak()`` probe path is also covered for back-compat — it remains
the fallback when no modern class is reachable.
"""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from mythic_vibe_cli.voice.tts import (
    ChatterboxEngine,
    TTSRequest,
)


def _fake_chatterbox_module() -> types.ModuleType:
    """Construct a stand-in ``chatterbox`` namespace package so
    ``ChatterboxEngine.__post_init__`` can succeed without the real
    dep being installed. Tests patch ``sys.modules`` with this so the
    engine constructs cleanly, then the individual tests further patch
    ``_resolve_modern_tts_cls`` (or the candidate import paths) to
    exercise specific branches.
    """
    mod = types.ModuleType("chatterbox")
    return mod


def _make_engine_with_fake_module() -> ChatterboxEngine:
    """Construct ChatterboxEngine while a fake ``chatterbox`` is on
    sys.modules so the try-import in __post_init__ succeeds."""
    fake = _fake_chatterbox_module()
    with patch.dict(sys.modules, {"chatterbox": fake}):
        engine = ChatterboxEngine()
    # After __post_init__, _module is bound to the fake; we can return
    # the engine outside the patch context because nothing else re-imports.
    return engine


class ResolveModernTtsClsTests(unittest.TestCase):
    """``_resolve_modern_tts_cls`` walks the candidate list and returns
    the first import that yields a class with a callable
    ``from_pretrained``."""

    def setUp(self) -> None:
        self.engine = _make_engine_with_fake_module()

    def test_returns_none_when_no_candidate_resolves(self) -> None:
        # Patch sys.modules so all four candidate modules raise ImportError.
        # Use __import__ patch so the engine's import attempts fail uniformly.
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            self.assertIsNone(self.engine._resolve_modern_tts_cls())

    def test_returns_first_candidate_with_callable_from_pretrained(self) -> None:
        fake_cls = MagicMock(name="ChatterboxTTS")
        fake_cls.from_pretrained = MagicMock(name="from_pretrained")
        fake_module = types.ModuleType("chatterbox.tts")
        fake_module.ChatterboxTTS = fake_cls

        with patch.dict(sys.modules, {"chatterbox.tts": fake_module}, clear=False):
            resolved = self.engine._resolve_modern_tts_cls()
        self.assertIsNotNone(resolved)
        cls, label = resolved
        self.assertIs(cls, fake_cls)
        self.assertEqual(label, "chatterbox.tts.ChatterboxTTS")

    def test_skips_class_without_from_pretrained(self) -> None:
        # First candidate has the class but no usable from_pretrained.
        # Second candidate provides a usable one. Resolver picks the second.
        bad_cls = type("FakeBad", (), {})  # no from_pretrained
        good_cls = MagicMock(name="ChatterboxTTS")
        good_cls.from_pretrained = MagicMock()

        bad_module = types.ModuleType("chatterbox.tts")
        bad_module.ChatterboxTTS = bad_cls
        good_module = types.ModuleType("chatterbox")
        good_module.ChatterboxTTS = good_cls

        with patch.dict(
            sys.modules,
            {"chatterbox.tts": bad_module, "chatterbox": good_module},
            clear=False,
        ):
            resolved = self.engine._resolve_modern_tts_cls()
        self.assertIsNotNone(resolved)
        cls, label = resolved
        self.assertIs(cls, good_cls)
        self.assertEqual(label, "chatterbox.ChatterboxTTS")

    def test_falls_back_to_multilingual_when_only_mtl_present(self) -> None:
        mtl_cls = MagicMock(name="ChatterboxMultilingualTTS")
        mtl_cls.from_pretrained = MagicMock()
        mtl_module = types.ModuleType("chatterbox.mtl_tts")
        mtl_module.ChatterboxMultilingualTTS = mtl_cls

        # Make the earlier candidates fail to import / lack the class.
        empty_module = types.ModuleType("chatterbox")
        # No ChatterboxTTS attribute on the bare chatterbox module.
        with patch.dict(
            sys.modules,
            {
                "chatterbox": empty_module,
                "chatterbox.mtl_tts": mtl_module,
            },
            clear=False,
        ):
            # chatterbox.tts must miss too — patch __import__ to make it fail.
            real_import = __import__

            def selective_import(name, *args, **kwargs):
                if name == "chatterbox.tts":
                    raise ImportError("no chatterbox.tts in this fake setup")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=selective_import):
                resolved = self.engine._resolve_modern_tts_cls()

        self.assertIsNotNone(resolved)
        cls, label = resolved
        self.assertIs(cls, mtl_cls)
        self.assertEqual(label, "chatterbox.mtl_tts.ChatterboxMultilingualTTS")


class DetectDeviceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _make_engine_with_fake_module()

    def test_explicit_override_wins(self) -> None:
        self.engine.device = "cpu"
        self.assertEqual(self.engine._detect_device(), "cpu")
        self.engine.device = "cuda"
        self.assertEqual(self.engine._detect_device(), "cuda")

    def test_auto_returns_cpu_when_torch_missing(self) -> None:
        self.engine.device = "auto"
        # Patch __import__ so `import torch` raises.
        real_import = __import__

        def no_torch(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("no torch")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=no_torch):
            self.assertEqual(self.engine._detect_device(), "cpu")

    def test_auto_picks_cuda_when_available(self) -> None:
        self.engine.device = "auto"
        fake_torch = types.ModuleType("torch")
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: True)
        fake_torch.backends = types.SimpleNamespace(mps=None)
        with patch.dict(sys.modules, {"torch": fake_torch}, clear=False):
            self.assertEqual(self.engine._detect_device(), "cuda")

    def test_auto_picks_mps_when_only_mps_available(self) -> None:
        self.engine.device = "auto"
        fake_torch = types.ModuleType("torch")
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        mps_ns = types.SimpleNamespace(is_available=lambda: True)
        fake_torch.backends = types.SimpleNamespace(mps=mps_ns)
        with patch.dict(sys.modules, {"torch": fake_torch}, clear=False):
            self.assertEqual(self.engine._detect_device(), "mps")

    def test_auto_returns_cpu_when_neither_cuda_nor_mps(self) -> None:
        self.engine.device = "auto"
        fake_torch = types.ModuleType("torch")
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        fake_torch.backends = types.SimpleNamespace(
            mps=types.SimpleNamespace(is_available=lambda: False)
        )
        with patch.dict(sys.modules, {"torch": fake_torch}, clear=False):
            self.assertEqual(self.engine._detect_device(), "cpu")


class ResolveOutputPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _make_engine_with_fake_module()

    def test_engine_output_path_wins(self) -> None:
        self.engine.output_path = "/tmp/explicit.wav"
        req = TTSRequest(text="hello", metadata={"output_path": "/tmp/loser.wav"})
        self.assertEqual(self.engine._resolve_output_path(req), "/tmp/explicit.wav")

    def test_request_metadata_used_when_engine_path_empty(self) -> None:
        req = TTSRequest(text="hello", metadata={"output_path": "/tmp/from-meta.wav"})
        self.assertEqual(self.engine._resolve_output_path(req), "/tmp/from-meta.wav")

    def test_temp_slug_when_neither_set(self) -> None:
        req = TTSRequest(text="Hello there, friend!")
        path = self.engine._resolve_output_path(req)
        self.assertTrue(path.endswith(".wav"))
        self.assertIn("mythic_chatterbox_", path)
        # The slug derives from text — should contain "hello"
        self.assertIn("hello", path.lower())

    def test_empty_text_falls_back_to_speech_slug(self) -> None:
        req = TTSRequest(text="")
        path = self.engine._resolve_output_path(req)
        self.assertIn("mythic_chatterbox_speech.wav", path)


class SayViaModernHappyPathTests(unittest.TestCase):
    """Modern path: from_pretrained → generate → torchaudio.save."""

    def setUp(self) -> None:
        self.engine = _make_engine_with_fake_module()
        # Use an explicit device so we don't go through torch detection.
        self.engine.device = "cpu"

    def _make_modern_cls(self):
        fake_wav = MagicMock(name="waveform-tensor")
        model = MagicMock(name="model-instance")
        model.generate.return_value = fake_wav
        model.sr = 24000
        cls = MagicMock(name="FakeChatterboxTTS")
        cls.from_pretrained.return_value = model
        return cls, model, fake_wav

    def test_happy_path_returns_spoken_true_with_metadata(self) -> None:
        cls, model, fake_wav = self._make_modern_cls()
        fake_torchaudio = types.ModuleType("torchaudio")
        fake_torchaudio.save = MagicMock(name="torchaudio.save")

        target_path = "C:/tmp/test-output.wav"
        req = TTSRequest(text="hello world", metadata={"output_path": target_path})

        with patch.dict(sys.modules, {"torchaudio": fake_torchaudio}, clear=False):
            result = self.engine._say_via_modern(req, cls, "fake.ChatterboxTTS")

        self.assertTrue(result.spoken)
        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.engine, "chatterbox")
        self.assertEqual(result.metadata["source"], "chatterbox-modern")
        self.assertEqual(result.metadata["engine_class"], "fake.ChatterboxTTS")
        self.assertEqual(result.metadata["device"], "cpu")
        self.assertEqual(result.metadata["output_path"], target_path)
        self.assertEqual(result.metadata["sample_rate"], 24000)
        cls.from_pretrained.assert_called_once_with(device="cpu")
        model.generate.assert_called_once_with("hello world")
        fake_torchaudio.save.assert_called_once_with(target_path, fake_wav, 24000)


class SayViaModernFailureBranchTests(unittest.TestCase):
    """Each failure branch returns ``spoken=False`` with a clean error
    message and never raises."""

    def setUp(self) -> None:
        self.engine = _make_engine_with_fake_module()
        self.engine.device = "cpu"

    def _good_cls(self):
        model = MagicMock()
        model.generate.return_value = MagicMock(name="wav")
        model.sr = 16000
        cls = MagicMock()
        cls.from_pretrained.return_value = model
        return cls, model

    def test_torchaudio_missing(self) -> None:
        cls, _model = self._good_cls()
        real_import = __import__

        def no_torchaudio(name, *args, **kwargs):
            if name == "torchaudio":
                raise ImportError("simulated missing torchaudio")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=no_torchaudio):
            result = self.engine._say_via_modern(
                TTSRequest(text="hi"), cls, "fake.ChatterboxTTS"
            )
        self.assertFalse(result.spoken)
        self.assertIn("torchaudio", result.error)

    def test_from_pretrained_raises(self) -> None:
        cls = MagicMock()
        cls.from_pretrained.side_effect = RuntimeError("disk full")
        fake_torchaudio = types.ModuleType("torchaudio")
        fake_torchaudio.save = MagicMock()
        with patch.dict(sys.modules, {"torchaudio": fake_torchaudio}, clear=False):
            result = self.engine._say_via_modern(
                TTSRequest(text="hi"), cls, "fake.ChatterboxTTS"
            )
        self.assertFalse(result.spoken)
        self.assertIn("from_pretrained failed", result.error)
        self.assertIn("disk full", result.error)

    def test_generate_raises(self) -> None:
        model = MagicMock()
        model.generate.side_effect = ValueError("bad text")
        model.sr = 16000
        cls = MagicMock()
        cls.from_pretrained.return_value = model
        fake_torchaudio = types.ModuleType("torchaudio")
        fake_torchaudio.save = MagicMock()
        with patch.dict(sys.modules, {"torchaudio": fake_torchaudio}, clear=False):
            result = self.engine._say_via_modern(
                TTSRequest(text="hi"), cls, "fake.ChatterboxTTS"
            )
        self.assertFalse(result.spoken)
        self.assertIn("generate failed", result.error)

    def test_model_missing_sr(self) -> None:
        model = types.SimpleNamespace(generate=lambda text: MagicMock(name="wav"))
        # No `.sr` attribute.
        cls = MagicMock()
        cls.from_pretrained.return_value = model
        fake_torchaudio = types.ModuleType("torchaudio")
        fake_torchaudio.save = MagicMock()
        with patch.dict(sys.modules, {"torchaudio": fake_torchaudio}, clear=False):
            result = self.engine._say_via_modern(
                TTSRequest(text="hi"), cls, "fake.ChatterboxTTS"
            )
        self.assertFalse(result.spoken)
        self.assertIn("did not expose `.sr`", result.error)

    def test_torchaudio_save_raises(self) -> None:
        model = MagicMock()
        model.generate.return_value = MagicMock()
        model.sr = 16000
        cls = MagicMock()
        cls.from_pretrained.return_value = model
        fake_torchaudio = types.ModuleType("torchaudio")
        fake_torchaudio.save = MagicMock(side_effect=PermissionError("read only"))
        with patch.dict(sys.modules, {"torchaudio": fake_torchaudio}, clear=False):
            result = self.engine._say_via_modern(
                TTSRequest(text="hi"), cls, "fake.ChatterboxTTS"
            )
        self.assertFalse(result.spoken)
        self.assertIn("save failed", result.error)
        self.assertIn("read only", result.error)


class SayDispatchTests(unittest.TestCase):
    """End-to-end ``say()`` dispatch: prefers modern path when the
    resolver returns a class; falls through to the legacy speak() probe
    when the resolver returns None."""

    def setUp(self) -> None:
        self.engine = _make_engine_with_fake_module()
        self.engine.device = "cpu"

    def test_modern_path_used_when_resolver_returns_class(self) -> None:
        cls, model = MagicMock(), MagicMock()
        model.generate.return_value = MagicMock()
        model.sr = 22050
        cls.from_pretrained.return_value = model

        fake_torchaudio = types.ModuleType("torchaudio")
        fake_torchaudio.save = MagicMock()
        with patch.object(
            self.engine, "_resolve_modern_tts_cls", return_value=(cls, "fake.label")
        ), patch.dict(sys.modules, {"torchaudio": fake_torchaudio}, clear=False):
            result = self.engine.say(TTSRequest(text="hello"))
        self.assertTrue(result.spoken)
        self.assertEqual(result.metadata["engine_class"], "fake.label")
        cls.from_pretrained.assert_called_once_with(device="cpu")

    def test_legacy_path_used_when_no_modern_class_and_speak_callable(self) -> None:
        # No modern class. Legacy module has a callable speak().
        fake_speak = MagicMock(name="legacy-speak")
        self.engine._module = types.SimpleNamespace(speak=fake_speak)
        with patch.object(
            self.engine, "_resolve_modern_tts_cls", return_value=None
        ):
            result = self.engine.say(TTSRequest(text="legacy hello", voice="aria"))
        self.assertTrue(result.spoken)
        self.assertEqual(result.metadata["source"], "chatterbox")
        fake_speak.assert_called_once_with("legacy hello", voice="aria")

    def test_returns_speak_not_callable_when_neither_modern_nor_legacy(self) -> None:
        # No modern class, no speak attribute on the module.
        self.engine._module = types.SimpleNamespace()  # no speak attr
        with patch.object(
            self.engine, "_resolve_modern_tts_cls", return_value=None
        ):
            result = self.engine.say(TTSRequest(text="hello"))
        self.assertFalse(result.spoken)
        self.assertIn("speak not callable", result.error)

    def test_legacy_speak_exception_returns_clean_error(self) -> None:
        # Legacy path's defensive except-block catches engine errors.
        bad_speak = MagicMock(side_effect=RuntimeError("audio device busy"))
        self.engine._module = types.SimpleNamespace(speak=bad_speak)
        with patch.object(
            self.engine, "_resolve_modern_tts_cls", return_value=None
        ):
            result = self.engine.say(TTSRequest(text="hello"))
        self.assertFalse(result.spoken)
        self.assertIn("audio device busy", result.error)


if __name__ == "__main__":
    unittest.main()
