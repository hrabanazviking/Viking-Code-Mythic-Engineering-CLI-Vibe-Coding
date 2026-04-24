---
title: "Mythic Vibe CLI — Architect Design Plan"
subtitle: "Advanced architecture plan for a Mythic Engineering CLI coding system"
architect: "Rúnhild Svartdóttir — The Architect"
status: "Design Plan / Not Yet Implemented"
repo: "hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding"
branch_assessed: "development"
date: "2026-04-24"
primary_runtime: "Python 3.10+"
active_product_path: "mythic_vibe_cli/"
---

# Mythic Vibe CLI — Architect Design Plan

## 0. Architectural Judgment

The current project already has the correct sacred spine:

```text
intent -> constraints -> architecture -> plan -> build -> verify -> reflect
```

The mistake would be to merely add more commands around this loop. The correct evolution is deeper: **turn Mythic Vibe CLI into a structured engineering kernel that governs AI-assisted coding through artifacts, domain ownership, repository intelligence, verification gates, recoverable memory, and explicit agent handoffs.**

The active runtime must remain small, disciplined, and Python-first. The surrounding monorepo may contain dormant runtime fragments, research islands, and vendor mirrors, but these must not bleed into the product path without declared adapters.

**Dominant design law:**

> `mythic_vibe_cli/` is the living runtime. Everything else is either governance, tests, templates, reference material, or an adapter target.

---

## 1. Current Repository Reading

### 1.1 Active product posture

The repository presents Mythic Vibe CLI as a method-first command-line tool for building software with continuity, architecture, and recoverable memory. It already defines the core loop, a prompt bridge, diagnostics, response logging, config layering, and durable artifacts.

Current load-bearing surfaces:

```text
mythic_vibe_cli/       active Python CLI runtime
tests/                 active verification surface
docs/                  governance, architecture, API, standards, system vision
README.md              product promise and onboarding
pyproject.toml         packaging and script entrypoints
DEVLOG.md              continuity history
CHANGELOG.md           release-facing history
```

### 1.2 Current active modules

```text
mythic_vibe_cli/cli.py           command surface, aliases, dispatch
mythic_vibe_cli/workflow.py      phase lifecycle, artifacts, status, doctor
mythic_vibe_cli/codex_bridge.py  prompt packet generation and compaction
mythic_vibe_cli/config.py        layered JSON config + env overrides
mythic_vibe_cli/mythic_data.py   canonical method sync/import/cache
```

### 1.3 Current strengths

- The loop is clear and memorable.
- The tool writes real files, not vapor-state context.
- The current architecture docs already warn against monorepo ambiguity.
- The product has a beginner-safe surface but room for advanced operators.
- The prompt bridge is simple enough to preserve and powerful enough to evolve.
- The config model is deterministic and easy to inspect.
- Current tests prove several meaningful command paths.

### 1.4 Current weakness pattern

The current tool is still **command-centered**, not **kernel-centered**.

That means:

- `cli.py` owns too much practical dispatch.
- command behavior is not yet expressed through a unified command/result contract.
- diagnostics are useful but shallow.
- prompt packet generation reads a few fixed files rather than a repository-aware context graph.
- plugin registration exists, but plugin execution contracts are not yet real.
- `config set` writes TOML while the actual loader reads JSON, creating a boundary mismatch.
- `db migrate` creates a table, but there is not yet a coherent persistence model.
- there is no symbol-aware code map, domain drift scanner, patchset model, worktree strategy, or agent capability registry.

**Architectural verdict:**

> The project does not need chaos. It needs a kernel.

---

## 2. Target Identity

## Mythic Vibe CLI should become:

A **method-governed AI engineering CLI** that wraps modern vibe coding in a durable, inspectable, refactor-safe process.

It should not merely call AI tools. It should prepare the battlefield, define the boundary, choose the correct agent, produce the task packet, verify the outcome, and preserve the reasoning.

### 2.1 Product class

```text
Category:        AI-assisted engineering CLI
Core method:     Mythic Engineering
Primary runtime: Python
Primary UX:      Terminal-first, docs-first, git-aware
Power layer:     Repository intelligence + agent bridge + verification gates
Memory model:    Durable artifacts + SQLite event log + optional external sync
Safety model:    Explicit boundary law + destructive-action guardrails
```

### 2.2 Design promise

The user should be able to run:

