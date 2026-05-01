"""Tests for PH-11 Slice 11.1 — approval modes."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.security.approval import (
    APPROVAL_ACTIONS,
    APPROVAL_MODES,
    ApprovalDecision,
    is_interactive_tty,
    load_security_config,
    normalise_mode,
    resolve_approval,
    resolve_default_mode,
    resolve_mode,
)


class _FakeStream:
    def __init__(self, *, isatty: bool) -> None:
        self._isatty = isatty

    def isatty(self) -> bool:
        return self._isatty


# ---- normalise_mode ---------------------------------------------------


class NormaliseModeTests(unittest.TestCase):
    def test_known_modes(self) -> None:
        for mode in APPROVAL_MODES:
            self.assertEqual(normalise_mode(mode), mode)
            self.assertEqual(normalise_mode(mode.upper()), mode)

    def test_unknown_falls_back_to_suggest(self) -> None:
        self.assertEqual(normalise_mode("ghost"), "suggest")

    def test_blank_falls_back_to_suggest(self) -> None:
        self.assertEqual(normalise_mode(""), "suggest")
        self.assertEqual(normalise_mode(None), "suggest")


# ---- TTY-aware default ------------------------------------------------


class IsInteractiveTtyTests(unittest.TestCase):
    def test_tty_stream(self) -> None:
        self.assertTrue(is_interactive_tty(stream=_FakeStream(isatty=True)))

    def test_non_tty_stream(self) -> None:
        self.assertFalse(is_interactive_tty(stream=_FakeStream(isatty=False)))

    def test_stream_without_isatty_method(self) -> None:
        self.assertFalse(is_interactive_tty(stream=io.StringIO()))

    def test_isatty_raises(self) -> None:
        class _Raising:
            def isatty(self) -> bool:
                raise OSError("no terminal")

        self.assertFalse(is_interactive_tty(stream=_Raising()))


class ResolveDefaultModeTests(unittest.TestCase):
    def test_tty_returns_suggest(self) -> None:
        self.assertEqual(
            resolve_default_mode(stream=_FakeStream(isatty=True)), "suggest"
        )

    def test_non_tty_returns_auto(self) -> None:
        self.assertEqual(
            resolve_default_mode(stream=_FakeStream(isatty=False)), "auto"
        )


# ---- load_security_config --------------------------------------------


class LoadSecurityConfigTests(unittest.TestCase):
    def test_missing_file_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_security_config(Path(tmp)), {})

    def test_valid_file_parses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "security.toml").write_text(
                '[approval]\nmode = "auto"\n', encoding="utf-8"
            )
            cfg = load_security_config(root)
            self.assertEqual(cfg, {"approval": {"mode": "auto"}})

    def test_invalid_toml_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "security.toml").write_text(
                "this is not valid toml = =", encoding="utf-8"
            )
            self.assertEqual(load_security_config(root), {})


# ---- resolve_mode ----------------------------------------------------


class ResolveModeTests(unittest.TestCase):
    def test_cli_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                resolve_mode(Path(tmp), cli_override="auto"), "auto"
            )
            self.assertEqual(
                resolve_mode(Path(tmp), cli_override="partial"), "partial"
            )

    def test_config_used_when_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "security.toml").write_text(
                '[approval]\nmode = "auto"\n', encoding="utf-8"
            )
            self.assertEqual(
                resolve_mode(root, stream=_FakeStream(isatty=True)),
                "auto",
            )

    def test_default_when_neither_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                resolve_mode(Path(tmp), stream=_FakeStream(isatty=True)),
                "suggest",
            )
            self.assertEqual(
                resolve_mode(Path(tmp), stream=_FakeStream(isatty=False)),
                "auto",
            )

    def test_unknown_cli_override_falls_back_to_suggest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                resolve_mode(Path(tmp), cli_override="ghost"), "suggest"
            )


# ---- resolve_approval ------------------------------------------------


class ResolveApprovalTests(unittest.TestCase):
    def test_auto_mode_no_prompt(self) -> None:
        for action in APPROVAL_ACTIONS:
            decision = resolve_approval(
                mode="auto",
                action=action,
                description="x",
                responder=lambda _p: "n",  # never asked
            )
            self.assertTrue(decision.approved)
            self.assertFalse(decision.prompted)
            self.assertEqual(decision.action, action)

    def test_partial_mode_allows_read_no_prompt(self) -> None:
        decision = resolve_approval(
            mode="partial",
            action="read",
            description="read x",
            responder=lambda _p: "n",
        )
        self.assertTrue(decision.approved)
        self.assertFalse(decision.prompted)

    def test_partial_mode_prompts_for_write(self) -> None:
        decision = resolve_approval(
            mode="partial",
            action="write",
            description="write x",
            responder=lambda _p: "y",
        )
        self.assertTrue(decision.prompted)
        self.assertTrue(decision.approved)

    def test_partial_mode_prompts_for_exec(self) -> None:
        decision = resolve_approval(
            mode="partial",
            action="exec",
            description="exec x",
            responder=lambda _p: "n",
        )
        self.assertTrue(decision.prompted)
        self.assertFalse(decision.approved)

    def test_suggest_mode_always_prompts(self) -> None:
        for action in APPROVAL_ACTIONS:
            decision = resolve_approval(
                mode="suggest",
                action=action,
                description="x",
                responder=lambda _p: "y",
            )
            self.assertTrue(decision.prompted)
            self.assertTrue(decision.approved)

    def test_suggest_mode_default_no_means_no(self) -> None:
        """Empty / unknown answer ⇒ not approved (conservative)."""
        for response in ("", "n", "no", "ghost"):
            decision = resolve_approval(
                mode="suggest",
                action="write",
                description="x",
                responder=lambda _p, r=response: r,
            )
            self.assertFalse(
                decision.approved, f"failed for response={response!r}"
            )

    def test_suggest_mode_yes_variants(self) -> None:
        for response in ("y", "yes", "YES"):
            decision = resolve_approval(
                mode="suggest",
                action="write",
                description="x",
                responder=lambda _p, r=response: r.lower(),
            )
            self.assertTrue(
                decision.approved, f"failed for response={response!r}"
            )


# ---- ApprovalDecision dataclass --------------------------------------


class ApprovalDecisionTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        d = ApprovalDecision(
            approved=True,
            mode="suggest",
            action="write",
            prompted=True,
            reason="operator answered 'y'",
        )
        payload = d.to_dict()
        for key in {"approved", "mode", "action", "prompted", "reason"}:
            self.assertIn(key, payload)
        self.assertTrue(payload["approved"])


if __name__ == "__main__":
    unittest.main()
