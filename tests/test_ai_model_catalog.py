"""Phase D 2026-05-02 (audit remediation, finding #5) — provider
model catalog tests.

Covers ``ai/providers/model_catalog.py`` (static catalogs + remote
fetchers + ``list_models`` dispatcher) and the per-provider
``list_models()`` methods on Anthropic / OpenAI / Gemini / OpenRouter.
``cmd_ai_models`` integration is covered in ``test_ai_models_cli.py``
which we extend at the end of this file.
"""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from mythic_vibe_cli.ai.providers.model_catalog import (
    ModelInfo,
    ModelListing,
    ProviderListingError,
    fetch_anthropic_models_remote,
    fetch_gemini_models_remote,
    fetch_openai_models_remote,
    fetch_openrouter_models_remote,
    list_models,
    list_models_static,
)
from mythic_vibe_cli.ai.providers.anthropic import AnthropicProvider
from mythic_vibe_cli.ai.providers.gemini import GeminiProvider
from mythic_vibe_cli.ai.providers.openai import OpenAIProvider
from mythic_vibe_cli.ai.providers.openrouter import OpenRouterProvider


def _stub_response(payload: dict | bytes, *, status: int = 200):
    """Build a context-manager that mimics urlopen's response for the
    JSON-fetch helper."""
    body_bytes = (
        payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    )

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return body_bytes

    return _FakeResp()


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #


class ModelInfoTests(unittest.TestCase):
    def test_default_fields(self) -> None:
        m = ModelInfo(id="x", family="anthropic", display_name="X")
        self.assertEqual(m.context_window, 0)
        self.assertEqual(m.max_output_tokens, 0)
        self.assertEqual(m.capabilities, ())
        self.assertEqual(m.source, "static")
        self.assertEqual(m.last_updated, "")

    def test_to_dict_round_trip(self) -> None:
        m = ModelInfo(
            id="claude-opus-4-7",
            family="anthropic",
            display_name="Claude Opus 4.7",
            context_window=200_000,
            max_output_tokens=8_192,
            capabilities=("vision", "tools"),
            source="remote",
            last_updated="2026-05-02",
        )
        d = m.to_dict()
        self.assertEqual(d["id"], "claude-opus-4-7")
        self.assertEqual(d["context_window"], 200_000)
        self.assertEqual(d["capabilities"], ["vision", "tools"])
        self.assertEqual(d["source"], "remote")


class ModelListingTests(unittest.TestCase):
    def test_to_dict_includes_implemented_flag(self) -> None:
        listing = ModelListing(
            family="openai",
            models=[
                ModelInfo(id="gpt-4o", family="openai", display_name="GPT-4o")
            ],
            source="static",
            warnings=["w1"],
        )
        d = listing.to_dict()
        self.assertTrue(d["implemented"])
        self.assertEqual(d["source"], "static")
        self.assertEqual(d["warnings"], ["w1"])
        self.assertEqual(len(d["models"]), 1)


# --------------------------------------------------------------------------- #
# Static catalogs
# --------------------------------------------------------------------------- #


class StaticCatalogTests(unittest.TestCase):
    """Each provider's static catalog must be non-empty + well-formed
    so operators always get useful output offline."""

    def test_anthropic_catalog_non_empty(self) -> None:
        models = list_models_static("anthropic")
        self.assertGreater(len(models), 0)
        ids = [m.id for m in models]
        self.assertIn("claude-opus-4-7", ids)

    def test_openai_catalog_non_empty(self) -> None:
        models = list_models_static("openai")
        self.assertGreater(len(models), 0)
        self.assertTrue(any(m.id.startswith("gpt-") for m in models))

    def test_gemini_catalog_non_empty(self) -> None:
        models = list_models_static("gemini")
        self.assertGreater(len(models), 0)
        self.assertTrue(any(m.id.startswith("gemini-") for m in models))

    def test_openrouter_catalog_non_empty(self) -> None:
        models = list_models_static("openrouter")
        self.assertGreater(len(models), 0)
        # OpenRouter ids include a vendor prefix.
        self.assertTrue(any("/" in m.id for m in models))

    def test_unknown_family_returns_empty(self) -> None:
        self.assertEqual(list_models_static("zzz-unknown"), [])

    def test_family_lookup_is_case_insensitive(self) -> None:
        a = list_models_static("Anthropic")
        b = list_models_static("anthropic")
        self.assertEqual([m.id for m in a], [m.id for m in b])

    def test_static_records_are_marked_static(self) -> None:
        for family in ("anthropic", "openai", "gemini", "openrouter"):
            for m in list_models_static(family):
                self.assertEqual(
                    m.source, "static", f"{family} {m.id} not marked static"
                )


# --------------------------------------------------------------------------- #
# list_models — top-level dispatcher
# --------------------------------------------------------------------------- #


class ListModelsStaticDefaultTests(unittest.TestCase):
    def test_remote_false_returns_static_catalog(self) -> None:
        listing = list_models("anthropic", remote=False)
        self.assertEqual(listing.source, "static")
        self.assertGreater(len(listing.models), 0)
        self.assertEqual(listing.warnings, [])

    def test_unknown_family_warns_and_returns_empty(self) -> None:
        listing = list_models("zzz-unknown", remote=False)
        self.assertEqual(listing.source, "static")
        self.assertEqual(listing.models, [])
        self.assertTrue(any("No catalog" in w for w in listing.warnings))


