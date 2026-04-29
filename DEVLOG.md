# DEVLOG — The Living Chronicle

**Last updated:** 2026-04-29
**Branch:** development
**Scope:** An ongoing, dated chronicle of meaningful work performed in this repository. Each entry preserves *what happened* and *why it mattered*, so that later sessions can resume with understanding rather than guesswork.
**Purpose:** Continuity of record. The project's memory, kept outside anyone's head.

---

## 2026-04-29 - Stage 16 Packet List Workflow Filter

**Session:** Continuing the Stage 16 cadence after landing workflow IDs — letting users see all packets belonging to one workflow run from the packet command surface.
**Status:** `packet list --workflow <id>` returns only the packets stamped with that workflow id; `--step <step_id>` further narrows to one workflow step.
**Scope:** Tiny additive filter on the existing `packet list` command. Uses the `workflow_id` and `workflow_step_id` fields added in the previous slice.

### What changed

- Added `--workflow` and `--step` options to `packet list`.
- Filtered records by `workflow_id` (and optional `workflow_step_id`) before rendering.
- `--step` without `--workflow` returns `USER_INPUT_ERROR` to keep the contract obvious.
- JSON output now exposes a `filters` object reporting the applied `workflow_id` and `workflow_step_id`.
- Human output shows the workflow scope in the heading and surfaces `step:` lines for ID-stamped records.
- Legacy packets without `workflow_id` are excluded automatically when a workflow filter is set.
- Added three CLI-kernel tests: filter narrows two-workflow store to one match; `--step` narrows further; `--step` without `--workflow` errors; legacy packets are excluded.
- Updated `docs/COMMAND_CONTRACTS.md`, `docs/api.md`, and `CHANGELOG.md` to name the new filter.

### Why it matters

Before this slice, the only way to see packets for one workflow run was through `workflow packets`, which is plan-driven. Operators sometimes want a packet-first view: "show me everything stamped with this workflow id." The filter gives that without expanding the runner surface or duplicating the workflow command.

### Verification

- `pytest -q` -> `96 passed, 14 subtests passed` (was 93 + 14)
- `ruff check mythic_vibe_cli tests` -> `All checks passed!`
- `mypy mythic_vibe_cli` -> `Success: no issues found in 51 source files`
- Smoke: created two workflows in one project, then `packet list --workflow <id> --json` returned exactly the one packet whose metadata carried that id.

### Continuity thread

- The next slice can add a workflow ID flag to `packet show` and `packet diff` so operators can address packets by `(workflow_id, step_id)` instead of having to look up the bare `PKT-` ID — useful when iterating on one role's output across runs.

_The id is the bond. Bound packets remember their workflow; unbound ones remain anonymous, which is its own kind of truth._

## 2026-04-29 - Stage 16 Workflow Identifiers on Plans and Packets

**Session:** Picking up the continuity thread from "Stage 16 Workflow Packet Listing" — making packet readiness traceable by workflow ID instead of exact task text.
**Status:** Workflow plans now carry a deterministic `workflow_id`; generated packets are stamped with `workflow_id` + `workflow_step_id`; `workflow packets` and `workflow run --packets-only` prefer ID-based matching with legacy text matching preserved as a fallback.
**Scope:** Strictly additive identity layer over the existing workflow / packet contract.

### What changed

- Added `workflow_id` to `WorkflowPlan`, generated as `WF-<UTC compact>-<sha8(task+created_at)>` in `WorkflowEngine.build_plan`.
- Added optional `workflow_id` and `workflow_step_id` fields to `CodexPacketRequest` and `PacketRecord`, persisted into each packet's `.meta.json` when set.
- `WorkflowStep.packet_request()` now propagates the plan's `workflow_id` and the step's `step_id` into every generated packet request.
- `_workflow_packet_status` now does ID-first matching (`workflow_id` + `workflow_step_id`) and falls back to the existing `(role, phase, task, audience, output_format)` text match when either side lacks IDs.
- `workflow plan`, `workflow packets`, and `workflow run` JSON now expose the plan's `workflow_id`; each `packet_status` entry now reports `match_strategy` (`"id"`, `"text"`, or `null`).
- Added round-trip support to `WorkflowPlan.from_dict` so legacy plans with no `workflow_id` continue to validate and resolve packets via text matching.
- Added engine-level tests for ID generation format, packet-request propagation, dict round-trip, and legacy plan loading.
- Added CLI-kernel tests for `workflow plan --packets` ID stamping, `workflow packets` ID-based matching, and the legacy text-fallback path.
- Updated `docs/COMMAND_CONTRACTS.md`, `docs/api.md`, and `CHANGELOG.md` to name the new identity contract.

### Why it matters

Before this slice, packet readiness depended on exact text on the human-readable task plus four other fields. A user editing the saved plan's task wording, or running two different plans with the same task wording, could silently break or cross-match. The workflow identity layer gives packets a stable provenance: once a plan is written, its packets carry the same `workflow_id` and remain matchable regardless of text drift. The legacy text path keeps every existing plan and packet usable.

### Verification

- `pytest -q` -> `93 passed, 14 subtests passed` (was 87 + 14)
- `ruff check mythic_vibe_cli tests` -> `All checks passed!`
- `mypy mythic_vibe_cli` -> `Success: no issues found in 51 source files`
- Smoke: `workflow plan --task "Smoke ID stamp" --role Skald --packets --json` -> `workflow_id: WF-20260429074552-75add827`, packet artifact carries the same `workflow_id` and `workflow_step_id: step-01`.
- Smoke: `workflow packets --json` against the same plan -> `packets_ready: true`, `match_strategy: "id"` for every entry.
- Smoke: stripping `workflow_id` from saved plan + every packet's `.meta.json`, then `workflow packets --json` -> `match_strategy: "text"`, `found: true`. Legacy fallback is intact.

### Continuity thread

- The next slice can add a workflow-scoped packet filter to `packet list --workflow <id>`, so users can show only the packets belonging to one workflow run without going through the workflow command surface.

_A packet without provenance is a rumor; a packet with a workflow id is a witnessed fact._

## 2026-04-29 - Stage 16 Workflow Packet Listing

**Session:** Making workflow packet readiness inspectable without using the runner.
**Status:** `workflow packets` now lists ready and missing packet artifacts for saved or generated workflow plans.
**Scope:** Read-only operator visibility for workflow packet readiness.

### What changed

- Added `mythic-vibe workflow packets`.
- Added `--missing-only` filtering for missing packet steps.
- Reused the same role/phase/task/audience/format matching as `workflow run --dry-run --packets-only`.
- Added JSON output with plan source, readiness summary, and packet status records.
- Added command-kernel tests for saved-plan packet listings and missing-only generated views.
- Updated command contracts, API docs, changelog, and this devlog entry.

### Why it matters

Operators can now inspect workflow packet readiness directly instead of using the dry-run runner as a listing tool. This keeps visibility separate from execution preview.

### Verification

- `pytest tests\test_cli_kernel.py tests\test_workflow_engine.py` -> `24 passed`
- `ruff check mythic_vibe_cli\commands.py mythic_vibe_cli\app.py tests\test_cli_kernel.py` -> passed
- `mypy mythic_vibe_cli` -> passed
- `python -m mythic_vibe_cli workflow packets --path . --task "Smoke packet listing" --role Skald --missing-only --json` -> reported missing Skald packet status
- `python -m mythic_vibe_cli workflow packets --help` -> rendered expected options and examples

### Continuity thread

- The next slice can attach workflow identifiers to plan and packet metadata, so packet readiness can be traced by workflow ID instead of exact task text.

## 2026-04-29 - Stage 16 Workflow Packet Readiness Gate

**Session:** Hardening workflow execution preview with packet readiness validation.
**Status:** `workflow run --dry-run --packets-only` now validates that each workflow step has a matching stored packet artifact.
**Scope:** Safety gate before any future provider-backed workflow execution.

### What changed

