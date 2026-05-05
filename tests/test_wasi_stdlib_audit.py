"""Tests for the WASI stdlib audit (PH-23.15).

The audit script walks the runtime package's AST + reports:
  - which stdlib modules are imported anywhere in the runtime tree
  - which stdlib modules are always-prunable in WASI (incompatible
    regardless of use)
  - which stdlib modules are unused-and-prunable
  - dynamic importlib.import_module call sites (operator-review)

These tests verify the script's structure + a few invariants
about the static stdlib lists. The audit's actual numbers are
intentionally NOT pinned (they shift as the runtime grows); we
only assert structural correctness + invariant relationships.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_SCRIPT = REPO_ROOT / "tools" / "wasi_stdlib_audit.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "_audit_under_test", str(AUDIT_SCRIPT)
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load {AUDIT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StaticListsTests(unittest.TestCase):
    """The two stdlib reference sets must satisfy a few invariants."""

    def setUp(self) -> None:
        self.module = _load_audit_module()

    def test_stdlib_top_level_includes_canonical_modules(self) -> None:
        # Sanity-check: a few well-known stdlib modules must
        # be present. If a future Python version reorganizes
        # these the audit needs an explicit update.
        for name in (
            "json", "os", "sys", "io", "argparse",
            "pathlib", "subprocess", "logging",
        ):
            self.assertIn(
                name, self.module.PY312_STDLIB_TOP_LEVEL,
                f"canonical stdlib name missing: {name}",
            )

    def test_wasi_incompatible_is_subset_of_stdlib(self) -> None:
        # Every always-prune entry must actually be a stdlib
        # module — otherwise we'd be claiming to prune a name
        # the freeze list doesn't even contain.
        non_stdlib = (
            self.module.WASI_INCOMPATIBLE_STDLIB
            - self.module.PY312_STDLIB_TOP_LEVEL
        )
        self.assertEqual(
            non_stdlib, frozenset(),
            f"WASI_INCOMPATIBLE_STDLIB has non-stdlib names: {non_stdlib}",
        )

    def test_subprocess_is_always_prunable(self) -> None:
        # The most-cited "doesn't work in WASI" module — explicit
        # invariant that this stays in the always-prune list.
        self.assertIn(
            "subprocess",
            self.module.WASI_INCOMPATIBLE_STDLIB,
        )

    def test_tkinter_is_always_prunable(self) -> None:
        # GUI modules don't apply to WASI.
        self.assertIn("tkinter", self.module.WASI_INCOMPATIBLE_STDLIB)


class WalkPythonFilesTests(unittest.TestCase):
    """The file walker excludes test/cache/build directories."""

    def setUp(self) -> None:
        self.module = _load_audit_module()

    def test_excludes_pycache_dirs(self) -> None:
        files = self.module._walk_python_files(REPO_ROOT / "mythic_vibe_cli")
        for path in files:
            self.assertNotIn("__pycache__", path.parts)

    def test_excludes_tests_tree(self) -> None:
        files = self.module._walk_python_files(REPO_ROOT)
        for path in files:
            self.assertNotIn(
                "tests", path.parts,
                f"unexpected tests/ file in walk: {path}",
            )


class ImportsFromFileTests(unittest.TestCase):
    """The AST extractor catches `import x` and `from a import b`
    + skips relative imports."""

    def setUp(self) -> None:
        self.module = _load_audit_module()

    def test_extracts_top_level_module_names(self) -> None:
        import tempfile

        src = (
            "import json\n"
            "import os.path\n"
            "from collections import OrderedDict\n"
            "from . import sibling  # relative — skipped\n"
            "from ..parent import foo  # relative — skipped\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "f.py"
            p.write_text(src, encoding="utf-8")
            imports = self.module._imports_from_file(p)
        self.assertEqual(imports, {"json", "os", "collections"})

    def test_handles_syntax_error_gracefully(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "broken.py"
            p.write_text("def broken(:\n", encoding="utf-8")
            imports = self.module._imports_from_file(p)
        self.assertEqual(imports, set())


class DynamicImportSiteTests(unittest.TestCase):
    """Static AST detection of importlib.import_module calls."""

    def setUp(self) -> None:
        self.module = _load_audit_module()

    def test_detects_importlib_dot_import_module(self) -> None:
        import tempfile

        src = (
            "import importlib\n"
            "def load(name):\n"
            "    return importlib.import_module(name)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "f.py"
            p.write_text(src, encoding="utf-8")
            sites = self.module._dynamic_import_call_sites(p)
        self.assertEqual(len(sites), 1)
        line, excerpt = sites[0]
        self.assertEqual(line, 3)
        self.assertIn("importlib.import_module", excerpt)

    def test_detects_naked_import_module(self) -> None:
        # `from importlib import import_module` then
        # `import_module(name)` — also caught.
        import tempfile

        src = (
            "from importlib import import_module\n"
            "def load(name):\n"
            "    return import_module(name)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "f.py"
            p.write_text(src, encoding="utf-8")
            sites = self.module._dynamic_import_call_sites(p)
        self.assertEqual(len(sites), 1)


class FullAuditTests(unittest.TestCase):
    """Drive the audit against the live mythic_vibe_cli/ tree."""

    def setUp(self) -> None:
        self.module = _load_audit_module()

    def test_audit_returns_expected_keys(self) -> None:
        report = self.module.audit(REPO_ROOT)
        for key in (
            "files_scanned",
            "stdlib_used",
            "stdlib_used_count",
            "third_party_imported",
            "always_prune_wasi_incompatible",
            "additional_prune_candidates_unused",
            "dynamic_import_sites",
            "total_stdlib_modules",
        ):
            self.assertIn(key, report)

    def test_audit_finds_real_imports(self) -> None:
        # The CLI imports json + argparse + pathlib among many
        # others — the report must include them.
        report = self.module.audit(REPO_ROOT)
        for module in ("json", "argparse", "pathlib", "os", "sys"):
            self.assertIn(
                module, report["stdlib_used"],
                f"expected {module} in stdlib_used",
            )

    def test_audit_flags_known_dynamic_imports(self) -> None:
        # The plugin loader uses importlib.import_module —
        # the audit must flag at least the loader site.
        report = self.module.audit(REPO_ROOT)
        site_files = {site["file"] for site in report["dynamic_import_sites"]}
        self.assertTrue(
            any("plugins/loader.py" in f for f in site_files),
            f"expected plugins/loader.py in dynamic sites: {site_files}",
        )

    def test_prune_candidates_disjoint_from_used(self) -> None:
        # No stdlib module can be both "used" AND "unused-prune
        # candidate" — that would be a logic bug. The
        # always_prune set CAN intersect with used (a CLI that
        # uses subprocess will see it in BOTH sets — used
        # because it's imported, always-prune because WASI
        # can't run it). The invariant is just
        # unused_prune ∩ used = ∅.
        report = self.module.audit(REPO_ROOT)
        used = set(report["stdlib_used"])
        unused_prune = set(report["additional_prune_candidates_unused"])
        self.assertEqual(used & unused_prune, set())
        # Always-prune CAN intersect with used (a CLI that uses
        # subprocess will see it in BOTH sets — used because it's
        # imported, always-prune because WASI can't run it). The
        # invariant is just unused-prune ∩ used = ∅.

    def test_audit_raises_when_package_missing(self) -> None:
        with self.assertRaises(SystemExit):
            self.module.audit(Path("/no/such/repo"))


class CliMainTests(unittest.TestCase):
    """The argparse + main() entry point."""

    def setUp(self) -> None:
        self.module = _load_audit_module()

    def test_main_text_mode(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            rc = self.module.main([])
        self.assertEqual(rc, 0)
        self.assertIn("WASI stdlib audit", buf.getvalue())

    def test_main_json_mode_emits_valid_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "stdout", buf):
            rc = self.module.main(["--json"])
        self.assertEqual(rc, 0)
        # Output must be parseable JSON with the expected keys.
        payload = json.loads(buf.getvalue())
        self.assertIn("stdlib_used", payload)


if __name__ == "__main__":
    unittest.main()
