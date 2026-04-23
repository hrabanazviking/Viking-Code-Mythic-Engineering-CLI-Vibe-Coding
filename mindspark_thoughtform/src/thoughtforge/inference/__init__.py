"""
Inference layer — TurboQuant engine + unified backend abstraction.

Supports all hardware tiers from phone/Pi Zero to 70B server GPU.
Quantization: 2-bit, 3-bit, 4-bit, 8-bit, fp16, bf16.
"""

from thoughtforge.inference.unified_backend import (
    GenerationRequest,
    GenerationResponse,
    UnifiedBackend,
    load_backend_from_config,
)

__all__ = [
    "GenerationRequest",
    "GenerationResponse",
    "UnifiedBackend",
    "load_backend_from_config",
]