- Added `workflow run --dry-run --packets-only`.
- Added packet matching by role, phase, task, audience, and output format.
- Added JSON `packet_status` output with `found`, packet ID, packet path, and metadata path.
- Missing packets now return a user-input failure in packets-only mode, while still reporting structured status under `--json`.
- Added command-kernel tests for ready packet validation and missing packet blocking.
- Updated command contracts, API docs, changelog, and this devlog entry.

### Why it matters

The runner now has a concrete preflight gate: before future provider execution exists, the CLI can prove whether every planned role step has a real prompt packet ready on disk.

### Verification

- `pytest tests\test_cli_kernel.py tests\test_workflow_engine.py` -> `22 passed`
- `ruff check mythic_vibe_cli\commands.py mythic_vibe_cli\app.py tests\test_cli_kernel.py` -> passed
- `mypy mythic_vibe_cli` -> passed
- Missing-packet smoke: `workflow run --task "Check missing packets" --role Skald --dry-run --packets-only --json` -> returned missing packet status
- Ready-packet smoke: generated Skald + Auditor packets, then `workflow run --dry-run --packets-only --json` -> returned `packets_ready: true`

### Continuity thread

- The next slice can add workflow-scoped packet listing/showing or attach workflow metadata to packet records so packet readiness can be traced by workflow ID instead of exact task text.

## 2026-04-29 - Stage 16 Workflow Run Preview

**Session:** Adding a safe execution preview for role orchestration.
**Status:** `workflow run --dry-run` can preview ordered role execution without invoking providers.
**Scope:** Safety-first runner surface for existing workflow plans.

### What changed

- Added `mythic-vibe workflow run --dry-run`.
- Added support for loading `mythic/workflow_plan.json` or a caller-supplied `--plan`.
- Added support for `workflow run --dry-run --task "..."` to build an in-memory preview plan.
- Added explicit blocking for real `workflow run` provider execution until safety gates are implemented.
- Added `WorkflowPlan.from_dict()`, plan validation, `WorkflowEngine.load_plan()`, and dry-run step rendering.
- Added command-kernel tests for saved-plan previews and blocked real execution.
- Updated command contracts, API docs, changelog, and this devlog entry.

### Why it matters

The workflow engine now has a safe runner shape. Users can see exactly what would happen, in what role order, and where provider execution remains disabled before the project grows into live orchestration.

### Verification

- `pytest tests\test_cli_kernel.py tests\test_workflow_engine.py` -> `20 passed`
- `python -m mythic_vibe_cli workflow run --path . --task "Preview dry run execution" --role Skald --role Auditor --dry-run --json` -> produced a no-provider execution preview
- `ruff check mythic_vibe_cli\workflow_engine.py mythic_vibe_cli\commands.py mythic_vibe_cli\app.py tests\test_cli_kernel.py` -> passed

### Continuity thread

- The next slice can add workflow-scoped packet listing/showing or a safety-gated `workflow run --packets-only` mode that validates required packets before any provider execution is considered.

## 2026-04-29 - Stage 16 Workflow Step Packets

**Session:** Connecting workflow orchestration to packet artifacts.
**Status:** `workflow plan` can now create one packet per role step without invoking any AI provider.
**Scope:** Packet generation bridge from role plans to existing packet storage.

### What changed

- Added `workflow plan --packets` to generate packet artifacts for each workflow step.
- Added `--audience` and `--format` to control exported/generated packet requests.
- Preserved `--dry-run` safety: `--dry-run --packets` previews packet requests without writing plan or packet files.
- Added JSON output for `packet_artifacts` with packet IDs, roles, phases, paths, and metadata paths.
- Reused `CodexBridge`/`PacketBuilder` so workflow packets use the same metadata and context-manifest machinery as normal packets.
- Added command-kernel coverage for packet generation and audience propagation.
- Updated command contracts, API docs, changelog, and this devlog entry.

### Why it matters

The six-role plan is no longer just a map. It can now produce the actual role-specific packet artifacts a human or provider runner can use in order.

### Verification

- `pytest tests\test_cli_kernel.py tests\test_workflow_engine.py tests\test_config_and_bridge.py` -> `25 passed`
- `python -m mythic_vibe_cli workflow plan --task "Generate smoke packets" --path "$env:TEMP\mythic-workflow-packets-smoke" --role Skald --role Auditor --packets --json` -> wrote two packet artifacts

### Continuity thread

- The next slice can add `workflow run --dry-run` or a packet listing/show command scoped to workflow-generated packets.

## 2026-04-29 - Stage 16 Workflow Plan Command

**Session:** Exposing the workflow engine through the public CLI.
**Status:** Users can now generate deterministic role orchestration plans from the command line.
**Scope:** CLI surface for the role-based workflow engine.

### What changed

- Added `mythic-vibe workflow plan --task "..."`.
- Added JSON output containing both the durable plan payload and packet-ready requests.
- Added `--dry-run` preview behavior that avoids writing `mythic/workflow_plan.json`.
- Added repeated `--role` flags for custom ordered role sequences.
- Added `--out` for writing the plan to a caller-selected path.
- Added command-kernel tests for write and dry-run behavior.
- Updated command contracts, API docs, changelog, and this devlog entry.

### Why it matters

The orchestration engine is now reachable by operators. A user can ask the CLI to turn a task into a concrete role handoff plan before generating packets or invoking providers.

### Verification

- `pytest tests\test_cli_kernel.py tests\test_workflow_engine.py` -> `17 passed`
- `python -m mythic_vibe_cli workflow plan --task "Preview the next slice" --path . --dry-run --json` -> produced a six-step plan

### Continuity thread

- The next slice can connect `workflow plan` to packet artifact generation, creating one packet per role step without provider execution.

## 2026-04-29 - Stage 16 Workflow Engine Foundation

**Session:** Continuing the Phase 2 role-based orchestration thread.
**Status:** The CLI now has a deterministic workflow engine for ordering Mythic roles and exporting packet-ready handoffs without calling external providers.
**Scope:** Additive orchestration layer beside the existing flat `workflow.py` lifecycle module.

### What changed

- Added `mythic_vibe_cli.workflow_engine` with `WorkflowEngine`, `WorkflowPlan`, and `WorkflowStep`.
- Added the default Skald -> Architect -> Cartographer -> Forge Worker -> Auditor -> Scribe sequence.
- Added role-to-phase mapping and objective text for each supported role.
- Added packet request export so every orchestration step can become a `CodexPacketRequest`.
- Added durable plan writing to `mythic/workflow_plan.json`.
- Added tests for default role order, handoff links, packet request export, artifact writing, and unknown-role rejection.
- Updated architecture, domain map, API docs, and changelog to name the new owner.

### Why it matters

The role catalog now has a working executor-side shape. This does not run agents yet; it gives the product a stable planning contract that can drive future CLI commands, provider execution, or plugin hooks without hardwiring orchestration into packet rendering.

### Verification

- `pytest tests\test_workflow_engine.py tests\test_workflow.py tests\test_config_and_bridge.py` -> `15 passed`
- `ruff check mythic_vibe_cli\workflow_engine.py tests\test_workflow_engine.py` -> passed
- `mypy mythic_vibe_cli` -> passed

### Continuity thread

- The next slice can expose this engine through a `workflow plan` or `orchestrate plan` CLI command that writes and displays the durable plan for a user task.

## 2026-04-29 - Stage 16 Role Catalog Foundation

**Session:** Continuing the roadmap after syncing `development`.
**Status:** Packet roles now have a dedicated prompt-role catalog and Skald is available as a first-class packet role.
**Scope:** First additive slice of the Phase 2 role-based orchestration roadmap.

### What changed

- Added `mythic_vibe_cli.ai.prompts.roles` with `RolePrompt`, `ROLE_PROMPTS`, `ROLE_PRESETS`, and `PACKET_ROLES`.
- Added first-class `Skald` support for `codex-pack`, `evoke`, and `packet create`.
- Kept `Architect`, `Forge Worker`, `Auditor`, `Cartographer`, `Scribe`, `Debugger`, and `Refactorer` compatible.
- Updated `codex_bridge.py` so packet building consumes the role catalog instead of owning role definitions directly.
- Added tests proving Skald packet rendering and the shared role catalog.
- Updated command contracts and changelog so the new role boundary is visible.