```bash
mythic design --task "Add plugin execution" --role architect
mythic packet --agent codex --task "Implement the approved plan"
mythic verify --gate full
mythic reflect --summary "Plugin execution added with tests"
```

…and the tool should produce:

- an architecture-aware task packet,
- relevant code/docs context,
- a domain ownership declaration,
- expected file changes,
- verification commands,
- a durable handoff record,
- optional agent-specific exports for Codex, Claude Code, OpenCode, Aider, or local models.

---

## 3. The New Architecture

## 3.1 Layered system shape

```text
User / Shell
  -> CLI Shell Layer
    -> Command Registry
      -> Mythic Kernel
        -> Project Context
        -> Artifact Engine
        -> Phase Engine
        -> Context Engine
        -> Agent Bridge
        -> Verification Engine
        -> Governance Engine
        -> Persistence/Event Log
          -> Filesystem artifacts
          -> SQLite state
          -> Git history/worktrees
          -> Optional external tools
```

### 3.2 Proposed package structure

```text
mythic_vibe_cli/
  __init__.py
  cli.py                         # compatibility wrapper only

  cli/
    __init__.py
    app.py                       # parser creation + top-level command binding
    output.py                    # human-readable terminal output
    errors.py                    # CLI exception rendering

  kernel/
    __init__.py
    context.py                   # ProjectContext, RuntimeContext
    result.py                    # CommandResult, DiagnosticResult
    paths.py                     # canonical path resolver
    events.py                    # event model for continuity log
    clock.py                     # testable time source
    errors.py                    # domain exceptions

  method/
    __init__.py
    phases.py                    # Mythic phases, transitions, gates
    ritual_engine.py             # loop execution orchestration
    rules.py                     # method invariants and anti-drift rules

  artifacts/
    __init__.py
    manifest.py                  # artifact registry + schema
    reader.py                    # safe artifact reads
    writer.py                    # atomic writes + backups
    migrations.py                # artifact upgrades
    templates.py                 # init templates

  context/
    __init__.py
    scanner.py                   # repo scan and ignore rules
    repomap.py                   # compact repository map
    symbols.py                   # optional tree-sitter/ctags/LSP symbol extraction
    relevance.py                 # task-to-file ranking
    budget.py                    # packet budget and excerpt policy
    selectors.py                 # context selector strategies

  agents/
    __init__.py
    roles.py                     # Architect, Auditor, Scribe, Forge Worker, etc.
    registry.py                  # agent profile registry
    packets.py                   # generic packet model
    codex.py                     # Codex/ChatGPT packet renderer
    claude.py                    # Claude Code packet/slash-command renderer
    opencode.py                  # OpenCode session prompt renderer
    aider.py                     # Aider-oriented file/context guidance
    local.py                     # local model packet renderer

  vcs/
    __init__.py
    git.py                       # git status, diff, commit metadata
    worktree.py                  # isolated branch/worktree support
    patchset.py                  # patch intent and review metadata

  diagnostics/
    __init__.py
    doctor.py                    # structural diagnostics
    boundary.py                  # import/domain boundary scanner
    docs_drift.py                # docs-vs-runtime drift scanner
    config_doctor.py             # config mismatch detection
    security.py                  # token/secrets/destructive command checks

  persistence/
    __init__.py
    db.py                        # SQLite connection and migrations
    schema.sql                   # event/task/artifact schema
    repositories.py              # typed DB access

  plugins/
    __init__.py
    spec.py                      # plugin protocol
    manager.py                   # register/list/load/execute
    sandbox.py                   # plugin trust and permission boundaries

  integrations/
    __init__.py
    mcp.py                       # optional MCP server/client surface
    github.py                    # GitHub metadata helpers
    lsp.py                       # optional LSP integration
    external_cli.py              # subprocess adapters for aider/opencode/codex/etc.

  commands/
    __init__.py
    init.py
    status.py
    checkin.py
    doctor.py
    config.py
    packet.py
    scan.py
    map.py
    design.py
    verify.py
    reflect.py
    worktree.py
    plugin.py
    db.py
```

### 3.3 Why this structure is stronger

The current `cli.py` should become a stable compatibility surface, not the place where the system keeps growing.

The new shape separates:

| Concern | Owner |
|---|---|
| Command parsing | `cli/app.py` |
| Command behavior | `commands/*` |
| Project state | `kernel/context.py` |
| Durable files | `artifacts/*` |
| Mythic loop law | `method/*` |
| Repository intelligence | `context/*` |
| Agent interoperability | `agents/*` |
| Git/worktree safety | `vcs/*` |
| Drift detection | `diagnostics/*` |
| Persistence | `persistence/*` |
| Extensibility | `plugins/*` |

