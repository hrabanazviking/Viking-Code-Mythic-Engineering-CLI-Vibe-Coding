"""Tests for the routing runtime / fallback chain (PH-08 slice 8.3).

Also covers the PH-08 follow-up wire-up of ``cmd_ai_run`` —
fallback on by default, ``--no-fallback`` preserves the legacy
direct-``provider.run`` path.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.ai.providers.base import ProviderResponse, ProviderStatus
from mythic_vibe_cli.ai.router import RouteDecision, RoutingRule
from mythic_vibe_cli.ai.routing_runtime import (
    FallbackAttempt,
    FallbackResult,
    _route_chain,
    run_with_fallback,
)


# ---- Fake provider helpers --------------------------------------------


@dataclass
class _FakeProvider:
    """Minimal duck-typed provider: configurable status + injectable
    failure mode for fallback testing."""

    name: str
    configured: bool = True
    raise_on_run: BaseException | None = None
    response_content: str = ""
    model: str = ""

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(
            configured=self.configured,
            details=[f"{self.name} (test)"],
        )

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        if self.raise_on_run is not None:
            raise self.raise_on_run
        return ProviderResponse(
            provider=self.name,
            model=self.model or f"{self.name}-test",
            content=self.response_content or f"reply from {self.name}",
            packet_id="PKT-TEST",
            dry_run=dry_run,
            usage={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
            metadata={"source": "test"},
        )


def _build_resolver(*providers: _FakeProvider):
    table = {p.name: p for p in providers}
    # copy-paste is the always-available terminal fallback; if a test
    # didn't supply one, inject a default that just succeeds.
    if "copy-paste" not in table:
        table["copy-paste"] = _FakeProvider(
            name="copy-paste",
            configured=True,
            response_content="copy-paste reply",
        )

    def resolver(name: str) -> _FakeProvider | None:
        return table.get(name)

    return resolver


def _decision(
    provider: str = "anthropic",
    fallbacks: tuple[str, ...] = ("openai", "copy-paste"),
) -> RouteDecision:
    return RouteDecision(
        provider=provider,
        model=f"{provider}-test",
        rule_matched=RoutingRule(provider=provider, fallbacks=fallbacks),
        fallbacks=fallbacks,
        reasons=("test rule matched",),
        role="Forge Worker",
        task_type="build",
    )


# ---- _coerce_chain / _route_chain -------------------------------------


class RouteChainTests(unittest.TestCase):
    def test_chain_starts_with_primary_then_fallbacks(self) -> None:
        decision = _decision("anthropic", ("openai", "copy-paste"))
        chain = list(_route_chain(decision))
        self.assertEqual(
            chain,
            [
                ("anthropic", "anthropic-test"),
                ("openai", ""),
                ("copy-paste", ""),
            ],
        )

    def test_chain_dedupes_repeated_provider_model_entries(self) -> None:
        decision = _decision("anthropic", ("anthropic", "openai", "openai"))
        chain = list(_route_chain(decision))
        self.assertEqual(
            chain,
            [
                ("anthropic", "anthropic-test"),
                ("anthropic", ""),
                ("openai", ""),
                ("copy-paste", "manual"),
            ],
        )

    def test_chain_appends_copy_paste_when_missing(self) -> None:
        decision = _decision("anthropic", ("openai",))
        chain = list(_route_chain(decision))
        self.assertEqual(chain[-1], ("copy-paste", "manual"))

    def test_chain_does_not_double_append_copy_paste(self) -> None:
        decision = _decision("copy-paste", ())
        chain = list(_route_chain(decision))
        self.assertEqual(chain, [("copy-paste", "copy-paste-test")])

    def test_chain_splits_provider_model_specs(self) -> None:
        decision = _decision(
            "anthropic",
            ("openrouter|anthropic/claude-sonnet-4-6", "copy-paste|manual"),
        )
        chain = list(_route_chain(decision))
        self.assertEqual(
            chain,
            [
                ("anthropic", "anthropic-test"),
                ("openrouter", "anthropic/claude-sonnet-4-6"),
                ("copy-paste", "manual"),
            ],
        )


# ---- run_with_fallback happy paths -----------------------------------


class RunWithFallbackHappyPathTests(unittest.TestCase):
    def test_primary_succeeds_no_fallback(self) -> None:
        resolver = _build_resolver(
            _FakeProvider(name="anthropic", configured=True),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = run_with_fallback(
                _decision(),
                packet={"text": "hi"},
                resolver=resolver,
                root=Path(tmp),
            )
        self.assertEqual(result.used_provider, "anthropic")
        self.assertEqual(result.primary_provider, "anthropic")
        self.assertFalse(result.fell_back)
        self.assertEqual(len(result.attempts), 1)
        self.assertTrue(result.attempts[0].succeeded)
        self.assertEqual(result.response.provider, "anthropic")
        self.assertEqual(result.response.model, "anthropic-test")
        self.assertEqual(result.attempts[0].model, "anthropic-test")

    def test_falls_through_unconfigured_to_next(self) -> None:
        resolver = _build_resolver(
            _FakeProvider(name="anthropic", configured=False),
            _FakeProvider(name="openai", configured=True),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = run_with_fallback(
                _decision("anthropic", ("openai", "copy-paste")),
                packet={"text": "hi"},
                resolver=resolver,
                root=Path(tmp),
            )
        self.assertEqual(result.used_provider, "openai")
        self.assertTrue(result.fell_back)
        # Two attempts: anthropic skipped, openai succeeded.
        self.assertEqual(len(result.attempts), 2)
        self.assertFalse(result.attempts[0].succeeded)
        self.assertEqual(result.attempts[0].model, "anthropic-test")
        self.assertEqual(
            result.attempts[0].skipped_reason, "provider not configured"
        )
        self.assertTrue(result.attempts[1].succeeded)

    def test_fallback_model_spec_sets_provider_model(self) -> None:
        resolver = _build_resolver(
            _FakeProvider(
                name="anthropic",
                configured=True,
                raise_on_run=ConnectionError("offline"),
            ),
            _FakeProvider(name="openrouter", configured=True),
        )
        decision = _decision(
            "anthropic",
            ("openrouter|anthropic/claude-sonnet-4-6", "copy-paste"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = run_with_fallback(
                decision,
                packet={"text": "hi"},
                resolver=resolver,
                root=Path(tmp),
            )

        self.assertEqual(result.used_provider, "openrouter")
        self.assertTrue(result.fell_back)
        self.assertEqual(result.response.model, "anthropic/claude-sonnet-4-6")
        self.assertEqual(result.attempts[1].model, "anthropic/claude-sonnet-4-6")

    def test_falls_through_run_exception_to_next(self) -> None:
        resolver = _build_resolver(
            _FakeProvider(
                name="anthropic",
                configured=True,
                raise_on_run=ConnectionError("boom"),
            ),
            _FakeProvider(name="openai", configured=True),
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = run_with_fallback(
                _decision(),
                packet={"text": "hi"},
                resolver=resolver,
                root=Path(tmp),
            )
        self.assertEqual(result.used_provider, "openai")
        self.assertEqual(result.attempts[0].error, "boom")
        self.assertFalse(result.attempts[0].succeeded)

    def test_unknown_provider_name_skipped(self) -> None:
        # Decision references a provider the resolver doesn't know.
        resolver = _build_resolver(
            _FakeProvider(name="copy-paste"),
        )
        decision = _decision("phantom", ("ghost", "copy-paste"))
        with tempfile.TemporaryDirectory() as tmp:
            result = run_with_fallback(
                decision,
                packet={"text": "hi"},
                resolver=resolver,
                root=Path(tmp),
            )
        self.assertEqual(result.used_provider, "copy-paste")
        # Three attempts: phantom (unknown), ghost (unknown),
        # copy-paste (success).
        self.assertEqual(len(result.attempts), 3)
        self.assertEqual(
            result.attempts[0].skipped_reason, "unknown provider name"
        )
        self.assertEqual(
            result.attempts[1].skipped_reason, "unknown provider name"
        )
        self.assertTrue(result.attempts[2].succeeded)

    def test_validate_config_raise_does_not_crash(self) -> None:
        class _Misbehaving:
            name = "broken"

            def validate_config(self):
                raise RuntimeError("status oops")

            def run(self, packet, *, dry_run=False):
                raise AssertionError("should not be called")

        broken = _Misbehaving()
        copy_paste_fallback = _FakeProvider(name="copy-paste")

        def resolver(name: str):
            return broken if name == "broken" else copy_paste_fallback

        with tempfile.TemporaryDirectory() as tmp:
            result = run_with_fallback(
                _decision("broken", ("copy-paste",)),
                packet={"text": "hi"},
                resolver=resolver,
                root=Path(tmp),
            )
        self.assertEqual(result.used_provider, "copy-paste")
        self.assertEqual(len(result.attempts), 2)
        self.assertIn("validate_config raised", result.attempts[0].error)


# ---- Telemetry recording ---------------------------------------------


class FallbackTelemetryTests(unittest.TestCase):
    def test_each_attempt_writes_routing_attempt_to_ledger(self) -> None:
        resolver = _build_resolver(
            _FakeProvider(name="anthropic", configured=False),
            _FakeProvider(name="openai", configured=True),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_with_fallback(
                _decision("anthropic", ("openai", "copy-paste")),
                packet={"text": "hi"},
                resolver=resolver,
                root=root,
            )
            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            entries = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        # Two routing-attempt entries — the skip + the success.
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertTrue(entry.get("routing_attempt"))
            self.assertEqual(entry["from_provider"], "anthropic")
        self.assertEqual(entries[0]["to_provider"], "anthropic")
        self.assertEqual(entries[0]["model"], "anthropic-test")
        self.assertEqual(entries[1]["to_provider"], "openai")
        self.assertEqual(entries[1]["model"], "")
        self.assertTrue(entries[1]["succeeded"])

    def test_packet_id_recorded_on_success(self) -> None:
        resolver = _build_resolver(
            _FakeProvider(
                name="copy-paste",
                response_content="manual reply",
            ),
        )
        decision = _decision("copy-paste", ())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_with_fallback(
                decision,
                packet={"text": "hi"},
                resolver=resolver,
                root=root,
            )
            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            entries = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["packet_id"], "PKT-TEST")


# ---- Result dataclasses ----------------------------------------------


class FallbackResultDataclassTests(unittest.TestCase):
    def test_attempt_to_dict(self) -> None:
        a = FallbackAttempt(
            provider="x", model="m", succeeded=False, error="oops", skipped_reason=""
        )
        payload = a.to_dict()
        self.assertEqual(payload["provider"], "x")
        self.assertEqual(payload["model"], "m")
        self.assertFalse(payload["succeeded"])
        self.assertEqual(payload["error"], "oops")

    def test_result_to_dict(self) -> None:
        response = ProviderResponse(
            provider="ollama",
            model="llama",
            content="ok",
            packet_id="PKT-1",
            dry_run=False,
            usage={"total_tokens": 5},
            metadata={"endpoint": "http://x"},
        )
        result = FallbackResult(
            response=response,
            used_provider="ollama",
            primary_provider="anthropic",
            attempts=(
                FallbackAttempt(
                    provider="anthropic",
                    model="claude",
                    succeeded=False,
                    error="boom",
                ),
            ),
        )
        payload = result.to_dict()
        self.assertTrue(payload["fell_back"])
        self.assertEqual(payload["primary_provider"], "anthropic")
        self.assertEqual(payload["used_provider"], "ollama")
        self.assertEqual(payload["response"]["provider"], "ollama")
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["attempts"][0]["model"], "claude")


# ---- cmd_ai_run integration (PH-08 follow-up) ------------------------


class _FakeRegistry:
    """Test double for :class:`ProviderRegistry`. Holds a fixed
    name → fake-provider mapping and exposes the same
    ``providers()`` shape ``cmd_ai_run`` consumes."""

    def __init__(self, providers: dict[str, _FakeProvider]) -> None:
        self._providers = providers

    def providers(self) -> dict[str, _FakeProvider]:
        # Returns a fresh dict each call to mirror the real registry's
        # behaviour — `cmd_ai_run` and `run_with_fallback` may both
        # call providers() and the real implementation rebuilds.
        return dict(self._providers)


class _RealResponseProvider:
    """Wraps a :class:`_FakeProvider` to surface a non-dry-run
    :class:`ProviderResponse` so the conversation-recording path
    fires under integration tests."""

    def __init__(self, name: str, *, configured: bool = True) -> None:
        self.name = name
        self._configured = configured

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=self._configured, details=[f"{self.name} (test)"])

    def estimate(self, packet: object) -> object:  # pragma: no cover — trivial
        class _E:
            cost_usd = 0.0
        return _E()

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            model=f"{self.name}-test",
            content=f"reply from {self.name}",
            packet_id="PKT-TEST",
            dry_run=False,  # real-call shape: forces conversation log
            usage={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
            metadata={"source": "real-test"},
        )


def _ai_run_namespace(**overrides: object) -> argparse.Namespace:
    base = dict(
        path=".",
        provider="anthropic",
        packet="hello",
        json=True,
        dry_run=False,
        conversation_id="",
        no_record=False,
        no_fallback=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


class CmdAiRunFallbackTests(unittest.TestCase):
    """Integration: ``cmd_ai_run`` routes through ``run_with_fallback``
    by default and falls back to copy-paste on primary failure."""

    def test_default_path_records_no_fallback_when_primary_succeeds(self) -> None:
        from mythic_vibe_cli import commands as cmd_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _FakeRegistry(
                {
                    "anthropic": _RealResponseProvider("anthropic"),
                    "copy-paste": _RealResponseProvider("copy-paste"),
                }
            )
            ns = _ai_run_namespace(path=str(root))
            buf = io.StringIO()
            with mock.patch.object(cmd_module, "_ai_registry", return_value=registry):
                with redirect_stdout(buf):
                    exit_code = cmd_module.cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["fallback_enabled"])
        self.assertFalse(payload["fell_back"])
        self.assertEqual(payload["primary_provider"], "anthropic")
        self.assertEqual(payload["used_provider"], "anthropic")
        # One attempt, succeeded.
        self.assertEqual(len(payload["fallback_attempts"]), 1)
        self.assertTrue(payload["fallback_attempts"][0]["succeeded"])
        self.assertEqual(payload["response"]["provider"], "anthropic")

    def test_primary_failure_falls_forward_to_copy_paste(self) -> None:
        from mythic_vibe_cli import commands as cmd_module

        # Primary raises; copy-paste catches.
        anthropic = _FakeProvider(
            name="anthropic",
            configured=True,
            raise_on_run=ConnectionError("offline"),
        )
        # Use _FakeProvider for copy-paste too — its `run` returns a
        # dry_run=False response (default _FakeProvider behaviour
        # doesn't set dry_run, so ProviderResponse defaults to False).
        copy_paste = _RealResponseProvider("copy-paste")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _FakeRegistry({"anthropic": anthropic, "copy-paste": copy_paste})
            ns = _ai_run_namespace(path=str(root))
            buf = io.StringIO()
            with mock.patch.object(cmd_module, "_ai_registry", return_value=registry):
                with redirect_stdout(buf):
                    exit_code = cmd_module.cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["fell_back"])
        self.assertEqual(payload["primary_provider"], "anthropic")
        self.assertEqual(payload["used_provider"], "copy-paste")
        # Two attempts: anthropic raised, copy-paste succeeded.
        attempts = payload["fallback_attempts"]
        self.assertEqual(len(attempts), 2)
        self.assertFalse(attempts[0]["succeeded"])
        self.assertEqual(attempts[0]["error"], "offline")
        self.assertTrue(attempts[1]["succeeded"])

    def test_unconfigured_primary_with_fallback_does_not_block(self) -> None:
        """Legacy behaviour: unconfigured primary + non-dry-run = USER_INPUT_ERROR.
        With fallback on, the runtime walks past unconfigured providers
        onto copy-paste; we must not return USER_INPUT_ERROR."""
        from mythic_vibe_cli import commands as cmd_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _FakeRegistry(
                {
                    "anthropic": _RealResponseProvider(
                        "anthropic", configured=False
                    ),
                    "copy-paste": _RealResponseProvider("copy-paste"),
                }
            )
            ns = _ai_run_namespace(path=str(root))
            buf = io.StringIO()
            with mock.patch.object(cmd_module, "_ai_registry", return_value=registry):
                with redirect_stdout(buf):
                    exit_code = cmd_module.cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["fell_back"])
        self.assertEqual(payload["used_provider"], "copy-paste")

    def test_no_fallback_flag_blocks_unconfigured_primary(self) -> None:
        """With ``--no-fallback`` set and an unconfigured provider on
        a non-dry-run, the legacy USER_INPUT_ERROR path fires."""
        from mythic_vibe_cli import commands as cmd_module
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _FakeRegistry(
                {
                    "anthropic": _RealResponseProvider(
                        "anthropic", configured=False
                    ),
                    "copy-paste": _RealResponseProvider("copy-paste"),
                }
            )
            ns = _ai_run_namespace(path=str(root), no_fallback=True)
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(cmd_module, "_ai_registry", return_value=registry):
                from contextlib import redirect_stderr
                with redirect_stderr(stderr), redirect_stdout(stdout):
                    exit_code = cmd_module.cmd_ai_run(ns)

        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("Provider not configured", stderr.getvalue())

    def test_no_fallback_flag_calls_provider_directly(self) -> None:
        """With ``--no-fallback`` and a configured provider, the
        legacy ``provider.run`` path fires — fallback fields show
        the chain was disabled."""
        from mythic_vibe_cli import commands as cmd_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _FakeRegistry(
                {
                    "anthropic": _RealResponseProvider("anthropic"),
                    "copy-paste": _RealResponseProvider("copy-paste"),
                }
            )
            ns = _ai_run_namespace(path=str(root), no_fallback=True)
            buf = io.StringIO()
            with mock.patch.object(cmd_module, "_ai_registry", return_value=registry):
                with redirect_stdout(buf):
                    exit_code = cmd_module.cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertFalse(payload["fallback_enabled"])
        self.assertFalse(payload["fell_back"])
        self.assertEqual(payload["used_provider"], "anthropic")
        # Empty attempts list — the runtime was not invoked.
        self.assertEqual(payload["fallback_attempts"], [])


class CmdAiRunArgparseTests(unittest.TestCase):
    def test_no_fallback_flag_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(
            ["ai", "run", "--provider", "copy-paste", "--packet", "hi", "--no-fallback"]
        )
        self.assertTrue(ns.no_fallback)

    def test_no_fallback_default_false(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(
            ["ai", "run", "--provider", "copy-paste", "--packet", "hi"]
        )
        self.assertFalse(ns.no_fallback)


if __name__ == "__main__":
    unittest.main()
