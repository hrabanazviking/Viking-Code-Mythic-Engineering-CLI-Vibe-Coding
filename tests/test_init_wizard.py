"""Phase 20.0 (audit remediation 2026-05-02) — init wizard tests.

Covers the opt-in ``mythic-vibe init --interactive`` wizard:

- Pure-function behaviour of ``run_wizard`` against scripted
  reader / writer callables (no real stdin).
- ``write_project_settings`` round-trip + force-overwrite gate.
- ``scaffold_sample_artifacts`` skips pre-existing files.
- ``cmd_init`` integration: ``--interactive`` writes settings +
  scaffolds; bare invocation without ``--goal`` or
  ``--interactive`` returns USER_INPUT_ERROR; default
  non-interactive behaviour with just ``--goal`` is unchanged.
- Provider list parity: SUPPORTED_PROVIDERS matches the runtime
  ProviderRegistry exactly.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.ai.registry import ProviderRegistry
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.init_wizard import (
    DEFAULT_PROVIDER,
    SETTINGS_FILENAME,
    SETTINGS_SCHEMA_VERSION,
    SUPPORTED_PROVIDERS,
    WizardAbortedError,
    WizardAnswers,
    WizardConfig,
    run_wizard,
    scaffold_sample_artifacts,
    write_project_settings,
)


def _scripted_reader(answers: list[str]):
    """Return a reader callable that consumes ``answers`` in
    order; mirrors what builtin ``input()`` does for tests."""
    iterator = iter(answers)

    def reader(_prompt: str) -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise EOFError() from exc

    return reader


class SupportedProvidersParityTest(unittest.TestCase):
    """Module-level constant must match the runtime registry —
    if a provider is added/removed in registry.py, the wizard
    list has to follow."""

    def test_matches_registry(self) -> None:
        registry_keys = tuple(ProviderRegistry().providers().keys())
        self.assertEqual(set(SUPPORTED_PROVIDERS), set(registry_keys))


class RunWizardTests(unittest.TestCase):
    def test_happy_path_collects_all_answers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = WizardConfig(
                root=Path(tmp),
                default_provider="anthropic",
                default_operator="vol",
            )
            reader = _scripted_reader([
                "MyProject",            # project name
                "Build a calm CLI",     # goal
                "openai",               # provider
                "alice",                # operator
                "y",                    # scaffold samples
            ])
            written: list[str] = []
            answers = run_wizard(
                config,
                reader=reader,
                writer=written.append,
            )
        self.assertEqual(answers.project_name, "MyProject")
        self.assertEqual(answers.goal, "Build a calm CLI")
        self.assertEqual(answers.provider, "openai")
        self.assertEqual(answers.operator, "alice")
        self.assertTrue(answers.scaffold_samples)
        self.assertEqual(answers.schema_version, SETTINGS_SCHEMA_VERSION)

    def test_initial_goal_skips_goal_prompt(self) -> None:
        """When the operator passed --goal on the CLI, the wizard
        carries it forward and skips the goal prompt entirely."""
        with tempfile.TemporaryDirectory() as tmp:
            config = WizardConfig(
                root=Path(tmp),
                initial_goal="cli-supplied-goal",
            )
            # Only 4 answers needed because goal is skipped.
            reader = _scripted_reader([
                "Proj", "openai", "alice", "n",
            ])
            written: list[str] = []
            answers = run_wizard(
                config, reader=reader, writer=written.append
            )
        self.assertEqual(answers.goal, "cli-supplied-goal")
        self.assertFalse(answers.scaffold_samples)

    def test_defaults_apply_on_empty_input(self) -> None:
        """Hitting ENTER on a defaulted prompt accepts the
        default (mirrors the convention in REPL / forge gate)."""
        with tempfile.TemporaryDirectory() as tmp:
            config = WizardConfig(
                root=Path(tmp) / "myproj",
                default_provider="copy-paste",
                default_operator="vol",
            )
            config.root.mkdir()
            reader = _scripted_reader([
                "",                  # project name → default to "myproj"
                "Build something",   # goal (no default → required)
                "",                  # provider → copy-paste
                "",                  # operator → vol
                "",                  # scaffold → default y
            ])
            written: list[str] = []
            answers = run_wizard(
                config, reader=reader, writer=written.append
            )
        self.assertEqual(answers.project_name, "myproj")
        self.assertEqual(answers.provider, "copy-paste")
        self.assertEqual(answers.operator, "vol")
        self.assertTrue(answers.scaffold_samples)

    def test_invalid_provider_re_prompts(self) -> None:
        """An unknown provider triggers a re-prompt; we don't
        hard-fail mid-wizard."""
        with tempfile.TemporaryDirectory() as tmp:
            config = WizardConfig(root=Path(tmp))
            reader = _scripted_reader([
                "Proj", "Goal",
                "lulwut",      # invalid → reject + re-prompt
                "anthropic",   # valid
                "alice", "n",
            ])
            written: list[str] = []
            answers = run_wizard(
                config, reader=reader, writer=written.append
            )
        self.assertEqual(answers.provider, "anthropic")
        # The writer should have surfaced the rejection notice.
        self.assertTrue(
            any("must be one of" in chunk for chunk in written),
            f"missing rejection notice in {written!r}",
        )

    def test_eof_on_required_field_raises(self) -> None:
        """Ctrl+D / piped-stdin-exhausted on a required field
        with no default raises WizardAbortedError so the caller
        can return USER_INPUT_ERROR cleanly."""
        with tempfile.TemporaryDirectory() as tmp:
            config = WizardConfig(root=Path(tmp))
            reader = _scripted_reader([])
            written: list[str] = []
            with self.assertRaises(WizardAbortedError):
                run_wizard(
                    config, reader=reader, writer=written.append
                )


class WriteProjectSettingsTests(unittest.TestCase):
    def _answers(self) -> WizardAnswers:
        return WizardAnswers(
            project_name="proj",
            goal="goal",
            provider="copy-paste",
            operator="alice",
            scaffold_samples=False,
        )

    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_project_settings(Path(tmp), self._answers())
            self.assertEqual(path.name, SETTINGS_FILENAME)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["project_name"], "proj")
            self.assertEqual(payload["schema_version"], SETTINGS_SCHEMA_VERSION)

    def test_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_project_settings(Path(tmp), self._answers())
            with self.assertRaises(WizardAbortedError):
                write_project_settings(Path(tmp), self._answers())

    def test_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_project_settings(Path(tmp), self._answers())
            second = WizardAnswers(
                project_name="renamed",
                goal="new goal",
                provider="anthropic",
                operator="bob",
                scaffold_samples=True,
            )
            path = write_project_settings(
                Path(tmp), second, force=True
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["project_name"], "renamed")


class ScaffoldSampleArtifactsTests(unittest.TestCase):
    def test_creates_three_files_when_requested(self) -> None:
        answers = WizardAnswers(
            project_name="proj",
            goal="goal",
            provider="copy-paste",
            operator="alice",
            scaffold_samples=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            created = scaffold_sample_artifacts(Path(tmp), answers)
            self.assertEqual(len(created), 3)
            for path in created:
                self.assertTrue(path.is_file())
                content = path.read_text(encoding="utf-8")
                self.assertIn("proj", content)

    def test_returns_empty_when_disabled(self) -> None:
        answers = WizardAnswers(
            project_name="proj",
            goal="goal",
            provider="copy-paste",
            operator="alice",
            scaffold_samples=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            created = scaffold_sample_artifacts(Path(tmp), answers)
            self.assertEqual(created, [])

    def test_skips_pre_existing_files(self) -> None:
        """Sample artefacts must NEVER overwrite operator-authored
        content. If a target path already exists, skip silently."""
        answers = WizardAnswers(
            project_name="proj",
            goal="goal",
            provider="copy-paste",
            operator="alice",
            scaffold_samples=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "ADRS"
            adr_dir.mkdir(parents=True)
            preexisting = adr_dir / "ADR-SAMPLE-wizard.md"
            preexisting.write_text("MINE", encoding="utf-8")
            created = scaffold_sample_artifacts(Path(tmp), answers)
            # Only oath + constraint should be created (ADR
            # sample already existed). Assertions inside the
            # with-block so the temp dir is still alive.
            self.assertEqual(len(created), 2)
            self.assertEqual(
                preexisting.read_text(encoding="utf-8"), "MINE"
            )


class CmdInitIntegrationTests(unittest.TestCase):
    """Integration tests that hit ``cmd_init`` directly. We feed
    a scripted reader by monkey-patching ``builtins.input``."""

    def _run_init(self, ns_overrides: dict) -> int:
        import argparse

        from mythic_vibe_cli import commands

        ns = argparse.Namespace(
            path=ns_overrides["path"],
            goal=ns_overrides.get("goal"),
            noob=False,
            interactive=ns_overrides.get("interactive", False),
            force=ns_overrides.get("force", False),
            dry_run=False,
        )
        return commands.cmd_init(ns)

    def test_no_goal_no_interactive_returns_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_init({"path": tmp})
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_default_non_interactive_path_unchanged(self) -> None:
        """The original ``--goal`` flow must keep working
        identically — no project_settings.json written, no sample
        artefacts."""
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_init({"path": tmp, "goal": "X"})
            self.assertEqual(code, SUCCESS)
            self.assertFalse(
                (Path(tmp) / "mythic" / SETTINGS_FILENAME).exists()
            )
            self.assertFalse(
                (Path(tmp) / "docs" / "ADRS" / "ADR-SAMPLE-wizard.md").exists()
            )

    def test_interactive_writes_settings_and_samples(self) -> None:
        from unittest import mock

        scripted = iter([
            "MyProj",            # project name
            "Build a calm CLI",  # goal
            "copy-paste",        # provider
            "alice",             # operator
            "y",                 # scaffold yes
        ])
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("builtins.input", lambda _p: next(scripted)):
            code = self._run_init({"path": tmp, "interactive": True})
            self.assertEqual(code, SUCCESS)
            settings_path = Path(tmp) / "mythic" / SETTINGS_FILENAME
            self.assertTrue(settings_path.is_file())
            payload = json.loads(
                settings_path.read_text(encoding="utf-8")
            )
            self.assertEqual(payload["project_name"], "MyProj")
            self.assertEqual(payload["goal"], "Build a calm CLI")
            self.assertEqual(payload["provider"], "copy-paste")
            # Sample artefacts created.
            adr_path = (
                Path(tmp) / "docs" / "ADRS" / "ADR-SAMPLE-wizard.md"
            )
            self.assertTrue(adr_path.is_file())

    def test_interactive_refuses_overwrite_without_force(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "mythic"
            settings_dir.mkdir()
            (settings_dir / SETTINGS_FILENAME).write_text(
                "{}", encoding="utf-8"
            )
            scripted = iter([
                "P", "G", DEFAULT_PROVIDER, "u", "n",
            ])
            with mock.patch("builtins.input", lambda _p: next(scripted)):
                code = self._run_init(
                    {"path": tmp, "interactive": True}
                )
        self.assertEqual(code, USER_INPUT_ERROR)


class OperatorDefaultResolutionTests(unittest.TestCase):
    """``WizardConfig.default_operator`` reads $USER / $USERNAME
    at construction time. Verify the fallback chain."""

    def test_user_env_wins(self) -> None:
        from unittest import mock

        with mock.patch.dict(
            os.environ, {"USER": "alice", "USERNAME": "bob"}, clear=True
        ):
            with tempfile.TemporaryDirectory() as tmp:
                config = WizardConfig(root=Path(tmp))
        self.assertEqual(config.default_operator, "alice")

    def test_username_fallback_when_user_missing(self) -> None:
        from unittest import mock

        with mock.patch.dict(
            os.environ, {"USERNAME": "bob"}, clear=True
        ):
            with tempfile.TemporaryDirectory() as tmp:
                config = WizardConfig(root=Path(tmp))
        self.assertEqual(config.default_operator, "bob")

    def test_unknown_when_neither_set(self) -> None:
        from unittest import mock

        with mock.patch.dict(os.environ, {}, clear=True):
            with tempfile.TemporaryDirectory() as tmp:
                config = WizardConfig(root=Path(tmp))
        self.assertEqual(config.default_operator, "unknown")


if __name__ == "__main__":
    unittest.main()