class ListModelsRemoteTests(unittest.TestCase):
    def test_remote_with_no_api_key_falls_back_to_static_with_warning(
        self,
    ) -> None:
        # Clear any inherited env vars so we deterministically hit the
        # missing-key branch.
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": ""},
            clear=False,
        ):
            listing = list_models("anthropic", remote=True, api_key=None)
        self.assertEqual(listing.source, "static-fallback")
        self.assertGreater(len(listing.models), 0)
        self.assertTrue(any("ANTHROPIC_API_KEY" in w for w in listing.warnings))

    def test_remote_http_error_falls_back_to_static_with_warning(self) -> None:
        from urllib.error import HTTPError

        def raise_http(*args, **kwargs):
            raise HTTPError(
                "https://api.anthropic.com/v1/models",
                401,
                "Unauthorized",
                {},
                None,
            )

        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            side_effect=raise_http,
        ):
            listing = list_models(
                "anthropic", remote=True, api_key="bad-key"
            )
        self.assertEqual(listing.source, "static-fallback")
        self.assertGreater(len(listing.models), 0)
        self.assertTrue(
            any("HTTP 401" in w for w in listing.warnings),
            f"expected HTTP 401 in warnings, got {listing.warnings!r}",
        )

    def test_remote_empty_data_falls_back_to_static_with_warning(self) -> None:
        # Some providers may return data: [] — we treat that as empty
        # and fall back to static rather than show an empty list.
        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response({"data": []}),
        ):
            listing = list_models(
                "openai", remote=True, api_key="test-key"
            )
        self.assertEqual(listing.source, "static-fallback")
        self.assertTrue(
            any("returned no models" in w for w in listing.warnings)
        )

    def test_remote_success_returns_remote_models(self) -> None:
        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(
                {
                    "data": [
                        {"id": "claude-opus-4-7"},
                        {"id": "claude-sonnet-4-6"},
                    ]
                }
            ),
        ):
            listing = list_models(
                "anthropic", remote=True, api_key="test-key"
            )
        self.assertEqual(listing.source, "remote")
        self.assertEqual(len(listing.models), 2)
        self.assertEqual([m.source for m in listing.models], ["remote", "remote"])
        self.assertEqual(listing.warnings, [])


# --------------------------------------------------------------------------- #
# Per-provider remote fetchers
# --------------------------------------------------------------------------- #


class FetchAnthropicTests(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        with self.assertRaises(ProviderListingError):
            fetch_anthropic_models_remote("")

    def test_parses_well_formed_response(self) -> None:
        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(
                {
                    "data": [
                        {"id": "claude-opus-4-7", "display_name": "Opus 4.7"},
                        {"id": "future-claude-x"},  # not in static; passes through
                    ]
                }
            ),
        ):
            models = fetch_anthropic_models_remote("test-key")
        self.assertEqual([m.id for m in models], ["claude-opus-4-7", "future-claude-x"])
        # Static cross-reference enriched the first; second has empty caps
        self.assertGreater(len(models[0].capabilities), 0)
        self.assertEqual(models[1].capabilities, ())

    def test_raises_on_non_object_payload(self) -> None:
        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(b"[]"),
        ):
            with self.assertRaises(ProviderListingError):
                fetch_anthropic_models_remote("test-key")


class FetchOpenAITests(unittest.TestCase):
    def test_parses_well_formed_response(self) -> None:
        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(
                {
                    "data": [
                        {"id": "gpt-4o", "created": 1_700_000_000},
                        {"id": "gpt-3.5-turbo", "created": 1_600_000_000},
                    ]
                }
            ),
        ):
            models = fetch_openai_models_remote("test-key")
        self.assertEqual([m.id for m in models], ["gpt-4o", "gpt-3.5-turbo"])
        # The 'created' Unix timestamps were converted to ISO-style strings.
        self.assertTrue(all(m.last_updated for m in models))


class FetchGeminiTests(unittest.TestCase):
    def test_parses_well_formed_response(self) -> None:
        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(
                {
                    "models": [
                        {
                            "name": "models/gemini-2.5-pro",
                            "displayName": "Gemini 2.5 Pro",
                            "inputTokenLimit": 2_000_000,
                            "outputTokenLimit": 8_192,
                        },
                        {"name": "models/gemini-something-new"},
                    ]
                }
            ),
        ):
            models = fetch_gemini_models_remote("test-key")
        self.assertEqual(
            [m.id for m in models], ["gemini-2.5-pro", "gemini-something-new"]
        )
        self.assertEqual(models[0].context_window, 2_000_000)


