"""JSON contract snapshot helper (Phase 19.1, audit remediation 2026-05-02).

Compares JSON-shaped CLI output against fixtures stored in
``tests/snapshots/<name>.json``. Locks the JSON contract so
accidental schema changes are caught at CI time.

Usage::

    from tests._snapshot import assert_json_snapshot

    def test_ai_models_anthropic_snapshot(self):
        result = run_cli(["ai", "models", "--provider", "anthropic", "--json"])
        payload = json.loads(result.stdout)
        assert_json_snapshot("ai_models_anthropic", payload)

Updating fixtures (intentional contract changes)::

    MYTHIC_SNAPSHOT_UPDATE=1 pytest tests/test_json_snapshots.py

The first run of any new snapshot bootstraps the fixture file
automatically — no need to set the env var explicitly. Subsequent
runs assert byte-equality against the stored fixture.

Normalization removes obviously-volatile fields (timestamps, UUIDs)
before comparison so the snapshots stay stable across runs / machines /
clocks. Tests with additional volatile fields (executable paths,
platform strings, etc.) can pre-normalize the payload before calling
``assert_json_snapshot``.
"""

from __future__ import annotations

import difflib
import json
import os
import re
from pathlib import Path
from typing import Any


SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
UPDATE_ENV = "MYTHIC_SNAPSHOT_UPDATE"


# ISO-8601 timestamps (with or without fractional seconds and Z).
_ISO_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?"
)
# Standard 8-4-4-4-12 UUID (case-insensitive).
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def normalize(value: Any) -> Any:
    """Recursively normalize timestamps and UUIDs to placeholder
    strings. Returns a new structure; doesn't mutate the input."""
    if isinstance(value, str):
        out = _ISO_TIMESTAMP_RE.sub("<TIMESTAMP>", value)
        out = _UUID_RE.sub("<UUID>", out)
        return out
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def assert_json_snapshot(name: str, payload: Any) -> None:
    """Compare ``payload`` against the snapshot at
    ``tests/snapshots/<name>.json``. Raises AssertionError with a
    unified diff if they differ.

    On first run (no fixture file exists), bootstraps the snapshot
    by writing the current payload — the test passes.

    Set ``MYTHIC_SNAPSHOT_UPDATE=1`` in the environment to overwrite
    existing snapshots with the current payload. Useful when an
    intentional contract change lands and the fixtures need to
    catch up.
    """
    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    snapshot_path = SNAPSHOTS_DIR / f"{name}.json"

    normalized = normalize(payload)
    serialized = json.dumps(normalized, indent=2, sort_keys=True) + "\n"

    update_requested = os.environ.get(UPDATE_ENV) == "1"
    bootstrap = not snapshot_path.exists()

    if update_requested or bootstrap:
        snapshot_path.write_text(serialized, encoding="utf-8")
        if bootstrap:
            return  # First run — wrote fixture, nothing to compare against.

    expected = snapshot_path.read_text(encoding="utf-8")
    if serialized == expected:
        return

    diff_lines = list(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            serialized.splitlines(keepends=True),
            fromfile=f"snapshots/{name}.json (expected)",
            tofile=f"current ({name})",
        )
    )
    raise AssertionError(
        f"JSON snapshot mismatch for {name!r}.\n"
        f"To update intentionally: MYTHIC_SNAPSHOT_UPDATE=1 pytest <path>\n\n"
        + "".join(diff_lines)
    )


__all__ = [
    "SNAPSHOTS_DIR",
    "UPDATE_ENV",
    "assert_json_snapshot",
    "normalize",
]
