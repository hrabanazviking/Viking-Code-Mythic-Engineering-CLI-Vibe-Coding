"""Daily cost guards (PH-08 slice 8.2).

Reads the per-call ledger at ``mythic/ai/provider_calls.jsonl``,
sums today's UTC ``observed_cost_usd`` across every provider, and
returns a typed :class:`BudgetCheck` saying whether a projected
new call would push the day's spend past the configured cap.

Cap configuration:

- ``MYTHIC_DAILY_COST_CAP_USD`` env var (positive float). When
  unset / non-positive / unparseable, the guard is **disabled**
  and :func:`check_budget` always returns ``allowed=True``.
- :func:`check_budget`'s ``cap_usd_override`` parameter wins over
  the env var (used by tests + future config-file integration).

Design choices:

- **Today = UTC date.** Per-call timestamps are written in UTC by
  every provider (slice 6.5), so date math is straightforward.
- **Best-effort.** Missing or corrupt ledger lines silently
  contribute 0; the guard never raises.
- **Pure read.** No state mutation — the guard answers "may I
  proceed?", it does not deduct or pre-record. The actual call's
  cost lands in the ledger via the provider's existing
  ``write_provider_log`` path.

Cross-platform: stdlib only.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COST_CAP_ENV = "MYTHIC_DAILY_COST_CAP_USD"
LEDGER_PATH = ("mythic", "ai", "provider_calls.jsonl")


def _today_utc_prefix() -> str:
    """Return the YYYY-MM-DD prefix that every today-UTC timestamp
    starts with (the ledger writes ISO-8601 strings via
    :func:`utc_now`)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_cap_env(raw: str | None) -> float:
    """Return the env-var-provided cap, or 0.0 when unset/invalid.

    Zero / negative / unparseable values disable the guard — the
    operator must explicitly opt in.
    """
    if not raw:
        return 0.0
    try:
        cap = float(raw.strip())
    except (TypeError, ValueError):
        return 0.0
    if cap <= 0.0:
        return 0.0
    return cap


def _ledger_path(root: Path) -> Path:
    return Path(root).joinpath(*LEDGER_PATH)


def _extract_observed_cost(entry: dict[str, Any]) -> float:
    """Pull ``observed_cost_usd`` from a ledger entry. The provider
    base writes it under ``response.metadata`` (PH-06 contract), so
    we look there first; ``metadata`` at the top level is a
    secondary path. Anything else returns 0.0."""
    response = entry.get("response")
    if isinstance(response, dict):
        meta = response.get("metadata")
        if isinstance(meta, dict):
            cost = meta.get("observed_cost_usd")
            if isinstance(cost, (int, float)):
                return float(cost)
    top_meta = entry.get("metadata")
    if isinstance(top_meta, dict):
        cost = top_meta.get("observed_cost_usd")
        if isinstance(cost, (int, float)):
            return float(cost)
    return 0.0


def compute_today_spend_usd(root: Path) -> float:
    """Sum ``observed_cost_usd`` across today-UTC ledger entries.

    Returns 0.0 when the ledger file doesn't exist or is empty.
    Best-effort: corrupt / non-dict / non-today entries contribute
    0 silently.
    """
    path = _ledger_path(root)
    if not path.is_file():
        return 0.0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0.0
    today_prefix = _today_utc_prefix()
    total = 0.0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        timestamp = entry.get("timestamp", "")
        if not isinstance(timestamp, str) or not timestamp.startswith(today_prefix):
            continue
        total += _extract_observed_cost(entry)
    return total


@dataclass(frozen=True)
class BudgetCheck:
    """Result of :func:`check_budget`.

    ``allowed`` is ``True`` when (a) the cap is disabled (``cap_usd
    <= 0``), or (b) ``today_spent_usd + projected_cost_usd`` does
    not exceed the cap. ``reason`` is a human-readable string for
    CLI / log surfaces.
    """

    allowed: bool
    today_spent_usd: float
    cap_usd: float
    projected_cost_usd: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "today_spent_usd": self.today_spent_usd,
            "cap_usd": self.cap_usd,
            "projected_cost_usd": self.projected_cost_usd,
            "reason": self.reason,
        }


def check_budget(
    root: Path,
    projected_cost_usd: float = 0.0,
    *,
    cap_usd_override: float | None = None,
) -> BudgetCheck:
    """Decide whether a projected new call may proceed.

    Args:
        root: Project directory.
        projected_cost_usd: The estimate the caller plans to spend
            on the next call (typically
            ``Estimate.cost_usd`` from the provider's pre-call
            estimator).
        cap_usd_override: Tests / config-file integration pass this
            to bypass the env var. ``None`` means "use the env var".
    """
    if cap_usd_override is None:
        cap = _parse_cap_env(os.environ.get(COST_CAP_ENV))
    else:
        cap = max(0.0, float(cap_usd_override))

    today_spent = compute_today_spend_usd(root)
    projected_total = today_spent + max(0.0, float(projected_cost_usd))

    if cap <= 0.0:
        return BudgetCheck(
            allowed=True,
            today_spent_usd=today_spent,
            cap_usd=0.0,
            projected_cost_usd=projected_cost_usd,
            reason="no daily cap configured (set MYTHIC_DAILY_COST_CAP_USD to enable)",
        )

    if projected_total <= cap:
        return BudgetCheck(
            allowed=True,
            today_spent_usd=today_spent,
            cap_usd=cap,
            projected_cost_usd=projected_cost_usd,
            reason=(
                f"within cap (today_spent=${today_spent:.4f} + "
                f"projected=${projected_cost_usd:.4f} <= cap=${cap:.4f})"
            ),
        )

    return BudgetCheck(
        allowed=False,
        today_spent_usd=today_spent,
        cap_usd=cap,
        projected_cost_usd=projected_cost_usd,
        reason=(
            f"daily cap exceeded: today_spent=${today_spent:.4f} + "
            f"projected=${projected_cost_usd:.4f} > cap=${cap:.4f}. "
            f"Override with MYTHIC_DAILY_COST_CAP_USD or use --dry-run."
        ),
    )


__all__ = [
    "COST_CAP_ENV",
    "LEDGER_PATH",
    "BudgetCheck",
    "check_budget",
    "compute_today_spend_usd",
]
