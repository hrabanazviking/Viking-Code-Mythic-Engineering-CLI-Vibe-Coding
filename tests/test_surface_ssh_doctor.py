"""Tests for PH-17 Slice 17.3 — SSH-readiness diagnostic."""

from __future__ import annotations

import io
import os
import unittest
from unittest import mock

from mythic_vibe_cli.surfaces.ssh_doctor import (
    SshCheck,
    SshDoctorReport,
    run_ssh_doctor,
)


class SshCheckTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        check = SshCheck(
            name="x", passed=True, detail="ok", severity="advisory"
        )
        payload = check.to_dict()
        for key in {"name", "passed", "detail", "severity"}:
            self.assertIn(key, payload)


class SshDoctorReportTests(unittest.TestCase):
    def test_ok_when_all_pass(self) -> None:
        report = SshDoctorReport(
            checks=[SshCheck(name="x", passed=True, detail="ok")]
        )
        self.assertTrue(report.ok)

    def test_warnings_count(self) -> None:
        report = SshDoctorReport(
            checks=[
                SshCheck(name="a", passed=True, detail="ok"),
                SshCheck(name="b", passed=False, detail="bad", severity="warn"),
                SshCheck(name="c", passed=False, detail="ad", severity="advisory"),
            ]
        )
        self.assertEqual(report.warnings, 1)
        self.assertFalse(report.ok)

    def test_to_dict(self) -> None:
        report = SshDoctorReport(
            checks=[SshCheck(name="x", passed=True, detail="ok")]
        )
        payload = report.to_dict()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["passed"], 1)
        self.assertTrue(payload["ok"])


class RunSshDoctorTests(unittest.TestCase):
    def test_runs_all_checks(self) -> None:
        report = run_ssh_doctor()
        names = {c.name for c in report.checks}
        # Each canonical check must appear.
        for required in {
            "tty-detected",
            "color-output-safe",
            "term-env-set",
            "approval-default-sensible",
        }:
            self.assertIn(required, names)

    def test_no_color_set_passes_color_check(self) -> None:
        previous = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        try:
            # Force non-TTY by mocking stdout.isatty.
            fake_stdout = io.StringIO()
            with mock.patch("sys.stdout", fake_stdout):
                report = run_ssh_doctor()
        finally:
            if previous is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = previous
        color_check = next(
            c for c in report.checks if c.name == "color-output-safe"
        )
        self.assertTrue(color_check.passed)

    def test_term_unset_warns(self) -> None:
        previous = os.environ.pop("TERM", None)
        try:
            report = run_ssh_doctor()
        finally:
            if previous is not None:
                os.environ["TERM"] = previous
        term_check = next(
            c for c in report.checks if c.name == "term-env-set"
        )
        self.assertFalse(term_check.passed)
        self.assertEqual(term_check.severity, "warn")

    def test_term_set_passes(self) -> None:
        previous = os.environ.get("TERM")
        os.environ["TERM"] = "xterm-256color"
        try:
            report = run_ssh_doctor()
        finally:
            if previous is None:
                os.environ.pop("TERM", None)
            else:
                os.environ["TERM"] = previous
        term_check = next(
            c for c in report.checks if c.name == "term-env-set"
        )
        self.assertTrue(term_check.passed)


if __name__ == "__main__":
    unittest.main()
