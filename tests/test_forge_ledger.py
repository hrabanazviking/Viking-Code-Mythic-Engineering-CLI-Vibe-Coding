"""Tests for PH-03 slice 3.2 — forge handoff ledger.

Pure persistence-layer tests: no orchestrator, no CLI command, no
provider call. Locks the ledger's read/write/round-trip behaviour
before slice 3.3 builds the ``forge`` command on top of it.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from mythic_vibe_cli.forge_ledger import (
    FORGE_LEDGER_FILENAME,
    FORGE_LEDGER_LIMIT,
    FORGE_LEDGER_SCHEMA_VERSION,
    FORGE_STEP_STATUSES,
    ForgeLedger,
    ForgeLedgerEntry,
)
from mythic_vibe_cli.workflow_agents import (
    AgentInput,
    AgentOutput,
    VerificationResult,
)


def _make_input(role: str = "Skald", task: str = "Smoke", phase: str = "intent") -> AgentInput:
    return AgentInput(role=role, task=task, phase=phase, workflow_id="WF-X", workflow_step_id="step-01")


def _make_output(role: str = "Skald", *, all_passed: bool = True) -> AgentOutput:
    return AgentOutput(
        role=role,
        timestamp="2026-04-29T22:00:00Z",
        workflow_id="WF-X",
        workflow_step_id="step-01",
        summary="captured intent",
        decisions=("name the engine 'mythic vibe'",),
        verification_results=(
            VerificationResult(name="g1", passed=all_passed),
        ),
    )


def _make_entry(
    *,
    workflow_id: str = "WF-X",
    step_id: str = "step-01",
    role: str = "Skald",
    status: str = "pending",
) -> ForgeLedgerEntry:
    return ForgeLedgerEntry(
        workflow_id=workflow_id,
        step_id=step_id,
        role=role,
        status=status,
        started_at="2026-04-29T22:00:00Z",
        agent_input=_make_input(role=role, phase="intent"),
    )


# ---- ForgeLedgerEntry round-trip ----------------------------------------


class ForgeLedgerEntryRoundTripTests(unittest.TestCase):
    def test_pending_entry_round_trip(self) -> None:
        entry = _make_entry()
        self.assertEqual(ForgeLedgerEntry.from_dict(entry.to_dict()), entry)

    def test_completed_entry_round_trip(self) -> None:
        entry = ForgeLedgerEntry(
            workflow_id="WF-X",
            step_id="step-01",
            role="Skald",
            status="succeeded",
            started_at="2026-04-29T22:00:00Z",
            agent_input=_make_input(),
            completed_at="2026-04-29T22:00:42Z",
            duration_ms=42000,
            agent_output=_make_output(),
            notes=("ran clean",),
        )
        self.assertEqual(ForgeLedgerEntry.from_dict(entry.to_dict()), entry)

    def test_from_dict_rejects_missing_agent_input(self) -> None:
        with self.assertRaises(ValueError):
            ForgeLedgerEntry.from_dict(
                {
                    "workflow_id": "WF-X",
                    "step_id": "s1",
                    "role": "Skald",
                    "status": "pending",
                    "started_at": "t",
                    # agent_input missing
                }
            )

    def test_from_dict_handles_invalid_duration_gracefully(self) -> None:
        payload = _make_entry().to_dict()
        payload["duration_ms"] = "not-a-number"
        rebuilt = ForgeLedgerEntry.from_dict(payload)
        self.assertIsNone(rebuilt.duration_ms)


class WithStatusTests(unittest.TestCase):
    def test_with_status_returns_new_entry_with_replaced_fields(self) -> None:
        original = _make_entry(status="pending")
        updated = original.with_status(
            "succeeded",
            completed_at="2026-04-29T22:00:42Z",
            duration_ms=42000,
            agent_output=_make_output(),
        )
        self.assertEqual(original.status, "pending")
        self.assertEqual(updated.status, "succeeded")
        self.assertEqual(updated.completed_at, "2026-04-29T22:00:42Z")
        self.assertEqual(updated.duration_ms, 42000)
        self.assertIsNotNone(updated.agent_output)

    def test_with_status_rejects_unknown_status(self) -> None:
        with self.assertRaises(ValueError) as cm:
            _make_entry().with_status("teleported")
        self.assertIn("teleported", str(cm.exception))

    def test_with_status_preserves_unspecified_fields(self) -> None:
        original = _make_entry(status="pending")
        updated = original.with_status("running")
        self.assertEqual(updated.completed_at, original.completed_at)
        self.assertEqual(updated.duration_ms, original.duration_ms)
        self.assertEqual(updated.agent_output, original.agent_output)
        self.assertEqual(updated.notes, original.notes)

    def test_known_statuses(self) -> None:
        self.assertEqual(
            FORGE_STEP_STATUSES,
            ("pending", "running", "succeeded", "failed", "blocked"),
        )


# ---- ForgeLedger persistence --------------------------------------------


class ForgeLedgerPathTests(unittest.TestCase):
    def test_path_resolves_under_mythic_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            self.assertEqual(
                ledger.path,
                Path(tmp) / "mythic" / FORGE_LEDGER_FILENAME,
            )


class ForgeLedgerEmptyAndCorruptTests(unittest.TestCase):
    def test_load_returns_empty_list_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            self.assertEqual(ledger.load(), [])

    def test_load_returns_empty_list_on_corrupt_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.path.parent.mkdir(parents=True)
            ledger.path.write_text("{not valid json", encoding="utf-8")
            self.assertEqual(ledger.load(), [])

    def test_load_returns_empty_when_top_level_is_not_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.path.parent.mkdir(parents=True)
            ledger.path.write_text("[]", encoding="utf-8")
            self.assertEqual(ledger.load(), [])

    def test_load_skips_malformed_rows_keeps_others(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.path.parent.mkdir(parents=True)
            payload = {
                "version": FORGE_LEDGER_SCHEMA_VERSION,
                "entries": [
                    _make_entry(step_id="step-01").to_dict(),
                    {"missing-required-fields": True},  # malformed
                    _make_entry(step_id="step-02").to_dict(),
                ],
            }
            ledger.path.write_text(json.dumps(payload), encoding="utf-8")
            entries = ledger.load()
            self.assertEqual([e.step_id for e in entries], ["step-01", "step-02"])


class ForgeLedgerAppendTests(unittest.TestCase):
    def test_append_writes_one_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            entry = _make_entry()
            ledger.append(entry)
            self.assertTrue(ledger.path.exists())
            payload = json.loads(ledger.path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], FORGE_LEDGER_SCHEMA_VERSION)
            self.assertEqual(len(payload["entries"]), 1)
            self.assertEqual(payload["entries"][0]["step_id"], entry.step_id)

    def test_append_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            for i in range(5):
                ledger.append(_make_entry(step_id=f"step-{i:02d}"))
            entries = ledger.load()
            self.assertEqual(
                [e.step_id for e in entries],
                [f"step-{i:02d}" for i in range(5)],
            )

    def test_append_caps_at_FORGE_LEDGER_LIMIT(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            for i in range(FORGE_LEDGER_LIMIT + 25):
                ledger.append(_make_entry(step_id=f"step-{i:04d}"))
            entries = ledger.load()
            self.assertEqual(len(entries), FORGE_LEDGER_LIMIT)
            # The oldest 25 are dropped.
            self.assertEqual(entries[0].step_id, f"step-{25:04d}")
            self.assertEqual(
                entries[-1].step_id,
                f"step-{FORGE_LEDGER_LIMIT + 24:04d}",
            )


class ForgeLedgerUpdateStepTests(unittest.TestCase):
    def test_update_step_replaces_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry(step_id="step-01", status="pending"))
            ledger.update_step(
                "WF-X",
                "step-01",
                status="running",
            )
            entries = ledger.load()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].status, "running")

    def test_update_step_records_full_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry(status="pending"))
            updated = ledger.update_step(
                "WF-X",
                "step-01",
                status="succeeded",
                completed_at="2026-04-29T22:00:42Z",
                duration_ms=42000,
                agent_output=_make_output(),
                notes=("clean run",),
            )
            self.assertEqual(updated.status, "succeeded")
            self.assertEqual(updated.duration_ms, 42000)
            self.assertIsNotNone(updated.agent_output)
            self.assertEqual(updated.notes, ("clean run",))
            reloaded = ledger.load()[0]
            self.assertEqual(reloaded, updated)

    def test_update_step_targets_latest_match_only(self) -> None:
        """If the same (workflow_id, step_id) appears multiple times — e.g.,
        a forge resume re-running a previously failed step — update_step
        replaces the most recent occurrence only."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            first = _make_entry(step_id="step-01")
            second = _make_entry(step_id="step-01")
            ledger.append(first)
            ledger.append(second)
            ledger.update_step("WF-X", "step-01", status="succeeded")
            entries = ledger.load()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].status, "pending")  # first untouched
            self.assertEqual(entries[1].status, "succeeded")  # second updated

    def test_update_step_raises_when_no_matching_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            with self.assertRaises(ValueError) as cm:
                ledger.update_step("WF-Y", "step-99", status="succeeded")
            self.assertIn("WF-Y", str(cm.exception))
            self.assertIn("step-99", str(cm.exception))

    def test_update_step_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry())
            with self.assertRaises(ValueError):
                ledger.update_step("WF-X", "step-01", status="exploded")


