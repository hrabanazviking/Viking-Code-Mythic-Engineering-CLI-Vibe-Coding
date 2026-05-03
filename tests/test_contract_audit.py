"""Phase 19.2 (audit remediation 2026-05-02) — contract auditor tests.

Tests for ``tools/contract_audit.py`` — the docs-↔-code drift
detector that runs in CI and flags handlers added without docs.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


# Load tools/contract_audit.py as a module without polluting sys.path
# (the script lives outside the mythic_vibe_cli package).
_TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "contract_audit", _TOOLS_DIR / "contract_audit.py"
)
contract_audit = importlib.util.module_from_spec(_SPEC)  # type: ignore[arg-type]
sys.modules["contract_audit"] = contract_audit
_SPEC.loader.exec_module(contract_audit)  # type: ignore[union-attr]


class DiscoverDocReferencesTests(unittest.TestCase):
    """``discover_doc_command_references`` finds tokens after the
    ``mythic-vibe`` / ``mythic`` CLI prefix in markdown files."""

    def test_extracts_mythic_vibe_prefix_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "guide.md"
            doc.write_text(
                "Run `mythic-vibe status` to see the current state.\n"
                "Then `mythic-vibe doctor` for diagnostics.\n",
                encoding="utf-8",
            )
            refs = contract_audit.discover_doc_command_references(Path(tmp))
        self.assertEqual(refs, {"status", "doctor"})

    def test_extracts_short_mythic_prefix_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "guide.md"
            doc.write_text(
                "Or shorthand: `mythic verify` and `mythic packet list`.\n",
                encoding="utf-8",
            )
            refs = contract_audit.discover_doc_command_references(Path(tmp))
        self.assertIn("verify", refs)
        self.assertIn("packet", refs)

    def test_walks_subdirectories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "ADRS"
            sub.mkdir()
            (sub / "ADR-0001.md").write_text(
                "We use `mythic-vibe init` to bootstrap.\n",
                encoding="utf-8",
            )
            refs = contract_audit.discover_doc_command_references(Path(tmp))
        self.assertEqual(refs, {"init"})

    def test_ignores_non_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "script.py").write_text(
                "# `mythic-vibe ignored-because-py-file`",
                encoding="utf-8",
            )
            refs = contract_audit.discover_doc_command_references(Path(tmp))
        self.assertEqual(refs, set())


class DiscoverBacktickedTokensTests(unittest.TestCase):
    """``discover_backticked_tokens`` finds bare backticked words —
    the looser secondary signal."""

    def test_extracts_single_word_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ref.md").write_text(
                "The `forge` command is documented separately.\n"
                "Also `verify` and `doctor`.\n",
                encoding="utf-8",
            )
            tokens = contract_audit.discover_backticked_tokens(Path(tmp))
        self.assertIn("forge", tokens)
        self.assertIn("verify", tokens)
        self.assertIn("doctor", tokens)


class AuditTests(unittest.TestCase):
    """Top-level audit() function returns the set of handlers
    without doc references."""

    def test_clean_when_every_handler_documented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ref.md").write_text(
                "Documented: `mythic-vibe alpha` `mythic-vibe beta`.\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                contract_audit, "load_handlers",
                return_value={"alpha", "beta"},
            ):
                drift = contract_audit.audit(Path(tmp))
        self.assertEqual(drift, set())

    def test_flags_undocumented_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ref.md").write_text(
                "Documented: `mythic-vibe alpha`.\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                contract_audit, "load_handlers",
                return_value={"alpha", "undocumented-beta"},
            ):
                drift = contract_audit.audit(Path(tmp))
        self.assertEqual(drift, {"undocumented-beta"})

    def test_allow_undocumented_exempts_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ref.md").write_text(
                "Documented: `mythic-vibe alpha`.\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                contract_audit, "load_handlers",
                return_value={"alpha", "internal-beta"},
            ):
                drift = contract_audit.audit(
                    Path(tmp),
                    allow_undocumented=frozenset({"internal-beta"}),
                )
        self.assertEqual(drift, set())

    def test_loose_backtick_signal_counts_as_documentation(self) -> None:
        """A bare backticked token (not after `mythic-vibe`) still
        counts as documentation. Some handlers are referenced in
        narrative prose without the CLI prefix."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "narrative.md").write_text(
                "The `gamma` workflow is for narrative-style refs.\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                contract_audit, "load_handlers",
                return_value={"gamma"},
            ):
                drift = contract_audit.audit(Path(tmp))
        self.assertEqual(drift, set())


