# ADR Sanity Sweep — 2026-05-03 (v1.0.0 doc audit)

This log records the v1.0.0 ADR sanity sweep performed during the comprehensive documentation audit. Each ADR was re-read against current code reality and confirmed accurate (or amended additively in a way that preserves the original decision text).

## Summary

| ADR | Status | v1.0 verdict |
|---|---|---|
| `ADR-0001-active-runtime-boundary.md` | Accepted | **Still accurate.** Decision text unchanged. Added a "v1.0 verification additions" section appending the mechanical gates that emerged after the original ADR (`tools/contract_audit.py`, ruff, mypy) and a forward-pointer to `docs/compatibility_policy.md` as the binding v1.0 contract that complements (does not supersede) this ADR. |
| `ADR-0002-no-direct-vendor-imports.md` | Accepted | **Still accurate.** No code in `mythic_vibe_cli/` imports from dormant runtime clusters or vendor mirrors. The `tools/contract_audit.py` + `mythic-vibe doctor --repo-boundary` gates continue to enforce this. |
| `ADR-0003-verification-gates.md` | Accepted | **Still accurate.** PH-13 drift detection + PH-19.4 hypothesis property tests for state migrations + PH-19.2 contract auditor are all extensions of the verification-gate philosophy this ADR established. None alter the original decision. |
| `ADR-0004-doctor-diagnostics.md` | Accepted | **Still accurate.** PH-19.8 stale-catalog watchdog (`evaluate_catalog_freshness`) and PH-20.2 `doctor --fix` are additive extensions of this ADR's "doctor as first-class diagnostic scanner" decision. |
| `ADR-0005-island-b-yggdrasil-adapter.md` | Accepted | **Still accurate.** Yggdrasil adapter remains gated by `MYTHIC_ISLAND_YGGDRASIL_ENABLED`. |
| `ADR-0006-island-c-mindspark-adapter.md` | Accepted | **Still accurate.** MindSpark adapter remains gated by `MYTHIC_ISLAND_MINDSPARK_ENABLED`. |
| `ADR-0007-island-d-wyrd-adapter.md` | Accepted | **Still accurate.** WYRD adapter remains gated by `MYTHIC_ISLAND_WYRD_ENABLED`. |
| `ADR-0008-island-e-chatterbox-adapter.md` | Accepted | **Still accurate.** Chatterbox TTS adapter remains gated by `MYTHIC_VOICE_TTS_ENABLED`. The 2026-05-02 audit-remediation Phase A.1 fix routes through `ChatterboxTTS.from_pretrained` per this ADR's intent. |
| `ADR-0009-internal-api-surfaces.md` | Accepted | **Still accurate.** `mythic_vibe_cli.robustness.api_audit.audit_api_surfaces` remains the implementation. |
| `ADR-0010-ai-model-listing-policy.md` | Accepted | **Still accurate.** Static-first with `--remote` opt-in; static catalog at `mythic_vibe_cli/ai/providers/model_catalog.py:_STATIC_LAST_UPDATED = "2026-05-02"`. PH-19.8 added the catalog-freshness watchdog so operators see drift before users do. |

## Sweep methodology

Each ADR was checked against:

1. The named modules / files referenced in the Decision section — confirmed present at the documented paths.
2. The named env-var gates — confirmed referenced in code (`mythic_vibe_cli/{voice,protocols,security,ai}/...`).
3. The Verification commands — confirmed runnable.
4. Any "current corpus has existing findings" carve-outs — confirmed still tracked-not-blocked.

## What was NOT changed

ADR text is **immutable** in this project's convention. The sweep only:

- **Read** each ADR for accuracy.
- **Appended** a "v1.0 verification additions" section to ADR-0001 (the most foundational ADR) noting the mechanical gates that emerged post-decision.
- **Logged** the sweep in this file.

If a future review finds an ADR has drifted from reality, the correct response is to write a NEW ADR superseding it (per the Status field convention), not to mutate the original text.

## Related

- [`docs/INDEX.md`](../INDEX.md) lists all 10 ADRs.
- [`docs/compatibility_policy.md`](../compatibility_policy.md) is the v1.0 binding contract that complements (does not supersede) the ADR set.
- [`docs/governance/quarterly_review.md`](../governance/quarterly_review.md) defines the quarterly architecture-review cadence; that review is the next scheduled chance to evaluate whether any ADR here needs superseding.