This gives the codebase load-bearing order.

---

## 4. Core Runtime Objects

The tool should stop passing loose `Path` and `argparse.Namespace` objects deep into behavior. Define exact runtime contracts.

### 4.1 `ProjectContext`

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectContext:
    root: Path
    docs_dir: Path
    tasks_dir: Path
    mythic_dir: Path
    config_file: Path
    status_file: Path
    db_file: Path

    @classmethod
    def from_root(cls, root: Path) -> "ProjectContext":
        root = root.resolve()
        return cls(
            root=root,
            docs_dir=root / "docs",
            tasks_dir=root / "tasks",
            mythic_dir=root / "mythic",
            config_file=root / ".mythic-vibe.json",
            status_file=root / "mythic" / "status.json",
            db_file=root / "mythic" / "weave.db",
        )
```

### 4.2 `CommandResult`

Every command should return a typed result. The CLI renderer prints it. Tests assert it.

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class CommandResult:
    ok: bool
    title: str
    summary: str = ""
    created: list[Path] = field(default_factory=list)
    changed: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    exit_code: int = 0
```

### 4.3 `Diagnostic`

```python
from dataclasses import dataclass
from enum import Enum

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    path: str | None = None
    fix: str | None = None
```

### 4.4 `AgentRole`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class AgentRole:
    key: str
    title: str
    focus: str
    allowed_outputs: tuple[str, ...]
    forbidden_behaviors: tuple[str, ...]
    packet_bias: tuple[str, ...]
```

Built-in roles:

```text
architect      boundaries, ownership, refactor strategy
auditor        verification, tests, risk, drift detection
scribe         docs, continuity, changelog, handoff
forge-worker   implementation, patch planning, build steps
cartographer   repo maps, file routes, dependency paths
seer           planning, uncertainty, model/provider selection
```

### 4.5 `ContextPacket`

```python
from dataclasses import dataclass, field

@dataclass
class ContextPacket:
    task: str
    phase: str
    role: str
    audience: str
    status_snapshot: str
    selected_files: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    verification: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
```

---

## 5. Command Surface: Final Form

The tool should keep current commands for compatibility but introduce a cleaner advanced surface.

## 5.1 Compatibility commands to preserve

```text
init / imbue
codex-pack / evoke
codex-log
checkin
status
doctor / scry
sync
method
weave
prune
heal
oath
grimoire add|list
config set
config
db migrate
plunder
```

## 5.2 New advanced command families

### Project and method

```bash
mythic init --goal "..." --profile beginner|standard|advanced
mythic adopt --path . --goal "..."
mythic status --json
mythic phase next
mythic phase set architecture --reason "Boundary unclear"
```

### Repository intelligence

```bash
mythic scan
mythic map --format md
mythic symbols --changed
mythic relevant --task "Add plugin execution"
```

### Architecture and planning

```bash
mythic design --task "Add plugin execution" --role architect
mythic plan --task "Implement context index" --milestones 5
mythic boundary check
mythic boundary explain mythic_vibe_cli/cli.py
```

### Agent bridge

```bash
mythic packet --agent codex --task "Implement scanner" --role forge-worker
mythic packet --agent claude-code --task "Refactor command registry" --role architect
mythic packet --agent aider --task "Patch tests" --files mythic_vibe_cli/workflow.py tests/test_cli.py
mythic packet --agent opencode --task "Explore repo map strategy"
```

### Verification

```bash
mythic verify --gate smoke
mythic verify --gate full
mythic verify --changed
mythic doctor --strict
mythic drift docs
mythic drift imports
```

### Continuity

```bash
mythic reflect --summary "Command registry extracted"
mythic handoff --next "Implement plugin sandbox"
mythic memory list
mythic memory show latest
```

### Git/worktree orchestration

```bash
mythic worktree create plugin-execution
mythic worktree list
mythic patchset summary
mythic patchset review
```

### Plugins

```bash
mythic plugin add package.module:Plugin
mythic plugin list
mythic plugin run repo-audit
mythic plugin doctor
```

---

## 6. Repository Intelligence Engine

This is the major power upgrade.

Current prompt packets read fixed docs. The advanced version should build a **task-specific context map**.

### 6.1 Context engine duties

```text
1. Scan repository files.
2. Respect .gitignore and tool-specific ignore patterns.
3. Classify files by domain.
4. Extract language/symbol summaries where possible.
5. Rank files against the task.
6. Build token/character-budgeted packet sections.
7. Preserve explicit truncation notices.
8. Emit a machine-readable context manifest.
```

### 6.2 Suggested scan output

```json
{
  "root": ".",
  "generated_at": "2026-04-24T00:00:00Z",
  "domains": {
    "product_cli": ["mythic_vibe_cli/cli.py", "mythic_vibe_cli/workflow.py"],
    "tests": ["tests/test_cli.py"],
    "governance_docs": ["docs/ARCHITECTURE.md", "docs/DOMAIN_MAP.md"]
  },
  "warnings": [
    "Vendor mirror ignored: ollama/",
    "Dormant island ignored unless explicit adapter requested: yggdrasil/"
  ]
}
```

### 6.3 Initial implementation strategy

Start stdlib-first:

```python
from pathlib import Path

