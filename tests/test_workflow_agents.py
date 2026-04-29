"""Tests for PH-03 slice 3.1 — agent contract spec.

Pure declarative-layer tests. No provider calls, no filesystem, no
``mythic-vibe forge`` command (that lands in slice 3.5). The tests
lock down:

- the canonical six-role sequence
- contract registry coverage
- AgentInput / AgentOutput / VerificationResult dataclass round-trips
- handoff chain consistency between AGENT_CONTRACTS and
  DEFAULT_AGENT_SEQUENCE
- input / output validation against contracts
- ``all_gates_passed`` aggregation logic
- separation between the contract layer (workflow_agents) and the
  prose layer (ai/prompts/roles)
- DEFAULT_AGENT_SEQUENCE matches workflow_engine.DEFAULT_ROLE_SEQUENCE
"""

from __future__ import annotations

import unittest

from mythic_vibe_cli.workflow_agents import (
    AGENT_CONTRACTS,
    AgentInput,
    AgentOutput,
    DEFAULT_AGENT_SEQUENCE,
    VerificationResult,
    contract_for,
    expected_handoff_chain,
    role_prose,
    validate_input,
    validate_output,
)


class CanonicalSequenceTests(unittest.TestCase):
    def test_six_roles_in_canonical_order(self) -> None:
        self.assertEqual(
            DEFAULT_AGENT_SEQUENCE,
            ("Skald", "Architect", "Cartographer", "Forge Worker", "Auditor", "Scribe"),
        )

    def test_sequence_matches_workflow_engine_default(self) -> None:
        from mythic_vibe_cli.workflow_engine import DEFAULT_ROLE_SEQUENCE

        self.assertEqual(DEFAULT_AGENT_SEQUENCE, DEFAULT_ROLE_SEQUENCE)

    def test_every_canonical_role_has_a_contract(self) -> None:
        for role in DEFAULT_AGENT_SEQUENCE:
            self.assertIn(role, AGENT_CONTRACTS, msg=f"role {role} missing contract")

    def test_no_orphan_contracts_outside_canonical_sequence(self) -> None:
        # AGENT_CONTRACTS may grow to include Debugger / Refactorer at a
        # later slice; today every entry must be in DEFAULT_AGENT_SEQUENCE.
        self.assertEqual(set(AGENT_CONTRACTS), set(DEFAULT_AGENT_SEQUENCE))


class HandoffChainTests(unittest.TestCase):
    def test_expected_chain_matches_default_sequence(self) -> None:
        chain = expected_handoff_chain()
        self.assertEqual(len(chain), len(DEFAULT_AGENT_SEQUENCE))
        for i, (role, next_role) in enumerate(chain):
            self.assertEqual(role, DEFAULT_AGENT_SEQUENCE[i])
            if i + 1 < len(DEFAULT_AGENT_SEQUENCE):
                self.assertEqual(next_role, DEFAULT_AGENT_SEQUENCE[i + 1])
            else:
                self.assertIsNone(next_role)

    def test_each_contract_handoff_matches_canonical_sequence(self) -> None:
        for i, role in enumerate(DEFAULT_AGENT_SEQUENCE):
            expected_next = DEFAULT_AGENT_SEQUENCE[i + 1] if i + 1 < len(DEFAULT_AGENT_SEQUENCE) else None
            self.assertEqual(
                AGENT_CONTRACTS[role].handoff_to_role,
                expected_next,
                msg=f"{role} handoff_to_role != expected {expected_next}",
            )


class ContractForTests(unittest.TestCase):
    def test_contract_for_returns_registered_role(self) -> None:
        contract = contract_for("Architect")
        self.assertEqual(contract.role, "Architect")
        self.assertIn("ARCHITECTURE.md", contract.output_artefact_kinds)

    def test_contract_for_unknown_role_raises_value_error(self) -> None:
        with self.assertRaises(ValueError) as cm:
            contract_for("NotARole")
        self.assertIn("NotARole", str(cm.exception))


class AgentInputRoundTripTests(unittest.TestCase):
    def test_to_dict_and_from_dict_round_trip(self) -> None:
        original = AgentInput(
            role="Architect",
            task="Refactor router",
            phase="architecture",
            workflow_id="WF-20260429-deadbeef",
            workflow_step_id="step-02",
            prior_outputs=("step-01-output-json",),
            context_files=("mythic_vibe_cli/cli.py",),
            forbidden_files=("mythic_vibe_cli/__init__.py",),
            invariants=("no-direct-vendor-imports",),
            notes=("keep alias compatibility",),
        )
        payload = original.to_dict()
        rebuilt = AgentInput.from_dict(payload)
        self.assertEqual(rebuilt, original)

    def test_from_dict_handles_missing_optional_fields(self) -> None:
        rebuilt = AgentInput.from_dict({"role": "Skald", "task": "X", "phase": "intent"})
        self.assertEqual(rebuilt.role, "Skald")
        self.assertEqual(rebuilt.task, "X")
        self.assertEqual(rebuilt.phase, "intent")
        self.assertIsNone(rebuilt.workflow_id)
        self.assertEqual(rebuilt.prior_outputs, ())

    def test_from_dict_filters_non_string_collection_entries(self) -> None:
        rebuilt = AgentInput.from_dict(
            {
                "role": "Skald",
                "task": "X",
                "phase": "intent",
                "context_files": ["valid.py", 42, None, "also-valid.md"],
            }
        )
        self.assertEqual(rebuilt.context_files, ("valid.py", "also-valid.md"))


