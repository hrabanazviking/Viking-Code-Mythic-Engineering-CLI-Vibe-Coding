# Mythic Vibe CLI Architect Master Plan

**Role posture:** Architect  
**Disposition:** additive overlay, Python-first nucleus, strict adapters, no silent coupling

My ruling is clean: this repository should **not** be fused into one import graph. Your connected Mythic Engineering documents define the method as architecture-first, document-guided, continuity-preserving, and role-based, with the Architect explicitly responsible for domain ownership, boundaries, and refactor strategy. The repo’s own maps then show that the only live product today is `mythic_vibe_cli/`, while the rest of the tree is an archipelago of dormant engines, research corpora, and vendored upstreams. The enduring form is therefore a **federated CLI control plane** in Python, with explicit adapters to legacy islands and external services, not a giant monolithic merge. fileciteturn4file6L1-L1 fileciteturn4file8L1-L1 fileciteturn23file0L1-L1 fileciteturn24file0L1-L1 fileciteturn32file0L1-L1

## Structural reading of the repository

The repository’s own cartography is unusually clear. It describes a hybrid archive plus active product repo, with `mythic_vibe_cli/` as the main runnable product, `tests/` and `docs/` as active support surfaces, and the Norse Saga runtime fragments, `mindspark_thoughtform/`, the WYRD Protocol subtree, and the vendored `ollama/`, `whisper/`, and `chatterbox/` trees as separate dormant or reference islands. The repo-wide architecture map goes further and calls the monorepo “five islands,” explicitly noting that only Island A, the Mythic Vibe CLI, has a working end-to-end path. Packaging confirms the same reading: `pyproject.toml` ships only `mythic_vibe_cli` and binds the `mythic-vibe` and `mythic` entry points to that package. fileciteturn31file0L1-L1 fileciteturn32file0L1-L1 fileciteturn19file0L1-L1

The live product is presently a **scaffold-and-bridge CLI**, not yet a full terminal coding agent. `cli.py` defines the command surface; `workflow.py` creates and updates project artifacts for the seven Mythic phases; `codex_bridge.py` renders a copy/paste packet into `mythic/codex_prompt.md`; `config.py` resolves layered settings; and `mythic_data.py` syncs and imports Mythic method notes from a canonical GitHub source. The active data-flow document is explicit that the current end-to-end route depends on human copy/paste from the generated packet into an external assistant, then a manual return step via `codex-log`; it even names “human bridge fragility” as a current risk. fileciteturn12file0L1-L1 fileciteturn14file0L1-L1 fileciteturn15file0L1-L1 fileciteturn16file0L1-L1 fileciteturn25file0L1-L1 fileciteturn39file0L1-L1

There are also several structural seams already showing strain. `ConfigStore` reads JSON from home, XDG, and project `.mythic-vibe.json` files, but `config set` writes TOML into `mythic/config.toml`, which the loader never reads. `workflow.py` defines a seven-phase loop that includes `architecture`, but the fallback method notes in `mythic_data.py` collapse to six steps and omit that phase entirely. The workflow templates create a generated downstream-project `SYSTEM_VISION.md` at repo root and `docs/DEVLOG.md`, while the source repo’s own active documentation spine uses `docs/SYSTEM_VISION.md` and a root `DEVLOG.md`, which means the product’s **control-plane documentation** and the **workspace documentation it generates for users** are currently interleaved conceptually rather than formally separated. Current tests cover basic scaffolding, config layering, bridge compaction, and a small amount of CLI behavior, but not a direct agent runtime, adapter contracts, or cross-island integration. fileciteturn13file0L1-L1 fileciteturn12file0L1-L1 fileciteturn14file0L1-L1 fileciteturn16file0L1-L1 fileciteturn29file0L1-L1 fileciteturn30file0L1-L1 fileciteturn39file0L1-L1 fileciteturn17file0L1-L1 fileciteturn18file0L1-L1

A second planning note from your connected Drive matters here. It argues for an **additive domain overlay** rather than destructive pruning: existing islands remain in place, while the new framework becomes an orchestrating web over them. That is the correct refactor doctrine for this repo. The hall is too broad, too mixed in lineage, and too rich in legacy experiments to survive a premature “rewrite everything into one package” move. fileciteturn4file7L1-L1