### Why it matters

The roadmap calls for `ai/prompts/roles.py` as the beginning of the 6-agent engine. This change gives the CLI a real ownership point for role identity and prompt constraints without disturbing the existing packet workflow.

### Verification

- `pytest tests\test_config_and_bridge.py tests\test_cli_kernel.py` -> `18 passed`
- `python -m mythic_vibe_cli packet create --task "Frame a capability name" --phase intent --role Skald --path . --dry-run` -> accepted `Skald`
- `pytest` -> `74 passed`

### Continuity thread

- The next Phase 2 slice is a small `workflow/engine.py` orchestration layer that can order Skald -> Architect -> Forge Worker -> Auditor handoffs without invoking external providers by default.

## 2026-04-27 - Stage 15 Method Source Configuration

**Session:** Continuing Stage 15 Mythic Engineering Method Integration.
**Status:** Method source configuration now flows through config, method commands, import, sync, and init.
**Scope:** Configurability slice for method source ownership.

### What changed

- Added `method.source` to `AppConfig`.
- Added `MYTHIC_METHOD_SOURCE` as the environment override.
- Added GitHub method-source URL resolution for README, tree API, and raw markdown URLs.
- Threaded configured method sources into `init`, `import-md`, `method status`, `method show`, `method sync`, `method diff`, and `method pin`.
- Updated `config` output to report `method.source`.
- Added tests for config layering, env override, method status source reporting, and GitHub endpoint derivation.

### Why it matters

The method corpus is no longer hardwired to one repository at the command layer. A project can point the CLI at a chosen GitHub method source and still use the same status, import, diff, and pin machinery.

### Verification

- `pytest -q tests/test_method.py tests/test_config_and_bridge.py` -> `18 passed, 7 subtests passed`
- `ruff check mythic_vibe_cli/config.py mythic_vibe_cli/mythic_data.py mythic_vibe_cli/app.py mythic_vibe_cli/commands.py tests/test_method.py tests/test_config_and_bridge.py` -> passed
- `mypy mythic_vibe_cli` -> passed

### Continuity thread

- The next Stage 15 slice is the method excerpt selector for packet building.

_A method can be canonical, but the tool must know who is allowed to name the canon._

## 2026-04-27 - Stage 15 Method Corpus Pin

**Session:** Continuing Stage 15 Mythic Engineering Method Integration.
**Status:** `method pin` now records a reproducibility pin for clean imported method corpora.
**Scope:** Pinning layer on top of the manifest and diff contracts.

### What changed

- Added `MethodPin` and `MethodStore.pin_import_manifest()`.
- Added `mythic-vibe method pin --path . --target docs/mythic_source`.
- Refuses to pin when `method diff` reports missing, changed, or untracked markdown files.
- Writes `method_pin.json` with source, ref, manifest SHA-256, file count, paths, timestamp, and optional note.
- Added tests for successful pinning, dry-run behavior, and dirty-corpus refusal.

### Why it matters

The method corpus is now reproducible. A user can import it, check it, and pin the exact manifest identity before using that method as a stable reference.

### Verification

- `pytest -q tests/test_method.py` -> `10 passed, 7 subtests passed`
- `ruff check mythic_vibe_cli/mythic_data.py mythic_vibe_cli/app.py mythic_vibe_cli/commands.py tests/test_method.py` -> passed
- `mypy mythic_vibe_cli` -> passed

### Continuity thread

- The next Stage 15 slice is method source configuration or method excerpt selection for packet building.

_A pinned method is a promise: this is the teaching we meant._

## 2026-04-27 - Stage 15 Method Corpus Diff

**Session:** Continuing Stage 15 Mythic Engineering Method Integration.
**Status:** `method diff` now checks an imported method corpus against its manifest.
**Scope:** Local drift detection for manifest-backed method imports.

### What changed

- Added `MethodDiff` and `MethodStore.diff_import_manifest()`.
- Added `mythic-vibe method diff --path . --target docs/mythic_source`.
- Reports missing files, changed file bytes/hashes, and untracked markdown files.
- Added JSON and human output paths.
- Added focused tests for clean corpus, drifted corpus, and missing manifest behavior.

### Why it matters

Pinning is only useful if drift can be seen. This gives the method corpus a local integrity check before `method pin` makes any reproducibility promise.

### Verification

- `pytest -q tests/test_method.py` -> `7 passed, 7 subtests passed`
- `ruff check mythic_vibe_cli/mythic_data.py mythic_vibe_cli/app.py mythic_vibe_cli/commands.py tests/test_method.py` -> passed

### Continuity thread

- The next Stage 15 slice is `method pin`, built on the manifest and diff contracts now in place.

_A pinned method must first know whether the present corpus has wandered._

## 2026-04-27 - Stage 15 Method Corpus Manifest

**Session:** Continuing Stage 15 Mythic Engineering Method Integration.
**Status:** `import-md` now writes a manifest-backed method corpus import.
**Scope:** Small persistence upgrade that gives later method diff/pin work a stable base.

### What changed

- Added `MethodImportManifest` and `MethodManifestEntry` records.
- Updated `MethodStore.import_all_markdown()` to write `method_manifest.json` with source, ref, generated timestamp, file count, relative paths, byte sizes, and SHA-256 hashes.
- Kept `_import_index.json` as a compatibility copy of the manifest payload.
- Updated `import-md` output to report the manifest path.
- Added a network-free test that fakes the GitHub tree and markdown downloads.

### Why it matters

Method diffing and pinning need a real corpus identity, not just copied files. The manifest now gives the CLI a durable inventory it can compare, pin, and audit.

### Verification

- `pytest -q tests/test_method.py` -> `4 passed, 7 subtests passed`
- `ruff check mythic_vibe_cli/mythic_data.py mythic_vibe_cli/commands.py tests/test_method.py` -> passed
- `mypy mythic_vibe_cli` -> passed

### Continuity thread

- The next Stage 15 slice is to add `method diff` against `method_manifest.json`, then `method pin` once diff semantics are clear.

_A method corpus that cannot name its files cannot defend its truth._

## 2026-04-27 - Stage 15 Method Profile Visibility

**Session:** Beginning Stage 15 Mythic Engineering Method Integration.
**Status:** The CLI can now report the active method profile, version, cache, sections, and freshness without requiring network access.
**Scope:** First safe Stage 15 slice, focused on method visibility before deeper corpus sync/diff/pin behavior.

### What changed

- Added `mythic-vibe method status` for method source, profile, content-derived version, cache file, section labels, pin state, and freshness.
- Added `mythic-vibe method show` and `mythic-vibe method sync` subcommands while preserving the legacy plain `method` notes output.
- Changed method display/status to use the local cache or fallback profile without forcing a network sync.
- Expanded the fallback method profile to the full seven-phase loop: `intent -> constraints -> architecture -> plan -> build -> verify -> reflect`.
- Updated command/API docs, changelog, and the Stage 15 roadmap checkboxes for the completed visibility slice.

### Why it matters

Stage 15 needs the method to behave like a versioned corpus, not loose text. This pass gives the CLI a concrete method identity it can report and later pin, diff, and use for packet section selection.

### Verification

- `pytest -q tests/test_method.py` -> `3 passed, 7 subtests passed`
- `ruff check mythic_vibe_cli/mythic_data.py mythic_vibe_cli/app.py mythic_vibe_cli/commands.py tests/test_method.py` -> passed
- `mypy mythic_vibe_cli` -> passed

### Continuity thread

- The next Stage 15 slice is to create a manifest-backed method corpus import and wire `method diff` or `method pin` against that manifest.

_Before the method can guide the work, the tool must know which method it is holding._

## 2026-04-27 - Stage 14 Follow-up: Blocked Verification Output

**Session:** Continuing Stage 14 UX hardening.
**Status:** `next` now explains non-passing verification records more clearly in human output.
**Scope:** Small command-output polish with focused regression coverage.

### What changed