DEFAULT_IGNORES = {
    ".git", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", "node_modules", "dist", "build",
    "ollama", "whisper", "chatterbox",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
    ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".rb",
    ".php", ".sh", ".ps1", ".md", ".toml", ".json", ".yaml", ".yml",
}

def iter_project_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & DEFAULT_IGNORES:
            continue
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS:
            files.append(path)
    return sorted(files)
```

Later, add optional accelerators:

```text
ripgrep      fast text search
tree-sitter  language-aware symbol extraction
ctags        fallback symbol index
LSP          project-native diagnostics and symbol maps
SQLite FTS5  local semantic-ish text search without cloud dependency
embeddings   optional advanced mode, never mandatory
```

### 6.4 Repository map format

Create:

```text
mythic/repo_map.md
mythic/repo_map.json
mythic/context_index.sqlite
```

The Markdown map is human-readable. The JSON/SQLite forms are for agents and command logic.

---

## 7. Artifact Engine

The current scaffold writes files directly from `workflow.py`. That is acceptable for v0.1, but the advanced system needs an artifact registry.

### 7.1 Artifact manifest

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ArtifactSpec:
    key: str
    path: str
    required: bool
    owner: str
    purpose: str
    schema_version: int = 1
```

Example registry:

```python
ARTIFACTS = [
    ArtifactSpec("system_vision", "SYSTEM_VISION.md", True, "method", "Defines project purpose"),
    ArtifactSpec("architecture", "docs/ARCHITECTURE.md", True, "governance", "Defines active system architecture"),
    ArtifactSpec("domain_map", "docs/DOMAIN_MAP.md", True, "governance", "Defines domain ownership"),
    ArtifactSpec("status", "mythic/status.json", True, "method", "Tracks phase state"),
    ArtifactSpec("repo_map", "mythic/repo_map.md", False, "context", "Repository map for packets"),
    ArtifactSpec("handoff", "mythic/handoff.md", False, "continuity", "End-of-session transfer note"),
]
```

### 7.2 Atomic writes

Every write to status, packets, maps, and logs should be atomic.

```python
from pathlib import Path
import tempfile
import os

def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)
```

### 7.3 Artifact migration

`mythic/status.json` should gain a version field.

```json
{
  "schema_version": 2,
  "goal": "...",
  "current_phase": "architecture",
  "completed_phases": ["intent", "constraints", "architecture"],
  "last_update": "2026-04-24T00:00:00Z",
  "history": [],
  "active_task": null,
  "verification": {
    "last_gate": null,
    "last_result": null
  }
}
```

---

## 8. Agent Bridge System

The existing `codex_bridge.py` should become the first renderer in a general agent bridge.

### 8.1 Agent adapters

```text
Codex / ChatGPT renderer
  -> structured paste packet
  -> explicit output format
  -> verification and check-in template

Claude Code renderer
  -> architecture packet
  -> slash command compatible blocks
  -> optional hook recommendations

OpenCode renderer
  -> model/provider-neutral terminal agent packet
  -> multi-session/worktree guidance

Aider renderer
  -> file selection guidance
  -> architect/editor split prompts
  -> test/lint loop instructions

Local model renderer
  -> smaller context budgets
  -> explicit local limitations
  -> compact symbol maps
```

### 8.2 Generic adapter protocol

```python
from typing import Protocol

class AgentRenderer(Protocol):
    key: str

    def render(self, packet: ContextPacket) -> str:
        ...
```