## Architectural decree

The future architecture should be written into `docs/ARCHITECTURE.md` as a four-lane federation.

The **active product lane** remains the packaged Python nucleus. This is where orchestration, command routing, approvals, context assembly, session state, prompt packets, and tests live. The **adapter lane** is new: optional bridges around legacy modules and external services. The **archive lane** contains dormant islands and vendored mirrors that are not imported directly by the product runtime. The **workspace lane** contains the generated artifacts that Mythic Vibe CLI writes into a user’s project. The critical boundary is this: **source-repo governance docs are not the same thing as generated workspace docs**. That distinction needs to become first-class. fileciteturn23file0L1-L1 fileciteturn24file0L1-L1 fileciteturn25file0L1-L1 fileciteturn39file0L1-L1

The execution model should likewise become explicitly tripartite. **Packet mode** preserves the current strength of the tool: a disciplined copy/paste bridge for web-based assistants and low-friction workflows. **Agent mode** adds a direct terminal execution engine with approvals, hooks, checkpoints, worktrees, and model backends. **Hybrid mode** lets the CLI generate a plan and context locally, delegate execution to an attached agent runtime, then write the results back into the continuity ledger. This preserves your beginner-safe bridge while allowing the product to grow into a true terminal agent without discarding the current user promise. fileciteturn25file0L1-L1 fileciteturn39file0L1-L1