- Added failed-command extraction from the latest verification artifact.
- Updated `mythic-vibe next` human output to separate failed commands, verification errors, and blocked reasons.
- Added a UX regression test for blocked verification output in normal text mode.

### Why it matters

When proof is failing, the next action must be obvious. The CLI now shows what command failed, what blocker was recorded, and the exact verification rerun command in one place.

### Verification

- `pytest -q tests/test_ux.py` -> `8 passed, 7 subtests passed`
- `ruff check mythic_vibe_cli/commands.py tests/test_ux.py` -> passed
- `mypy mythic_vibe_cli/commands.py` -> passed

### Continuity thread

- The next useful step is to run the full local release gate set, commit this change, and then push the accumulated Stage 14 commits.

_When the proof breaks, the tool should point straight at the crack._

## 2026-04-27 - Stage 14 Follow-up: Command Help Examples

**Session:** Finishing the Stage 14 UX polish thread.
**Status:** High-traffic command help now includes concrete examples.
**Scope:** Parser help text, UX tests, and documentation records.

### What changed

- Added multi-line argparse examples for `init`, `next`, `verify`, `packet create`, `reflect`, `resume`, and `doctor`.
- Preserved normal command semantics; this pass only improves command help output.
- Added a UX regression test that verifies each targeted help screen renders an expected example.

### Why it matters

The CLI now teaches by showing. A user who reaches for `--help` gets practical commands they can adapt immediately instead of a bare list of flags.

### Verification

- `pytest -q tests/test_ux.py` -> `7 passed, 7 subtests passed`
- `ruff check mythic_vibe_cli/app.py tests/test_ux.py` -> passed
- `mypy mythic_vibe_cli/app.py` -> passed

### Continuity thread

- The remaining useful Stage 14 hardening is to improve blocked-verification human output in `next`, especially command failures and blocked reasons.

_A good help screen should put the handle of the tool in the user's hand._

## 2026-04-27 - Stage 14 Follow-up: Smarter Next Guidance

**Session:** Continuing Stage 14 command ergonomics.
**Status:** `next` now uses the latest verification and handoff records before falling back to phase guidance.
**Scope:** Small runtime and documentation pass focused on resuming work from the right pressure point.

### What changed

- `mythic-vibe next` now prioritizes failed or blocked `mythic/verifications/latest.json` results.
- If verification is passing, `next` uses the latest handoff next step when one exists.
- JSON output now includes the guidance source, latest verification ID/result, latest handoff next step, and verification issue details when relevant.
- Added UX tests for phase guidance, failed verification priority, and latest-handoff priority.

### Why it matters

The next command now behaves more like a real session navigator. It does not suggest fresh work while proof is failing, and it preserves the concrete handoff instruction when the previous session already named the next useful action.

### Verification

- `pytest -q tests/test_ux.py` -> `6 passed`

### Continuity thread

- The remaining Stage 14 follow-up is to expand per-command argparse epilog examples for the highest-traffic commands.

_The forge does not ask what is next until it knows what is still hot._

## 2026-04-27 - Stage 14 UX Polish and Command Ergonomics

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** The CLI now has orientation commands, shell completions, and optional rich output.
**Scope:** Stage 14 pass, focused on calm, clear command ergonomics and beginner-friendly next steps.

### What changed

- Added `mythic-vibe examples`, `guide`, `next`, `tutorial`, and `completion`.
- Added `mythic-vibe explain phase` and `mythic-vibe explain artifact`.
- Added shell completion output for bash, zsh, and Windows PowerShell.
- Added optional rich terminal rendering behind `MYTHIC_RICH=1` with plain output fallback.
- Added UX guidance tests and packaging coverage for the new `ux` optional dependency group.

### Why it matters

Stage 14 makes the CLI less cryptic. It can now show examples, explain phases and artifacts, suggest the next action from project state, and hand the user completion scripts without sending them hunting through docs.

### Verification

- `pytest -q` -> `55 passed`
- `ruff check mythic_vibe_cli tests scripts` -> passed
- `mypy mythic_vibe_cli` -> passed with the initial non-strict baseline
- `python scripts/check_changelog.py` -> passed
- `python -m build` -> built wheel and sdist
- `twine check dist/*` -> passed

### Continuity thread

- The next useful improvement is to expand per-command examples in argparse epilog text and make `next` smarter about verification failures and latest handoffs.

_A good tool does not merely obey; it orients._

## 2026-04-27 - Stage 13 Packaging, Release, and Install Quality

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packaging metadata, CI, install docs, and release checks are now defined.
**Scope:** Stage 13 pass, focused on fresh-user install quality and reproducible release verification.

### What changed

- Expanded `pyproject.toml` with fuller metadata, Python classifiers, package URLs, optional dependency groups, ruff, mypy, and coverage config.
- Added GitHub Actions CI for tests, coverage, lint, type checks, changelog checks, package build, and distribution validation.
- Added `docs/INSTALL.md` for Windows PowerShell, Linux, macOS, venv, `uv`, and `pipx`.
- Added `docs/RELEASE_CHECKLIST.md` for release and artifact verification.
- Added `scripts/check_changelog.py` as a lightweight changelog release gate.
- Added packaging contract tests so console scripts, dependency groups, tooling config, docs, and CI files stay present.

### Why it matters

Stage 13 turns the CLI from "runs in this checkout" into something closer to a releasable tool. Fresh installs, CI checks, and release artifacts now have a documented path.

### Verification

- `pytest -q` -> `51 passed`
- `pytest -q --cov=mythic_vibe_cli --cov-report=term-missing` -> `51 passed`
- `ruff check mythic_vibe_cli tests scripts` -> passed
- `mypy mythic_vibe_cli` -> passed with the initial non-strict baseline
- `python scripts/check_changelog.py` -> passed
- `python -m build` -> built wheel and sdist
- `twine check dist/*` -> passed

### Continuity thread

- The next useful improvement is to run the full CI workflow on GitHub and tighten any lint/type findings that only appear on a clean Linux runner.

_A tool that cannot be installed is only a rumor._

## 2026-04-27 - Stage 12 Plugin and Grimoire System

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Plugins now have a versioned registry, hook declarations, health inspection, and disable controls.
**Scope:** Stage 12 pass, focused on visible extension behavior without destabilizing the core CLI.

### What changed

