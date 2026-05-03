"""Phase 20.B (audit remediation 2026-05-03) — verify replay
shortcut tests.

Covers:

- ``--replay`` flag delegates to ``cmd_forge_resume`` (verified
  via mock).
- Existing flat ``verify`` calls without ``--replay`` continue
  to invoke ``cmd_verify`` unchanged (regression guard).
- Default provider is ``copy-paste`` when ``--provider`` is
  omitted with ``--replay``.
- The forwarded Namespace carries the expected fields.
"""

from __future__ import annotations

import argparse
import unittest
from unittest import mock


class CmdVerifyDispatchReplayTests(unittest.TestCase):
    def _ns(self, **overrides) -> argparse.Namespace:
        kwargs = {
            "path": ".",
            "commands": False,
            "changed_files": False,
            "docs": False,
            "invariants": False,
            "record": False,
            "replay": False,
            "provider": "",
            "workflow": "",
            "strict": False,
            "json": False,
        }
        kwargs.update(overrides)
        return argparse.Namespace(**kwargs)

    def test_no_replay_calls_normal_verify(self) -> None:
        from mythic_vibe_cli.commands import cmd_verify_dispatch

        ns = self._ns(replay=False)
        with mock.patch(
            "mythic_vibe_cli.commands.cmd_verify",
            return_value=0,
        ) as verify_mock:
            cmd_verify_dispatch(ns)
        verify_mock.assert_called_once_with(ns)

    def test_replay_calls_forge_resume(self) -> None:
        from mythic_vibe_cli.commands import cmd_verify_dispatch

        ns = self._ns(replay=True, provider="anthropic")
        with mock.patch(
            "mythic_vibe_cli.forge.cmd_forge_resume",
            return_value=0,
        ) as resume_mock:
            cmd_verify_dispatch(ns)
        resume_mock.assert_called_once()
        forwarded = resume_mock.call_args.args[0]
        self.assertEqual(forwarded.provider, "anthropic")
        self.assertEqual(forwarded.workflow, "")
        self.assertFalse(forwarded.strict)
        self.assertFalse(forwarded.interactive)
        self.assertFalse(forwarded.skip_ledger)
        self.assertFalse(forwarded.skip_reflection)

    def test_replay_default_provider_is_copy_paste(self) -> None:
        from mythic_vibe_cli.commands import cmd_verify_dispatch

        ns = self._ns(replay=True)  # no --provider
        with mock.patch(
            "mythic_vibe_cli.forge.cmd_forge_resume",
            return_value=0,
        ) as resume_mock:
            cmd_verify_dispatch(ns)
        forwarded = resume_mock.call_args.args[0]
        self.assertEqual(forwarded.provider, "copy-paste")

    def test_replay_strict_forwards(self) -> None:
        from mythic_vibe_cli.commands import cmd_verify_dispatch

        ns = self._ns(replay=True, strict=True)
        with mock.patch(
            "mythic_vibe_cli.forge.cmd_forge_resume",
            return_value=0,
        ) as resume_mock:
            cmd_verify_dispatch(ns)
        forwarded = resume_mock.call_args.args[0]
        self.assertTrue(forwarded.strict)

    def test_replay_workflow_id_forwards(self) -> None:
        from mythic_vibe_cli.commands import cmd_verify_dispatch

        ns = self._ns(replay=True, workflow="WF-000123")
        with mock.patch(
            "mythic_vibe_cli.forge.cmd_forge_resume",
            return_value=0,
        ) as resume_mock:
            cmd_verify_dispatch(ns)
        forwarded = resume_mock.call_args.args[0]
        self.assertEqual(forwarded.workflow, "WF-000123")

    def test_replay_propagates_exit_code(self) -> None:
        from mythic_vibe_cli.commands import cmd_verify_dispatch

        ns = self._ns(replay=True)
        with mock.patch(
            "mythic_vibe_cli.forge.cmd_forge_resume",
            return_value=42,
        ):
            code = cmd_verify_dispatch(ns)
        self.assertEqual(code, 42)


if __name__ == "__main__":
    unittest.main()