The dependency law must also harden. No product-runtime code should import `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, `mindspark_thoughtform/`, or the WYRD tree directly. Those islands may only be reached through explicit adapters declared in the packaged nucleus. Vendored languages stay in their native form. Python remains the orchestration language. Go, C++, and CUDA remain out-of-process or behind service contracts. Markdown, TOML, YAML, and JSON remain first-class artifacts for memory, commands, policy, and state. That law is already latent in the repo’s domain map; it should now become absolute. fileciteturn24file0L1-L1 fileciteturn32file0L1-L1

## Domain map and ownership

This is the ownership law I would write into `docs/DOMAIN_MAP.md`.

| Domain | Owns | Must never own | Primary implementation |
|---|---|---|---|
| `ui` | CLI parsing, REPL/TUI, slash commands, human-facing output, progress status | business rules, direct legacy imports, direct filesystem mutations beyond application services | Python |
| `application` | command handlers, use-case orchestration, compatibility aliases, lifecycle sequencing | provider-specific model calls, vendor process control, persistence internals | Python |
| `kernel` | phases, task intents, approval states, invariants, command contracts, event types | UI concerns, shell execution, network access | Python |
| `workspace` | scaffold generation, Markdown projections, handoff notes, changelog/devlog sync, artifact graph | model routing, repo scanning heuristics | Python + Markdown |
| `context` | repo map, symbol graph, code oracle, document index, diff summarization, compaction logic | shell execution, approvals, state mutation | Python |
| `execution` | patch planning, sandboxing, shell runs, lint/test/typecheck pipeline, worktrees, checkpoints | domain ownership rules, doc templates | Python |
| `agents` | role cards, skill packs, subagent registry, permission profiles, prompt composition | direct file writes outside execution services | Python + Markdown/TOML |
| `integrations` | Git, GitHub, model backends, MCP, plugin host, external services | workflow state truth, domain invariants | Python |
| `legacy_adapters` | optional wrappers for local providers, Yggdrasil, WYRD, ThoughtForge, vendor services | new product logic, direct re-export of unstable legacy APIs | Python |
| `archive` | untouched historical source, vendors, research corpora | live product behavior | native upstream languages + Markdown |

A second table is necessary because the existing five-file core should not simply be “moved.” It should be decomposed.

| Current file | New home | What survives | What changes |
|---|---|---|---|
| `mythic_vibe_cli/cli.py` | `ui/` + `application/commands/` | command names and aliases | file becomes a thin compatibility façade |
| `mythic_vibe_cli/workflow.py` | `kernel/phases.py`, `workspace/scaffold.py`, `workspace/status.py`, `application/checkin.py` | phase logic and scaffold intent | state and projection logic separate cleanly |
| `mythic_vibe_cli/codex_bridge.py` | `context/packet_builder.py`, `agents/prompt_renderer.py` | packet rendering and compaction | packet mode becomes one execution mode among several |
| `mythic_vibe_cli/config.py` | `kernel/settings.py`, `integrations/settings_store.py`, `workspace/migrations.py` | layered precedence | JSON/TOML split removed, migrations added |
| `mythic_vibe_cli/mythic_data.py` | `integrations/method_sources/`, `workspace/method_cache.py` | sync/import intent | hard-coded source becomes pluggable and versioned |

The law for new work is therefore simple. If a feature changes **how a user asks the tool to do something**, it belongs in `ui` or `application`. If it changes **what the loop means**, it belongs in `kernel`. If it changes **what the tool remembers or writes**, it belongs in `workspace`. If it changes **what the tool knows about the repo**, it belongs in `context`. If it changes **how the tool edits, tests, or executes**, it belongs in `execution`. If it changes **how the tool reaches outside itself**, it belongs in `integrations` or `legacy_adapters`.

## Refactor waves

The refactor should proceed in waves, not a single storm front. Your own additive overlay note argues for growth without erasure, while the current documentation charter requires canonical homes, explicit update obligations, and session closure discipline. That combination implies staged extraction with compatibility preserved until the new nucleus is load-bearing. fileciteturn4file7L1-L1 fileciteturn40file0L1-L1 fileciteturn41file0L1-L1

The **first wave** is contract stabilization. Keep the current entry points and aliases, but turn `cli.py` into a façade over a command registry. Unify phase definitions so the kernel, fallback method notes, and generated plan artifacts agree on one sequence. Replace the current JSON-versus-TOML mismatch with a typed settings layer that can **read old JSON, write new TOML, and emit a migration notice once**. Add tests that lock the current command surface before any internal split. This is the wave that removes silent drift without changing the visible product.

The **second wave** is domain extraction. Split `workflow.py` into phase law, workspace projections, and doctor services. Split `codex_bridge.py` into packet collection, packet compaction, and prompt rendering. Move GitHub file-plunder logic out of `cli.py` into an integration adapter. Turn `grimoire` and `db migrate` from placeholders into real systems with manifests and migrations, or explicitly downgrade them to experimental.

The **third wave** is memory reform. Right now state is scattered across `status.json`, generated Markdown, `plugins.json`, `weave.db`, and a method cache. The correct next form is an **event-sourced SQLite control plane** with Markdown and JSON as projections rather than the system of record. The SQLite store should own sessions, checkpoints, approval decisions, artifact hashes, hook runs, and packet generations; `DEVLOG.md`, handoff files, and status summaries become materialized views. fileciteturn25file0L1-L1 fileciteturn12file0L1-L1 fileciteturn14file0L1-L1 fileciteturn16file0L1-L1

The **fourth wave** is context intelligence. Build a repo map, symbol index, dependency graph, doc index, and a read-only **Code Oracle** that can answer questions like “what owns this capability,” “what files define this symbol,” “what invariants mention this path,” and “what changed near this interface.” This is where the product stops being merely a packet generator and becomes an architecture-aware coding substrate.

The **fifth wave** is agent runtime. Introduce role cards for Skald, Architect, Forge Worker, Auditor, Cartographer, and Scribe as actual subagents with tool scopes and memory scopes. Put approvals, hooks, checkpoints, and worktrees under `execution`. Preserve Packet mode. Add Agent mode. Then bind both through one kernel so the same task intent can be executed in either path.

The **sixth wave** is legacy binding. Harvest the most reusable concepts from the dormant islands through adapters rather than direct imports. This is where local models, world-style context packets, cognition retrieval, and external service control become optional power-ups rather than architectural contamination.

The **seventh wave** is top-tier ergonomics. Add an interactive TUI, slash commands, path-scoped instructions, watch mode, plugin SDK, and team-grade governance. Only then should the product claim to stand in the first rank.

## Competitive synthesis

The external feature bar is now set across several different tools, each strong in a different direction. Aider contributes repo maps, an explicit architect/editor split, auto lint/test loops, and watched-file prompting. citeturn6search1turn6search2turn6search0turn6search3

entity["company","Anthropic","ai company"] Claude Code contributes slash commands, custom command files, hooks, hierarchical memory, subagents, and MCP-aware tool routing. citeturn0search0turn1search5turn4search4turn1search4

entity["company","Google","technology company"] Gemini CLI contributes hierarchical `GEMINI.md` context loading, TOML-based custom commands, agent reloads, and resumable project-scoped checkpoints. citeturn2search1turn5search1turn5search0turn5search2turn5search3

entity["company","GitHub","developer platform"] Copilot CLI contributes repository-wide and path-specific instructions, `AGENTS.md`, custom agents, and automatic context compaction. citeturn4search0turn4search1turn4search3turn4search6

entity["company","OpenAI","ai company"] Codex CLI contributes explicit approval modes, local pairing plus cloud delegation, and a broader ecosystem around `AGENTS.md`, hooks, skills, MCP, and plugins. citeturn2search0turn7search2turn8search2turn8search8

The gap, then, is not a missing gimmick. It is a missing **synthesis**. No durable Mythic tool should chase a single competitor’s silhouette. It should combine:
- Aider’s repo intelligence and architect/editor discipline,
- Claude’s hook and subagent depth,
- Gemini’s hierarchical context and checkpoint ergonomics,
- Copilot’s instruction layering and background compaction,
- Codex’s approvals, plugin direction, and direct terminal execution,

and then add what none of them center as a first principle: **Mythic Engineering continuity artifacts, role law, document governance, and architecture-first refactor ritual**. That is the credible path to a genuinely exceptional CLI. fileciteturn4file6L1-L1 fileciteturn4file8L1-L1 fileciteturn40file0L1-L1

Concretely, the command surface should evolve into a layered grammar:
- stable compat commands such as `init`, `imbue`, `status`, `doctor`, `codex-pack`, and `evoke`,
- direct role invocations such as `architect`, `forge`, `audit`, `scribe`, `map`,
- execution commands such as `run`, `verify`, `approve`, `checkpoint`, `resume`,
- integration commands such as `mcp`, `service`, `adapter`, `model`,
- and governance commands such as `handoff`, `changelog`, `decision`.

The differentiator is not only that these commands exist. It is that they all write to the same event ledger, speak the same domain vocabulary, and obey the same boundary law.

## Python-first implementation blueprint

The live package should grow inward, not sideways. Keep `mythic_vibe_cli` as the import root and build the following structure beneath it:

```text
mythic_vibe_cli/
  ui/
    main.py
    repl.py
    tui.py
    slash_commands.py
  application/
    command_bus.py
    commands/
      init.py
      packet.py
      status.py
      doctor.py
      verify.py
      checkpoint.py
      agent.py
  kernel/
    phases.py
    tasks.py
    approvals.py
    events.py
    invariants.py
    settings.py
  workspace/
    scaffold.py
    projections.py
    docs_sync.py
    handoff.py
    changelog.py
  context/
    repomap.py
    symbols.py
    dependency_graph.py
    code_oracle.py
    packet_builder.py
  execution/
    planner.py
    patcher.py
    sandbox.py
    verifier.py
    worktrees.py
    hooks.py
  agents/
    registry.py
    cards.py
    roles/
      skald.py
      architect.py
      forge.py
      auditor.py
      cartographer.py
      scribe.py
  integrations/
    git.py
    github.py
    settings_store.py
    method_sources/
      github_method.py
      local_method.py
  legacy_adapters/
    local_models.py
    yggdrasil_router.py
    wyrd_oracle.py
    thoughtforge.py
    vendor_services.py
  storage/
    sqlite.py
    migrations.py
    checkpoints.py
  plugins/
    loader.py
    manifest.py
