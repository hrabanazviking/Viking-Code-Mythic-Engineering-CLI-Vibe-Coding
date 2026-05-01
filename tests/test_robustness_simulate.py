"""Tests for PH-18 Slice 18.4 — failure simulation."""

from __future__ import annotations

import argparse
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mythic_vibe_cli.commands import cmd_simulate
from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.robustness.simulate import (
    SimulationOutcome,
    SimulationReport,
    run_simulation,
)


# ---- SimulationOutcome / Report --------------------------------------


class SimulationOutcomeTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        outcome = SimulationOutcome(
            name="x",
            passed=True,
            expected_exit_code=0,
            actual_exit_code=0,
            stdout="hi",
            stderr="",
        )
        payload = outcome.to_dict()
        for key in {
            "name",
            "passed",
            "expected_exit_code",
            "actual_exit_code",
            "stdout_chars",
            "stderr_chars",
            "stderr_preview",
        }:
            self.assertIn(key, payload)


class SimulationReportTests(unittest.TestCase):
    def test_passed_failed_counts(self) -> None:
        report = SimulationReport(
            outcomes=[
                SimulationOutcome(
                    name="a",
                    passed=True,
                    expected_exit_code=0,
                    actual_exit_code=0,
                    stdout="",
                    stderr="",
                ),
                SimulationOutcome(
                    name="b",
                    passed=False,
                    expected_exit_code=0,
                    actual_exit_code=1,
                    stdout="",
                    stderr="",
                ),
            ]
        )
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
        self.assertFalse(report.ok)


# ---- run_simulation (canonical scenarios) ----------------------------


class RunSimulationCanonicalTests(unittest.TestCase):
    """Run the full canonical scenario set against the live CLI.
    All four scenarios should pass — they're chosen to exercise
    paths where the CLI already handles failure cleanly."""

    def test_all_canonical_scenarios_pass(self) -> None:
        report = run_simulation()
        self.assertEqual(len(report.outcomes), 4)
        for outcome in report.outcomes:
            self.assertTrue(
                outcome.passed,
                f"scenario {outcome.name!r} failed: "
                f"exit={outcome.actual_exit_code} stderr={outcome.stderr!r}",
            )
        self.assertTrue(report.ok)

    def test_canonical_scenarios_include_all_four(self) -> None:
        report = run_simulation()
        names = {o.name for o in report.outcomes}
        self.assertEqual(
            names,
            {
                "malformed-status",
                "missing-artefact",
                "provider-unconfigured",
                "constraint-blocking-no-override",
            },
        )


class RunSimulationCustomScenariosTests(unittest.TestCase):
    def test_custom_scenario_passing(self) -> None:
        def passing_scenario(root: Path) -> SimulationOutcome:
            return SimulationOutcome(
                name="custom-pass",
                passed=True,
                expected_exit_code=0,
                actual_exit_code=0,
                stdout="",
                stderr="",
            )

        report = run_simulation(scenarios=(passing_scenario,))
        self.assertTrue(report.ok)
        self.assertEqual(len(report.outcomes), 1)

    def test_scenario_raising_captured_as_failure(self) -> None:
        def crashing_scenario(root: Path) -> SimulationOutcome:
            raise RuntimeError("scenario blew up")

        report = run_simulation(scenarios=(crashing_scenario,))
        self.assertFalse(report.ok)
        outcome = report.outcomes[0]
        self.assertFalse(outcome.passed)
        self.assertIn("blew up", outcome.stderr)
        self.assertIn("RuntimeError", outcome.detail)


# ---- cmd_simulate ----------------------------------------------------


class CmdSimulateTests(unittest.TestCase):
    def test_canonical_run_returns_success(self) -> None:
        ns = argparse.Namespace(json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_simulate(ns)
        payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertTrue(payload["report"]["ok"])
        self.assertEqual(payload["report"]["total"], 4)

    def test_text_mode_prints_summary(self) -> None:
        ns = argparse.Namespace(json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_simulate(ns)
        output = buf.getvalue()
        self.assertIn("Mythic resilience simulation", output)
        self.assertIn("Total scenarios", output)
        # Each scenario marked PASS or FAIL.
        self.assertIn("[PASS]", output)


class SimulateArgparseTests(unittest.TestCase):
    def test_simulate_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["simulate", "--json"])
        self.assertEqual(ns.command, "simulate")
        self.assertTrue(ns.json)


if __name__ == "__main__":
    unittest.main()
