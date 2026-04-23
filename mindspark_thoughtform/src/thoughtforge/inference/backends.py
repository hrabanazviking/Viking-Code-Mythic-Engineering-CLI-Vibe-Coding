"""
Inference backend detection and llama-cpp-python configuration.

Detects which acceleration backends are available on the current machine
and builds the appropriate kwargs for the Llama() constructor.

Backend priority: CUDA > ROCm > Vulkan > DirectML (Windows) > Metal (macOS) > CPU
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Quantization types → GGUF file suffix mapping
QUANT_SUFFIXES: dict[str, list[str]] = {
    "q2_k":   ["-Q2_K.gguf", "-q2_k.gguf"],
    "q3_k_m": ["-Q3_K_M.gguf", "-q3_k_m.gguf"],
    "q4_k_m": ["-Q4_K_M.gguf", "-q4_k_m.gguf"],
    "q4_0":   ["-Q4_0.gguf", "-q4_0.gguf"],
    "q5_k_m": ["-Q5_K_M.gguf", "-q5_k_m.gguf"],
    "q6_k":   ["-Q6_K.gguf", "-q6_k.gguf"],
    "q8_0":   ["-Q8_0.gguf", "-q8_0.gguf"],
    "fp16":   ["-F16.gguf", "-f16.gguf", ".fp16.gguf"],
    "bf16":   ["-BF16.gguf", "-bf16.gguf"],
}


@dataclass
class BackendInfo:
    """Information about an available inference backend."""
    name: str
    available: bool
    priority: int                   # lower = higher priority
    llama_cpp_kwargs: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


def detect_backends() -> list[BackendInfo]:
    """
    Probe all backends and return them sorted by priority (best first).
    All detection is best-effort — no exceptions bubble up.
    """
    backends: list[BackendInfo] = []
    backends.append(_probe_cuda())
    backends.append(_probe_rocm())
    backends.append(_probe_metal())
    backends.append(_probe_vulkan())
    backends.append(_probe_directml())
    backends.append(_probe_cpu())

    available = [b for b in backends if b.available]
    available.sort(key=lambda b: b.priority)

    logger.debug(
        "Available backends: %s",
        [b.name for b in available],
    )
    return available


def select_backend(
    preferred: str = "auto",
    fallbacks: list[str] | None = None,
) -> BackendInfo:
    """
    Select the best available backend.

    Args:
        preferred:  "auto" | "cuda" | "rocm" | "vulkan" | "directml" | "metal" | "cpu"
        fallbacks:  List of fallback backend names (in priority order)

    Returns:
        The best available BackendInfo.
    """
    all_backends = detect_backends()
    available_map = {b.name: b for b in all_backends}

    if preferred == "auto":
        if all_backends:
            chosen = all_backends[0]
            logger.info("Backend auto-selected: %s", chosen.name)
            return chosen
    else:
        if preferred in available_map:
            logger.info("Backend selected: %s (preferred)", preferred)
            return available_map[preferred]
        logger.warning("Preferred backend '%s' not available", preferred)

        for fb in (fallbacks or []):
            if fb in available_map:
                logger.info("Backend fallback: %s", fb)
                return available_map[fb]

    # Always have CPU as ultimate fallback
    cpu = available_map.get("cpu")
    if cpu:
        logger.info("Backend: cpu (ultimate fallback)")
        return cpu

    # Construct a CPU backend in case detect failed
    logger.warning("No backends detected — constructing minimal CPU backend")
    return BackendInfo(
        name="cpu",
        available=True,
        priority=100,
        llama_cpp_kwargs={"n_gpu_layers": 0},
        notes="fallback construction",
    )


def build_llama_kwargs(
    backend: BackendInfo,
    model_path: str,
    n_ctx: int = 4096,
    n_gpu_layers: int = 0,
    n_threads: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Build the complete kwargs dict for llama_cpp.Llama() constructor.

    Args:
        backend:        Selected BackendInfo
        model_path:     Path to the GGUF model file
        n_ctx:          Context window size
        n_gpu_layers:   Number of layers to offload to GPU (0=none, -1=all)
        n_threads:      CPU thread count (None = auto)
        verbose:        llama.cpp verbosity

    Returns:
        kwargs dict ready to pass to Llama(**kwargs)
    """
    import os

    if n_threads is None:
        n_threads = max(1, (os.cpu_count() or 4) - 1)

    kwargs: dict[str, Any] = {
        "model_path": model_path,
        "n_ctx": n_ctx,
        "n_threads": n_threads,
        "verbose": verbose,
    }

    # Merge backend-specific kwargs
    kwargs.update(backend.llama_cpp_kwargs)

    # Override n_gpu_layers from caller (profile resolution may override backend default)
    if n_gpu_layers != 0:
        kwargs["n_gpu_layers"] = n_gpu_layers
    elif "n_gpu_layers" not in kwargs:
        kwargs["n_gpu_layers"] = 0

    logger.debug("Llama kwargs: ctx=%d, gpu_layers=%d, threads=%d, backend=%s",
                 n_ctx, kwargs["n_gpu_layers"], n_threads, backend.name)
    return kwargs