### 8.3 Renderer registry

```python
class AgentRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, AgentRenderer] = {}

    def register(self, renderer: AgentRenderer) -> None:
        self._renderers[renderer.key] = renderer

    def get(self, key: str) -> AgentRenderer:
        try:
            return self._renderers[key]
        except KeyError as exc:
            valid = ", ".join(sorted(self._renderers))
            raise ValueError(f"Unknown agent renderer '{key}'. Valid: {valid}") from exc
```

### 8.4 The Architect packet should be stricter

When the role is `architect`, generated packets should demand:

```text
1. State exact domain ownership.
2. Name files likely affected.
3. Declare forbidden imports/couplings.
4. Define invariants.
5. Propose smallest refactor boundary.
6. Give tests and docs that must change together.
7. Return a check-in sentence.
```

---

## 9. Verification Engine

The current README already recommends:

```bash
pytest -q
python -m mythic_vibe_cli.cli --help
mythic-vibe doctor
```

Turn this into named gates.

### 9.1 Verification gates

```text
smoke:
  - python -m mythic_vibe_cli.cli --help
  - mythic-vibe doctor

unit:
  - pytest -q

docs:
  - mythic drift docs
  - mythic boundary check

full:
  - smoke
  - unit
  - docs
  - import-cycle scan
  - packaging metadata check
```

### 9.2 Gate config

```json
{
  "verification": {
    "gates": {
      "smoke": [
        "python -m mythic_vibe_cli.cli --help",
        "mythic-vibe doctor"
      ],
      "unit": ["pytest -q"]
    }
  }
}
```

### 9.3 Verification result model

```python
@dataclass
class VerificationRun:
    gate: str
    command: str
    exit_code: int
    stdout_excerpt: str
    stderr_excerpt: str
    duration_ms: int
```

Persist results into SQLite and summarize into `mythic/verification.md`.

---

## 10. Boundary and Drift Law

The strongest thing this project already knows is that boundaries matter. Make that executable.

### 10.1 Boundary scanner

Detect forbidden imports:

```python
import ast
from pathlib import Path

FORBIDDEN_TOP_LEVEL_IMPORTS = {
    "ai", "core", "systems", "sessions", "yggdrasil",
    "ollama", "whisper", "chatterbox", "mindspark_thoughtform",
}

def scan_python_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_TOP_LEVEL_IMPORTS:
                    violations.append(f"{path}: forbidden import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top in FORBIDDEN_TOP_LEVEL_IMPORTS:
                violations.append(f"{path}: forbidden import from {node.module}")
    return violations
```

### 10.2 Docs/runtime drift scanner

Check that commands listed in `docs/api.md` exist in the parser.

```text
mythic drift docs
  -> parse CLI help
  -> parse documented commands
  -> report documented-but-missing
  -> report implemented-but-undocumented
```

### 10.3 Config drift scanner

Current issue to fix:

```text
ConfigStore reads:
  ~/.mythic-vibe.json
  $XDG_CONFIG_HOME/mythic-vibe/config.json
  <project>/.mythic-vibe.json

config set writes:
  mythic/config.toml
```

This is a boundary mismatch. Correct options:

**Option A — JSON purity:**

```bash
mythic config set codex.excerpt_limit 2200
# writes <project>/.mythic-vibe.json
```

**Option B — TOML upgrade:**

Adopt `tomllib` for reads and write `mythic/config.toml` intentionally.

Recommended: **Option A first.** Preserve simple JSON until a full config schema exists.

---

## 11. Persistence Model

SQLite should stop being symbolic and become the durable event spine.

### 11.1 Tables

```sql
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  phase TEXT,
  summary TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  phase TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  owner_role TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT NOT NULL,
  path TEXT NOT NULL,
  schema_version INTEGER NOT NULL DEFAULT 1,
  last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(key, path)
);

CREATE TABLE IF NOT EXISTS verification_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  gate TEXT NOT NULL,
  command TEXT NOT NULL,
  exit_code INTEGER NOT NULL,
  stdout_excerpt TEXT,
  stderr_excerpt TEXT,
  duration_ms INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS context_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL UNIQUE,
  domain TEXT,
  language TEXT,
  size_bytes INTEGER,
  sha256 TEXT,
  summary TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 11.2 Event examples

```json
{
  "event_type": "phase.checkin",
  "phase": "architecture",
  "summary": "Defined plugin execution boundary",
  "payload": {
    "changed_files": ["docs/DOMAIN_MAP.md", "mythic_vibe_cli/plugins/spec.py"]
  }
}
```

---

## 12. Plugin System

The current `grimoire` command registers plugin strings. Evolve it into a real plugin law.

### 12.1 Plugin protocol

```python
from typing import Protocol

