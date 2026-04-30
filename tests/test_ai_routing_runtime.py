"""Tests for the routing runtime / fallback chain (PH-08 slice 8.3)."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

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
            model=f"{self.name}-test",
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
        self.assertEqual(chain, ["anthropic", "openai", "copy-paste"])

    def test_chain_dedupes_repeated_entries(self) -> None:
        decision = _decision("anthropic", ("anthropic", "openai", "openai"))
        chain = list(_route_chain(decision))
        self.assertEqual(chain, ["anthropic", "openai", "copy-paste"])

    def test_chain_appends_copy_paste_when_missing(self) -> None:
        decision = _decision("anthropic", ("openai",))
        chain = list(_route_chain(decision))
        self.assertEqual(chain[-1], "copy-paste")

    def test_chain_does_not_double_append_copy_paste(self) -> None:
        decision = _decision("copy-paste", ())
        chain = list(_route_chain(decision))
        self.assertEqual(chain, ["copy-paste"])


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
        self.assertEqual(
            result.attempts[0].skipped_reason, "provider not configured"
        )
        self.assertTrue(result.attempts[1].succeeded)

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
        self.assertEqual(entries[1]["to_provider"], "openai")
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
            provider="x", succeeded=False, error="oops", skipped_reason=""
        )
        payload = a.to_dict()
        self.assertEqual(payload["provider"], "x")
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
            attempts=(FallbackAttempt(provider="anthropic", succeeded=False, error="boom"),),
        )
        payload = result.to_dict()
        self.assertTrue(payload["fell_back"])
        self.assertEqual(payload["primary_provider"], "anthropic")
        self.assertEqual(payload["used_provider"], "ollama")
        self.assertEqual(payload["response"]["provider"], "ollama")
        self.assertEqual(len(payload["attempts"]), 1)


if __name__ == "__main__":
    unittest.main()
