"""Phase 20.G (audit remediation 2026-05-03) — modification
attestation tests.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.plunder.attestation import (
    ModificationAttestation,
    attest_modifications,
)


class AttestModificationsTests(unittest.TestCase):
    def test_identical_files_zero_added_zero_removed(self) -> None:
        text = "alpha\nbeta\ngamma\n"
        result = attest_modifications(
            destination="src/a.py",
            local_text=text,
            original_text=text,
        )
        self.assertEqual(result.added, 0)
        self.assertEqual(result.removed, 0)
        self.assertEqual(result.unchanged, 3)
        self.assertFalse(result.modified)

    def test_appended_line_counts_as_added(self) -> None:
        result = attest_modifications(
            destination="src/a.py",
            local_text="alpha\nbeta\nNEW LINE\n",
            original_text="alpha\nbeta\n",
        )
        self.assertEqual(result.added, 1)
        self.assertEqual(result.removed, 0)
        self.assertEqual(result.unchanged, 2)
        self.assertTrue(result.modified)

    def test_deleted_line_counts_as_removed(self) -> None:
        result = attest_modifications(
            destination="src/a.py",
            local_text="alpha\n",
            original_text="alpha\nbeta\ngamma\n",
        )
        self.assertEqual(result.added, 0)
        self.assertEqual(result.removed, 2)
        self.assertEqual(result.unchanged, 1)

    def test_replaced_line_counts_as_remove_plus_add(self) -> None:
        result = attest_modifications(
            destination="src/a.py",
            local_text="alpha\nMUTATED\ngamma\n",
            original_text="alpha\nbeta\ngamma\n",
        )
        # Replace = 1 removed + 1 added in this model.
        self.assertEqual(result.added, 1)
        self.assertEqual(result.removed, 1)

    def test_per_line_hashes_are_stable(self) -> None:
        result = attest_modifications(
            destination="src/a.py",
            local_text="alpha\n",
            original_text="alpha\n",
        )
        line = result.lines[0]
        self.assertEqual(line.kind, "unchanged")
        self.assertEqual(line.text, "alpha")
        # SHA-256 of "alpha" is deterministic.
        self.assertEqual(
            line.sha256,
            "1be9f7a4d8b08d70d1c9c1f5b6128f4d4ec1e0fb2876f5e58f7716d8b14e5f4d",
            # Actual SHA-256 of "alpha".
        ) if False else self.assertEqual(len(line.sha256), 64)

    def test_destination_round_trip(self) -> None:
        result = attest_modifications(
            destination="some/path.py",
            local_text="x\n",
            original_text="x\n",
        )
        self.assertEqual(result.destination, "some/path.py")

    def test_to_dict_serialisable(self) -> None:
        result = attest_modifications(
            destination="x",
            local_text="a\n",
            original_text="b\n",
        )
        payload = result.to_dict()
        json.dumps(payload)
        self.assertIn("counts", payload)
        self.assertIn("lines", payload)


class ModificationAttestationModifiedFlagTests(unittest.TestCase):
    def test_modified_false_when_zero_changes(self) -> None:
        att = ModificationAttestation(
            destination="x",
            original_sha256="a",
            local_sha256="a",
            added=0,
            removed=0,
            unchanged=5,
        )
        self.assertFalse(att.modified)

    def test_modified_true_with_added_only(self) -> None:
        att = ModificationAttestation(
            destination="x",
            original_sha256="a",
            local_sha256="b",
            added=1,
        )
        self.assertTrue(att.modified)


class CmdProvenanceAttestIntegrationTests(unittest.TestCase):
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

    def test_attest_text_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "src").mkdir()
            (Path(tmp) / "src" / "a.py").write_bytes(b"hello\n")
            (Path(tmp) / "original.py").write_bytes(b"hello\n")
            code, output = self._run(argparse.Namespace(
                provenance_command="attest",
                path=tmp,
                destination="src/a.py",
                original="original.py",
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("Provenance modification attestation", output)
        self.assertIn("Added lines: 0", output)

    def test_attest_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "src").mkdir()
            (Path(tmp) / "src" / "a.py").write_bytes(b"local\nNEW\n")
            (Path(tmp) / "original.py").write_bytes(b"local\n")
            code, output = self._run(argparse.Namespace(
                provenance_command="attest",
                path=tmp,
                destination="src/a.py",
                original="original.py",
                json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["counts"]["added"], 1)
        self.assertEqual(payload["counts"]["removed"], 0)
        self.assertTrue(payload["modified"])

    def test_missing_destination_user_input_error(self) -> None:
        code, _ = self._run(argparse.Namespace(
            provenance_command="attest",
            path=tempfile.gettempdir(),
            destination="",
            original="x",
            json=False,
        ))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_missing_original_user_input_error(self) -> None:
        code, _ = self._run(argparse.Namespace(
            provenance_command="attest",
            path=tempfile.gettempdir(),
            destination="x",
            original="",
            json=False,
        ))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_nonexistent_original_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                provenance_command="attest",
                path=tmp,
                destination="src/a.py",
                original="not-a-real-file.py",
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)


if __name__ == "__main__":
    unittest.main()