class MythicPlugin(Protocol):
    name: str
    version: str

    def describe(self) -> str:
        ...

    def run(self, context: ProjectContext, args: dict[str, str]) -> CommandResult:
        ...
```

### 12.2 Plugin manifest

```json
{
  "plugins": [
    {
      "name": "repo-audit",
      "entrypoint": "mythic_repo_audit:Plugin",
      "enabled": true,
      "permissions": ["read_project", "write_mythic_artifacts"]
    }
  ]
}
```

### 12.3 Permission model

```text
read_project
write_mythic_artifacts
write_docs
run_commands
network
modify_source
```

Default plugin permissions should be read-only.

---

## 13. Git and Worktree Strategy

Advanced vibe coding needs isolation. Agents should not collide in one working tree.

### 13.1 Worktree design

```bash
mythic worktree create plugin-execution --base development
```

Creates:

```text
../Viking-Code-Mythic-Engineering-CLI-Vibe-Coding-plugin-execution/
branch: mythic/plugin-execution
handoff: mythic/worktrees/plugin-execution.md
```

### 13.2 Why worktrees matter

- Parallel agent sessions do not trample each other.
- Refactors become isolated experiments.
- Failed agent edits can be abandoned cleanly.
- Each task can carry its own plan, verification, and reflection.

### 13.3 Patchset summary

```bash
mythic patchset summary
```

Outputs:

```text
Branch: mythic/plugin-execution
Changed files:
- mythic_vibe_cli/plugins/spec.py
- mythic_vibe_cli/plugins/manager.py
- tests/test_plugins.py