```

The kernel should be tiny, typed, and boring in the best sense.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

class ApprovalMode(str, Enum):
    SUGGEST = "suggest"
    GUIDED = "guided"
    AUTONOMOUS = "autonomous"

class MythicRole(str, Enum):
    SKALD = "skald"
    ARCHITECT = "architect"
    FORGE = "forge"
    AUDITOR = "auditor"
    CARTOGRAPHER = "cartographer"
    SCRIBE = "scribe"

@dataclass(frozen=True)
class TaskIntent:
    goal: str
    phase: str
    role: MythicRole
    constraints: tuple[str, ...] = ()
    target_paths: tuple[str, ...] = ()

@dataclass(frozen=True)
class ContextPacket:
    summary: str
    files: tuple[str, ...]
    invariants: tuple[str, ...]
    char_budget: int

class ContextProvider(Protocol):
    def build(self, intent: TaskIntent) -> ContextPacket: ...

class Executor(Protocol):
    def plan(self, intent: TaskIntent, packet: ContextPacket) -> str: ...
    def apply(self, plan: str, *, mode: ApprovalMode) -> list[str]: ...
    def verify(self, intent: TaskIntent) -> list[str]: ...
```

The first direct code reuse should come from `ai/local_providers.py`, because it is already practical: retries, health checks, model listing, and support for Ollama and OpenAI-compatible servers are all there. Harvest it through an adapter, not a direct product import. The same pattern applies to `docs/hardware_profiles.md`: fold that guide into a `ProfileResolver` so local model routing becomes hardware-aware rather than guess-based. fileciteturn33file0L1-L1 fileciteturn42file0L1-L1

