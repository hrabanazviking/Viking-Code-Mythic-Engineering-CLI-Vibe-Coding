"""
Hardware profile detection and selection for ThoughtForge.

Auto-detects the current machine's RAM, VRAM, CPU architecture, and OS,
then selects the most appropriate hardware profile from hardware_profiles/.

Profile priority order (auto-detect):
  server_gpu → desktop_gpu → desktop_cpu → pi_5 → phone_low → pi_zero
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from thoughtforge.utils.config import load_hardware_profile, list_hardware_profiles
from thoughtforge.utils.paths import get_hardware_profiles_dir

logger = logging.getLogger(__name__)


# ── Hardware snapshot ──────────────────────────────────────────────────────────

@dataclass
class HardwareSnapshot:
    """Detected hardware characteristics of the current machine."""
    ram_gb: float = 0.0
    vram_gb: float = 0.0
    cpu_arch: str = ""          # "x86_64" | "arm64" | "armv7" | "armv6"
    os_name: str = ""           # "windows" | "linux" | "macos" | "android"
    cpu_count: int = 1
    gpu_name: str | None = None
    has_cuda: bool = False
    has_vulkan: bool = False
    has_directml: bool = False
    has_rocm: bool = False
    is_arm: bool = False
    is_raspberry_pi: bool = False
    is_mobile: bool = False

    def __str__(self) -> str:
        return (
            f"HardwareSnapshot(ram={self.ram_gb:.1f}GB, vram={self.vram_gb:.1f}GB, "
            f"arch={self.cpu_arch}, os={self.os_name}, cuda={self.has_cuda}, "
            f"pi={self.is_raspberry_pi})"
        )


class HardwareDetector:
    """
    Detects current machine hardware. Uses psutil if available,
    with graceful fallback to platform/os module introspection.
    """

    def detect(self) -> HardwareSnapshot:
        snap = HardwareSnapshot()
        snap.cpu_arch = self._detect_cpu_arch()
        snap.os_name = self._detect_os()
        snap.cpu_count = os.cpu_count() or 1
        snap.is_arm = snap.cpu_arch.startswith("arm") or snap.cpu_arch == "aarch64"
        snap.is_raspberry_pi = self._detect_raspberry_pi()
        snap.is_mobile = self._detect_mobile(snap)
        snap.ram_gb = self._detect_ram_gb()
        snap.vram_gb, snap.gpu_name = self._detect_gpu()
        snap.has_cuda = self._check_cuda()
        snap.has_vulkan = self._check_vulkan()
        snap.has_directml = self._check_directml(snap.os_name)
        snap.has_rocm = self._check_rocm()

        logger.info("Hardware detected: %s", snap)
        return snap

    # ── Individual detectors ───────────────────────────────────────────────────

    @staticmethod
    def _detect_cpu_arch() -> str:
        machine = platform.machine().lower()
        arch_map = {
            "x86_64": "x86_64", "amd64": "x86_64",
            "aarch64": "arm64", "arm64": "arm64",
            "armv7l": "armv7", "armv7": "armv7",
            "armv6l": "armv6", "armv6": "armv6",
        }
        return arch_map.get(machine, machine)

    @staticmethod
    def _detect_os() -> str:
        sys = platform.system().lower()
        if sys == "windows":
            return "windows"
        if sys == "darwin":
            return "macos"
        if sys == "linux":
            # Check for Android via Termux
            if "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ:
                return "android"
            return "linux"
        return sys

    @staticmethod
    def _detect_raspberry_pi() -> bool:
        try:
            with open("/proc/cpuinfo", "r") as f:
                content = f.read().lower()
            return "raspberry pi" in content or "bcm2" in content
        except (OSError, PermissionError):
            return False

    @staticmethod
    def _detect_mobile(snap: HardwareSnapshot) -> bool:
        return snap.os_name == "android" or (snap.is_arm and snap.ram_gb < 4.0)

    @staticmethod
    def _detect_ram_gb() -> float:
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            pass
        # Fallback: /proc/meminfo on Linux
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(re.search(r"\d+", line).group())  # type: ignore[union-attr]
                        return kb / (1024 ** 2)
        except (OSError, AttributeError):
            pass
        # Windows fallback via wmic
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                    capture_output=True, text=True, timeout=5,
                )
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.isdigit():
                        return int(line) / (1024 ** 3)
            except (subprocess.SubprocessError, OSError, ValueError):
                pass
        logger.warning("Could not detect RAM — assuming 4GB")
        return 4.0

    @staticmethod
    def _detect_gpu() -> tuple[float, str | None]:
        """Returns (vram_gb, gpu_name). Returns (0.0, None) if no GPU detected."""
        # Try nvidia-smi first (CUDA GPUs)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                line = result.stdout.strip().split("\n")[0]
                parts = line.split(",")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    vram_mb = float(parts[1].strip())
                    return vram_mb / 1024.0, name
        except (subprocess.SubprocessError, OSError, ValueError):
            pass

        # Try ROCm (AMD)
        try:
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram", "--json"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                # rocm-smi JSON structure varies; attempt first GPU
                for key, val in data.items():
                    if isinstance(val, dict):
                        total = val.get("VRAM Total Memory (B)", 0)
                        if total:
                            return float(total) / (1024 ** 3), f"AMD GPU ({key})"
        except (subprocess.SubprocessError, OSError, ValueError, Exception):
            pass

        # Try wmic on Windows for integrated/discrete GPU
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM"],
                    capture_output=True, text=True, timeout=5,
                )
                lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "Name" not in l]
                if lines:
                    parts = lines[0].rsplit(None, 1)
                    name = parts[0].strip() if len(parts) > 1 else lines[0]
                    try:
                        vram_bytes = int(parts[1]) if len(parts) > 1 else 0
                        return vram_bytes / (1024 ** 3), name
                    except ValueError:
                        return 0.0, name
            except (subprocess.SubprocessError, OSError):
                pass

        return 0.0, None

    @staticmethod
    def _check_cuda() -> bool:
        try:
            result = subprocess.run(
                ["nvidia-smi"], capture_output=True, timeout=3,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            pass
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            pass
        return False

    @staticmethod
    def _check_vulkan() -> bool:
        # Check for vulkaninfo or presence of Vulkan libraries
        try:
            result = subprocess.run(
                ["vulkaninfo", "--summary"], capture_output=True, timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            pass
        # Check for library presence
        for lib in ["/usr/lib/libvulkan.so", "/usr/lib/x86_64-linux-gnu/libvulkan.so.1"]:
            if Path(lib).exists():
                return True
        return False

    @staticmethod
    def _check_directml(os_name: str) -> bool:
        if os_name != "windows":
            return False
        try:
            import ctypes
            ctypes.windll.LoadLibrary("DirectML.dll")  # type: ignore[attr-defined]
            return True
        except (OSError, AttributeError):
            pass
        return False

    @staticmethod
    def _check_rocm() -> bool:
        try:
            result = subprocess.run(["rocm-smi"], capture_output=True, timeout=3)
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False


# ── Profile selection ──────────────────────────────────────────────────────────

@dataclass
class ProfileMatch:
    """Result of profile auto-detection."""
    profile_id: str
    profile: dict[str, Any]
    hardware: HardwareSnapshot
    confidence: str = "auto"   # "auto" | "manual" | "fallback"
    reason: str = ""


class ProfileSelector:
    """
    Selects the most appropriate hardware profile for the current machine.

    Selection logic:
      - server_gpu:   VRAM >= 24GB AND CUDA/ROCm available
      - desktop_gpu:  VRAM >= 6GB AND GPU backend available
      - desktop_cpu:  RAM >= 6GB AND x86_64 AND not ARM SBC
      - pi_5:         ARM AND RAM >= 2GB
      - phone_low:    ARM AND RAM >= 1GB (mobile/phone class)
      - pi_zero:      ARM AND RAM < 1GB (extreme edge)
    """

    def __init__(self) -> None:
        self._detector = HardwareDetector()

    def auto_select(self) -> ProfileMatch:
        """Detect hardware and return the best matching profile."""
        hw = self._detector.detect()
        profile_id = self._select_id(hw)
        try:
            profile = load_hardware_profile(profile_id)
            reason = self._build_reason(profile_id, hw)
            logger.info("Auto-selected profile: %s (%s)", profile_id, reason)
            return ProfileMatch(
                profile_id=profile_id,
                profile=profile,
                hardware=hw,
                confidence="auto",
                reason=reason,
            )
        except FileNotFoundError:
            logger.warning("Profile %s not found — falling back to desktop_cpu", profile_id)
            profile = load_hardware_profile("desktop_cpu")
            return ProfileMatch(
                profile_id="desktop_cpu",
                profile=profile,
                hardware=hw,
                confidence="fallback",
                reason="profile file not found",
            )

    def load(self, profile_id: str) -> ProfileMatch:
        """Load a specific profile by ID."""
        hw = self._detector.detect()
        profile = load_hardware_profile(profile_id)
        return ProfileMatch(
            profile_id=profile_id,
            profile=profile,
            hardware=hw,
            confidence="manual",
            reason=f"manually specified: {profile_id}",
        )

    @staticmethod
    def _select_id(hw: HardwareSnapshot) -> str:
        if hw.vram_gb >= 24 and (hw.has_cuda or hw.has_rocm):
            return "server_gpu"
        if hw.vram_gb >= 6 and (hw.has_cuda or hw.has_vulkan or hw.has_directml or hw.has_rocm):
            return "desktop_gpu"
        if hw.is_raspberry_pi or (hw.is_arm and not hw.is_mobile):
            if hw.ram_gb >= 2.0:
                return "pi_5"
            return "pi_zero"
        if hw.is_mobile:
            if hw.ram_gb >= 1.0:
                return "phone_low"
            return "pi_zero"
        # x86_64 or mac desktop/laptop
        if hw.ram_gb >= 6.0:
            return "desktop_cpu"
        return "phone_low"  # very low RAM fallback

    @staticmethod
    def _build_reason(profile_id: str, hw: HardwareSnapshot) -> str:
        parts = [f"ram={hw.ram_gb:.1f}GB", f"arch={hw.cpu_arch}"]
        if hw.vram_gb > 0:
            parts.append(f"vram={hw.vram_gb:.1f}GB")
        if hw.has_cuda:
            parts.append("cuda=yes")
        if hw.is_raspberry_pi:
            parts.append("rpi=yes")
        return f"{profile_id} selected [{', '.join(parts)}]"


# ── Generation params from profile ────────────────────────────────────────────

@dataclass
class ResolvedGenerationParams:
    """Generation parameters resolved from a hardware profile."""
    max_response_tokens: int
    temperature: float
    repeat_penalty: float
    top_p: float
    max_refinement_passes: int
    draft_count: int
    max_context_tokens: int
    token_budget_per_turn: int
    quantization: str
    inference_backend: str
    inference_backend_fallbacks: list[str] = field(default_factory=list)
    n_gpu_layers: int = 0      # 0 = CPU only; -1 = all layers on GPU


def resolve_generation_params(profile: dict[str, Any]) -> ResolvedGenerationParams:
    """Extract and resolve generation parameters from a hardware profile dict."""
    hw = profile.get("hardware", {})
    model = profile.get("model", {})
    gen = profile.get("generation", {})

    backend = hw.get("inference_backend", "cpu")
    fallbacks = hw.get("inference_backend_fallback", [])
    quant = model.get("quantization", "q4_k_m")
    vram_gb = hw.get("vram_gb", 0)

    # Determine n_gpu_layers based on VRAM and backend
    if backend == "cpu":
        n_gpu_layers = 0
    elif vram_gb >= 24:
        n_gpu_layers = -1  # full GPU offload
    elif vram_gb >= 12:
        n_gpu_layers = 40  # partial offload for 13B models
    elif vram_gb >= 6:
        n_gpu_layers = 20
    else:
        n_gpu_layers = 0

    return ResolvedGenerationParams(
        max_response_tokens=gen.get("max_response_tokens", 250),
        temperature=gen.get("temperature", 0.7),
        repeat_penalty=gen.get("repeat_penalty", 1.1),
        top_p=gen.get("top_p", 0.9),
        max_refinement_passes=gen.get("max_refinement_passes", 2),
        draft_count=model.get("draft_count", 3),
        max_context_tokens=model.get("max_context_tokens", 4096),
        token_budget_per_turn=model.get("token_budget_per_turn", 250),
        quantization=quant,
        inference_backend=backend,
        inference_backend_fallbacks=fallbacks,
        n_gpu_layers=n_gpu_layers,
    )