Required docs:
- docs/api.md
- docs/DOMAIN_MAP.md
- CHANGELOG.md
```

---

## 14. External CLI App Wisdom to Absorb

Do not copy other tools blindly. Take their strongest structural lessons and make them Mythic.

### 14.1 From Codex CLI

Absorb:

- local repo operation,
- approvals workflow,
- sandbox consciousness,
- multimodal task packet idea,
- fast handoff from human intent to code action.

Mythic adaptation:

```text
Codex acts as Forge Worker or Auditor.
Mythic Vibe CLI owns task framing, boundaries, packet construction, and continuity logging.
```

### 14.2 From Claude Code

Absorb:

- hooks,
- lifecycle events,
- slash commands,
- pre/post tool-use governance,
- subagent and session event concepts.

Mythic adaptation:

```text
Mythic hooks become method gates:
- before editing: boundary check
- after editing: artifact drift check
- before completion: verification gate
- session end: handoff generation
```

### 14.3 From Aider

Absorb:

- repo map,
- git-native workflow,
- architect/editor split,
- lint/test feedback loop,
- multi-file edit awareness.

Mythic adaptation:

```text
The Architect creates the domain-safe design.
The Forge Worker applies the smallest patch.
The Auditor verifies.
The Scribe records continuity.
```

### 14.4 From OpenCode

Absorb:

- provider-neutral model strategy,
- multi-session operation,
- terminal/desktop/IDE presence,
- LSP-aware context.

Mythic adaptation:

```text
Mythic Vibe CLI remains the method kernel that can feed OpenCode sessions with exact role packets and repository maps.
```

---

## 15. Refactor Roadmap

## Phase 0 — Stabilize Current Runtime

Goal: protect current behavior before expansion.

Tasks:

- Add golden tests for `--help` output.
- Add tests for `init`, `checkin`, `status`, `doctor`, `codex-pack`, `config`.
- Add a fixture project generator for tests.
- Fix `config set` mismatch.
- Add `schema_version` to `mythic/status.json`.
- Ensure `python -m mythic_vibe_cli.cli --help` and installed scripts match.

Verification:

```bash
pytest -q
python -m mythic_vibe_cli.cli --help
```

## Phase 1 — Extract Kernel

Goal: move behavior out of `cli.py` without breaking commands.

Tasks:

- Create `kernel/context.py`.
- Create `kernel/result.py`.
- Create `cli/output.py`.
- Move command functions into `commands/*` one at a time.
- Keep `cli.py` as the compatibility entrypoint.

Boundary rule:

> No command module may own global project paths directly. It receives `ProjectContext`.

## Phase 2 — Artifact Engine

Goal: make scaffold and diagnostics registry-driven.

Tasks:

- Add `artifacts/manifest.py`.
- Replace hardcoded doctor required-file list with manifest.
- Add artifact schema versions.
- Add atomic writes.
- Add backup-on-migration behavior.

## Phase 3 — Repository Scanner and Map

Goal: create local project intelligence.

Tasks:

- Add `context/scanner.py`.
- Add `context/repomap.py`.
- Add `mythic scan`.
- Add `mythic map`.
- Persist `mythic/repo_map.md` and `mythic/repo_map.json`.
- Ignore vendor/dormant islands by default, unless `--include-dormant` is passed.

## Phase 4 — Agent Bridge Generalization

Goal: turn Codex bridge into multi-agent bridge.

Tasks:

- Add `agents/packets.py`.
- Move current Codex packet renderer into `agents/codex.py`.
- Add `--agent` and `--role` to packet generation.
- Add role registry.
- Preserve `codex-pack` as alias to `packet --agent codex`.

## Phase 5 — Verification Gates

Goal: make testing a first-class method phase.

Tasks:

- Add `mythic verify --gate smoke|unit|docs|full`.
- Store run results.
- Add `mythic/verification.md`.
- Let packet generation include last verification status.

## Phase 6 — Boundary Scanner

Goal: enforce domain law automatically.

Tasks:

- Add Python import scanner.
- Add docs/runtime command drift scanner.
- Add config drift scanner.
- Add `mythic boundary check`.
- Add `mythic drift docs`.

## Phase 7 — Worktrees and Patchsets

Goal: support parallel AI work safely.

Tasks:

- Add git adapter.
- Add `mythic worktree create/list/remove`.
- Add `mythic patchset summary`.
- Add patchset review prompt generation.

## Phase 8 — Plugin Execution

Goal: evolve `grimoire` from registry to plugin runtime.

Tasks:

- Define plugin protocol.
- Add permission model.
- Add plugin doctor.
- Add plugin run command.
- Document plugin API.

## Phase 9 — Optional MCP/LSP Layer

Goal: expose Mythic capabilities to external agent tools.

Tasks:

- Add optional MCP server exposing:
  - `mythic_status`
  - `mythic_repo_map`
  - `mythic_make_packet`
  - `mythic_verify`
  - `mythic_checkin`
- Add LSP diagnostics import when available.

Keep this optional. Do not make MCP or LSP required for the core CLI.

---

## 16. Documentation Update Plan

Every architectural phase must update docs in the same commit.

### Required doc changes

| Change | Docs to update |
|---|---|
| New command | `docs/api.md`, `README.md` command overview |
| New domain | `docs/DOMAIN_MAP.md`, `docs/ARCHITECTURE.md` |
| New artifact | `docs/DATA_FLOW.md`, `docs/api.md` |
| New config key | `docs/api.md`, `docs/quickstart.md` |
| New verification gate | `docs/api.md`, `docs/DOCUMENTATION_STANDARDS.md` |
| Breaking behavior | `CHANGELOG.md`, `DEVLOG.md`, migration notes |

### New docs to add

```text
docs/ADVANCED_ARCHITECTURE_PLAN.md
docs/AGENT_BRIDGE.md
docs/CONTEXT_ENGINE.md
docs/VERIFICATION_GATES.md
docs/PLUGIN_API.md
docs/WORKTREE_STRATEGY.md
docs/BOUNDARY_LAW.md
```

---

## 17. Test Strategy

### 17.1 Unit tests

```text
tests/test_context.py
tests/test_artifacts.py
tests/test_config.py
tests/test_phases.py
tests/test_packets.py
tests/test_boundary.py
tests/test_plugins.py
tests/test_verification.py
```

### 17.2 CLI tests

Use both direct `main([...])` tests and subprocess tests.

```python
import subprocess
import sys

def test_module_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "mythic_vibe_cli.cli", "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "mythic-vibe" in result.stdout
```

### 17.3 Golden packet tests

Generated prompt packets should be snapshot-tested with stable time injected.

```text
tests/golden/codex_packet_architect.md
tests/golden/claude_packet_auditor.md
tests/golden/aider_packet_forge_worker.md
```

### 17.4 Integration tests

Use temporary git repos.

```text
- initialize repo
- run mythic init
- create sample source files
- run mythic scan
- generate packet
- run doctor
- run verify smoke
```

---

## 18. Security and Trust Boundaries

### 18.1 Secrets

- Never print tokens.
- Never write API keys into packets.
- Scan `.env`, config, and shell history references before packet export.
- Redact common secret patterns.

### 18.2 Destructive actions

Require explicit confirmation flags for:

```text
file deletion
branch deletion
worktree removal
plugin execution with write permission
network sync from untrusted source
```

### 18.3 AI authority boundary

Packets should preserve user sovereignty:

```text
The assistant may propose changes.
The user or local command policy approves execution.
The repository remains the source of truth.
No hidden state outranks files.
```

---

## 19. Performance Design

### 19.1 Keep default fast

Default commands should avoid full repository scanning unless requested.

```text
status       reads status only
doctor       checks manifest + shallow config
scan         explicit full scan
packet       uses existing scan if fresh; otherwise shallow fallback
verify       only runs chosen gate
```

### 19.2 Incremental context index

Use file metadata and hash.

```python
@dataclass
class FileFingerprint:
    path: str
    size: int
    mtime_ns: int
    sha256: str | None = None
```

Only hash when size/mtime changed.

### 19.3 Packet budget policy

```text
Tier 1: status, task, phase, domain law
Tier 2: selected current files
Tier 3: architecture/domain docs
Tier 4: repo map excerpts
Tier 5: devlog/changelog excerpts
```

Never let historical logs crowd out current task files.

---

## 20. Exact First Implementation Tickets

### Ticket 1 — Fix config writer/loader mismatch

**Files:**

```text
mythic_vibe_cli/cli.py
mythic_vibe_cli/config.py
tests/test_cli.py
docs/api.md
CHANGELOG.md
DEVLOG.md
```

**Decision:** `config set` writes `<project>/.mythic-vibe.json`.

### Ticket 2 — Add ProjectContext

**Files:**

```text
mythic_vibe_cli/kernel/context.py
mythic_vibe_cli/kernel/__init__.py
mythic_vibe_cli/cli.py
tests/test_context.py
```

### Ticket 3 — Add CommandResult and output renderer

**Files:**

```text
mythic_vibe_cli/kernel/result.py
mythic_vibe_cli/cli/output.py
mythic_vibe_cli/cli.py
tests/test_output.py
```

### Ticket 4 — Extract doctor into diagnostics

**Files:**

```text
mythic_vibe_cli/diagnostics/doctor.py
mythic_vibe_cli/artifacts/manifest.py
mythic_vibe_cli/workflow.py
mythic_vibe_cli/cli.py
tests/test_doctor.py
```

### Ticket 5 — Add repository scanner

**Files:**

```text
mythic_vibe_cli/context/scanner.py
mythic_vibe_cli/context/repomap.py
mythic_vibe_cli/commands/scan.py
mythic_vibe_cli/commands/map.py
tests/test_scanner.py
docs/CONTEXT_ENGINE.md
```

### Ticket 6 — Generalize CodexBridge

**Files:**

```text
mythic_vibe_cli/agents/packets.py
mythic_vibe_cli/agents/registry.py
mythic_vibe_cli/agents/codex.py
mythic_vibe_cli/codex_bridge.py
tests/test_packets.py
docs/AGENT_BRIDGE.md
```

---

## 21. Non-Negotiable Invariants

1. `mythic_vibe_cli/` remains independently executable.
2. Dormant islands are not imported directly into active runtime.
3. Vendor mirrors are never active product dependencies.
4. Every advanced action leaves an artifact trail.
5. Every generated packet declares phase, role, task, constraints, and verification.
6. Every meaningful behavior change updates docs.
7. Config reads and writes must share one real contract.
8. AI handoff is explicit; hidden memory must never override files.
9. Verification failure must be visible, not swallowed.
10. The Mythic loop remains the spine.

---

## 22. Final Architecture Statement

Mythic Vibe CLI should become the **ritual operating system for AI-assisted engineering**: a Python-first command-line kernel that binds human intent, AI execution, repository structure, verification, and continuity into one durable method.

The path is not to make it louder.

The path is to make it lawful.

Build the kernel. Enforce the boundaries. Map the repo. Generate the packet. Verify the work. Preserve the memory.

That is how this tool becomes more than another agent wrapper.

That is how it becomes Mythic Engineering in executable form.