# ── Backend probers ────────────────────────────────────────────────────────────

def _probe_cuda() -> BackendInfo:
    available = False
    notes = ""
    try:
        # Try nvidia-smi subprocess check
        import subprocess
        result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=3)
        if result.returncode == 0:
            available = True
            notes = "nvidia-smi detected"
    except Exception:
        pass

    if not available:
        try:
            import torch
            if torch.cuda.is_available():
                available = True
                notes = f"torch.cuda ({torch.version.cuda})"  # type: ignore[attr-defined]
        except ImportError:
            pass

    return BackendInfo(
        name="cuda",
        available=available,
        priority=1,
        llama_cpp_kwargs={"n_gpu_layers": -1},
        notes=notes,
    )


def _probe_rocm() -> BackendInfo:
    available = False
    notes = ""
    try:
        import subprocess
        result = subprocess.run(["rocm-smi"], capture_output=True, timeout=3)
        if result.returncode == 0:
            available = True
            notes = "rocm-smi detected"
    except Exception:
        pass

    if not available:
        try:
            import torch
            if hasattr(torch, "hip") and torch.cuda.is_available():
                available = True
                notes = "torch ROCm backend"
        except ImportError:
            pass

    return BackendInfo(
        name="rocm",
        available=available,
        priority=2,
        llama_cpp_kwargs={"n_gpu_layers": -1},
        notes=notes,
    )


def _probe_metal() -> BackendInfo:
    """Apple Metal backend — available on macOS with Apple Silicon or AMD GPU."""
    available = False
    notes = ""
    if platform.system() == "Darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and ("Metal" in result.stdout or "Apple M" in result.stdout):
                available = True
                notes = "macOS Metal detected"
        except Exception:
            # If system_profiler fails, assume Metal is available on Darwin
            available = True
            notes = "macOS assumed Metal support"

    return BackendInfo(
        name="metal",
        available=available,
        priority=3,
        llama_cpp_kwargs={"n_gpu_layers": -1},
        notes=notes,
    )


def _probe_vulkan() -> BackendInfo:
    available = False
    notes = ""
    try:
        import subprocess
        result = subprocess.run(
            ["vulkaninfo", "--summary"], capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            available = True
            notes = "vulkaninfo detected"
    except Exception:
        pass

    if not available:
        # Check for library presence on Linux
        from pathlib import Path
        for lib in [
            "/usr/lib/libvulkan.so",
            "/usr/lib/x86_64-linux-gnu/libvulkan.so.1",
            "/usr/lib/aarch64-linux-gnu/libvulkan.so.1",
        ]:
            if Path(lib).exists():
                available = True
                notes = f"libvulkan at {lib}"
                break

    return BackendInfo(
        name="vulkan",
        available=available,
        priority=4,
        llama_cpp_kwargs={"n_gpu_layers": -1},
        notes=notes,
    )


def _probe_directml() -> BackendInfo:
    available = False
    notes = ""
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.LoadLibrary("DirectML.dll")  # type: ignore[attr-defined]
            available = True
            notes = "DirectML.dll found"
        except (OSError, AttributeError):
            # DirectML may still be available via llama-cpp-python build flags
            available = True
            notes = "Windows assumed DirectML support"

    return BackendInfo(
        name="directml",
        available=available,
        priority=5,
        llama_cpp_kwargs={"n_gpu_layers": 0},  # DirectML handled via build, not kwargs
        notes=notes,
    )


def _probe_cpu() -> BackendInfo:
    return BackendInfo(
        name="cpu",
        available=True,
        priority=100,
        llama_cpp_kwargs={"n_gpu_layers": 0},
        notes="always available",
    )
