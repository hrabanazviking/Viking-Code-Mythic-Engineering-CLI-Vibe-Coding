"""
Phase 2 tests — TurboQuant Universal Inference Engine.

Tests hardware detection, profile selection, backend detection,
parameter resolution, and TurboQuantEngine lifecycle — all without
requiring an actual GGUF model file or GPU hardware.
"""

from __future__ import annotations

import json
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from thoughtforge.inference.backends import (
    BackendInfo,
    build_llama_kwargs,
    detect_backends,
    select_backend,
)
from thoughtforge.inference.profiles import (
    HardwareDetector,
    HardwareSnapshot,
    ProfileSelector,
    ResolvedGenerationParams,
    resolve_generation_params,
)
from thoughtforge.inference.turboquant import (
    DraftSet,
    GenerationParams,
    GenerationResult,
    TurboQuantEngine,
    create_engine,
)
from thoughtforge.utils.config import load_hardware_profile, list_hardware_profiles


# ── Hardware detection tests ───────────────────────────────────────────────────

class TestHardwareDetector:
    def test_detect_returns_snapshot(self) -> None:
        detector = HardwareDetector()
        snap = detector.detect()
        assert isinstance(snap, HardwareSnapshot)

    def test_cpu_arch_is_set(self) -> None:
        detector = HardwareDetector()
        snap = detector.detect()
        assert snap.cpu_arch != ""

    def test_os_name_is_known(self) -> None:
        detector = HardwareDetector()
        snap = detector.detect()
        assert snap.os_name in ("windows", "linux", "macos", "android", "darwin")

    def test_ram_gb_positive(self) -> None:
        detector = HardwareDetector()
        snap = detector.detect()
        assert snap.ram_gb > 0

    def test_cpu_count_positive(self) -> None:
        detector = HardwareDetector()
        snap = detector.detect()
        assert snap.cpu_count >= 1

    def test_detect_cpu_arch_known_values(self) -> None:
        arch = HardwareDetector._detect_cpu_arch()
        assert isinstance(arch, str)
        assert len(arch) > 0

    def test_detect_os_known_values(self) -> None:
        os_name = HardwareDetector._detect_os()
        assert os_name in ("windows", "linux", "macos", "android")

    def test_detect_ram_gb_fallback(self) -> None:
        ram = HardwareDetector._detect_ram_gb()
        assert ram > 0

    def test_is_arm_flag(self) -> None:
        detector = HardwareDetector()
        snap = detector.detect()
        expected_arm = snap.cpu_arch.startswith("arm") or snap.cpu_arch == "aarch64"
        assert snap.is_arm == expected_arm


# ── Profile selection tests ────────────────────────────────────────────────────

