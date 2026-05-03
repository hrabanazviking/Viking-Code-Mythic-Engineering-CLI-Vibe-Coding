"""Phase 20.5 (audit remediation 2026-05-03) — provider contract
conformance suite.

Asserts every provider in ``ProviderRegistry`` honors the
documented :class:`AIProvider` Protocol. The tests are
intentionally **shape-checks**, not behavioural — they don't
hit any remote endpoint. The goal: catch the class of
regression where someone adds a provider but forgets to
implement, e.g., ``estimate``, or returns the wrong dataclass
type.

Coverage per provider (parameterised across every entry in
``ProviderRegistry().providers()``):

- Has the ``name`` class attribute.
- ``validate_config()`` returns a :class:`ProviderStatus`.
- ``estimate(packet)`` returns an :class:`Estimate` with
  non-negative integer token counts.
- ``run(packet, dry_run=True)`` returns a
  :class:`ProviderResponse` carrying ``provider``, ``model``,
  ``packet_id``. Dry-run is the safe path that doesn't hit the
  network.
- Optional streaming surface — when present, ``run_stream``
  yields :class:`StreamChunk` items terminating with
  ``done=True``.

Cross-platform: pure stdlib, no API keys required.
"""

from __future__ import annotations

import unittest

from mythic_vibe_cli.ai.providers.base import (
    AIProvider,
    Estimate,
    PacketView,
    ProviderResponse,
    ProviderStatus,
    StreamChunk,
)
from mythic_vibe_cli.ai.registry import ProviderRegistry


def _make_packet() -> PacketView:
    """A trivial packet for conformance pings. Real packets carry
    structured markdown; for shape-checks an inline string is
    enough."""
    return PacketView(
        text="Conformance test packet.",
        packet_id="PKT-CONFORM",
        source="test",
    )


class ProviderRegistryShapeTests(unittest.TestCase):
    """Top-level invariants on the registry itself."""

    def test_providers_dict_is_non_empty(self) -> None:
        providers = ProviderRegistry().providers()
        self.assertGreater(len(providers), 0)

    def test_provider_keys_are_lowercase_strings(self) -> None:
        providers = ProviderRegistry().providers()
        for key in providers:
            self.assertIsInstance(key, str)
            self.assertEqual(key, key.lower())
            self.assertNotIn(" ", key)


class ProviderConformanceTests(unittest.TestCase):
    """One conformance battery per provider. Generated
    dynamically so adding a provider in the registry
    automatically extends coverage without editing this file."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._providers = ProviderRegistry().providers()

    def test_every_provider_has_name_attribute(self) -> None:
        for key, provider in self._providers.items():
            with self.subTest(provider=key):
                name = getattr(provider, "name", None)
                self.assertIsNotNone(
                    name, f"{key}: missing `name` attribute"
                )
                self.assertIsInstance(name, str)
                self.assertTrue(
                    name.strip(),
                    f"{key}: `name` attribute is empty",
                )

    def test_validate_config_returns_provider_status(self) -> None:
        for key, provider in self._providers.items():
            with self.subTest(provider=key):
                status = provider.validate_config()
                self.assertIsInstance(
                    status, ProviderStatus,
                    f"{key}: validate_config returned {type(status).__name__}",
                )
                self.assertIsInstance(status.configured, bool)
                self.assertIsInstance(status.details, list)

    def test_estimate_returns_estimate_with_non_negative_tokens(self) -> None:
        packet = _make_packet()
        for key, provider in self._providers.items():
            with self.subTest(provider=key):
                est = provider.estimate(packet)
                self.assertIsInstance(
                    est, Estimate,
                    f"{key}: estimate returned {type(est).__name__}",
                )
                self.assertGreaterEqual(est.input_tokens, 0)
                self.assertGreaterEqual(est.output_tokens, 0)
                self.assertGreaterEqual(est.cost_usd, 0.0)

    def test_dry_run_returns_provider_response(self) -> None:
        """Dry-run is the safe shape-check path — every provider
        must return a populated :class:`ProviderResponse` without
        actually calling out."""
        packet = _make_packet()
        for key, provider in self._providers.items():
            with self.subTest(provider=key):
                try:
                    response = provider.run(packet, dry_run=True)
                except NotImplementedError:
                    # Some providers may raise NotImplementedError
                    # rather than return a dry-run shell. That's a
                    # contract bug — fail the conformance check.
                    self.fail(
                        f"{key}: run(dry_run=True) raised "
                        "NotImplementedError; dry_run must be safe"
                    )
                self.assertIsInstance(
                    response, ProviderResponse,
                    f"{key}: run returned {type(response).__name__}",
                )
                self.assertEqual(response.dry_run, True)
                self.assertEqual(
                    response.packet_id, packet.packet_id,
                    f"{key}: response.packet_id mismatch",
                )
                self.assertIsInstance(response.provider, str)
                self.assertTrue(
                    response.provider.strip(),
                    f"{key}: response.provider is empty",
                )

    def test_run_stream_yields_terminal_chunk_when_supported(self) -> None:
        """Providers with a ``run_stream`` attribute must
        terminate with a ``done=True`` chunk. Providers without
        the attribute are skipped — non-streaming providers are
        adapted via ``single_chunk_stream`` at the call site."""
        packet = _make_packet()
        for key, provider in self._providers.items():
            run_stream = getattr(provider, "run_stream", None)
            if not callable(run_stream):
                continue
            with self.subTest(provider=key):
                chunks = list(
                    run_stream(packet, dry_run=True)
                )
                self.assertGreater(
                    len(chunks), 0,
                    f"{key}: run_stream yielded zero chunks",
                )
                self.assertTrue(
                    all(isinstance(c, StreamChunk) for c in chunks),
                    f"{key}: run_stream yielded non-StreamChunk",
                )
                self.assertTrue(
                    chunks[-1].done,
                    f"{key}: terminal chunk missing done=True",
                )

    def test_provider_satisfies_protocol_isinstance(self) -> None:
        """Verify the AIProvider Protocol's runtime check passes
        on every provider. Catches missing methods at import
        time rather than at first call."""
        for key, provider in self._providers.items():
            with self.subTest(provider=key):
                # Protocol with @runtime_checkable would be
                # ideal here; AIProvider is not decorated, so we
                # do an attribute check instead.
                for method_name in ("validate_config", "estimate", "run"):
                    self.assertTrue(
                        callable(getattr(provider, method_name, None)),
                        f"{key}: missing required method {method_name!r}",
                    )

    def test_run_dry_run_does_not_hit_network(self) -> None:
        """Belt-and-braces: dry_run=True invocations must not
        construct any network handle. We sentinel-patch
        ``urllib.request.urlopen`` and assert it was never
        called during the dry-run battery."""
        from unittest import mock

        packet = _make_packet()
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=AssertionError(
                "dry_run=True must not hit the network"
            ),
        ):
            for key, provider in self._providers.items():
                with self.subTest(provider=key):
                    provider.run(packet, dry_run=True)


# Type-checking convenience — keeps mypy quiet about unused
# imports while making the AIProvider Protocol citable.
_ = AIProvider


if __name__ == "__main__":
    unittest.main()