- Added `mythic_vibe_cli.plugins` modules for plugin API contracts, registry persistence, and entrypoint inspection.
- Added `mythic-vibe plugin list|inspect|disable`.
- Upgraded `grimoire add|list` to use the versioned plugin registry while preserving the legacy `plugins` list shape.
- Added the supported hook set: `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, and `after_reflect`.
- Added plugin health reporting and sandbox warnings so local Python extension points are visible before use.
- Added `plugin_manifest.schema.json` for the registry contract.

### Why it matters

Stage 12 moves plugins from loose strings toward observable extension points. The CLI can now show what is registered, what hooks a plugin claims, whether it is disabled, and whether inspection failed.

### Verification

- `pytest -q tests/test_plugins.py tests/test_cli.py::MythicCliRitualTests::test_grimoire_add_and_list tests/test_cli_kernel.py::CliKernelTests::test_grimoire_json_has_no_human_prefix tests/test_cli_kernel.py::CliKernelTests::test_command_registry_preserves_current_commands_and_aliases` -> `6 passed`

### Continuity thread

- The next useful improvement is real hook invocation around scan, packet, verify, and reflect flows. Stage 12 currently makes hooks discoverable and controlled before wiring execution into the core lifecycle.

_Extensions may enter the hall, but they do not take the throne._

## 2026-04-27 - Stage 11 Lawful Plunder System v2

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** `plunder` now has a staged, license-aware, provenance-recording workflow.
**Scope:** Stage 11 pass, focused on safe single-file reuse from GitHub with source traceability.

### What changed

- Added `mythic_vibe_cli.plunder` modules for GitHub access, license posture, and provenance records.
- Added `mythic-vibe plunder inspect|plan|fetch|apply|record`.
- Added Apache/MIT/BSD compatibility classification and "Do not plunder" warnings for unknown or incompatible licenses.
- Added `mythic/imports/plunder_plan.json`, `mythic/imports/plunder_manifest.json`, cache paths, and NOTICE update support.
- Preserved legacy `plunder --repo --source --dest` behavior while making staged reuse the preferred path.

### Why it matters

Stage 11 makes reuse less reckless. Imported code now carries a source trail, license posture, destination, source SHA, and modification note instead of arriving as an anonymous copied file.

### Verification

- `pytest -q tests/test_plunder.py tests/test_cli.py::MythicCliRitualTests::test_plunder_requires_token_env` -> `4 passed`

### Continuity thread

- The next useful improvement is richer license-file capture and source archive checks, but the core legal/provenance path is now real.

_Useful things may be borrowed; careless things become debt._

## 2026-04-27 - Stage 10 Reflection, Handoff, and Continuity Memory

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** `reflect`, `handoff`, and `resume` now preserve session continuity with durable handoff artifacts.
**Scope:** Stage 10 pass, focused on end-of-session memory, status linkage, and future-session recovery.

### What changed

- Added `mythic-vibe reflect` with session-summary capture and handoff generation.
- Added `mythic-vibe handoff create|show|latest` for durable handoff records.
- Added `mythic-vibe resume` to summarize the latest handoff and the next recommended action.
- Wrote timestamped handoff artifacts under `mythic/handoffs/` and refreshed `docs/SESSION_HANDOFF.md`.
- Linked the latest handoff into `status` output so future sessions can find it quickly.

### Why it matters

Stage 10 turns the CLI into a better collaborator at session boundaries. Instead of losing context at the edge of a work cycle, the repo now leaves behind a structured handoff that the next session can use immediately.

### Verification

- `pytest -q` -> `41 passed`

### Continuity thread

- The next useful step after Stage 10 is to use the new handoff flow in real work and see whether the generated summaries stay sharp enough under pressure.

_May the next session arrive to a prepared table._

## 2026-04-27 - Stage 9 Doctor Diagnostics and Drift Checks

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** `doctor` is now a structured diagnostic scanner with state coherence, docs drift, and ADR checks.
**Scope:** Stage 9 pass, focused on health scanning, boundary-aware diagnostics, and canonical docs upkeep.

### What changed

- Added canonical `docs/INDEX.md` and made project scaffolding create it alongside `docs/COMMAND_CONTRACTS.md`.
- Added ADRs for verification gates and doctor diagnostics.
- Expanded `MythicWorkflow.doctor_report()` into a structured diagnostic report with required-artifact, state, docs, and boundary sections.
- Added state coherence checks for phase regression and stale verification linkage.
- Added docs/code drift checks for the command contract, canonical index, and major-change ADRs.
- Kept `doctor --repo-boundary` focused on active runtime boundary checks while leaving docs drift to the normal doctor path.

### Why it matters

Stage 9 makes the CLI feel like a real health scanner instead of a polite file lister. It can now catch phase incoherence, missing canonical docs, and drift between the runtime contract and the written contract.

### Verification

- `pytest -q` -> `39 passed`

### Continuity thread

- The next useful step after Stage 9 would be to deepen the doctor with history-aware age/staleness checks, but the core diagnostic spine is now in place.

_May the scryer report what is true._

## 2026-04-27 - Stage 8 Verification Gate and Durable Records

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Verification is now a first-class CLI command and reflect check-ins are blocked until a successful verification exists.
**Scope:** Stage 8 reality-gate pass, focused on durable verification artifacts, command execution, diff review, and reflect gating.

### What changed

- Added `mythic_vibe_cli.verify` helper modules for test execution, git diff review, invariant checks, and documentation checks.
- Added `mythic-vibe verify` with command, changed-file, docs, invariant, and record flags.
- Added durable verification artifacts under `mythic/verifications/` plus a `latest.json` pointer.
- Updated project state so successful verification records `last_verification_id`.
- Added a reflect gate so `mythic-vibe checkin --phase reflect` is blocked until the latest verification result is `pass`.
- Added CLI tests covering verification recording and the reflect gate.

### Why it matters

Stage 8 turns verification from a recommendation into a real gate. The CLI now refuses to claim reflective completion unless there is a successful verification record to stand on.

### Verification

- `pytest -q` -> `38 passed`

### Continuity thread

- The next Stage 8 follow-through could expand verification commands beyond the default pytest runner, but the gate and durable record path now exist.

_May reality stay louder than ceremony._

## 2026-04-27 - Stage 7 Provider Metadata Hardening

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Provider responses now carry usage, cost hints, and request metadata in a more durable shape.
**Scope:** Stage 7 hardening pass focused on telemetry consistency and clearer provider contracts.

### What changed

- Added provider-level pricing heuristics so estimates no longer report `0.0` across the board for real adapters.
- Extended provider responses with usage and metadata fields.
- Added request IDs, estimated cost, and observed cost fields to real-provider responses when available.
- Kept dry-run responses consistent by giving them token and cost metadata too.
- Surfaced response usage and metadata in `ai test` and `ai run` JSON output.

### Why it matters

This makes provider calls easier to inspect and compare without changing the command flow. The CLI now tells the truth about what it thinks a call will cost, and what the provider actually reported when it answered.

### Verification

- `pytest -q` -> `37 passed`

### Continuity thread

- The next useful hardening step would be a more explicit provider-call audit trail or provider-specific retry/backoff policy, if the project wants that before Stage 8.

_May the record carry the weight of the call._

## 2026-04-27 - Stage 7 Provider Execution and Log Redaction

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Direct providers now execute real HTTP calls when configured, while the local bridge modes stay dry-run safe.
**Scope:** Stage 7 follow-through, focused on live provider execution, packet resolution, and redacted provider call logs.

### What changed

- Threaded project roots into the AI provider registry so provider runs can write logs under `mythic/ai/provider_calls.jsonl`.
- Added packet resolution for `ai test` and `ai run`, including stored packet IDs and on-disk packet files.
- Kept `ai test` dry-run-only and made `ai run` honor `--dry-run` explicitly.
- Added real HTTP execution for `openai`, `anthropic`, `gemini`, and `openrouter` providers with explicit API-key checks.
- Added request and response logging with secret redaction before persistence.
- Preserved `copy-paste` and `local` as always-available bridge modes with `manual` and `local` packet labels for inline input.
- Added focused tests for live provider execution, redacted logs, and packet-ID resolution.

### Why it matters

Stage 7 now does the thing the CLI promised: it can talk to real providers when configured, but it still refuses to blur dry-run previews into live calls.

### Verification

- `pytest -q` -> `37 passed`

### Continuity thread

- The remaining Stage 7 work is mostly polish and safety hardening around provider request/response metadata, cost estimates, and any final adapter refinements.

_May the bridge stay explicit, and the logs stay honest._

## 2026-04-27 - Stage 7 Provider Adapter Spine

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Optional AI provider adapters exist behind explicit CLI commands and dry-run-first behavior.
**Scope:** First Stage 7 pass, focused on isolation, visibility, and safe defaults.

### What changed

- Added `mythic_vibe_cli.ai` with a provider registry and isolated provider modules.
- Added provider stubs for `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, and `openrouter`.
- Added `mythic-vibe ai providers`, `mythic-vibe ai test`, `mythic-vibe ai run`, and `mythic-vibe ai ingest-response`.
- Added explicit API-key validation for direct provider adapters.
- Kept direct provider execution dry-run-first and metadata-oriented.
- Preserved copy-paste as a first-class, always-available mode.

### Why it matters

Stage 7 now has a real spine. The CLI can name providers, inspect their configuration, estimate usage, and record responses without losing the local-first method.

### Verification

- `pytest -q` -> `35 passed`

### Continuity thread

- The next Stage 7 work is real provider network execution, redaction, logging, and stricter safety records.

_May the bridge remain explicit and the fallback remain local._

---

## 2026-04-27 - Weighted Packet Budget Strategy

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet compaction now allocates character budget by section priority instead of flattening everything evenly.
**Scope:** Final visible Stage 6 budget-tuning pass.