class TestProfileSelector:
    def test_auto_select_returns_valid_profile(self) -> None:
        selector = ProfileSelector()
        match = selector.auto_select()
        assert match.profile_id in (
            "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
        )
        assert isinstance(match.profile, dict)
        assert match.hardware is not None

    def test_manual_load_all_profiles(self) -> None:
        selector = ProfileSelector()
        for profile_id in list_hardware_profiles():
            match = selector.load(profile_id)
            assert match.profile_id == profile_id
            assert match.confidence == "manual"

    def test_server_gpu_not_selected_without_vram(self) -> None:
        snap = HardwareSnapshot(ram_gb=64, vram_gb=0, cpu_arch="x86_64", has_cuda=False)
        profile_id = ProfileSelector._select_id(snap)
        assert profile_id != "server_gpu"

    def test_server_gpu_selected_with_large_vram_and_cuda(self) -> None:
        snap = HardwareSnapshot(ram_gb=64, vram_gb=24, cpu_arch="x86_64", has_cuda=True)
        profile_id = ProfileSelector._select_id(snap)
        assert profile_id == "server_gpu"

    def test_desktop_gpu_selected_with_consumer_gpu(self) -> None:
        snap = HardwareSnapshot(ram_gb=16, vram_gb=10, cpu_arch="x86_64", has_cuda=True)
        profile_id = ProfileSelector._select_id(snap)
        assert profile_id == "desktop_gpu"

    def test_desktop_cpu_selected_for_high_ram_no_gpu(self) -> None:
        snap = HardwareSnapshot(ram_gb=16, vram_gb=0, cpu_arch="x86_64", has_cuda=False)
        profile_id = ProfileSelector._select_id(snap)
        assert profile_id == "desktop_cpu"

    def test_pi_5_selected_for_arm_with_decent_ram(self) -> None:
        snap = HardwareSnapshot(
            ram_gb=4, vram_gb=0, cpu_arch="arm64",
            is_arm=True, is_raspberry_pi=True,
        )
        profile_id = ProfileSelector._select_id(snap)
        assert profile_id == "pi_5"

    def test_pi_zero_selected_for_very_low_ram_arm(self) -> None:
        snap = HardwareSnapshot(
            ram_gb=0.4, vram_gb=0, cpu_arch="armv6",
            is_arm=True, is_raspberry_pi=True,
        )
        profile_id = ProfileSelector._select_id(snap)
        assert profile_id == "pi_zero"

    def test_phone_low_selected_for_mobile(self) -> None:
        snap = HardwareSnapshot(
            ram_gb=2, vram_gb=0, cpu_arch="arm64",
            is_arm=True, is_mobile=True,
        )
        profile_id = ProfileSelector._select_id(snap)
        assert profile_id == "phone_low"

    def test_reason_string_not_empty(self) -> None:
        snap = HardwareSnapshot(ram_gb=8, vram_gb=0, cpu_arch="x86_64")
        reason = ProfileSelector._build_reason("desktop_cpu", snap)
        assert "desktop_cpu" in reason
        assert "ram" in reason.lower()


# ── Profile loading tests ──────────────────────────────────────────────────────

class TestProfileLoading:
    @pytest.mark.parametrize("profile_id", [
        "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
    ])
    def test_profile_loads_all_required_keys(self, profile_id: str) -> None:
        profile = load_hardware_profile(profile_id)
        assert "profile_id" in profile
        assert "hardware" in profile
        assert "model" in profile
        assert "generation" in profile
        assert "memory" in profile
        assert profile["profile_id"] == profile_id

    @pytest.mark.parametrize("profile_id", [
        "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
    ])
    def test_model_section_has_required_keys(self, profile_id: str) -> None:
        profile = load_hardware_profile(profile_id)
        model = profile["model"]
        assert "max_params_b" in model
        assert "quantization" in model
        assert "token_budget_per_turn" in model
        assert "draft_count" in model

    @pytest.mark.parametrize("profile_id", [
        "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
    ])
    def test_generation_section_has_required_keys(self, profile_id: str) -> None:
        profile = load_hardware_profile(profile_id)
        gen = profile["generation"]
        assert "max_response_tokens" in gen
        assert "temperature" in gen
        assert "max_refinement_passes" in gen

    def test_token_budget_increases_with_capability(self) -> None:
        pi_zero = load_hardware_profile("pi_zero")
        pi_5 = load_hardware_profile("pi_5")
        desktop = load_hardware_profile("desktop_cpu")
        server = load_hardware_profile("server_gpu")

        assert pi_zero["model"]["token_budget_per_turn"] < pi_5["model"]["token_budget_per_turn"]
        assert pi_5["model"]["token_budget_per_turn"] < desktop["model"]["token_budget_per_turn"]
        assert desktop["model"]["token_budget_per_turn"] < server["model"]["token_budget_per_turn"]

    def test_draft_count_range(self) -> None:
        for profile_id in list_hardware_profiles():
            profile = load_hardware_profile(profile_id)
            assert 1 <= profile["model"]["draft_count"] <= 5


# ── Generation param resolution tests ─────────────────────────────────────────