```python
from importlib import import_module

class LocalModelGateway:
    def __init__(self, provider_config: dict):
        legacy = import_module("ai.local_providers")
        self._client = legacy.create_local_client({"local_ai": provider_config})

    def complete(self, messages: list[dict[str, str]]) -> str:
        openrouter = import_module("ai.openrouter")
        payload = [
            openrouter.Message(role=item["role"], content=item["content"])
            for item in messages
        ]
        return self._client.complete(payload).content
```

The second reuse should be conceptual and contractual. `yggdrasil/router.py` has the right instinct even if it is not the right dependency surface: **all model calls should flow through one router** that enriches context, logs decisions, and applies shared law before the backend runs. WYRD’s `PassiveOracle` has the right instinct on the read side: a read-only query layer that can assemble an LLM-ready context packet from authoritative state. ThoughtForge has the right instinct for cognition: an optional enhancement layer, not the core of the executable product. Those three should become `ModelGateway`, `CodeOracle`, and `CognitionProvider` inside the new nucleus. fileciteturn34file0L1-L1 fileciteturn37file0L1-L1 fileciteturn35file0L1-L1

The persistence model should become event-first.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class ProjectEvent:
    event_id: str
    event_type: str
    created_at: datetime
    payload: dict[str, Any]

@dataclass(frozen=True)
class ArtifactProjection:
    path: str
    sha256: str
    derived_from: str
    artifact_kind: str
```

From there, `status.json`, `DEVLOG.md`, packet files, handoff files, and changelog entries are all projections. That gives you replay, resumption, deterministic summaries, and a clean checkpoint system without sacrificing human-readable artifacts.

Finally, documentation must be brought under the same law as code. `docs/DOMAIN_MAP.md` should be rewritten to distinguish **source-repo governance domains** from **generated workspace domains** and to add a formal adapter catalog. `docs/ARCHITECTURE.md` should add the three execution modes, the new kernel/application/context/execution split, and the sovereignty rule for legacy islands. `docs/DATA_FLOW.md` should grow beyond the human copy/paste loop and describe packet, agent, and hybrid paths. `docs/api.md` should split stable commands from experimental surfaces. New documents should be added for `ADAPTER_CATALOG.md`, `EXECUTION_MODEL.md`, `SECURITY_MODEL.md`, `PLUGIN_SDK.md`, and `PROVENANCE.md`. That last file matters because the repo already mixes Apache-licensed product code with legacy and auxiliary trees that declare different licensing terms. fileciteturn23file0L1-L1 fileciteturn24file0L1-L1 fileciteturn25file0L1-L1 fileciteturn28file0L1-L1 fileciteturn40file0L1-L1 fileciteturn19file0L1-L1 fileciteturn35file0L1-L1 fileciteturn36file0L1-L1

The final form is plain. The repo stops pretending to be one system and becomes four things under law: a Python control plane, a continuity-preserving workspace memory, an adapter ring around older powers, and an archive that can be mined without infecting the core. That is the shape that will hold.