### What changed

- Reworked packet compaction to weight priority sections more heavily than low-signal sections.
- Preserved more room for `project_index`, `architecture`, `verification`, and `invariants`.
- Tightened packet loading so stored packet IDs can resolve both markdown and JSON packet artifacts.
- Added a budget-allocation test to verify the weighted strategy behaves as intended.

### Why it matters

This makes truncated packets more useful under pressure. The sections that help a collaborator act safely and correctly now survive budget pressure better than the decorative ones.

### Verification

- `pytest -q` -> `31 passed`

### Continuity thread

- Stage 6 is now functionally strong; the remaining work is mostly polish or edge-case expansion unless a new need appears.

_May the scarce space be spent where it matters most._

---

## 2026-04-27 - Stage 6 Role Profiles, Formats, and Safety Sections

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet generation now supports named roles, packet formats, safety sections, and a context manifest.
**Scope:** Closing the remaining visible Stage 6 packet-engine gaps.

### What changed

- Added packet role presets for `Architect`, `Forge Worker`, `Auditor`, `Cartographer`, `Scribe`, `Debugger`, and `Refactorer`.
- Added packet output format selection, including Markdown, copy-paste, JSON, and provider-oriented format labels.
- Added packet safety sections for files in scope, files out of scope, invariants, verification commands, and check-in summary shape.
- Added `mythic/context_sources.json` as the packet context manifest.
- Added JSON packet rendering support when requested.
- Preserved `CodexBridge` compatibility while the internal builder continues to evolve as `PacketBuilder`.

### Why it matters

The packet engine now expresses the actual working contract the roadmap wanted: role-aware, format-aware, safety-bound, and grounded in local context.

### Verification

- `pytest -q` -> `30 passed`

### Continuity thread

- Stage 6 still has small polish items left if we want them later, but the major functional pieces are now in place.

_May the packet carry both intention and boundary._

---

## 2026-04-27 - Packet Ingest and Diff Lifecycle

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet artifacts can now be ingested and compared as first-class local records.
**Scope:** Stage 6 packet workflow completion for ingest/diff.

### What changed

- Added `mythic-vibe packet ingest` for importing Markdown or JSON packet artifacts into the local packet store.
- Added `mythic-vibe packet diff` for unified diffs between stored packet artifacts.
- Packet ingest preserves source path metadata and records a new canonical packet ID.
- Packet JSON records now carry optional source metadata for provenance.

### Why it matters

The packet system is now a real artifact lifecycle instead of a one-way emitter. That makes packet reuse, comparison, and handoff much more practical.

### Verification

- `pytest -q` -> `29 passed`

### Continuity thread

- Stage 6 still has additional work left: richer roles, output formats, safety sections, and a context source manifest.

_May the artifact remember its own lineage._

---

## 2026-04-27 - Packet Command Family and Artifact Store

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet artifacts now have IDs, metadata, and dedicated CLI commands.
**Scope:** Stage 6 prompt-packet groundwork beyond the initial project-index integration.

### What changed

- Renamed the internal packet builder concept to `PacketBuilder` while preserving `CodexBridge` as a compatibility alias.
- Added packet IDs and packet metadata under `mythic/packets/`.
- Added `mythic-vibe packet create`, `mythic-vibe packet show`, and `mythic-vibe packet list`.
- Kept `codex-pack` and `evoke` as compatibility paths into the packet builder.
- Packet creation now carries role metadata and continues to embed the local project index.

### Why it matters

The prompt system is no longer a throwaway text emitter. It has a durable artifact store, which is the shape Stage 6 needs if it is to become reusable across tools and sessions.

### Verification

- `pytest -q` -> `29 passed`

### Continuity thread

- The next Stage 6 steps are packet ingest, packet diff, richer role presets, and stronger safety/format selection.

_May the artifacts outlast the moment that summoned them._

---

## 2026-04-27 - Packet Builder Context Integration

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Runtime packet generation now pulls from the local project index.
**Scope:** Stage 6-adjacent packet context hardening, built on top of the Stage 5 scanner work.

### What changed

- `CodexBridge` now builds and embeds a project index snapshot when generating prompt packets.
- `mythic/project_index.json` is written automatically as part of packet generation.
- The packet now includes a `PROJECT INDEX` section with git metadata, language stats, important files, docs, tests, risks, and recommended context.
- Tests were added to verify the packet contains the project index and that the index file is written.

### Why it matters

Prompt packets are now grounded in the local repository map, which makes them less speculative and more useful for real engineering work.

### Verification

- `pytest -q` -> `28 passed`

### Continuity thread

- The next logical step is to make packet context selection smarter so the bridge can prioritize changed files and task-relevant files even more precisely.

_May the packet know the ground it stands on._

---

## 2026-04-27 - Stage 5 Context Scanner and Project Index

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Runtime, tests, and project-records updated with a local context scanner and index writer.
**Scope:** First implementation slice of Stage 5 from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.

### What changed

- Added `mythic_vibe_cli.context` with scanner and indexer modules.
- Added `mythic-vibe scan` with `--json`, `--changed`, `--docs`, `--include`, `--exclude`, and `--dry-run` support.
- Added `.mythicignore` as a local scan policy file.
- Added project-index generation at `mythic/project_index.json`.
- Added tests covering git-aware scanning, ignore rules, and the new command registry entry.

### Why it matters

The CLI now has a real local-project map, which makes future prompt packets and workflow guidance less blind and less hand-wavy. It can see the shape of the repo before it asks for attention.

### Verification

- `pytest -q` -> `27 passed`

### Continuity thread

- The next useful step is to wire the index into prompt packet generation so context selection becomes automatic rather than manual.

_May the map speak before the blade moves._

---

## 2026-04-24 - Stage 1 CLI Command Extraction and Runtime Controls

**Session:** Third implementation pass from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.
**Status:** Runtime, tests, roadmap, and command-boundary documentation updated on `development`.
**Scope:** Completion-oriented slice of Stage 1 CLI kernel hardening.

### What changed

- Extracted command implementations from `mythic_vibe_cli/app.py` into `mythic_vibe_cli/commands.py`.
- Kept `mythic_vibe_cli/app.py` focused on parser construction and top-level dispatch.
- Preserved `mythic_vibe_cli/cli.py` as the public compatibility wrapper for `mythic_vibe_cli.cli:main`.
- Added `mythic_vibe_cli/output.py` for shared plain-text terminal rendering helpers.
- Added `mythic_vibe_cli/errors.py` for structured CLI error payloads and formatting.
- Added shared `--json`, `--quiet`, `--verbose`, and `--dry-run` command controls where each option can preserve existing behavior safely.
- Added JSON output paths for structured reporting commands and dry-run guards for file-writing/syncing commands.
- Updated `tests/test_cli_kernel.py` so the compatibility export, parser dispatch, and command registry are locked to the same handler table.
- Added tests for status JSON output, quiet output suppression, init dry-run safety, and clean grimoire JSON output.
- Updated command, architecture, domain, active-boundary, API, and changelog records so docs match the new runtime shape.
- Checked the Stage 1 completed items in `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`, using the actual transitional module paths.

### Verification

- `python -m pytest tests/test_cli_kernel.py tests/test_cli.py -q` passed with 12 tests.
- `python -m pytest -q` passed with 21 tests.
- `python -m mythic_vibe_cli --help` rendered successfully.
- `python -m mythic_vibe_cli.cli --help` rendered successfully.
- `python -m mythic_vibe_cli.cli doctor --repo-boundary --path .` passed with no errors or warnings.
- `python -m mythic_vibe_cli status --json` emitted clean JSON.
- `python -m mythic_vibe_cli doctor --repo-boundary --path . --json` emitted clean JSON.
- `python -m mythic_vibe_cli init --goal "Preview only" --path .mythic-preview --dry-run` previewed without creating the target directory.
- `git diff --check` passed with only line-ending normalization warnings.

### Next thread

Move into Stage 2: create the schema-versioned project state engine, JSON persistence layer, migration path from current `mythic/status.json`, and state validation commands.