class AgentOutputRoundTripTests(unittest.TestCase):
    def test_to_dict_and_from_dict_round_trip(self) -> None:
        original = AgentOutput(
            role="Auditor",
            timestamp="2026-04-29T20:00:00Z",
            workflow_id="WF-20260429-deadbeef",
            workflow_step_id="step-05",
            summary="Reviewed three diffs; found one architecture violation",
            artefacts=("mythic/verifications/VER-001.json",),
            decisions=("block-on-violation",),
            risks=("circular import in cli.py",),
            handoff_notes=("Forge Worker should refactor cli imports",),
            verification_results=(
                VerificationResult(name="diff-reviewed-against-architecture", passed=False, detail="cli.py:42 imports yggdrasil_core"),
                VerificationResult(name="no-invariant-violation", passed=False, detail=""),
                VerificationResult(name="test-evidence-recorded", passed=True),
            ),
            raw_response="Provider response text...",
        )
        rebuilt = AgentOutput.from_dict(original.to_dict())
        self.assertEqual(rebuilt, original)

    def test_all_gates_passed_with_mixed_results_is_false(self) -> None:
        output = AgentOutput(
            role="Auditor",
            timestamp="2026-04-29T20:00:00Z",
            verification_results=(
                VerificationResult(name="g1", passed=True),
                VerificationResult(name="g2", passed=False),
            ),
        )
        self.assertFalse(output.all_gates_passed)

    def test_all_gates_passed_with_all_passing_is_true(self) -> None:
        output = AgentOutput(
            role="Auditor",
            timestamp="2026-04-29T20:00:00Z",
            verification_results=(
                VerificationResult(name="g1", passed=True),
                VerificationResult(name="g2", passed=True),
            ),
        )
        self.assertTrue(output.all_gates_passed)

    def test_all_gates_passed_with_no_gates_is_true(self) -> None:
        # Documented behaviour: no recorded gates is treated as
        # passing. The orchestrator is responsible for ensuring gates
        # are run when required, not this property.
        output = AgentOutput(role="Auditor", timestamp="2026-04-29T20:00:00Z")
        self.assertTrue(output.all_gates_passed)


class VerificationResultRoundTripTests(unittest.TestCase):
    def test_round_trip_preserves_all_fields(self) -> None:
        original = VerificationResult(
            name="boundaries-declared", passed=True, detail="all 5 ADRs in place"
        )
        self.assertEqual(VerificationResult.from_dict(original.to_dict()), original)

    def test_from_dict_default_passed_is_false(self) -> None:
        rebuilt = VerificationResult.from_dict({"name": "x"})
        self.assertEqual(rebuilt.name, "x")
        self.assertFalse(rebuilt.passed)
        self.assertEqual(rebuilt.detail, "")


class AgentContractSerializationTests(unittest.TestCase):
    def test_to_dict_lists_required_fields_and_artefact_kinds(self) -> None:
        contract = AGENT_CONTRACTS["Skald"]
        payload = contract.to_dict()
        self.assertEqual(payload["role"], "Skald")
        self.assertIsInstance(payload["input_required_fields"], list)
        self.assertIsInstance(payload["output_required_fields"], list)
        self.assertIn("SYSTEM_VISION.md", payload["output_artefact_kinds"])
        self.assertEqual(payload["handoff_to_role"], "Architect")

    def test_every_contract_has_at_least_one_verification_gate(self) -> None:
        for role, contract in AGENT_CONTRACTS.items():
            self.assertGreater(
                len(contract.verification_gate),
                0,
                msg=f"contract for {role} has no verification gates",
            )

    def test_every_contract_declares_at_least_one_artefact_kind(self) -> None:
        for role, contract in AGENT_CONTRACTS.items():
            self.assertGreater(
                len(contract.output_artefact_kinds),
                0,
                msg=f"contract for {role} has no output artefact kinds",
            )