class FetchOpenRouterTests(unittest.TestCase):
    def test_unauthenticated_path_is_supported(self) -> None:
        # OpenRouter's listing is public; api_key is optional.
        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(
                {
                    "data": [
                        {
                            "id": "anthropic/claude-opus-4-7",
                            "name": "Claude Opus 4.7",
                            "context_length": 200_000,
                        },
                    ]
                }
            ),
        ):
            models = fetch_openrouter_models_remote(None)
        self.assertEqual(models[0].id, "anthropic/claude-opus-4-7")
        self.assertEqual(models[0].context_window, 200_000)

    def test_api_key_supplied_adds_auth_header(self) -> None:
        captured: dict[str, dict] = {}

        def capture_urlopen(req, timeout):
            captured["headers"] = dict(req.headers)
            return _stub_response({"data": []})

        with patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            side_effect=capture_urlopen,
        ):
            try:
                fetch_openrouter_models_remote("my-key")
            except ProviderListingError:
                # Could raise if data is empty — we don't care; we want headers.
                pass
        # urllib normalises header names to title-case.
        self.assertIn("Authorization", captured["headers"])
        self.assertIn("my-key", captured["headers"]["Authorization"])


# --------------------------------------------------------------------------- #
# Per-provider class wire-ups
# --------------------------------------------------------------------------- #


class ProviderListModelsTests(unittest.TestCase):
    """Each provider's ``list_models()`` must delegate to the catalog."""

    def test_anthropic_provider_static_listing(self) -> None:
        listing = AnthropicProvider().list_models(remote=False)
        self.assertEqual(listing.source, "static")
        self.assertGreater(len(listing.models), 0)

    def test_openai_provider_static_listing(self) -> None:
        listing = OpenAIProvider().list_models(remote=False)
        self.assertEqual(listing.source, "static")
        self.assertGreater(len(listing.models), 0)

    def test_gemini_provider_static_listing(self) -> None:
        listing = GeminiProvider().list_models(remote=False)
        self.assertEqual(listing.source, "static")
        self.assertGreater(len(listing.models), 0)

    def test_openrouter_provider_static_listing(self) -> None:
        listing = OpenRouterProvider().list_models(remote=False)
        self.assertEqual(listing.source, "static")
        self.assertGreater(len(listing.models), 0)

    def test_gemini_provider_resolves_either_env_var_for_remote(self) -> None:
        """GeminiProvider.list_models reads GEMINI_API_KEY first
        (matching its validate_config), then GOOGLE_API_KEY as
        Google's canonical fallback. The catalog itself doesn't need
        to know about both — the provider passes the resolved key."""
        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "primary-key", "GOOGLE_API_KEY": "secondary"},
            clear=False,
        ), patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(
                {"models": [{"name": "models/gemini-2.5-flash"}]}
            ),
        ) as mock_urlopen:
            listing = GeminiProvider().list_models(remote=True)
        self.assertEqual(listing.source, "remote")
        # The URL passed to urlopen should embed the GEMINI_API_KEY value.
        call_args = mock_urlopen.call_args
        request_obj = call_args.args[0] if call_args.args else call_args.kwargs.get("url")
        self.assertIn("primary-key", request_obj.full_url)


# --------------------------------------------------------------------------- #
# cmd_ai_models dispatcher integration
# --------------------------------------------------------------------------- #


class CmdAiModelsDispatchTests(unittest.TestCase):
    """``cmd_ai_models`` for non-Ollama providers now routes through
    each provider's ``list_models`` method. The legacy canned
    ``"not implemented"`` payload is preserved as a fallback for
    providers that lack the method."""

    def _run(self, argv: list[str]) -> tuple[int, dict]:
        from mythic_vibe_cli import app

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = app.main(argv)
        return code, json.loads(stdout.getvalue())

    def test_static_listing_returns_implemented_true_with_models(self) -> None:
        code, payload = self._run(
            ["ai", "models", "--provider", "anthropic", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload["implemented"])
        self.assertEqual(payload["source"], "static")
        self.assertGreater(len(payload["models"]), 0)
        self.assertEqual(payload["warnings"], [])

    def test_remote_flag_with_no_key_falls_back_with_warning(self) -> None:
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": ""},
            clear=False,
        ):
            code, payload = self._run(
                [
                    "ai",
                    "models",
                    "--provider",
                    "anthropic",
                    "--remote",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["source"], "static-fallback")
        self.assertTrue(payload["warnings"])

    def test_remote_flag_with_mocked_remote_returns_remote_listing(
        self,
    ) -> None:
        with patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False
        ), patch(
            "mythic_vibe_cli.ai.providers.model_catalog.urllib_request.urlopen",
            return_value=_stub_response(
                {"data": [{"id": "gpt-4o", "created": 1_700_000_000}]}
            ),
        ):
            code, payload = self._run(
                [
                    "ai",
                    "models",
                    "--provider",
                    "openai",
                    "--remote",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["source"], "remote")
        self.assertEqual(len(payload["models"]), 1)
        self.assertEqual(payload["models"][0]["id"], "gpt-4o")

    def test_models_json_payload_shape(self) -> None:
        code, payload = self._run(
            ["ai", "models", "--provider", "openrouter", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            sorted(payload.keys()),
            sorted(
                [
                    "command",
                    "configured",
                    "details",
                    "implemented",
                    "models",
                    "provider",
                    "source",
                    "warnings",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