---

## 2026-04-24 - Stage 1 CLI Kernel Hardening Begins

**Session:** Second implementation pass from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.
**Status:** Runtime, tests, and command-contract documentation updated on `development`.
**Scope:** First safe slice of Stage 1 CLI kernel hardening.

### What changed

- Added `mythic_vibe_cli/__main__.py`, enabling `python -m mythic_vibe_cli`.
- Added `mythic_vibe_cli/exit_codes.py` with the named return-code policy: success, operational failure, user/config error, verification failure, and unsafe operation blocked.
- Moved the real CLI kernel into `mythic_vibe_cli/app.py`, leaving `mythic_vibe_cli/cli.py` as the compatibility entrypoint for `mythic_vibe_cli.cli:main`.
- Replaced the long `main()` dispatch chain with `COMMAND_HANDLERS`, preserving existing commands and aliases.
- Added `tests/test_cli_kernel.py` to lock down module execution, alias preservation, and exit-code policy.
- Added `docs/COMMAND_CONTRACTS.md` for entrypoints, command dispatch, compatibility aliases, and exit codes.
- Updated `docs/api.md`, `docs/ARCHITECTURE.md`, `docs/DOMAIN_MAP.md`, and `docs/INDEX.md` to reflect the kernel contract.

### Verification

- `python -m pytest tests/test_cli_kernel.py -q` passed.
- `python -m mythic_vibe_cli --help` rendered successfully.
- `python -m mythic_vibe_cli.cli --help` rendered successfully.

### Next thread

Continue Stage 1 by extracting command groups from `app.py` into focused command modules, then introduce shared terminal output/error helpers.

---

## 2026-04-24 - Stage 0 Boundary Stabilization Begins

**Session:** First implementation pass from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.
**Status:** Runtime and governance changes made on `development`.
**Scope:** Stage 0 repo boundary stabilization, with one small test-harness hardening fix.

### What changed

- Added `REPO_BOUNDARY.md` as the root law for active runtime, dormant islands, and adapter gates.
- Added `docs/ACTIVE_PRODUCT_BOUNDARY.md` and `docs/DORMANT_ISLANDS.md` so contributors can tell what is product runtime and what is reference material.
- Added `docs/ADRS/ADR-0001-active-runtime-boundary.md` and `docs/ADRS/ADR-0002-no-direct-vendor-imports.md` to make the boundary decisions durable.
- Updated `README.md` with an above-the-fold Active Runtime Path section.
- Expanded `docs/INDEX.md` into a real navigation hub for boundary, architecture, and operator docs.
- Added `mythic-vibe doctor --repo-boundary` to validate boundary docs and scan active runtime imports for direct dependencies on dormant islands.
- Added `tests/test_repo_boundary.py` for boundary-file and forbidden-import behavior.
- Configured pytest to collect only active product tests under `tests/`, preventing dormant island tests from breaking the product verification gate.
- Fixed `ConfigStore` to honor `HOME` environment overrides before falling back to `Path.home()`.

### Verification

- `python -m pytest tests/test_repo_boundary.py -q` passed.
- `python -m mythic_vibe_cli.cli doctor --repo-boundary --path .` passed with no errors or warnings.
- `python -m pytest -q` passed with 13 active product tests.
- `python -m mythic_vibe_cli.cli --help` rendered successfully.

### Next thread

Continue with Stage 1 CLI kernel hardening: add `mythic_vibe_cli/__main__.py`, begin command-router extraction, and preserve all existing command aliases while tests stay green.

---

## 2026-04-23 — The Gathering Hall is Mapped

**Session:** Repo-wide exploration pass.
**Status:** Read-only inventory and attribution phase. No source code was modified.
**Hands on the wheel:** Runa Gridweaver Freyjasdottir (orchestrator) directed the work. Védis Eikleið, the Cartographer, drew the structural maps (`MAP.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`, `DATA_FLOW.md`). I, Eirwyn Rúnblóm, the Scribe, wrote the narrative records: `INVENTORY.md` (the canonical inventory), `ORIGINS.md` (attribution of imported pieces), and this chronicle.

### What was discovered

The repository is, at present, a **gathering hall**, not a finished hall-bench. Volmarr has pulled material together from a constellation of prior projects and staged them beside the genuinely new work — the Mythic Vibe CLI — so that an integration phase can follow.

The shape, in plain terms:

