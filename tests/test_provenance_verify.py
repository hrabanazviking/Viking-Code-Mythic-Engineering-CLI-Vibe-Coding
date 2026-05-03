"""Phase 20.6 (audit remediation 2026-05-03) — provenance
verify tests.

Covers ``mythic_vibe_cli/plunder/verify.py`` + the
``provenance verify`` CLI handler.

Strategy: build a fake mythic/imports/plunder_manifest.json
with three records (matching SHA, drifted SHA, missing
destination) and assert each lands in the correct bucket.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.plunder.verify import (
    VerificationEntry,
    VerificationReport,
    verify_provenance,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_manifest(root: Path, imports: list[dict[str, object]]) -> None:
    path = root / "mythic" / "imports" / "plunder_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "imports": imports}
    path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _seed_file(root: Path, relpath: str, content: str) -> None:
    """Write bytes directly to avoid Windows ``\\r\\n`` newline
    translation that ``write_text`` would otherwise apply, which
    would shift the on-disk SHA away from the test's expected
    hash of ``content``."""
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content.encode("utf-8"))


class VerifyProvenanceTests(unittest.TestCase):
    def test_match_when_sha_aligns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = "exact upstream contents\n"
            _seed_file(Path(tmp), "src/a.py", content)
            _write_manifest(Path(tmp), [
                {
                    "destination": "src/a.py",
                    "repo": "owner/repo",
                    "source_file": "a.py",
                    "source_sha": _sha256(content),
                },
            ])
            report = verify_provenance(Path(tmp))
        self.assertEqual(len(report.entries), 1)
        self.assertEqual(report.entries[0].status, "match")
        self.assertEqual(len(report.matches), 1)
        self.assertEqual(len(report.drifts), 0)
        self.assertEqual(len(report.missing), 0)

    def test_drift_when_local_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_file(Path(tmp), "src/b.py", "modified locally\n")
            _write_manifest(Path(tmp), [
                {
                    "destination": "src/b.py",
                    "repo": "owner/repo",
                    "source_file": "b.py",
                    "source_sha": _sha256("original upstream\n"),
                },
            ])
            report = verify_provenance(Path(tmp))
        self.assertEqual(report.entries[0].status, "drift")
        self.assertEqual(len(report.drifts), 1)

    def test_missing_when_destination_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write_manifest(Path(tmp), [
                {
                    "destination": "src/c.py",
                    "repo": "owner/repo",
                    "source_file": "c.py",
                    "source_sha": _sha256("anything"),
                },
            ])
            report = verify_provenance(Path(tmp))
        self.assertEqual(report.entries[0].status, "missing")
        self.assertEqual(report.entries[0].actual_sha, "")

    def test_empty_manifest_yields_empty_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = verify_provenance(Path(tmp))
        self.assertEqual(report.entries, [])
        self.assertTrue(report.ok)

    def test_drift_does_not_flip_ok_to_false(self) -> None:
        """``ok`` is permissive by design — operators may
        modify imports intentionally. Use the per-bucket counts
        if you want a stricter signal."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_file(Path(tmp), "src/x.py", "drifted\n")
            _write_manifest(Path(tmp), [
                {
                    "destination": "src/x.py",
                    "source_sha": _sha256("original"),
                    "repo": "r",
                    "source_file": "x.py",
                },
            ])
            report = verify_provenance(Path(tmp))
        self.assertTrue(report.ok)
        self.assertEqual(len(report.drifts), 1)


class VerificationReportSerializationTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        report = VerificationReport(entries=[
            VerificationEntry(
                destination="src/a.py",
                repo="r",
                source_file="a.py",
                source_sha="aaa",
                actual_sha="aaa",
                status="match",
            ),
        ])
        payload = report.to_dict()
        self.assertEqual(payload["counts"]["match"], 1)
        self.assertEqual(payload["counts"]["total"], 1)
        json.dumps(payload)  # serialisable.


class CmdProvenanceVerifyIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_provenance

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_provenance(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_verify_subcommand_text_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = "ok\n"
            _seed_file(Path(tmp), "src/a.py", content)
            _write_manifest(Path(tmp), [
                {
                    "destination": "src/a.py",
                    "repo": "r",
                    "source_file": "a.py",
                    "source_sha": _sha256(content),
                },
            ])
            code, output = self._run(argparse.Namespace(
                provenance_command="verify",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("Provenance verification", output)
        self.assertIn("Match: 1", output)

    def test_verify_subcommand_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content = "ok\n"
            _seed_file(Path(tmp), "src/a.py", content)
            _write_manifest(Path(tmp), [
                {
                    "destination": "src/a.py",
                    "repo": "r",
                    "source_file": "a.py",
                    "source_sha": _sha256(content),
                },
            ])
            code, output = self._run(argparse.Namespace(
                provenance_command="verify",
                path=tmp,
                json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["counts"]["match"], 1)
        self.assertEqual(payload["counts"]["total"], 1)

    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        code, _ = self._run(argparse.Namespace(
            provenance_command="bogus",
            path=tempfile.gettempdir(),
            json=False,
        ))
        self.assertEqual(code, USER_INPUT_ERROR)


if __name__ == "__main__":
    unittest.main()