class ValidateInputTests(unittest.TestCase):
    def test_well_formed_skald_input_validates(self) -> None:
        contract = AGENT_CONTRACTS["Skald"]
        errors = validate_input(
            AgentInput(role="Skald", task="Name the engine", phase="intent"),
            contract,
        )
        self.assertEqual(errors, [])

    def test_role_mismatch_errors_with_clear_message(self) -> None:
        contract = AGENT_CONTRACTS["Skald"]
        errors = validate_input(
            AgentInput(role="Architect", task="X", phase="architecture"),
            contract,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("does not match", errors[0])

    def test_missing_required_string_field_is_flagged(self) -> None:
        contract = AGENT_CONTRACTS["Skald"]
        errors = validate_input(AgentInput(role="Skald", task="", phase="intent"), contract)
        self.assertTrue(any("task" in err for err in errors))

    def test_blank_string_required_field_is_flagged(self) -> None:
        contract = AGENT_CONTRACTS["Skald"]
        errors = validate_input(
            AgentInput(role="Skald", task="   ", phase="intent"), contract
        )
        self.assertTrue(any("task" in err and "non-empty" in err for err in errors))

    def test_architect_requires_prior_outputs(self) -> None:
        contract = AGENT_CONTRACTS["Architect"]
        errors = validate_input(
            AgentInput(role="Architect", task="X", phase="architecture"),
            contract,
        )
        self.assertTrue(any("prior_outputs" in err for err in errors))

    def test_architect_with_prior_outputs_passes(self) -> None:
        contract = AGENT_CONTRACTS["Architect"]
        errors = validate_input(
            AgentInput(
                role="Architect",
                task="X",
                phase="architecture",
                prior_outputs=("skald-output-json",),
            ),
            contract,
        )
        self.assertEqual(errors, [])


class ValidateOutputTests(unittest.TestCase):
    def test_well_formed_scribe_output_validates(self) -> None:
        contract = AGENT_CONTRACTS["Scribe"]
        errors = validate_output(
            AgentOutput(
                role="Scribe",
                timestamp="2026-04-29T20:00:00Z",
                summary="Updated DEVLOG and CHANGELOG",
                artefacts=("DEVLOG.md", "CHANGELOG.md"),
                handoff_notes=("Phase complete; next forge cycle ready"),
            ),
            contract,
        )
        self.assertEqual(errors, [])

    def test_role_mismatch_short_circuits(self) -> None:
        contract = AGENT_CONTRACTS["Scribe"]
        errors = validate_output(
            AgentOutput(role="Auditor", timestamp="t", summary="x"),
            contract,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("does not match", errors[0])

    def test_missing_artefacts_for_architect_is_flagged(self) -> None:
        contract = AGENT_CONTRACTS["Architect"]
        errors = validate_output(
            AgentOutput(
                role="Architect",
                timestamp="t",
                summary="declared boundaries",
                decisions=("prefer narrow ownership",),
                # artefacts intentionally missing
            ),
            contract,
        )
        self.assertTrue(any("artefacts" in err for err in errors))

    def test_auditor_requires_verification_results(self) -> None:
        contract = AGENT_CONTRACTS["Auditor"]
        errors = validate_output(
            AgentOutput(role="Auditor", timestamp="t", summary="reviewed"),
            contract,
        )
        self.assertTrue(any("verification_results" in err for err in errors))


class RoleProseSeparationTests(unittest.TestCase):
    """The contract layer (workflow_agents) and the prose layer
    (ai/prompts/roles) must stay independent. ``role_prose`` is the
    only sanctioned bridge."""

    def test_role_prose_returns_identity_focus_and_prompt(self) -> None:
        prose = role_prose("Skald")
        self.assertEqual(prose["name"], "Skald")
        self.assertIn("Sigrun", prose["identity"])
        self.assertTrue(prose["focus"])
        self.assertTrue(prose["system_prompt"])
        self.assertIsInstance(prose["invariants"], list)

    def test_role_prose_unknown_role_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            role_prose("NotARole")

    def test_every_canonical_role_has_prose(self) -> None:
        for role in DEFAULT_AGENT_SEQUENCE:
            prose = role_prose(role)
            self.assertEqual(prose["name"], role)


class AgentInputHashabilityTests(unittest.TestCase):
    """Frozen dataclasses with tuple fields should be hashable so
    they can sit in dicts/sets without surprise."""

    def test_agent_input_is_hashable(self) -> None:
        a = AgentInput(role="Skald", task="X", phase="intent")
        s = {a}
        self.assertIn(a, s)

    def test_agent_output_is_hashable(self) -> None:
        a = AgentOutput(role="Skald", timestamp="t")
        s = {a}
        self.assertIn(a, s)

    def test_verification_result_is_hashable(self) -> None:
        a = VerificationResult(name="x", passed=True)
        s = {a}
        self.assertIn(a, s)

    def test_agent_contract_is_hashable(self) -> None:
        contract = AGENT_CONTRACTS["Skald"]
        s = {contract}
        self.assertIn(contract, s)


class AgentInputContractKnownPhasesTests(unittest.TestCase):
    """Sanity checks against typo drift between workflow_agents and
    workflow_engine (which both name phases by string literal)."""

    def test_each_role_phase_matches_workflow_engine_role_phases(self) -> None:
        from mythic_vibe_cli.workflow_engine import ROLE_PHASES

        for role in DEFAULT_AGENT_SEQUENCE:
            self.assertIn(role, ROLE_PHASES, msg=f"{role} missing from ROLE_PHASES")


if __name__ == "__main__":
    unittest.main()