- At the centre sits the new CLI — `mythic_vibe_cli/` — small, deliberate, and the only sub-tree authored *for* this repo. It carries the Mythic Engineering seven-phase workflow (`intent → constraints → architecture → plan → build → verify → reflect`) and a ChatGPT-Plus / Codex copy-paste bridge so that a Plus subscriber can vibe-code without paying for API access.
- Around the CLI, three substantial imports stand almost untouched: `mindspark_thoughtform/` (the MindSpark ThoughtForge project in near-full form), `WYRD-Protocol-.../` (the WYRD Protocol v1.0.0 source, including all twenty engine integrations), and — pulled from the Norse Saga Engine but distributed across several directories — the systems, core, ai, sessions, and yggdrasil trees, plus a thirty-five-thousand-line `config.yaml` whose own header names it as *Norse Saga Engine v8.0.0*.
- Three upstream open-source projects have been vendored whole: `chatterbox/` (TTS), `whisper/` (speech-to-text), and `ollama/` (Go-language LLM server — the source of the repo's 681 Go files, 185 C++ files, and 158 CUDA files).
- The methodology corpus — `Mystic_Engineering_Protocals1.0.md`, `Mythic_Engineers_Codex.md`, `Ada_Lovelace_Explains_Mythic_Engineering.md`, `practical_mythic_engineering_step_by_step.md`, `Quick_Guide_to_Mythic_Engineering_Vibe_Coding.md`, and a 178-kilobyte treatise on the Viking TTRPG Emotional Engine — sits at the root as reference scripture.
- Research and specs are in triplicate: `research_data/` appears identically at the repo root, inside `mindspark_thoughtform/`, and inside `WYRD-Protocol-.../`. The same holds for `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md`, `WORLD_MODELING_SKILL.md`, `PHILOSOPHY.md`, and `RULES.AI.md`. These duplications are catalogued in `ORIGINS.md` so the integration phase can decide whether one canonical copy will suffice.

### What was preserved

- `INVENTORY.md` — a directory-by-directory narrative of what exists, its current function, and its state of completeness.
- `ORIGINS.md` — best-effort attribution for every major piece, indicating the prior project it most likely came from, plus a duplicate register.
- `DEVLOG.md` — this scroll, opened.

Cross-reference Védis's maps for the structural/diagrammatic view; the two sets of records are deliberately non-overlapping.

### Threads still loose

- `core/saga_odin_rag.py` imports `..yggdrasil_core`, which does not exist anywhere in the repository. At least one file arrived in a mid-refactor state. This is flagged in `INVENTORY.md` and `ORIGINS.md` as an orphan import to reconcile in a later phase.
- `diagnostics/` contains a single 46-megabyte `turn_trace.jsonl`. Its provenance (which session, which build, which character) is not declared in-file.
- The repo root's `systems/`, the embedded `imports/norsesaga/systems/`, and NSE's upstream all contain overlapping files (`event_dispatcher.py` appears in both). Which copy is canonical will be an integration-phase decision.
- `yggdrasil/` (earlier NSE-era Yggdrasil, OpenRouter-centric, with paired AI-sidecar markdown on every module) and `WYRD-Protocol-.../src/wyrdforge/ecs/yggdrasil.py` (the WYRD ECS spatial-hierarchy module of the same name) describe *two different Yggdrasils*. They must not be silently merged.

### The seed of the chronicle

This is the first entry. Every future pass — integration decisions, merges, removals, module rewrites — should add a dated entry here, so the living record keeps pace with the living code. Absolute dates only. One entry per session of meaningful work.

_May the record hold._

---

## 2026-04-23 — The Register of Keep and Let Go

**Session:** Second exploration pass — integration-readiness judgement.
**Status:** Read-only source. Only `.md` files written.
**Hands on the wheel:** Runa Gridweaver Freyjasdottir (orchestrator) directed a second pass. Védis Eikleið was commissioned to produce the structural/diagrammatic companions (`IMPACT_integration.md`, `DUPLICATES.md`, `YGGDRASIL_COMPARISON.md`). I, Eirwyn Rúnblóm, composed the narrative judgement — `RECOMMENDATIONS.md` — and added this entry.

### What the deeper reading revealed

The first pass mapped what exists. The second pass asked *what should become of it*, measured against the actual product — the Mythic Vibe CLI, whose sources were read in full during this session (`cli.py`, `workflow.py`, `codex_bridge.py`, `config.py`, `mythic_data.py`, `pyproject.toml`, `README.md`).

Three realisations shape every recommendation now on the table:

- **The CLI is a true island** — it imports nothing outside its own package and the Python stdlib. A keep-or-drop decision on any imported subtree therefore has *zero runtime cost* to the product. The question is entirely one of maintenance surface, distribution weight, and narrative clarity.
- **`pyproject.toml` packages only `mythic_vibe_cli`.** When this project is installed, none of the surrounding corpora ship. They are reference material, not product code — which is a strong structural hint about the author's real intent.
- **The CLI already syncs the canonical Mythic Engineering methodology from GitHub** (`mythic_data.py` pulls from `hrabanazviking/Mythic-Engineering`). A second copy of that methodology sitting at the repo root is therefore a silent duplication that will go stale.

### Recommendations now on the table

Full register is in `RECOMMENDATIONS.md`. In brief:

- **`KEEP AS-IS`** — the CLI package itself (`mythic_vibe_cli/`, `tests/`), the license/notice triad, the methodology-instruction scrolls at root (`PHILOSOPHY.md`, `PROJECT_LAWS.md`, `RULES.AI.md`, and kin), and the seed-chronicle we are writing now.
- **`DROP — DUPLICATE`** (unconditional) — the empty `mindspark_thoughtform/MindSpark_ThoughtForge/` nested shell; one of the two differently-cased copies of the *Emotional Engine Integration Plan for Norse Saga Engine*; the partial `research_data/src/wyrdforge/` shadow.
- **`DROP — UNUSED`** — the 46 MB `diagnostics/turn_trace.jsonl`; NSE-specific config (`config.yaml` = NSE v8.0.0) and schema (`CHARACTER_TEMPLATE_SCHEM.yaml`) at root; `sessions/`; NSE diagnostics entry points at root (`debug_router_integration.py`, `diagnostics.py`); `imports/norsesaga/systems/`.
- **`DEFER — NEEDS VOLMARR`** — the load-bearing decisions: does the CLI run local models (controls `ai/`, `ollama/`, `whisper/`, `chatterbox/`); which Yggdrasil survives (controls `yggdrasil/`, and the choice between NSE-era cognitive router and WYRD ECS hierarchy); is MindSpark/WYRD *incorporated* into this repo or *referenced* from it (controls the two largest subtrees); does the CLI *embody* the methodology or *reference* it (controls the big root-level essay corpus); and the MIT-vs-Apache license discrepancy between `pyproject.toml` and `LICENSE`.

Cross-reference Védis's forthcoming `IMPACT_integration.md` for the structural view of how these calls ripple through the dependency graph, `DUPLICATES.md` for the precise list of redundant files with byte-level evidence where available, and `YGGDRASIL_COMPARISON.md` for the two-Yggdrasils contrast (NSE-era cognitive-routing Yggdrasil at `yggdrasil/` vs the WYRD ECS spatial-hierarchy Yggdrasil at `wyrdforge/ecs/yggdrasil.py`).

### Corrections applied to `ORIGINS.md`

The deeper reading surfaced one missing duplicate and one cleaner attribution; both are noted in the dated corrections block now at the top of `ORIGINS.md`.

### Threads still loose — rolled into the register

The five upstream decisions named above are the only real open questions. Until Volmarr chooses on them, most of the register is `DEFER` not from timidity but from honesty: the calls are genuinely his to make, and pretending otherwise would be a disservice to the record.

### The seed-chronicle now carries two entries

This is the second entry of the exploration phase. The register is laid; the decisions wait. Future entries will mark each integration motion as it is taken — one rune cut at a time.

_May the record hold, and may the choices, when they come, be clear._

## 2026-04-23 — Scribe Sweep: Documentation Polished and Expanded

**Session:** Documentation consolidation and expansion pass.
**Status:** Markdown-only change set across active docs. No runtime Python code modified.
**Hands on the wheel:** Eirwyn Rúnblóm, The Scribe, performed a repository-facing continuity pass focused on the active Mythic Vibe CLI documentation suite.

### What was changed

This session executed a deep rewrite of the active documentation surfaces so they can function as durable, navigable, and contributor-safe records rather than short-form placeholders.

Updated/added artifacts:

- `README.md` — rewritten as a full operator/contributor guide with command orientation, repository posture notes, configuration model, and active-doc map.
- `docs/INDEX.md` — newly added canonical navigation index and maintenance protocol.
- `docs/index.md` — expanded user-facing hub with role-based reading paths.
- `docs/quickstart.md` — expanded onboarding flow with bridge usage and troubleshooting depth.
- `docs/ARCHITECTURE.md` — expanded component contracts, dependency law, risks, and architecture review checklist.
- `docs/DOMAIN_MAP.md` — expanded ownership matrix, dependency boundaries, escalation path, and drift indicators.
- `docs/api.md` — expanded command/module contracts, compatibility policy, and integration examples.
- `docs/SYSTEM_VISION.md` — expanded mission, scope, design principles, UX expectations, and evolution horizons.
- `CHANGELOG.md` — created release-facing history ledger.

### Why it matters

Before this pass, several docs were concise but shallow. The repository now has a clearer archival spine for:

- onboarding new contributors,
- preventing boundary drift in a large monorepo,
- preserving release/session continuity,
- and recovering intent after long pauses.

### Continuity note

This entry marks the beginning of explicit dual-record discipline:

- `DEVLOG.md` for narrative chronology and rationale,
- `CHANGELOG.md` for user/release-facing deltas.

The two records should now evolve together when meaningful behavior or governance changes occur.

_May the record hold._

---

## 2026-04-23 — Scribe Invocation: Continuity Charter and Handoff Ritual

**Session:** Focused documentation-governance hardening pass.
**Status:** Markdown-only updates; repository runtime code untouched.
**Hands on the wheel:** Eirwyn Rúnblóm, responding to a direct Scribe invocation, polished and expanded the active documentation layer with an emphasis on continuity under interruption.

### What was changed in this pass

- `docs/DOCUMENTATION_STANDARDS.md` was created as a formal charter for writing quality, update obligations, drift detection, and archival discipline.
- `docs/SESSION_HANDOFF_TEMPLATE.md` was created as a pragmatic close-out template to preserve rationale and next actions between sessions.
- `docs/INDEX.md` was expanded into a true canonical map with role-based pathways, update matrices, quality gates, and cadence guidance.
- `docs/index.md` was transformed into a compatibility redirect to prevent duplicate authority and future drift.
- `README.md` was updated with a dedicated governance section linking the continuity documents.
- `CHANGELOG.md` was synchronized with this session so user-facing records remain aligned with contributor-facing memory.

### Why this matters now

The earlier documentation sweep made the docs richer; this pass made them more **self-healing**. The project now has explicit rules for how docs remain trustworthy when features, priorities, and maintainers change.

In practical terms, this reduces three recurring failure patterns:

1. **Silent divergence** between command behavior and docs.
2. **Lost intent** after long pauses or handoffs.
3. **Navigation decay** caused by duplicated index surfaces.

### Continuity threads left deliberately open

- The broader monorepo still contains a large volume of historical/reference documentation outside the active CLI spine. A future archival curation pass can classify those files as canonical, reference-only, or frozen history.
- If command surfaces evolve significantly, the next maintainer should validate that `docs/api.md` still matches runtime semantics before release tagging.

_May the memory remain legible when the fire burns low._