class TestResolvedGenerationParams:
    @pytest.mark.parametrize("profile_id", [
        "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
    ])
    def test_resolve_all_profiles(self, profile_id: str) -> None:
        profile = load_hardware_profile(profile_id)
        params = resolve_generation_params(profile)
        assert isinstance(params, ResolvedGenerationParams)
        assert params.max_response_tokens > 0
        assert 0.0 < params.temperature <= 2.0
        assert params.draft_count >= 1

    def test_cpu_profile_has_zero_gpu_layers(self) -> None:
        profile = load_hardware_profile("desktop_cpu")
        params = resolve_generation_params(profile)
        assert params.n_gpu_layers == 0
        assert params.inference_backend == "cpu"

    def test_server_gpu_has_full_offload(self) -> None:
        profile = load_hardware_profile("server_gpu")
        params = resolve_generation_params(profile)
        assert params.n_gpu_layers == -1

    def test_pi_zero_minimal_tokens(self) -> None:
        profile = load_hardware_profile("pi_zero")
        params = resolve_generation_params(profile)
        assert params.max_response_tokens <= 180
        assert params.draft_count == 1

    def test_server_allows_long_responses(self) -> None:
        profile = load_hardware_profile("server_gpu")
        params = resolve_generation_params(profile)
        assert params.max_response_tokens >= 1000


# ── Backend detection tests ────────────────────────────────────────────────────

class TestBackendDetection:
    def test_detect_backends_returns_list(self) -> None:
        backends = detect_backends()
        assert isinstance(backends, list)
        assert len(backends) > 0

    def test_cpu_always_available(self) -> None:
        backends = detect_backends()
        backend_names = [b.name for b in backends]
        assert "cpu" in backend_names

    def test_backends_sorted_by_priority(self) -> None:
        backends = detect_backends()
        for i in range(len(backends) - 1):
            assert backends[i].priority <= backends[i + 1].priority

    def test_select_backend_auto_returns_backendinfo(self) -> None:
        backend = select_backend("auto")
        assert isinstance(backend, BackendInfo)
        assert backend.available is True

    def test_select_backend_cpu_always_works(self) -> None:
        backend = select_backend("cpu")
        assert backend.name == "cpu"
        assert backend.available is True

    def test_select_backend_unknown_falls_back_to_cpu(self) -> None:
        backend = select_backend("nonexistent_backend_xyz")
        assert backend.name in ("cpu",)  # ultimate fallback

    def test_build_llama_kwargs_cpu(self) -> None:
        backend = BackendInfo(name="cpu", available=True, priority=100,
                              llama_cpp_kwargs={"n_gpu_layers": 0})
        kwargs = build_llama_kwargs(backend, "/fake/model.gguf", n_ctx=2048)
        assert kwargs["model_path"] == "/fake/model.gguf"
        assert kwargs["n_ctx"] == 2048
        assert kwargs["n_gpu_layers"] == 0
        assert kwargs["n_threads"] >= 1

    def test_build_llama_kwargs_with_gpu_layers(self) -> None:
        backend = BackendInfo(name="cuda", available=True, priority=1,
                              llama_cpp_kwargs={"n_gpu_layers": -1})
        kwargs = build_llama_kwargs(backend, "/fake/model.gguf", n_gpu_layers=32)
        assert kwargs["n_gpu_layers"] == 32


# ── TurboQuantEngine tests ─────────────────────────────────────────────────────

