"""Phase 19.1 (audit remediation 2026-05-02) — JSON contract
snapshot tests.

Locks JSON-shaped CLI output against fixtures so accidental schema
changes (renamed keys, removed fields, type swaps, value drift)
are caught at CI time.

Coverage:

- ``ai models --provider <name> --json`` for each of Anthropic /
  OpenAI / Gemini / OpenRouter — these are highly deterministic
  (drawn from the static catalog in
  ``mythic_vibe_cli/ai/providers/model_catalog.py``) and form a
  contract with downstream tooling.

This file is the seed for follow-up snapshot work — additional
commands (``status --json``, ``doctor --json``,
``forge ledger latest --json``, etc.) get added as they're
identified and stabilised. The :mod:`tests._snapshot` helper
provides the comparison + bootstrap + update-on-demand machinery.

Updating fixtures intentionally::

    MYTHIC_SNAPSHOT_UPDATE=1 pytest tests/test_json_snapshots.py

The first run of any new test bootstraps its fixture
automatically — no env var needed.
"""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from mythic_vibe_cli import app

from tests._snapshot import assert_json_snapshot


def _run_cli_json(argv: list[str]) -> dict:
    """Invoke ``app.main(argv)`` capturing stdout, return parsed
    JSON. Raises if exit code is non-zero or stdout isn't valid
    JSON — both are bugs we want to surface."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = app.main(argv)
    if code != 0:
        raise AssertionError(
            f"CLI exited {code} for argv={argv!r}; stdout={buf.getvalue()!r}"
        )
    text = buf.getvalue()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI output for argv={argv!r} was not valid JSON: {exc}\n"
            f"stdout={text!r}"
        )


class AiModelsCatalogSnapshotTests(unittest.TestCase):
    """Each provider's static catalog is the v1.0 contract for
    downstream tooling that consumes ``ai models --json``. Snap it
    so any drift surfaces explicitly in PRs."""

    def setUp(self) -> None:
        # Clear any inherited API-key env vars so the ``configured``
        # / ``details`` portions of the response are deterministic
        # regardless of where the test runs (operator's machine vs
        # a clean CI box).
        self._env_patcher = mock.patch.dict(
            "os.environ",
            {
                "ANTHROPIC_API_KEY": "",
                "OPENAI_API_KEY": "",
                "GEMINI_API_KEY": "",
                "GOOGLE_API_KEY": "",
                "OPENROUTER_API_KEY": "",
            },
            clear=False,
        )
        self._env_patcher.start()

    def tearDown(self) -> None:
        self._env_patcher.stop()

    def test_anthropic_static_catalog_snapshot(self) -> None:
        payload = _run_cli_json(
            ["ai", "models", "--provider", "anthropic", "--json"]
        )
        assert_json_snapshot("ai_models_anthropic_static", payload)

    def test_openai_static_catalog_snapshot(self) -> None:
        payload = _run_cli_json(
            ["ai", "models", "--provider", "openai", "--json"]
        )
        assert_json_snapshot("ai_models_openai_static", payload)

    def test_gemini_static_catalog_snapshot(self) -> None:
        payload = _run_cli_json(
            ["ai", "models", "--provider", "gemini", "--json"]
        )
        assert_json_snapshot("ai_models_gemini_static", payload)

    def test_openrouter_static_catalog_snapshot(self) -> None:
        payload = _run_cli_json(
            ["ai", "models", "--provider", "openrouter", "--json"]
        )
        assert_json_snapshot("ai_models_openrouter_static", payload)


class SnapshotHelperSelfTests(unittest.TestCase):
    """Sanity-check the snapshot helper itself — bootstrap, mismatch
    detection, and the MYTHIC_SNAPSHOT_UPDATE override."""

    def test_normalize_replaces_timestamps(self) -> None:
        from tests._snapshot import normalize

        out = normalize({"created_at": "2026-05-02T19:43:21Z"})
        self.assertEqual(out, {"created_at": "<TIMESTAMP>"})

    def test_normalize_replaces_uuids(self) -> None:
        from tests._snapshot import normalize

        out = normalize({"id": "12345678-abcd-1234-5678-abcdef123456"})
        self.assertEqual(out, {"id": "<UUID>"})

    def test_normalize_walks_nested_structures(self) -> None:
        from tests._snapshot import normalize

        out = normalize({
            "items": [
                {"ts": "2026-05-02T19:43:21Z"},
                {"ts": "2026-05-03T00:00:00Z"},
            ]
        })
        self.assertEqual(
            out,
            {"items": [{"ts": "<TIMESTAMP>"}, {"ts": "<TIMESTAMP>"}]},
        )

    def test_assert_json_snapshot_bootstrap_then_match(self) -> None:
        """First call writes the fixture; second call asserts byte
        equality. We use a temp snapshot name + cleanup."""
        import tempfile

        from tests import _snapshot

        # Redirect SNAPSHOTS_DIR to a temp dir for isolation.
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                _snapshot, "SNAPSHOTS_DIR", _snapshot.Path(tmp)
            ):
                payload = {"a": 1, "b": [2, 3]}
                # First call — bootstrap, no comparison.
                _snapshot.assert_json_snapshot("self_test", payload)
                # Second call with same payload — must pass.
                _snapshot.assert_json_snapshot("self_test", payload)
                # Third call with different payload — must fail.
                with self.assertRaises(AssertionError) as ctx:
                    _snapshot.assert_json_snapshot(
                        "self_test", {"a": 1, "b": [2, 4]}
                    )
                self.assertIn("snapshot mismatch", str(ctx.exception))

    def test_update_env_overwrites_existing_snapshot(self) -> None:
        import tempfile

        from tests import _snapshot

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                _snapshot, "SNAPSHOTS_DIR", _snapshot.Path(tmp)
            ):
                # Bootstrap with original payload.
                _snapshot.assert_json_snapshot("update_test", {"v": 1})
                # Set update env var, write a different payload.
                with mock.patch.dict(
                    "os.environ",
                    {_snapshot.UPDATE_ENV: "1"},
                    clear=False,
                ):
                    _snapshot.assert_json_snapshot("update_test", {"v": 2})
                # Without the env var, the new fixture is now the
                # baseline — assertion against {"v": 2} passes.
                _snapshot.assert_json_snapshot("update_test", {"v": 2})
                # And the OLD payload now mismatches.
                with self.assertRaises(AssertionError):
                    _snapshot.assert_json_snapshot("update_test", {"v": 1})


if __name__ == "__main__":
    unittest.main()
