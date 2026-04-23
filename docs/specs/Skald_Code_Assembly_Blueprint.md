# Skald Code Assembly Blueprint

## Executive engineering read

This blueprint translates project vision into concrete build architecture.

## 1) Current technical shape (observed)

### A. Stable product core
`mythic_vibe_cli/` is a focused Python package with:

- argument parser and command dispatch,
- workflow scaffolding and state updates,
- prompt-packet rendering,
- config layering,
- remote markdown sync/import operations.

### B. Massive surrounding corpus
The repository includes many additional trees (imports, research packs, vendored projects). These are valuable but create ambiguity around “what ships” vs “what informs.”

### C. Packaging reality
`pyproject.toml` currently packages only `mythic_vibe_cli`, which confirms the CLI as present production artifact.

## 2) Architecture target model

Adopt a **three-ring model**:

1. **Ring 1: Product Runtime (strict)**
   - `mythic_vibe_cli/`, tests, minimal docs for users.
2. **Ring 2: Capability Extensions (optional runtime)**
   - plugins/adapters with explicit interfaces.
3. **Ring 3: Knowledge & Research (non-runtime)**
   - large markdown corpora, R&D notes, external imports.

Implement guardrails so Ring 3 cannot silently leak into Ring 1 dependencies.

## 3) Required code modules (detailed)

### Module set A — Topology & Canonicalization

#### `mythic_vibe_cli/topology.py`
Responsibilities:
- scan project for duplicate subtree signatures,
- classify files as runtime/capability/research,
- generate canonicalization report.

Key API:
- `analyze_topology(root: Path) -> TopologyReport`
- `suggest_canonical_moves(report) -> list[MoveProposal]`

#### `mythic_vibe_cli/commands/topology_cmd.py`
CLI command:
- `mythic topology --report markdown|json --apply-plan <file>`

### Module set B — Capability Registry

#### `mythic_vibe_cli/capabilities.py`
Responsibilities:
- load capability manifests,
- validate version + compatibility,
- expose enabled capabilities to CLI commands.

Manifest draft:
```yaml
name: wyrd-world-model
version: 0.1.0
entrypoint: integrations.wyrd:register
requires:
  python: ">=3.10"
  cli_api: ">=0.2"
```

### Module set C — Memory Spine

#### `mythic_vibe_cli/memory/events.py`
- append-only event stream (`mythic/events.jsonl`)
- event types: `init`, `pack_generated`, `checkin`, `doctor_run`, `capability_loaded`.

#### `mythic_vibe_cli/memory/decisions.py`
- decision capture with ADR-like schema.
- auto-link decision IDs into devlog entries.

### Module set D — Quality Gates

#### `mythic_vibe_cli/quality/packets.py`
- checks packet size compliance,
- verifies required sections,
- validates prompt contract format.

#### `mythic_vibe_cli/quality/docs.py`
- verifies required docs exist,
- checks stale references and orphan status pointers.

## 4) Command roadmap

### Near-term commands
- `mythic topology` — visibility into repo sprawl.
- `mythic canonicalize --plan plan.yaml` — controlled de-dup migrations.
- `mythic capability add/list/doctor` — plugin lifecycle.
- `mythic memory summarize --since 14d` — continuity aid.

### Later commands
- `mythic quest` — convert goals + constraints into milestone graph.
- `mythic witness` — produce release-ready narrative changelog from event stream.

## 5) Testing strategy needed

1. **Contract tests** for each CLI command output.
2. **Golden-file tests** for prompt packets.
3. **Property tests** for config precedence merges.
4. **Integration tests** with mock upstream markdown tree API.
5. **Topology tests** using synthetic repo fixtures with duplicates.

## 6) Risk register

- **Risk:** project identity dilution due to oversized mixed-purpose repo.
  - **Mitigation:** enforce three-ring boundaries with lint/check commands.
- **Risk:** method drift between local docs and upstream source.
  - **Mitigation:** explicit sync provenance and freshness indicators.
- **Risk:** contributor overwhelm.
  - **Mitigation:** guided command flow and concise first-run diagnostics.

## 7) Milestone phasing

- **Phase I — Clarify**: topology scanner + canonical report.
- **Phase II — Stabilize**: event spine + packet quality gates.
- **Phase III — Extend**: capability registry + adapters.
- **Phase IV — Compose**: cross-project orchestration with explicit contracts.