class TestTurboQuantEngine:
    def test_engine_creates_without_model_path(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        assert not engine.is_loaded

    def test_engine_loads_without_model_path(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        assert engine.is_loaded
        assert engine.profile_id == "desktop_cpu"
        engine.unload()

    def test_engine_profile_is_set_after_load(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="pi_5")
        engine.load()
        assert engine.profile_id == "pi_5"
        assert engine.params is not None
        assert engine.max_response_tokens > 0
        engine.unload()

    def test_engine_auto_profile_resolves(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="auto")
        engine.load()
        assert engine.profile_id in (
            "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
        )
        engine.unload()

    def test_engine_generate_raises_without_model(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        with pytest.raises(RuntimeError, match="No model is loaded"):
            engine.generate("Hello")
        engine.unload()

    def test_engine_generate_raises_if_not_loaded(self) -> None:
        engine = TurboQuantEngine(model_path=None)
        with pytest.raises(RuntimeError, match="not loaded"):
            engine.generate("Hello")

    def test_engine_double_load_is_safe(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        engine.load()  # Should not raise
        assert engine.is_loaded
        engine.unload()

    def test_engine_double_unload_is_safe(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        engine.unload()
        engine.unload()  # Should not raise

    def test_engine_context_manager(self) -> None:
        with TurboQuantEngine(model_path=None, profile_id="desktop_cpu") as engine:
            assert engine.is_loaded
        assert not engine.is_loaded

    def test_engine_raises_for_missing_model_file(self) -> None:
        engine = TurboQuantEngine(
            model_path="/nonexistent/path/model.gguf",
            profile_id="desktop_cpu",
        )
        with pytest.raises(FileNotFoundError):
            engine.load()

    def test_estimate_tokens_heuristic_fallback(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        # Without a loaded model, falls back to heuristic (~4 chars/token)
        n = engine.estimate_tokens("Hello, how are you today?")
        assert n >= 1
        engine.unload()

    def test_estimate_tokens_longer_text(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        short = engine.estimate_tokens("Hi")
        long_text = engine.estimate_tokens("The quick brown fox jumps over the lazy dog " * 10)
        assert long_text > short
        engine.unload()

    def test_token_budget_enforcement(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="pi_zero")
        engine.load()
        # Pi Zero budget is 120; asking for 500 should get capped
        capped = engine._enforce_token_budget(500)
        assert capped <= 120
        engine.unload()

    def test_token_budget_server_allows_large(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="server_gpu")
        engine.load()
        capped = engine._enforce_token_budget(1500)
        assert capped <= engine.params.token_budget_per_turn  # type: ignore[union-attr]
        engine.unload()

    def test_merge_params_inherits_defaults(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        merged = engine._merge_params(None)
        assert "temperature" in merged
        assert "max_tokens" in merged
        assert merged["temperature"] > 0
        engine.unload()

    def test_merge_params_override_works(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        override = GenerationParams(temperature=0.1, max_tokens=50)
        merged = engine._merge_params(override)
        assert merged["temperature"] == 0.1
        assert merged["max_tokens"] == 50
        engine.unload()

    def test_backend_name_set_after_load(self) -> None:
        engine = TurboQuantEngine(model_path=None, profile_id="desktop_cpu")
        engine.load()
        assert engine.backend_name is not None
        assert isinstance(engine.backend_name, str)
        engine.unload()

    def test_create_engine_no_model(self) -> None:
        engine = create_engine(model_path=None, profile_id="desktop_cpu")
        assert engine.is_loaded
        engine.unload()


# ── Generation result / draft set tests ───────────────────────────────────────

class TestGenerationTypes:
    def test_generation_result_fields(self) -> None:
        r = GenerationResult(
            text="Hello world",
            tokens_generated=10,
            tokens_prompt=5,
            total_tokens=15,
            duration_ms=200,
            tokens_per_second=50.0,
        )
        assert r.text == "Hello world"
        assert r.tokens_generated == 10

    def test_draft_set_texts_property(self) -> None:
        r1 = GenerationResult("draft one", 5, 3, 8, 100, 50.0)
        r2 = GenerationResult("draft two", 6, 3, 9, 120, 50.0)
        ds = DraftSet(drafts=[r1, r2], prompt="test", profile_id="desktop_cpu", total_duration_ms=220)
        assert ds.texts == ["draft one", "draft two"]

    def test_draft_set_best_returns_longest(self) -> None:
        r1 = GenerationResult("short", 5, 3, 8, 100, 50.0)
        r2 = GenerationResult("longer draft here", 20, 3, 23, 200, 50.0)
        ds = DraftSet(drafts=[r1, r2], prompt="x", profile_id="desktop_cpu", total_duration_ms=300)
        assert ds.best.tokens_generated == 20

    def test_generation_params_defaults(self) -> None:
        p = GenerationParams()
        assert p.max_tokens is None
        assert p.temperature is None
        assert p.stop == []
        assert p.stream is False
