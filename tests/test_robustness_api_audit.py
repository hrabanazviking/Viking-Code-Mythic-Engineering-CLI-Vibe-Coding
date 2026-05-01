"""Tests for PH-18 Slice 18.3 — API surface audit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.robustness.api_audit import (
    ApiAuditResult,
    ApiFinding,
    _enumerate_subpackages_with_public_api,
    _importer_subpackage,
    _module_dot_to_subpackage,
    _scan_module,
    audit_api_surfaces,
)


def _runtime_tree(root: Path, files: dict[str, str]) -> None:
    runtime = root / "mythic_vibe_cli"
    runtime.mkdir(parents=True, exist_ok=True)
    for relative, body in files.items():
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


# ---- helpers ---------------------------------------------------------


class ImporterSubpackageTests(unittest.TestCase):
    def test_top_level_returns_empty(self) -> None:
        self.assertEqual(_importer_subpackage("commands.py"), "")

    def test_subpackage_returns_first_segment(self) -> None:
        self.assertEqual(
            _importer_subpackage("ai/providers/yggdrasil.py"), "ai"
        )

    def test_nested_path(self) -> None:
        self.assertEqual(
            _importer_subpackage("policy/constraint_store.py"), "policy"
        )


class ModuleDotResolutionTests(unittest.TestCase):
    def test_in_tree_subpackage(self) -> None:
        self.assertEqual(
            _module_dot_to_subpackage(
                "mythic_vibe_cli.policy.constraint_store",
                importer_relative="ai/providers/yggdrasil.py",
            ),
            ("policy", "constraint_store"),
        )

    def test_subpackage_init_only(self) -> None:
        self.assertEqual(
            _module_dot_to_subpackage(
                "mythic_vibe_cli.policy",
                importer_relative="ai/providers/yggdrasil.py",
            ),
            ("policy", ""),
        )

    def test_third_party_returns_none(self) -> None:
        self.assertIsNone(
            _module_dot_to_subpackage(
                "json",
                importer_relative="ai/providers/yggdrasil.py",
            )
        )

    def test_relative_import_returns_none(self) -> None:
        self.assertIsNone(
            _module_dot_to_subpackage("", importer_relative="x.py")
        )


# ---- _enumerate_subpackages_with_public_api ---------------------------


class EnumerateSubpackagesTests(unittest.TestCase):
    def test_trivial_init_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "mythic_vibe_cli"
            runtime.mkdir()
            sub = runtime / "tiny"
            sub.mkdir()
            (sub / "__init__.py").write_text(
                '"""docstring."""\n', encoding="utf-8"
            )
            qualifying = _enumerate_subpackages_with_public_api(runtime)
        self.assertNotIn("tiny", qualifying)

    def test_non_trivial_init_included(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "mythic_vibe_cli"
            runtime.mkdir()
            sub = runtime / "fat"
            sub.mkdir()
            (sub / "__init__.py").write_text(
                "from .a import A\n"
                "from .b import B\n"
                "from .c import C\n"
                "from .d import D\n"
                "from .e import E\n"
                "from .f import F\n"
                "from .g import G\n",
                encoding="utf-8",
            )
            qualifying = _enumerate_subpackages_with_public_api(runtime)
        self.assertIn("fat", qualifying)


# ---- _scan_module ----------------------------------------------------


class ScanModuleTests(unittest.TestCase):
    def test_clean_module_no_findings(self) -> None:
        findings = _scan_module(
            "import json\nx = 1\n",
            relative="ai/providers/x.py",
            qualifying_subpackages={"policy"},
        )
        self.assertEqual(findings, [])

    def test_cross_subpackage_private_import_flagged(self) -> None:
        findings = _scan_module(
            "from mythic_vibe_cli.policy.constraint_store import Constraint\n",
            relative="ai/providers/x.py",
            qualifying_subpackages={"policy"},
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].target_subpackage, "policy")
        self.assertEqual(findings[0].target_module, "constraint_store")

    def test_cross_subpackage_public_init_import_allowed(self) -> None:
        findings = _scan_module(
            "from mythic_vibe_cli.policy import Constraint\n",
            relative="ai/providers/x.py",
            qualifying_subpackages={"policy"},
        )
        self.assertEqual(findings, [])

    def test_within_subpackage_private_import_allowed(self) -> None:
        findings = _scan_module(
            "from mythic_vibe_cli.policy.constraint_store import Constraint\n",
            relative="policy/policy_gate.py",
            qualifying_subpackages={"policy"},
        )
        self.assertEqual(findings, [])

    def test_relative_import_allowed(self) -> None:
        findings = _scan_module(
            "from .constraint_store import Constraint\n",
            relative="policy/policy_gate.py",
            qualifying_subpackages={"policy"},
        )
        self.assertEqual(findings, [])

    def test_non_qualifying_subpackage_not_gated(self) -> None:
        findings = _scan_module(
            "from mythic_vibe_cli.tiny.private import X\n",
            relative="ai/providers/x.py",
            qualifying_subpackages={"policy"},  # tiny not in set
        )
        self.assertEqual(findings, [])


# ---- audit_api_surfaces ----------------------------------------------


class AuditApiSurfacesTests(unittest.TestCase):
    def _build_qualifying_tree(self, root: Path) -> None:
        runtime = root / "mythic_vibe_cli"
        runtime.mkdir(parents=True, exist_ok=True)
        # Make `policy` a qualifying subpackage.
        policy_init = "\n".join(
            f"from .m{i} import x" for i in range(7)
        ) + "\n"
        _runtime_tree(
            root,
            {
                "policy/__init__.py": policy_init,
                "policy/private_helper.py": "x = 1\n",
            },
        )

    def test_cross_subpackage_private_import_flagged_in_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_qualifying_tree(root)
            _runtime_tree(
                root,
                {
                    "ai/providers/x.py": (
                        "from mythic_vibe_cli.policy.private_helper import x\n"
                    ),
                },
            )
            result = audit_api_surfaces(root)
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]
        self.assertEqual(finding.location, "ai/providers/x.py")
        self.assertEqual(finding.target_subpackage, "policy")
        self.assertEqual(finding.target_module, "private_helper")

    def test_public_api_import_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_qualifying_tree(root)
            _runtime_tree(
                root,
                {
                    "ai/providers/x.py": (
                        "from mythic_vibe_cli.policy import x\n"
                    ),
                },
            )
            result = audit_api_surfaces(root)
        self.assertEqual(result.findings, [])

    def test_subpackages_with_public_api_listed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_qualifying_tree(root)
            result = audit_api_surfaces(root)
        self.assertIn("policy", result.subpackages_with_public_api)


# ---- ApiFinding / ApiAuditResult -------------------------------------


class DataclassTests(unittest.TestCase):
    def test_finding_to_dict(self) -> None:
        f = ApiFinding(
            location="a.py",
            line=1,
            column=0,
            snippet="x",
            importer_subpackage="ai",
            target_subpackage="policy",
            target_module="private_helper",
        )
        payload = f.to_dict()
        for key in {
            "location",
            "line",
            "column",
            "snippet",
            "importer_subpackage",
            "target_subpackage",
            "target_module",
            "detail",
        }:
            self.assertIn(key, payload)

    def test_result_ok_when_empty(self) -> None:
        self.assertTrue(ApiAuditResult().ok)


class SelfAuditTests(unittest.TestCase):
    def test_live_repo_audit_completes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = audit_api_surfaces(repo_root)
        self.assertGreater(result.files_scanned, 50)
        payload = result.to_dict()
        self.assertIn("findings", payload)


if __name__ == "__main__":
    unittest.main()
