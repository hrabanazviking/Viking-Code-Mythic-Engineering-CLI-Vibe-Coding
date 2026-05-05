from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.workflow import MythicRunConfig, MythicWorkflow


class MythicWorkflowTests(unittest.TestCase):
    def test_checkin_preserves_phase_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(MythicRunConfig(goal="Test", noob_mode=False), method_source="test")
            workflow.check_in("build", "did build")
            workflow.check_in("intent", "rechecked intent")

            status = json.loads((root / "mythic" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["completed_phases"], ["build", "intent"])

    def test_doctor_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            errors, warnings = workflow.doctor()
            self.assertTrue(errors)
            self.assertFalse(any("Invalid JSON" in item for item in errors))
            self.assertEqual(warnings, [])

    def test_status_summary_handles_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir(parents=True, exist_ok=True)
            (mythic / "status.json").write_text("{broken", encoding="utf-8")

            workflow = MythicWorkflow(root)
            summary = workflow.status_summary()
            self.assertIn("Goal:", summary)

    def test_doctor_report_detects_state_regression_and_contract_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(MythicRunConfig(goal="Test", noob_mode=False), method_source="test")

            (root / "docs" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
            (root / "docs" / "COMMAND_CONTRACTS.md").write_text(
                "# Command Contracts\n\nThis doc mentions doctor and scry only.\n",
                encoding="utf-8",
            )

            status_path = root / "mythic" / "status.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["current_phase"] = "build"
            status["completed_phases"] = ["build", "intent"]
            status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

            report = workflow.doctor_report()

            self.assertFalse(report["ok"])
            self.assertTrue(any("Phase order regressed" in item for item in report["errors"]))
            self.assertTrue(any("may be drifting" in item for item in report["warnings"]))
            self.assertIn("docs/INDEX.md", report["sections"]["docs"])
            self.assertIn("docs/COMMAND_CONTRACTS.md", report["sections"]["docs"])


# PH-23.13 — coverage push for workflow.py from 82% toward 95%+.
# Targets: invalid-phase rejection, verification-record edge
# cases, status_summary handoff line, doctor edge branches
# (StateStoreError, missing-active-runtime, syntax error in
# runtime file, ADR + docs warnings), _load_status fallbacks,
# _next_phase all-complete branch.


class WorkflowEdgeBranchTests(unittest.TestCase):
    """PH-23.13 — focused edge-branch tests for workflow.py."""

    def test_check_in_rejects_invalid_phase(self) -> None:
        # Lines 73-75: ValueError on phase not in PHASES.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            with self.assertRaises(ValueError) as ctx:
                workflow.check_in("phase_does_not_exist", "x")
            self.assertIn("Invalid phase", str(ctx.exception))

    def test_check_in_reflect_blocked_without_verification(self) -> None:
        # Reflect requires a successful verification record.
        # Without one, check_in("reflect") raises ValueError.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            with self.assertRaises(ValueError) as ctx:
                workflow.check_in("reflect", "trying anyway")
            self.assertIn("verification", str(ctx.exception).lower())

    def test_check_in_reflect_blocked_when_record_invalid_json(self) -> None:
        # Lines 105-106: latest.json exists but JSON is broken.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            verif_dir = root / "mythic" / "verifications"
            verif_dir.mkdir(parents=True, exist_ok=True)
            (verif_dir / "latest.json").write_text(
                "{ broken json", encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                workflow.check_in("reflect", "x")
            self.assertIn("Cannot read latest verification", str(ctx.exception))

    def test_check_in_reflect_blocked_when_record_not_dict(self) -> None:
        # Line 109: latest.json parses but isn't a dict.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            verif_dir = root / "mythic" / "verifications"
            verif_dir.mkdir(parents=True, exist_ok=True)
            (verif_dir / "latest.json").write_text(
                '["array, not dict"]', encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                workflow.check_in("reflect", "x")
            self.assertIn("invalid", str(ctx.exception).lower())

    def test_check_in_reflect_blocked_when_result_not_pass(self) -> None:
        # Line 111: result is "fail" or anything other than "pass".
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            verif_dir = root / "mythic" / "verifications"
            verif_dir.mkdir(parents=True, exist_ok=True)
            (verif_dir / "latest.json").write_text(
                json.dumps({"result": "fail"}), encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                workflow.check_in("reflect", "x")
            self.assertIn("pass", str(ctx.exception).lower())

    def test_status_summary_with_handoff_record(self) -> None:
        # Line 127-131: when load_latest_handoff returns a record,
        # the summary appends a "Latest handoff" line.
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            # Create a fake handoff record at the path the workflow loader expects.
            from dataclasses import dataclass
            @dataclass
            class FakeHandoff:
                handoff_id: str = "h-2026-05-05-001"
                next_steps: list = None
                def __post_init__(self):
                    if self.next_steps is None:
                        self.next_steps = ["Resume the auth slice"]

            with mock.patch(
                "mythic_vibe_cli.workflow.load_latest_handoff",
                return_value=FakeHandoff(),
            ):
                summary = workflow.status_summary()

        self.assertIn("Latest handoff", summary)
        self.assertIn("h-2026-05-05-001", summary)
        self.assertIn("Resume the auth slice", summary)

    def test_load_status_fallback_when_path_missing(self) -> None:
        # Line 356-357: status.json missing → return template.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            status = workflow._load_status(root / "no-status.json")
        self.assertEqual(status["goal"], "unspecified goal")
        self.assertEqual(status["completed_phases"], [])

    def test_load_status_fallback_on_invalid_json(self) -> None:
        # Lines 359-362: status.json exists but JSON is broken.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            broken = root / "broken.json"
            broken.write_text("{not valid json", encoding="utf-8")
            status = workflow._load_status(broken)
        self.assertEqual(status["goal"], "unspecified goal")

    def test_load_status_fallback_when_payload_not_dict(self) -> None:
        # Lines 364-365: status.json parses but isn't a dict.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            list_payload = root / "list.json"
            list_payload.write_text("[1, 2, 3]", encoding="utf-8")
            status = workflow._load_status(list_payload)
        self.assertEqual(status["goal"], "unspecified goal")

    def test_load_status_sets_defaults_for_partial_payload(self) -> None:
        # Lines 367-371: dict-shaped but missing keys → defaults
        # filled in via setdefault.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            partial = root / "partial.json"
            partial.write_text(
                json.dumps({"current_phase": "build"}),
                encoding="utf-8",
            )
            status = workflow._load_status(partial)
        self.assertEqual(status["goal"], "unspecified goal")
        self.assertEqual(status["current_phase"], "build")
        self.assertEqual(status["completed_phases"], [])
        self.assertEqual(status["history"], [])
        self.assertIsNone(status["last_update"])

    def test_next_phase_all_phases_complete(self) -> None:
        # Lines 374-378: when every phase has been completed at
        # least once, returns the special "all phases completed"
        # marker rather than just the next phase name.
        from mythic_vibe_cli.workflow import PHASES

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            result = workflow._next_phase(list(PHASES))
        self.assertIn("all phases completed", result)

    def test_doctor_repo_boundary_warns_on_readme_without_active_runtime(
        self,
    ) -> None:
        # Line 263-264: README exists but lacks "Active Runtime
        # Path" section → warning emitted.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            (root / "README.md").write_text(
                "# Project\nNo runtime section here.",
                encoding="utf-8",
            )
            # Provide the boundary docs so the test isolates the
            # README warning.
            (root / "REPO_BOUNDARY.md").write_text("x", encoding="utf-8")
            (root / "docs" / "ACTIVE_PRODUCT_BOUNDARY.md").write_text(
                "x", encoding="utf-8",
            )
            (root / "docs" / "DORMANT_ISLANDS.md").write_text(
                "x", encoding="utf-8",
            )
            adrs = root / "docs" / "ADRS"
            adrs.mkdir(parents=True, exist_ok=True)
            (adrs / "ADR-0001-active-runtime-boundary.md").write_text(
                "x", encoding="utf-8",
            )
            (adrs / "ADR-0002-no-direct-vendor-imports.md").write_text(
                "x", encoding="utf-8",
            )

            errors, warnings = workflow._doctor_repo_boundary()[:2]

        self.assertTrue(
            any("Active Runtime Path" in w for w in warnings),
            f"warnings={warnings}",
        )

    def test_doctor_repo_boundary_errors_on_missing_active_runtime(
        self,
    ) -> None:
        # Lines 267-269: missing mythic_vibe_cli/ package is a
        # hard error and short-circuits further checks.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            # Provide just the boundary docs but NO runtime
            # package — even if the runtime package exists in the
            # actual repo, the workflow's root is the temp dir.
            (root / "REPO_BOUNDARY.md").write_text("x", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "ACTIVE_PRODUCT_BOUNDARY.md").write_text(
                "x", encoding="utf-8",
            )
            (root / "docs" / "DORMANT_ISLANDS.md").write_text(
                "x", encoding="utf-8",
            )
            adrs = root / "docs" / "ADRS"
            adrs.mkdir()
            (adrs / "ADR-0001-active-runtime-boundary.md").write_text(
                "x", encoding="utf-8",
            )
            (adrs / "ADR-0002-no-direct-vendor-imports.md").write_text(
                "x", encoding="utf-8",
            )

            errors, _, _ = workflow._doctor_repo_boundary()

        self.assertTrue(
            any("Missing active runtime package" in e for e in errors),
        )

    def test_doctor_docs_drift_warns_on_legacy_index2(self) -> None:
        # Line 312-313: legacy docs/index2.md alongside docs/INDEX.md
        # → warning recommending the canonical hub.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(
                MythicRunConfig(goal="t", noob_mode=False),
                method_source="test",
            )
            # init_project creates INDEX.md; manually add legacy.
            (root / "docs" / "index2.md").write_text(
                "# legacy", encoding="utf-8",
            )
            errors, warnings, _ = workflow._doctor_docs_drift(
                project_scaffold=True,
            )
        self.assertTrue(
            any("Legacy docs/index2.md" in w for w in warnings),
            f"warnings={warnings}",
        )


if __name__ == "__main__":
    unittest.main()
