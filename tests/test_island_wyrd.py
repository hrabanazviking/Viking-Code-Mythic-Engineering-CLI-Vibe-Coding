"""Tests for Island D (WYRD Protocol) verifier gate — PH-09 Slice 9.3."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.verify.wyrd_oracle import (
    GATE_NAME,
    INSTALL_HINT,
    ISLAND_ENABLED_ENV,
    _interpret_oracle_verdict,
    gate_wyrd_oracle,
    is_island_enabled,
    wyrd_gate_if_enabled,
)
from mythic_vibe_cli.workflow_agents import AgentInput, AgentOutput
from mythic_vibe_cli.workflow_engine import WorkflowPlan, WorkflowStep


def _plan() -> WorkflowPlan:
    return WorkflowPlan(
        task="WYRD island test",
        created_at="2026-05-01T00:00:00Z",
        steps=(
            WorkflowStep(
                step_id="step-auditor",
                role="Auditor",
                phase="reflect",
                objective="Audit",
                identity="Auditor",
                focus="audit",
                system_prompt="audit",
                invariants=(),
                verification=(),
            ),
        ),
        workflow_id="WF-TEST-WYRD",
    )


def _agent_input(role: str = "Auditor") -> AgentInput:
    return AgentInput(
        role=role,
        task="WYRD test packet",
        phase="reflect",
        prior_outputs=("OK",),
    )


def _agent_output(raw_response: str) -> AgentOutput:
    return AgentOutput(
        role="Auditor",
        timestamp="2026-05-01T00:00:00Z",
        summary="audit summary",
        raw_response=raw_response,
    )


# ---- env gate ---------------------------------------------------------


class IsIslandEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_default_off(self) -> None:
        self.assertFalse(is_island_enabled())

    def test_truthy_on(self) -> None:
        os.environ[ISLAND_ENABLED_ENV] = "1"
        self.assertTrue(is_island_enabled())


# ---- gate_wyrd_oracle behaviour --------------------------------------


class GateDisabledPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_disabled_passes_with_disabled_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = gate_wyrd_oracle(
                _plan(),
                _agent_input(),
                _agent_output("audit text"),
                Path(tmp),
            )
        self.assertEqual(result.name, GATE_NAME)
        self.assertTrue(result.passed)
        self.assertIn("disabled", result.detail)


class GateMissingDepPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)
        os.environ[ISLAND_ENABLED_ENV] = "1"

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_missing_wyrd_dep_fails_with_install_hint(self) -> None:
        with mock.patch(
            "mythic_vibe_cli.verify.wyrd_oracle._try_import_wyrd",
            return_value=None,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = gate_wyrd_oracle(
                    _plan(),
                    _agent_input(),
                    _agent_output("audit text"),
                    Path(tmp),
                )
        self.assertFalse(result.passed)
        self.assertIn("not importable", result.detail)
        self.assertIn("wyrd-protocol", result.detail)


class GateRealPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)
        os.environ[ISLAND_ENABLED_ENV] = "1"

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_passive_oracle_truthy_passes(self) -> None:
        fake = mock.MagicMock()
        fake.passive_oracle.return_value = True

        with mock.patch(
            "mythic_vibe_cli.verify.wyrd_oracle._try_import_wyrd",
            return_value=fake,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = gate_wyrd_oracle(
                    _plan(),
                    _agent_input(),
                    _agent_output("audit text"),
                    Path(tmp),
                )
        fake.passive_oracle.assert_called_once_with("audit text")
        self.assertTrue(result.passed)

    def test_passive_oracle_falsy_fails(self) -> None:
        fake = mock.MagicMock()
        fake.passive_oracle.return_value = False

        with mock.patch(
            "mythic_vibe_cli.verify.wyrd_oracle._try_import_wyrd",
            return_value=fake,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = gate_wyrd_oracle(
                    _plan(),
                    _agent_input(),
                    _agent_output("inconsistent claim"),
                    Path(tmp),
                )
        self.assertFalse(result.passed)

    def test_dict_verdict_with_passed_key(self) -> None:
        fake = mock.MagicMock()
        fake.passive_oracle.return_value = {
            "passed": False,
            "detail": "world-state mismatch",
        }

        with mock.patch(
            "mythic_vibe_cli.verify.wyrd_oracle._try_import_wyrd",
            return_value=fake,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = gate_wyrd_oracle(
                    _plan(),
                    _agent_input(),
                    _agent_output("audit text"),
                    Path(tmp),
                )
        self.assertFalse(result.passed)
        self.assertIn("world-state mismatch", result.detail)

    def test_oracle_exception_contained(self) -> None:
        fake = mock.MagicMock()
        fake.passive_oracle.side_effect = RuntimeError("oracle exploded")

        with mock.patch(
            "mythic_vibe_cli.verify.wyrd_oracle._try_import_wyrd",
            return_value=fake,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = gate_wyrd_oracle(
                    _plan(),
                    _agent_input(),
                    _agent_output("audit text"),
                    Path(tmp),
                )
        self.assertFalse(result.passed)
        self.assertIn("oracle raised", result.detail)
        self.assertIn("oracle exploded", result.detail)

    def test_unknown_oracle_shape_fails_with_contract_gap_detail(self) -> None:
        class _Empty:
            pass

        with mock.patch(
            "mythic_vibe_cli.verify.wyrd_oracle._try_import_wyrd",
            return_value=_Empty(),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = gate_wyrd_oracle(
                    _plan(),
                    _agent_input(),
                    _agent_output("audit text"),
                    Path(tmp),
                )
        self.assertFalse(result.passed)
        self.assertIn("does not expose a known", result.detail)

    def test_empty_audit_response_passes(self) -> None:
        """When the Auditor's response is empty, there's nothing for
        the oracle to check — pass with a "nothing to check" detail."""
        fake = mock.MagicMock()
        with mock.patch(
            "mythic_vibe_cli.verify.wyrd_oracle._try_import_wyrd",
            return_value=fake,
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = gate_wyrd_oracle(
                    _plan(),
                    _agent_input(),
                    _agent_output("   "),  # whitespace only
                    Path(tmp),
                )
        self.assertTrue(result.passed)
        self.assertIn("nothing", result.detail.lower())
        fake.passive_oracle.assert_not_called()


# ---- _interpret_oracle_verdict ---------------------------------------


class InterpretVerdictTests(unittest.TestCase):
    def test_bool_true(self) -> None:
        passed, detail = _interpret_oracle_verdict(True)
        self.assertTrue(passed)
        self.assertIn("bool", detail)

    def test_bool_false(self) -> None:
        passed, detail = _interpret_oracle_verdict(False)
        self.assertFalse(passed)

    def test_dict_passed_key(self) -> None:
        passed, _detail = _interpret_oracle_verdict({"passed": True})
        self.assertTrue(passed)

    def test_dict_ok_key(self) -> None:
        passed, _detail = _interpret_oracle_verdict({"ok": False})
        self.assertFalse(passed)

    def test_dict_consistent_key(self) -> None:
        passed, _detail = _interpret_oracle_verdict({"consistent": True})
        self.assertTrue(passed)

    def test_dict_with_detail(self) -> None:
        _passed, detail = _interpret_oracle_verdict(
            {"passed": True, "detail": "all good"}
        )
        self.assertEqual(detail, "all good")

    def test_dict_no_recognised_key(self) -> None:
        passed, _detail = _interpret_oracle_verdict({"random": "value"})
        self.assertTrue(passed)  # non-empty dict is truthy

    def test_truthy_other(self) -> None:
        passed, _detail = _interpret_oracle_verdict("any string")
        self.assertTrue(passed)


# ---- wyrd_gate_if_enabled --------------------------------------------


class WyrdGateIfEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_returns_empty_when_disabled(self) -> None:
        result = wyrd_gate_if_enabled()
        self.assertEqual(result, {})

    def test_returns_gate_when_enabled(self) -> None:
        os.environ[ISLAND_ENABLED_ENV] = "1"
        result = wyrd_gate_if_enabled()
        self.assertIn(GATE_NAME, result)
        self.assertIs(result[GATE_NAME], gate_wyrd_oracle)


# ---- DEFAULT_AUDITOR_GATES unchanged ---------------------------------


class DefaultGatesUnchangedTests(unittest.TestCase):
    """Backwards-compat invariant: the WYRD gate must NOT be in the
    default Auditor registry. ADR-0007 explicitly preserves
    pre-PH-09 behaviour for every project that doesn't opt in."""

    def test_wyrd_oracle_not_in_default_registry(self) -> None:
        from mythic_vibe_cli.forge_verifier import DEFAULT_AUDITOR_GATES

        self.assertNotIn(GATE_NAME, DEFAULT_AUDITOR_GATES)


# ---- INSTALL_HINT constant -------------------------------------------


class InstallHintConstantTests(unittest.TestCase):
    def test_constant_mentions_extra(self) -> None:
        self.assertIn("wyrd-protocol", INSTALL_HINT)
        self.assertIn("wyrd", INSTALL_HINT.lower())


if __name__ == "__main__":
    unittest.main()
