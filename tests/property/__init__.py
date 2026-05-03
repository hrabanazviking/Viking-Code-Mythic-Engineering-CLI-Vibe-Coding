"""Phase 19.4 (audit remediation 2026-05-02) — property-based
tests for state migrations.

Hypothesis-generated test cases that exercise
``mythic_vibe_cli.persistence.migrations.migrate_project_state``
against arbitrary legacy and current-schema payloads. Verifies the
durable invariants: schema upgrade idempotency, lossless field
preservation, validation-clean output, and corrupt-input recovery.
"""