class ForgeLedgerQueryTests(unittest.TestCase):
    def test_latest_returns_newest_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            for i in range(10):
                ledger.append(_make_entry(step_id=f"step-{i:02d}"))
            window = ledger.latest(limit=3)
            self.assertEqual([e.step_id for e in window], ["step-07", "step-08", "step-09"])

    def test_latest_zero_or_negative_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry())
            self.assertEqual(ledger.latest(limit=0), [])
            self.assertEqual(ledger.latest(limit=-1), [])

    def test_find_by_workflow_groups_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry(workflow_id="WF-A", step_id="step-01"))
            ledger.append(_make_entry(workflow_id="WF-B", step_id="step-01"))
            ledger.append(_make_entry(workflow_id="WF-A", step_id="step-02"))
            wf_a = ledger.find_by_workflow("WF-A")
            wf_b = ledger.find_by_workflow("WF-B")
            self.assertEqual([e.step_id for e in wf_a], ["step-01", "step-02"])
            self.assertEqual([e.step_id for e in wf_b], ["step-01"])
            self.assertEqual(ledger.find_by_workflow("WF-NONEXISTENT"), [])

    def test_find_step_returns_most_recent_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry(step_id="step-01"))
            ledger.append(_make_entry(step_id="step-01"))
            # Update the second one so we can distinguish them.
            ledger.update_step("WF-X", "step-01", status="succeeded")
            found = ledger.find_step("WF-X", "step-01")
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found.status, "succeeded")

    def test_find_step_returns_none_when_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry(step_id="step-01"))
            self.assertIsNone(ledger.find_step("WF-X", "no-such-step"))


class ForgeLedgerConcurrencyTests(unittest.TestCase):
    """Append goes through file_mutation_queue, so concurrent appends
    against the same file must not corrupt or lose entries."""

    def test_concurrent_appends_preserve_every_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            errors: list[Exception] = []

            def _writer(i: int) -> None:
                try:
                    ledger.append(_make_entry(step_id=f"step-{i:04d}"))
                except Exception as exc:  # noqa: BLE001 - test surface
                    errors.append(exc)

            threads = [threading.Thread(target=_writer, args=(i,)) for i in range(40)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            entries = ledger.load()
            step_ids = sorted(e.step_id for e in entries)
            expected = sorted(f"step-{i:04d}" for i in range(40))
            self.assertEqual(step_ids, expected)


class ForgeLedgerFileShapeTests(unittest.TestCase):
    def test_written_file_has_version_and_entries_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ForgeLedger(root=Path(tmp))
            ledger.append(_make_entry())
            payload = json.loads(ledger.path.read_text(encoding="utf-8"))
            self.assertIn("version", payload)
            self.assertIn("entries", payload)
            self.assertEqual(payload["version"], FORGE_LEDGER_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