class CliMainTests(unittest.TestCase):
    """The ``main()`` entry point — exit codes and --strict mode."""

    def test_clean_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ref.md").write_text(
                "All handlers documented: `mythic-vibe alpha`.\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                contract_audit, "load_handlers",
                return_value={"alpha"},
            ):
                code = contract_audit.main(["--docs-dir", tmp])
        self.assertEqual(code, 0)

    def test_drift_without_strict_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ref.md").write_text(
                "Only one: `mythic-vibe alpha`.\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                contract_audit, "load_handlers",
                return_value={"alpha", "beta"},
            ):
                code = contract_audit.main(["--docs-dir", tmp])
        self.assertEqual(code, 0)  # informational mode

    def test_drift_with_strict_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ref.md").write_text(
                "Only one: `mythic-vibe alpha`.\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                contract_audit, "load_handlers",
                return_value={"alpha", "beta"},
            ):
                code = contract_audit.main(["--docs-dir", tmp, "--strict"])
        self.assertEqual(code, 1)

    def test_missing_docs_dir_exits_two(self) -> None:
        code = contract_audit.main([
            "--docs-dir", "/nonexistent-path-for-test", "--strict",
        ])
        self.assertEqual(code, 2)


class LiveContractAuditTests(unittest.TestCase):
    """The live audit against the actual repo docs/ + handlers
    must stay clean once the baseline ratchet (the
    ``allow_undocumented`` set inside ``main()``) is applied.
    This is the regression that catches new drift in real PRs."""

    # Match the baseline in tools/contract_audit.py:main().
    # Keep in sync — when a handler is documented, drop it here
    # AND in main()'s allow_undocumented set.
    _BASELINE_ALLOW_UNDOCUMENTED = frozenset({
        "architecture", "audit", "build", "changelog", "ci",
        "constraints", "docker", "drift", "graph", "hardware",
        "lint", "policy", "protocols", "provider", "release",
        "rollback", "scaffold", "security", "test", "typecheck",
        # PH-20.A (additive 2026-05-03): persona presets — new
        # surface, doc page coming in 20.7 launch checklist.
        "persona",
    })

    def test_repo_contract_audit_clean_with_baseline(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        docs_dir = repo_root / "docs"
        self.assertTrue(docs_dir.is_dir())
        drift = contract_audit.audit(
            docs_dir,
            allow_undocumented=self._BASELINE_ALLOW_UNDOCUMENTED,
        )
        self.assertEqual(
            drift, set(),
            f"Contract drift detected: {sorted(drift)}.\n"
            "Document the handler in docs/ OR add it to "
            "allow_undocumented in tools/contract_audit.py.",
        )

    def test_baseline_handlers_still_exist(self) -> None:
        """If a baseline-allowed handler is removed from
        COMMAND_HANDLERS, drop it from the baseline too."""
        handlers = contract_audit.load_handlers()
        stale = self._BASELINE_ALLOW_UNDOCUMENTED - handlers
        self.assertEqual(
            stale, set(),
            f"Baseline references handlers no longer in "
            f"COMMAND_HANDLERS: {sorted(stale)}. Remove them from "
            "tools/contract_audit.py:main allow_undocumented.",
        )


if __name__ == "__main__":
    unittest.main()
