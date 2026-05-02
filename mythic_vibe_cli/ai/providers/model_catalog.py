"""Provider model catalog — static + remote listing (Phase D, 2026-05-02).

Background
==========

The first 2026-05-02 audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`,
finding #5) caught ``cmd_ai_models`` returning a canned
``"models": []`` + "not implemented" payload for every non-Ollama
provider. Phase D ships **fully featured** model listing for the four
remote providers (Anthropic / OpenAI / Gemini / OpenRouter):

- A **static catalog** per provider — accurate at the documented
  cutoff date, queryable without an API key, no network access. This
  is the default path for ``mythic-vibe ai models --provider <name>``.
- A **remote listing** path triggered by ``--remote``. Hits each
  provider's documented ``models``-listing endpoint via stdlib
  ``urllib.request``. Falls back to the static catalog with a
  warning if the API key is missing or the remote call fails.

Both paths return a :class:`ModelListing` carrying a list of
:class:`ModelInfo` records, a ``source`` flag (``"static"`` or
``"remote"``), an ``implemented: True`` flag (so JSON consumers can
distinguish real listings from the legacy canned payload), and a
list of ``warnings`` collected during the lookup.

The legacy canned branch in ``cmd_ai_models`` is **preserved as a
fallback** for any provider that does not expose a ``list_models``
method (per the additive-only remediation rule).

Cross-platform: pure stdlib (``urllib.request``, ``json``, ``os``,
``dataclasses``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from urllib import error as urllib_error
from urllib import request as urllib_request


@dataclass(frozen=True)
class ModelInfo:
    """One row in the model catalog.

    ``id`` is the canonical provider model id (passed to
    ``ai run --model``). ``family`` is the lower-case provider/family
    name. ``display_name`` is operator-friendly. ``context_window``
    and ``max_output_tokens`` are token counts (0 = unknown).
    ``capabilities`` is an open tuple of capability tags
    (``"vision"``, ``"audio"``, ``"tools"``, ``"thinking"``,
    ``"streaming"``, ``"json_mode"``, ``"long_context"``, etc.).
    ``source`` records where the record was sourced from
    (``"static"`` / ``"remote"``); ``last_updated`` is an ISO date for
    static records (the curator-update cadence) and the response
    timestamp for remote records when available.
    """

    id: str
    family: str
    display_name: str
    context_window: int = 0
    max_output_tokens: int = 0
    capabilities: tuple[str, ...] = ()
    source: str = "static"
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family": self.family,
            "display_name": self.display_name,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "capabilities": list(self.capabilities),
            "source": self.source,
            "last_updated": self.last_updated,
        }


@dataclass(frozen=True)
class ModelListing:
    """Result of ``list_models(family, remote=...)``.

    ``models`` is the list of :class:`ModelInfo` records; ``source``
    is ``"static"``, ``"remote"``, or ``"static-fallback"`` (when
    remote was requested but failed and we fell back to static);
    ``implemented`` is True for any listing produced by this module
    (consumers use this to distinguish from the legacy canned
    payload). ``warnings`` collects diagnostic strings — missing API
    key, remote HTTP error, parse failure, empty remote response, etc.
    """

    family: str
    models: list[ModelInfo]
    source: str = "static"
    implemented: bool = True
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "source": self.source,
            "implemented": self.implemented,
            "warnings": list(self.warnings),
            "models": [m.to_dict() for m in self.models],
        }


# ---------------------------------------------------------------------------
# Static catalogs — curated per provider. Update ``last_updated`` whenever
# you bump a list. Capability tags follow the open vocabulary above.
# ---------------------------------------------------------------------------

_STATIC_LAST_UPDATED = "2026-05-02"


_ANTHROPIC_STATIC: tuple[ModelInfo, ...] = (
    ModelInfo(
        id="claude-opus-4-7",
        family="anthropic",
        display_name="Claude Opus 4.7",
        context_window=200_000,
        max_output_tokens=8_192,
        capabilities=("vision", "tools", "thinking", "streaming", "json_mode"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="claude-sonnet-4-6",
        family="anthropic",
        display_name="Claude Sonnet 4.6",
        context_window=200_000,
        max_output_tokens=8_192,
        capabilities=("vision", "tools", "streaming", "json_mode"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="claude-haiku-4-5-20251001",
        family="anthropic",
        display_name="Claude Haiku 4.5",
        context_window=200_000,
        max_output_tokens=8_192,
        capabilities=("vision", "tools", "streaming"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
)


_OPENAI_STATIC: tuple[ModelInfo, ...] = (
    ModelInfo(
        id="gpt-4o",
        family="openai",
        display_name="GPT-4o",
        context_window=128_000,
        max_output_tokens=16_384,
        capabilities=("vision", "audio", "tools", "streaming", "json_mode"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="gpt-4o-mini",
        family="openai",
        display_name="GPT-4o mini",
        context_window=128_000,
        max_output_tokens=16_384,
        capabilities=("vision", "tools", "streaming", "json_mode"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="gpt-4-turbo",
        family="openai",
        display_name="GPT-4 Turbo",
        context_window=128_000,
        max_output_tokens=4_096,
        capabilities=("vision", "tools", "streaming", "json_mode"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="gpt-3.5-turbo",
        family="openai",
        display_name="GPT-3.5 Turbo",
        context_window=16_385,
        max_output_tokens=4_096,
        capabilities=("tools", "streaming", "json_mode"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
)


_GEMINI_STATIC: tuple[ModelInfo, ...] = (
    ModelInfo(
        id="gemini-2.5-pro",
        family="gemini",
        display_name="Gemini 2.5 Pro",
        context_window=2_000_000,
        max_output_tokens=8_192,
        capabilities=(
            "vision", "audio", "tools", "streaming", "json_mode", "long_context",
        ),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="gemini-2.5-flash",
        family="gemini",
        display_name="Gemini 2.5 Flash",
        context_window=1_000_000,
        max_output_tokens=8_192,
        capabilities=("vision", "tools", "streaming", "json_mode", "long_context"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="gemini-1.5-pro",
        family="gemini",
        display_name="Gemini 1.5 Pro",
        context_window=2_000_000,
        max_output_tokens=8_192,
        capabilities=("vision", "audio", "streaming", "long_context"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="gemini-1.5-flash",
        family="gemini",
        display_name="Gemini 1.5 Flash",
        context_window=1_000_000,
        max_output_tokens=8_192,
        capabilities=("vision", "streaming", "long_context"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
)


_OPENROUTER_STATIC: tuple[ModelInfo, ...] = (
    ModelInfo(
        id="anthropic/claude-opus-4-7",
        family="openrouter",
        display_name="Claude Opus 4.7 (via OpenRouter)",
        context_window=200_000,
        max_output_tokens=8_192,
        capabilities=("vision", "tools", "thinking", "streaming"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="anthropic/claude-sonnet-4-6",
        family="openrouter",
        display_name="Claude Sonnet 4.6 (via OpenRouter)",
        context_window=200_000,
        max_output_tokens=8_192,
        capabilities=("vision", "tools", "streaming"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="openai/gpt-4o",
        family="openrouter",
        display_name="GPT-4o (via OpenRouter)",
        context_window=128_000,
        max_output_tokens=16_384,
        capabilities=("vision", "tools", "streaming"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="google/gemini-2.5-pro",
        family="openrouter",
        display_name="Gemini 2.5 Pro (via OpenRouter)",
        context_window=2_000_000,
        max_output_tokens=8_192,
        capabilities=("vision", "audio", "streaming", "long_context"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
    ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct",
        family="openrouter",
        display_name="Llama 3.3 70B Instruct (via OpenRouter)",
        context_window=128_000,
        max_output_tokens=4_096,
        capabilities=("tools", "streaming"),
        last_updated=_STATIC_LAST_UPDATED,
    ),
)


_STATIC_CATALOGS: dict[str, tuple[ModelInfo, ...]] = {
    "anthropic": _ANTHROPIC_STATIC,
    "openai": _OPENAI_STATIC,
    "gemini": _GEMINI_STATIC,
    "openrouter": _OPENROUTER_STATIC,
}


def list_models_static(family: str) -> list[ModelInfo]:
    """Return the curated static catalog for ``family`` (case-
    insensitive). Returns an empty list when no catalog exists."""
    return list(_STATIC_CATALOGS.get(family.strip().lower(), ()))


# ---------------------------------------------------------------------------
# Remote listing — one fetch helper per provider. Each returns a list of
# ModelInfo records on success or raises a ProviderListingError on failure.
# Callers wrap them in a defensive try/except inside list_models() to
# preserve the static fallback.
# ---------------------------------------------------------------------------


class ProviderListingError(RuntimeError):
    """Raised when a remote listing call fails (network, auth, parse).
    The caller is expected to wrap this and surface a warning rather
    than crash. Carries an ``http_status`` int (0 if unknown) and the
    upstream error message."""

    def __init__(self, message: str, *, http_status: int = 0) -> None:
        super().__init__(message)
        self.http_status = http_status


def _http_get_json(url: str, headers: dict[str, str], *, timeout: float = 30.0) -> Any:
    """Minimal stdlib JSON GET. Raises :class:`ProviderListingError`
    with ``http_status`` set on HTTP errors; ValueError on parse
    failures."""
    req = urllib_request.Request(url, headers=headers, method="GET")
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except urllib_error.HTTPError as exc:
        raise ProviderListingError(
            f"HTTP {exc.code} from {url}: {exc.reason}",
            http_status=exc.code,
        ) from exc
    except urllib_error.URLError as exc:
        raise ProviderListingError(
            f"Network error contacting {url}: {exc.reason}"
        ) from exc
    except OSError as exc:
        raise ProviderListingError(
            f"OS error contacting {url}: {exc}"
        ) from exc
    try:
        return json.loads(data)
    except (ValueError, TypeError) as exc:
        raise ProviderListingError(
            f"Could not parse JSON from {url}: {exc}"
        ) from exc


def fetch_anthropic_models_remote(api_key: str) -> list[ModelInfo]:
    """Hit ``GET https://api.anthropic.com/v1/models`` with the
    standard ``x-api-key`` + ``anthropic-version`` headers. Returns a
    list of :class:`ModelInfo` records with ``source="remote"`` and
    capability tags inferred from the model id (Anthropic's listing
    endpoint returns minimal metadata; we cross-reference the static
    catalog to enrich)."""
    if not api_key:
        raise ProviderListingError(
            "Anthropic remote listing requires ANTHROPIC_API_KEY"
        )
    payload = _http_get_json(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "User-Agent": "mythic-vibe-cli",
        },
    )
    if not isinstance(payload, dict):
        raise ProviderListingError("Anthropic /v1/models returned non-object")
    raw_models = payload.get("data") or []
    if not isinstance(raw_models, list):
        raise ProviderListingError("Anthropic /v1/models 'data' is not a list")
    static_by_id = {m.id: m for m in _ANTHROPIC_STATIC}
    models: list[ModelInfo] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            continue
        # Cross-reference for richer metadata.
        ref = static_by_id.get(model_id)
        models.append(
            ModelInfo(
                id=model_id,
                family="anthropic",
                display_name=str(item.get("display_name") or (ref.display_name if ref else model_id)),
                context_window=ref.context_window if ref else 0,
                max_output_tokens=ref.max_output_tokens if ref else 0,
                capabilities=ref.capabilities if ref else (),
                source="remote",
                last_updated=str(item.get("created_at") or ""),
            )
        )
    return models


def fetch_openai_models_remote(api_key: str) -> list[ModelInfo]:
    """Hit ``GET https://api.openai.com/v1/models`` with
    ``Authorization: Bearer <key>``. The endpoint returns a flat list
    of model objects; we cross-reference the static catalog to
    enrich capability metadata."""
    if not api_key:
        raise ProviderListingError(
            "OpenAI remote listing requires OPENAI_API_KEY"
        )
    payload = _http_get_json(
        "https://api.openai.com/v1/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "mythic-vibe-cli",
        },
    )
    if not isinstance(payload, dict):
        raise ProviderListingError("OpenAI /v1/models returned non-object")
    raw_models = payload.get("data") or []
    if not isinstance(raw_models, list):
        raise ProviderListingError("OpenAI /v1/models 'data' is not a list")
    static_by_id = {m.id: m for m in _OPENAI_STATIC}
    models: list[ModelInfo] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            continue
        ref = static_by_id.get(model_id)
        created_ts = item.get("created")
        last_updated = ""
        if isinstance(created_ts, (int, float)):
            from datetime import datetime, timezone

            try:
                last_updated = datetime.fromtimestamp(
                    int(created_ts), tz=timezone.utc
                ).strftime("%Y-%m-%d")
            except (OverflowError, OSError, ValueError):
                last_updated = ""
        models.append(
            ModelInfo(
                id=model_id,
                family="openai",
                display_name=ref.display_name if ref else model_id,
                context_window=ref.context_window if ref else 0,
                max_output_tokens=ref.max_output_tokens if ref else 0,
                capabilities=ref.capabilities if ref else (),
                source="remote",
                last_updated=last_updated,
            )
        )
    return models


def fetch_gemini_models_remote(api_key: str) -> list[ModelInfo]:
    """Hit ``GET https://generativelanguage.googleapis.com/v1beta/models?key=<KEY>``.
    Gemini's listing endpoint returns an object with a ``models``
    array; each entry has a ``name`` like ``"models/gemini-1.5-pro"``."""
    if not api_key:
        raise ProviderListingError(
            "Gemini remote listing requires GOOGLE_API_KEY"
        )
    payload = _http_get_json(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        headers={"User-Agent": "mythic-vibe-cli"},
    )
    if not isinstance(payload, dict):
        raise ProviderListingError("Gemini models endpoint returned non-object")
    raw_models = payload.get("models") or []
    if not isinstance(raw_models, list):
        raise ProviderListingError("Gemini 'models' field is not a list")
    static_by_id = {m.id: m for m in _GEMINI_STATIC}
    models: list[ModelInfo] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        full_name = str(item.get("name") or "").strip()
        if not full_name:
            continue
        # 'models/gemini-1.5-pro' -> 'gemini-1.5-pro'
        model_id = full_name.split("/", 1)[1] if "/" in full_name else full_name
        ref = static_by_id.get(model_id)
        # Gemini reports inputTokenLimit / outputTokenLimit numerically.
        context_window = int(item.get("inputTokenLimit") or (ref.context_window if ref else 0))
        max_output_tokens = int(item.get("outputTokenLimit") or (ref.max_output_tokens if ref else 0))
        models.append(
            ModelInfo(
                id=model_id,
                family="gemini",
                display_name=str(item.get("displayName") or (ref.display_name if ref else model_id)),
                context_window=context_window,
                max_output_tokens=max_output_tokens,
                capabilities=ref.capabilities if ref else (),
                source="remote",
                last_updated=str(item.get("version") or ""),
            )
        )
    return models


def fetch_openrouter_models_remote(api_key: str | None = None) -> list[ModelInfo]:
    """Hit ``GET https://openrouter.ai/api/v1/models``. OpenRouter's
    models endpoint is unauthenticated for listing; an optional API
    key is accepted but not required. Returns a list of
    :class:`ModelInfo` records."""
    headers: dict[str, str] = {"User-Agent": "mythic-vibe-cli"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = _http_get_json(
        "https://openrouter.ai/api/v1/models", headers=headers
    )
    if not isinstance(payload, dict):
        raise ProviderListingError("OpenRouter /api/v1/models returned non-object")
    raw_models = payload.get("data") or []
    if not isinstance(raw_models, list):
        raise ProviderListingError("OpenRouter /api/v1/models 'data' is not a list")
    static_by_id = {m.id: m for m in _OPENROUTER_STATIC}
    models: list[ModelInfo] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            continue
        ref = static_by_id.get(model_id)
        context_length = int(item.get("context_length") or (ref.context_window if ref else 0))
        # OpenRouter doesn't report max_output_tokens directly; use static ref.
        max_output_tokens = ref.max_output_tokens if ref else 0
        models.append(
            ModelInfo(
                id=model_id,
                family="openrouter",
                display_name=str(item.get("name") or (ref.display_name if ref else model_id)),
                context_window=context_length,
                max_output_tokens=max_output_tokens,
                capabilities=ref.capabilities if ref else (),
                source="remote",
                last_updated="",
            )
        )
    return models


_REMOTE_FETCHERS: dict[str, Any] = {
    "anthropic": (fetch_anthropic_models_remote, "ANTHROPIC_API_KEY"),
    "openai": (fetch_openai_models_remote, "OPENAI_API_KEY"),
    "gemini": (fetch_gemini_models_remote, "GOOGLE_API_KEY"),
    "openrouter": (fetch_openrouter_models_remote, ""),
}


def list_models(
    family: str, *, remote: bool = False, api_key: str | None = None
) -> ModelListing:
    """Top-level catalog query.

    - ``family``: provider family (case-insensitive). Unknown families
      return an empty listing with an explanatory warning.
    - ``remote``: when False (default), returns the static catalog
      verbatim. When True, attempts the provider's documented listing
      endpoint via stdlib urllib; on failure (no key, HTTP error,
      parse error, empty response) falls back to the static catalog
      and records a warning explaining why remote was skipped.
    - ``api_key``: explicit override. When omitted, the relevant
      ``OS_ENVIRON`` variable for the family is consulted (none for
      OpenRouter, since its listing endpoint is unauthenticated).
    """
    cleaned_family = family.strip().lower()
    static_models = list_models_static(cleaned_family)
    warnings: list[str] = []

    if cleaned_family not in _REMOTE_FETCHERS:
        if not static_models:
            warnings.append(
                f"No catalog defined for provider {cleaned_family!r}."
            )
        return ModelListing(
            family=cleaned_family,
            models=static_models,
            source="static",
            warnings=warnings,
        )

    if not remote:
        return ModelListing(
            family=cleaned_family,
            models=static_models,
            source="static",
            warnings=warnings,
        )

    fetcher, env_var = _REMOTE_FETCHERS[cleaned_family]
    resolved_key = api_key
    if resolved_key is None and env_var:
        resolved_key = os.getenv(env_var, "").strip() or None

    try:
        if env_var and not resolved_key:
            raise ProviderListingError(
                f"{cleaned_family} remote listing requires {env_var} (not set)"
            )
        if env_var:
            remote_models = fetcher(resolved_key)
        else:
            # OpenRouter — unauthenticated path
            remote_models = fetcher(resolved_key)
    except ProviderListingError as exc:
        warnings.append(
            f"Remote listing failed; using static catalog. ({exc})"
        )
        return ModelListing(
            family=cleaned_family,
            models=static_models,
            source="static-fallback",
            warnings=warnings,
        )

    if not remote_models:
        warnings.append(
            "Remote listing returned no models; using static catalog."
        )
        return ModelListing(
            family=cleaned_family,
            models=static_models,
            source="static-fallback",
            warnings=warnings,
        )

    return ModelListing(
        family=cleaned_family,
        models=remote_models,
        source="remote",
        warnings=warnings,
    )


__all__ = [
    "ModelInfo",
    "ModelListing",
    "ProviderListingError",
    "fetch_anthropic_models_remote",
    "fetch_gemini_models_remote",
    "fetch_openai_models_remote",
    "fetch_openrouter_models_remote",
    "list_models",
    "list_models_static",
]
