"""Thor's stability guardrails for timeout and crash resistance."""

from __future__ import annotations

import logging
import hmac
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, TypeVar

from systems.crash_reporting import get_crash_reporter

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class StabilityCircuit:
    """Track repeated failures for one guarded operation."""

    failures: int = 0
    opened_at: float = 0.0
    last_error: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    security_events: int = 0


class ThorGuardian:
    """Thor stands watch over risky operations and deflects crash trolls."""

    def __init__(self, max_failures: int = 3, cooldown_seconds: int = 45, max_retries: int = 2):
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self.max_retries = max_retries
        self._circuits: Dict[str, StabilityCircuit] = {}
        self.crash_reporter = get_crash_reporter()

    def sanitize_text_input(self, text: str, max_length: int = 4000) -> str:
        """Clean untrusted text by stripping control chars and enforcing limits."""
        raw_text = (text or "")[:max(1, max_length)]
        # Huginn clears hidden rune-noise before speech reaches the hall.
        without_nul = raw_text.replace("\x00", "")
        cleaned = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]", "", without_nul)
        return cleaned.strip()

    @staticmethod
    def safe_compare_secrets(expected: str, supplied: str) -> bool:
        """Constant-time secret comparison for tokens and session keys."""
        return hmac.compare_digest(str(expected or ""), str(supplied or ""))

    def is_safe_relative_path(self, base_dir: Path, candidate_name: str, expected_suffix: str = ".yaml") -> bool:
        """Block path traversal and extension confusion for persisted files."""
        try:
            safe_name = self.sanitize_text_input(candidate_name, max_length=96)
            if not safe_name or "/" in safe_name or "\\" in safe_name:
                return False
            if ".." in safe_name or not re.fullmatch(r"[A-Za-z0-9_-]+", safe_name):
                return False
            expected = (base_dir / f"{safe_name}{expected_suffix}").resolve()
            return str(expected).startswith(str(base_dir.resolve()))
        except Exception as exc:
            logger.warning("ThorGuardian path validation failed: %s", exc)
            return False

    def record_security_event(self, key: str, reason: str, metadata: Optional[Dict[str, str]] = None) -> None:
        """Record suspicious behavior without interrupting saga flow."""
        circuit = self._get_circuit(key)
        circuit.security_events += 1
        report_meta = {
            "guard_key": key,
            "reason": reason,
            "security_events": str(circuit.security_events),
        }
        if metadata:
            report_meta.update(metadata)
        self.crash_reporter.report_incident(
            source=f"thor_guardian.security.{key}",
            message="Security guard tripped",
            metadata=report_meta,
        )

    def _get_circuit(self, key: str) -> StabilityCircuit:
        if key not in self._circuits:
            self._circuits[key] = StabilityCircuit()
        return self._circuits[key]

    def _cooling_down(self, circuit: StabilityCircuit) -> bool:
        if circuit.failures < self.max_failures:
            return False
        return (time.time() - circuit.opened_at) < self.cooldown_seconds

    # If a downstream system's OWN circuit is already open, its exception message
    # will contain one of these phrases.  We treat these as pass-through: the
    # underlying service is unavailable, not a new ThorGuardian-level failure, so
    # we return the fallback immediately without burning retry attempts or
    # incrementing our own failure counter.
    _PASSTHROUGH_CIRCUIT_MARKERS: tuple = (
        "circuit is temporarily open",
        "circuit is open",
    )

    def guard(self, key: str, operation: Callable[[], T], fallback: T, metadata: Optional[Dict[str, str]] = None) -> T:
        """Execute operation with retries, circuit-breaker and crash reporting."""
        circuit = self._get_circuit(key)
        if self._cooling_down(circuit):
            logger.warning("ThorGuardian blocked '%s' while circuit cools down.", key)
            return fallback

        attempts = max(1, self.max_retries + 1)
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                result = operation()
                circuit.failures = 0
                circuit.opened_at = 0.0
                circuit.last_error = ""
                return result
            except Exception as exc:
                exc_str = str(exc).lower()
                # Downstream circuit already open — not a new failure on our side.
                if any(marker in exc_str for marker in self._PASSTHROUGH_CIRCUIT_MARKERS):
                    logger.warning(
                        "ThorGuardian: downstream circuit already open for '%s'; returning fallback without counting failure.", key
                    )
                    return fallback

                last_exc = exc
                circuit.failures += 1
                circuit.last_error = str(exc)
                if circuit.failures >= self.max_failures:
                    circuit.opened_at = time.time()

                report_meta = {
                    "guard_key": key,
                    "failures": str(circuit.failures),
                    "attempt": str(attempt),
                }
                if metadata:
                    report_meta.update(metadata)
                self.crash_reporter.report_exception(
                    exc,
                    source=f"thor_guardian.{key}",
                    metadata=report_meta,
                )
                logger.warning("ThorGuardian intercepted failure in '%s' (attempt %s/%s): %s", key, attempt, attempts, exc)

                if attempt < attempts:
                    time.sleep(min(0.35 * attempt + random.random() * 0.2, 1.5))

        if last_exc:
            logger.error("ThorGuardian returned fallback for '%s' after retries: %s", key, last_exc)
        return fallback
