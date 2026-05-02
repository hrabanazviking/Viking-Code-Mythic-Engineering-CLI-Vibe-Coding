# ADR-0010: AI Model Listing Policy — Static-First with Remote Opt-in

- ID: ADR-0010
- Status: accepted
- Date: 2026-05-02
- Author: Volmarr / RuneForgeAI
- Phase: D (audit remediation, finding #5)

## Context

Before Phase D of the 2026-05-02 audit remediation,
`mythic-vibe ai models --provider <name>` returned a useful listing
**only** for Ollama. The four remote providers (Anthropic, OpenAI,
Gemini, OpenRouter) all returned a canned `{"models": [], "note":
"Model listing is not implemented..."}` payload. The 2026-05-02
fake-code audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`, finding #5)
flagged this as a Medium-severity gap — operators couldn't discover
available model IDs without leaving the CLI.

Two options for closing it:

1. **Static-only** — hardcode a curated catalog per provider, updated
   when SDKs change.
2. **Remote-only** — hit each provider's documented `/models`
   endpoint on every call. Requires an API key for most.
3. **Hybrid** — static by default; an opt-in flag triggers remote.

## Decision

Adopt **option 3: static-first with `--remote` opt-in.** Both paths
ship in Phase D as fully-featured implementations.

- **Default path** (`mythic-vibe ai models --provider <name>`):
  returns the curated static catalog from `ai/providers/model_catalog.py`.
  No network access, no API key required. Always works offline.
- **Remote path** (`--remote` flag): hits the provider's documented
  listing endpoint via stdlib `urllib.request`. Falls back to the
  static catalog **with a warning** when:
  - The required API key is not set;
  - The HTTP call fails (4xx, 5xx, network error, parse error);
  - The response payload is malformed;
  - The response contains zero models.

Endpoints used:

| Provider   | Endpoint                                                   | Auth                                |
|------------|------------------------------------------------------------|-------------------------------------|
| Anthropic  | `GET https://api.anthropic.com/v1/models`                  | `x-api-key` (`ANTHROPIC_API_KEY`)   |
| OpenAI     | `GET https://api.openai.com/v1/models`                     | `Authorization: Bearer` (`OPENAI_API_KEY`) |
| Gemini     | `GET .../v1beta/models?key=<KEY>`                          | URL param (`GEMINI_API_KEY` or `GOOGLE_API_KEY`) |
| OpenRouter | `GET https://openrouter.ai/api/v1/models`                  | None (auth optional)                |

JSON output gains:

- `"implemented": true` (vs `false` for the legacy fallback path
  preserved in `commands.py` for hypothetical future providers
  without `list_models`).
- `"source": "static" | "remote" | "static-fallback"` — consumers
  can distinguish the curated catalog from a live listing from a
  remote-failed fallback.
- `"warnings": [string, ...]` — diagnostic strings explaining any
  fallback or partial failure.

## Why static-first wins UX-wise

- **Operators without API keys still get useful output.** The
  pre-Phase-D state gave them an empty list + apology note. The new
  static catalog gives them a real, accurate list of model IDs they
  can pass to `ai run --model`.
- **Operators with keys can refresh on demand** via `--remote`.
- **Static catalogs go stale slowly.** Anthropic / OpenAI / Gemini
  ship new models on a quarterly cadence; PR-time updates handle
  drift. Catalog records carry `last_updated` so reviewers can see
  the curation date.
- **Matches the durable "stdlib-first / no API call required by
  default" pattern** of the rest of the CLI (`voice/transcribe.py`,
  `forge plan --dry-run`, etc.).

## Consequences

- **Positive:**
  - `ai models` works for all 5 providers (Ollama + 4 remote).
  - Operators discover model IDs without leaving the CLI.
  - JSON consumers can reliably detect static vs remote vs fallback.
  - Static catalog upgrades land via PRs, with `last_updated` for
    review.
- **Negative:**
  - The static catalog can drift from upstream between updates.
    Mitigation: prominent `last_updated` field + a follow-up agent
    (suggest `/schedule`) to refresh quarterly.
  - Providers may add new models that aren't in the static list —
    operators see them via `--remote` only.
- **Neutral:**
  - The legacy `cmd_ai_models` "not implemented" branch is preserved
    as a defensive fallback for any provider that lacks
    `list_models` — currently unreachable (all 4 implement it),
    but kept per the additive-only rule.

## Links

- Driver audit: `AUDIT_FAKE_TEMP_CODE_2026-05-02.md` finding #5.
- Phase D closeout addendum: `PHASE6_FINALE_CLOSEOUT.md`.
- Implementation: `mythic_vibe_cli/ai/providers/model_catalog.py`.
- Per-provider wire-ups: `anthropic.py`, `openai.py`, `gemini.py`,
  `openrouter.py`.
- Dispatcher: `mythic_vibe_cli/commands.py:cmd_ai_models`.
- Tests: `tests/test_ai_model_catalog.py`,
  `tests/test_ai_models_cli.py`.
