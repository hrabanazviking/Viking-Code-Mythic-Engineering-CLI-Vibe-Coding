# HJARTAFORGUN — The Heart-Forging
## A Complete Design Plan for the Most Advanced Mythic Engineering CLI in Existence

**Primary Owner:** Rúnhild Svartdóttir, The Architect  
**Repository:** `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`  
**Date:** April 24, 2026  
**Status:** Canonical Design Blueprint — Phase 0 Entry  
**Companion Scrolls:** `DOMAIN_MAP.md`, `ARCHITECTURE.md`, `DATA_FLOW.md`, `ARCHITECT_REFACTOR_BLUEPRINT.md`, `CODE_REQUIREMENTS_MATRIX.md`, `ROBUSTNESS_ADVANCEMENT_ROADMAP.md`, `VÖLUSPÁ_CLI_VISION.md`

---

## Preamble: The Law of the Forge

This document is not a wish-list. It is a structural mandate. Every line here answers one of three questions:

1. **Where does the capability belong?** — domain ownership, bounded context, layer assignment.
2. **What is the exact contract?** — interfaces, data shapes, protocol boundaries.
3. **How does it survive scale?** — hardening trajectory, migration pathway, verification gate.

The target is to transform the current five-island sprawl into a single, sovereign, layered monolith — *Völuspá CLI* — that holds the complete wisdom of all vibe-coding tools ever built. The method is **Mythic Engineering**. The engine is **Python**, with Rust acceleration where throughput demands it. The architecture is sacred geometry, not sprawl.

No feature enters the forge without a domain, a contract, and a hardening path. Nothing is added until it can be defended.

---

## ᛉ 0. Architectural Principles (Non-Negotiable)

These govern every decision that follows. Violate them and the structure rots.

| Principle | Definition | Enforcement |
|---|---|---|
| **Stability Before Expansion** | The active product (`mythic_vibe_cli`) remains unbroken through every phase. | Regression gate before any merge. |
| **Contracts Before Coupling** | Define API/event contracts before code reuse across domains. | Interface stubs must exist before implementation. |
| **One-Way Dependencies** | Upper layers depend on lower layers; never the reverse. | Static import boundary checker in CI. |
| **Delete Ambiguity** | Every module has one owner and one purpose. | Domain map must show exactly one owner per file. |
| **Prove With Checks** | Each phase has explicit verification gates. | Documented exit criteria per phase; gate script per domain. |
| **Method-First** | The Mythic Engineering loop (`intent → constraints → architecture → plan → build → verify → reflect`) is the spine of every workflow. | Every command that mutates must log phase transition. |

---

## ᛏ I. Domain Architecture — The Eight Pillars

The current five-island model is refactored into a single coherent system of **eight bounded contexts**, each with hard ownership, explicit contracts, and layered placement.

```
┌──────────────────────────────────────────────────────────┐
│                    UI LAYER (Presentation)                │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ CLI Router   │  │ Web Terminal │  │ Mobile / SSH  │  │
│  │ (argparse)   │  │ (aiohttp)    │  │ (adapters)    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
├─────────┼─────────────────┼───────────────────┼──────────┤
│         ▼                 ▼                   ▼          │
│              WORKFLOW LAYER (Orchestration)               │
│  ┌──────────────────────────────────────────────────┐    │
│  │              MythicLoop (state machine)            │    │
│  │  intent → constraints → architecture → plan       │    │
│  │              → build → verify → reflect            │    │
│  └──────────┬───────────────────────┬───────────────┘    │
│             │                       │                     │
├─────────────┼───────────────────────┼─────────────────────┤
│             ▼                       ▼                     │
│            DOMAIN LAYER (Bounded Contexts)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Codex    │ │ Forge     │ │ Wardr    │ │ Seidr       │  │
│  │ Bridge   │ │ (Code Gen)│ │ (Security)│ │ (Test/QA)  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬─────┘  │
│       │             │             │               │       │
│  ┌────┴─────────────┴─────────────┴───────────────┴────┐ │
│  │              Mímir (Context & Memory)                │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           │                               │
├───────────────────────────┼───────────────────────────────┤
│                           ▼                               │
│              PERSISTENCE LAYER                             │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐  │
│  │ SQLite   │ │ File Tree │ │ WeaveDB    │ │ Cache     │  │
│  │ (runes)  │ │ (docs/)   │ │ (vectors)  │ │ (~/.mjoll)│  │
│  └──────────┘ └───────────┘ └────────────┘ └──────────┘  │
│                                                           │
├───────────────────────────────────────────────────────────┤
│              INTEGRATION LAYER                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ LLM API  │ │ MCP      │ │ ACP      │ │ OpenTele-  │  │
│  │ Gateway  │ │ Bridge   │ │ Bridge   │ │ metry       │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## ᛚ II. Domain Ownership Map — Hard Boundaries

### Domain 1: `cli/` — Command Router (UI Layer)
**Owner:** CLI Team  
**Python Path:** `mythic_vibe_cli/cli/` (refactored from single `cli.py`)  
**Status:** Active — Major Modification Required

#### Responsibility
- Parse and dispatch all subcommands via `argparse` → `click` migration
- Route to appropriate domain handler
- Structured exit codes, consistent error formatting
- `--json` flag for all commands (machine-readable output)

#### Current State → Target State

| Current (`cli.py`) | Target (`cli/` package) |
|---|---|
| Single 240-line monolith | `cli/__init__.py` — `build_parser()` and `main()` |
| All handlers inline | `cli/commands/` — one module per command family |
| argparse | click for composability, with argparse compatibility shim |
| No structured exit codes | `cli/exit_codes.py` — enum of all exit conditions |

#### Contract
```python
# cli/commands/__init__.py — Registration interface
from typing import Protocol

class CommandHandler(Protocol):
    """Every command handler must satisfy this protocol."""
    def register(self, app: "click.Group") -> None: ...
    def execute(self, ctx: "click.Context") -> int: ...
```

#### Code Scaffold

```python
# mythic_vibe_cli/cli/main.py (entry point)
"""Mythic Vibe CLI — main entry point."""
from __future__ import annotations
import click
from mythic_vibe_cli.cli.commands import (
    init_commands, checkin_commands, status_commands,
    codex_commands, forge_commands, wardr_commands,
    seidr_commands, mimir_commands, rune_commands,
)

@click.group()
@click.version_option()
@click.option("--path", default=".", help="Project directory")
@click.option("--json", "json_output", is_flag=True, help="Machine-readable output")
@click.pass_context
def main(ctx: click.Context, path: str, json_output: bool) -> None:
    """Mythic Engineering-aligned vibe coding CLI — the Seeress's Forge."""
    ctx.ensure_object(dict)
    ctx.obj["root"] = Path(path).resolve()
    ctx.obj["json"] = json_output

# Register all command families
init_commands.register(main)
checkin_commands.register(main)
status_commands.register(main)
codex_commands.register(main)
forge_commands.register(main)
wardr_commands.register(main)
seidr_commands.register(main)
mimir_commands.register(main)
rune_commands.register(main)
```

---

### Domain 2: `loop/` — Mythic Workflow Engine (Workflow Layer)
**Owner:** Workflow Team  
**Python Path:** `mythic_vibe_cli/loop/` (extracted from `workflow.py`)  
**Status:** Active — Structural Refactor

#### Responsibility
- Enforce the seven-phase Mythic Engineering loop
- State machine with valid transitions
- Schema-versioned `status.json` with migration support
- Invariant checks (completed phase ordering, phase preconditions)

#### Phase State Machine

```python
# mythic_vibe_cli/loop/state_machine.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional, Self
import json
from datetime import datetime, timezone
from pathlib import Path

class Phase(StrEnum):
    INTENT = "intent"
    CONSTRAINTS = "constraints"
    ARCHITECTURE = "architecture"
    PLAN = "plan"
    BUILD = "build"
    VERIFY = "verify"
    REFLECT = "reflect"

# Valid transitions: you can advance forward or revisit any previous phase
VALID_TRANSITIONS: dict[Phase, set[Phase]] = {
    Phase.INTENT: {Phase.CONSTRAINTS, Phase.INTENT},
    Phase.CONSTRAINTS: {Phase.ARCHITECTURE, Phase.INTENT},
    Phase.ARCHITECTURE: {Phase.PLAN, Phase.CONSTRAINTS},
    Phase.PLAN: {Phase.BUILD, Phase.ARCHITECTURE},
    Phase.BUILD: {Phase.VERIFY, Phase.PLAN},
    Phase.VERIFY: {Phase.REFLECT, Phase.BUILD},
    Phase.REFLECT: {Phase.INTENT, Phase.VERIFY},
}

@dataclass
class LoopState:
    """Versioned state of the Mythic Engineering loop."""
    schema_version: int = 2
    goal: str = ""
    current_phase: Phase = Phase.INTENT
    completed_phases: list[Phase] = field(default_factory=list)
    last_update: str = ""
    history: list[dict] = field(default_factory=list)
    # New fields for advanced features
    run_id: str = ""
    constraints_validated: bool = False
    architecture_decisions: list[str] = field(default_factory=list)
    test_results: dict[str, str] = field(default_factory=dict)
    reflection_notes: list[str] = field(default_factory=list)

    def transition_to(self, target: Phase) -> bool:
        """Validate and execute a phase transition."""
        if target not in VALID_TRANSITIONS.get(self.current_phase, set()):
            return False
        self.current_phase = target
        if target not in self.completed_phases:
            self.completed_phases.append(target)
        self.last_update = datetime.now(timezone.utc).isoformat()
        return True

    @classmethod
    def migrate(cls, data: dict) -> Self:
        """Migrate from older schema versions."""
        version = data.get("schema_version", 1)
        if version == 1:
            data = cls._migrate_v1_to_v2(data)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def _migrate_v1_to_v2(data: dict) -> dict:
        data["schema_version"] = 2
        data["run_id"] = data.get("run_id", "")
        data["constraints_validated"] = False
        data["architecture_decisions"] = []
        data["test_results"] = {}
        data["reflection_notes"] = []
        return data
```

---

### Domain 3: `codex/` — Prompt Bridge (Domain Layer)
**Owner:** Integration Team  
**Python Path:** `mythic_vibe_cli/codex/` (extracted from `codex_bridge.py`)  
**Status:** Active — Major Expansion

#### Responsibility
- Generate structured prompt packets for external AI assistants
- Context provider abstraction (composable sections)
- Multi-provider support: ChatGPT, Codex, Claude, Gemini, Grok, local models
- Packet compaction with telemetry
- Response ingestion and logging

#### Contract: Context Provider Interface

```python
# mythic_vibe_cli/codex/providers.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

@dataclass
class ContextSection:
    """A named section of context for a prompt packet."""
    name: str           # e.g., "architecture", "goals", "plan"
    content: str        # The actual text
    priority: int = 5   # 1 (critical) to 10 (optional)
    token_estimate: int = 0  # Estimated token count

class ContextProvider(Protocol):
    """Protocol for composable context section providers."""
    def provide(self, root: Path, task: str, phase: str) -> ContextSection: ...

class FileContextProvider:
    """Reads a section from a project file."""
    def __init__(self, name: str, path: str, priority: int = 5):
        self.name = name
        self.path = path
        self.priority = priority

    def provide(self, root: Path, task: str, phase: str) -> ContextSection:
        file_path = root / self.path
        if not file_path.exists():
            return ContextSection(name=self.name, content="(missing)", priority=self.priority)
        content = file_path.read_text(encoding="utf-8")
        return ContextSection(name=self.name, content=content, priority=self.priority,
                              token_estimate=len(content) // 4)

class StatusContextProvider:
    """Provides the current loop state as context."""
    def provide(self, root: Path, task: str, phase: str) -> ContextSection:
        status_path = root / "mythic" / "status.json"
        if not status_path.exists():
            return ContextSection(name="status", content="No status.", priority=1)
        import json
        state = json.loads(status_path.read_text(encoding="utf-8"))
        return ContextSection(
            name="status",
            content=json.dumps(state, indent=2),
            priority=1
        )
```

#### Target API: Multi-Model Packet Generation

```python
# mythic_vibe_cli/codex/packet_builder.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from mythic_vibe_cli.codex.providers import ContextProvider, ContextSection
from mythic_vibe_cli.loop.state_machine import LoopState, Phase

@dataclass
class ModelTarget:
    """Configuration for a specific AI model target."""
    name: str                                    # "chatgpt", "claude", "gemini"
    max_tokens: int = 12000
    system_prompt_prefix: str = ""
    supports_thinking: bool = False
    requires_json_mode: bool = False

@dataclass
class PacketConfig:
    task: str
    phase: Phase
    audience: str = "intermediate"               # beginner/intermediate/advanced
    model: ModelTarget = field(default_factory=lambda: ModelTarget("chatgpt"))
    auto_compact: bool = True
    char_budget: int = 12000
    excerpt_limit: int = 1800
    include_thinking: bool = False               # For Claude extended thinking

@dataclass
class PacketResult:
    """Result of packet generation with telemetry."""
    packet_text: str
    sections_included: list[str]
    sections_compacted: list[str]
    total_tokens_estimate: int
    compaction_ratio: float
    target_file: Path

class PacketBuilder:
    """Builds model-specific prompt packets from composable context providers."""

    def __init__(self, providers: list[ContextProvider], config: PacketConfig):
        self.providers = providers
        self.config = config

    def build(self, root: Path) -> PacketResult:
        """Assemble a complete prompt packet."""
        sections: list[ContextSection] = []
        for provider in sorted(self.providers, key=lambda p: getattr(p, 'priority', 5)):
            sections.append(provider.provide(root, self.config.task, self.config.phase))

        # Compact if needed
        compacted_names: list[str] = []
        if self.config.auto_compact:
            total_chars = sum(len(s.content) for s in sections)
            if total_chars > self.config.char_budget:
                sections, compacted_names = self._compact(sections)

        packet = self._render(sections)
        return PacketResult(
            packet_text=packet,
            sections_included=[s.name for s in sections if s.name not in compacted_names],
            sections_compacted=compacted_names,
            total_tokens_estimate=len(packet) // 4,
            compaction_ratio=len(packet) / max(1, sum(len(s.content) for s in sections)),
            target_file=root / "mythic" / "codex_prompt.md"
        )

    def _compact(self, sections: list[ContextSection]) -> tuple[list[ContextSection], list[str]]:
        """Intelligently compact sections, preserving high-priority first."""
        compacted: list[ContextSection] = []
        compacted_names: list[str] = []
        budget = self.config.char_budget
        # Sort by priority (ascending)
        sorted_sections = sorted(sections, key=lambda s: s.priority)
        for section in sorted_sections:
            if budget <= 0:
                break
            if len(section.content) <= budget:
                compacted.append(section)
                budget -= len(section.content)
            else:
                truncated = ContextSection(
                    name=section.name,
                    content=section.content[:budget] + "\n... [truncated]",
                    priority=section.priority
                )
                compacted.append(truncated)
                compacted_names.append(section.name)
                budget = 0
        return compacted, compacted_names

    def _render(self, sections: list[ContextSection]) -> str:
        """Render sections into a model-optimized packet."""
        model = self.config.model
        parts = []
        if model.system_prompt_prefix:
            parts.append(model.system_prompt_prefix)
        parts.append(f"# Task: {self.config.task}")
        parts.append(f"# Phase: {self.config.phase}")
        for section in sections:
            parts.append(f"\n## {section.name}")
            parts.append(section.content)
        return "\n".join(parts)
```

---

### Domain 4: `forge/` — Code Generation Engine (Domain Layer)
**Owner:** Forge Team  
**Python Path:** `mythic_vibe_cli/forge/`  
**Status:** NEW — Must Be Built

#### Responsibility
- Natural language to code generation via LLM gateways
- Multi-file coordinated generation with rollback
- Code completion (tab-based inline suggestions)
- Refactoring engine (search-and-replace, import management)
- 100+ language support via tree-sitter parsing
- Boilerplate automation (auth, CRUD, routing)

#### Contract: LLM Gateway Interface

```python
# mythic_vibe_cli/forge/gateway.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional
from enum import StrEnum

class ModelVendor(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
    LOCAL = "local"
    OLLAMA = "ollama"
    CUSTOM = "custom"

@dataclass
class GenerationRequest:
    """Standardized request across all LLM providers."""
    prompt: str
    system_prompt: str = ""
    model: str = "claude-sonnet-4-20250514"
    vendor: ModelVendor = ModelVendor.ANTHROPIC
    max_tokens: int = 4096
    temperature: float = 0.7
    context_files: list[str] = field(default_factory=list)  # File paths to include
    stream: bool = False
    thinking: bool = False  # Extended thinking for Claude
    json_mode: bool = False

@dataclass
class GenerationResponse:
    """Standardized response from any LLM provider."""
    text: str
    model: str
    vendor: ModelVendor
    tokens_used: int
    finish_reason: str
    latency_ms: float

class LLMGateway(ABC):
    """Abstract gateway — one implementation per vendor."""

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse: ...

    @abstractmethod
    async def generate_stream(self, request: GenerationRequest) -> AsyncIterator[str]: ...

    @abstractmethod
    def count_tokens(self, text: str) -> int: ...

class GatewayRouter:
    """Routes generation requests to the correct vendor gateway."""

    def __init__(self):
        self._gateways: dict[ModelVendor, LLMGateway] = {}

    def register(self, vendor: ModelVendor, gateway: LLMGateway) -> None:
        self._gateways[vendor] = gateway

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        gateway = self._gateways.get(request.vendor)
        if gateway is None:
            raise ValueError(f"No gateway registered for vendor: {request.vendor}")
        return await gateway.generate(request)
```

#### Code Generation Contract

```python
# mythic_vibe_cli/forge/code_gen.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class CodeChange:
    """A single code change to be applied."""
    file_path: Path
    original_content: str
    new_content: str
    change_type: str  # "create", "modify", "delete"
    description: str

@dataclass
class GenerationPlan:
    """A plan for multi-file code generation."""
    goal: str
    phase: str
    changes: list[CodeChange]
    rollback_snapshot: dict[Path, str] = field(default_factory=dict)

    def apply(self, dry_run: bool = False) -> list[Path]:
        """Apply all changes, capturing rollback snapshots."""
        modified: list[Path] = []
        for change in self.changes:
            if change.change_type == "create" and not change.file_path.exists():
                self.rollback_snapshot[change.file_path] = None
                if not dry_run:
                    change.file_path.parent.mkdir(parents=True, exist_ok=True)
                    change.file_path.write_text(change.new_content, encoding="utf-8")
                modified.append(change.file_path)
            elif change.change_type == "modify" and change.file_path.exists():
                self.rollback_snapshot[change.file_path] = change.file_path.read_text(encoding="utf-8")
                if not dry_run:
                    change.file_path.write_text(change.new_content, encoding="utf-8")
                modified.append(change.file_path)
        return modified

    def rollback(self) -> list[Path]:
        """Roll back all applied changes."""
        restored: list[Path] = []
        for path, original in self.rollback_snapshot.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(original, encoding="utf-8")
            restored.append(path)
        return restored
```

---

### Domain 5: `wardr/` — Security & Governance (Domain Layer)
**Owner:** Security Team  
**Python Path:** `mythic_vibe_cli/wardr/`  
**Status:** NEW — Must Be Built

#### Responsibility
- Vulnerability scanning (secrets, SQLi, XSS, command injection)
- Auto-fix generation for security issues
- Zero-knowledge secret encryption
- Policy generation (59+ policies across 10 categories)
- Configuration health scoring (0-100)
- Sandboxed code execution

```python
# mythic_vibe_cli/wardr/scanner.py
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re

class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class Vulnerability:
    """A detected vulnerability."""
    id: str
    file_path: Path
    line_number: int
    severity: Severity
    category: str          # "secret", "injection", "xss", "eval"
    description: str
    remediation: str       # AI-generated fix instruction
    auto_fixable: bool = False

class SecurityScanner:
    """Scans codebases for security vulnerabilities."""

    PATTERNS: dict[str, tuple[re.Pattern, Severity]] = {
        "hardcoded_secret": (re.compile(
            r'(?:password|secret|key|token|auth)\s*[:=]\s*["\'][^"\']+["\']',
            re.IGNORECASE
        ), Severity.CRITICAL),
        "sql_injection": (re.compile(
            r'(?:execute|cursor\.execute)\s*\(\s*["\'].*\%[srd]',
            re.IGNORECASE
        ), Severity.HIGH),
        "eval_usage": (re.compile(
            r'\beval\s*\(', re.IGNORECASE
        ), Severity.CRITICAL),
        "command_injection": (re.compile(
            r'\bos\.system\s*\(|subprocess\.call\s*\(.*shell\s*=\s*True',
            re.IGNORECASE
        ), Severity.HIGH),
    }

    def scan_file(self, file_path: Path) -> list[Vulnerability]:
        """Scan a single file for vulnerabilities."""
        if not file_path.is_file() or file_path.suffix not in {'.py', '.js', '.ts', '.sh', '.yaml', '.yml', '.json'}:
            return []
        vulnerabilities: list[Vulnerability] = []
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for category, (pattern, severity) in self.PATTERNS.items():
            for match in pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                vulnerabilities.append(Vulnerability(
                    id=f"{category}-{line_no}",
                    file_path=file_path,
                    line_number=line_no,
                    severity=severity,
                    category=category,
                    description=f"Potential {category.replace('_', ' ')} detected",
                    remediation=f"Review and secure the {category.replace('_', ' ')} at line {line_no}"
                ))
        return vulnerabilities
```

---

### Domain 6: `seidr/` — Testing & Quality (Domain Layer)
**Owner:** Quality Team  
**Python Path:** `mythic_vibe_cli/seidr/`  
**Status:** NEW — Must Be Built

#### Responsibility
- Test generation (unit, integration, E2E)
- Browser-based testing via Playwright
- Continuous testing on code generation
- Code review automation
- Pull request description generation
- Structured debugging

```python
# mythic_vibe_cli/seidr/test_gen.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TestSpec:
    """Specification for test generation."""
    source_file: Path
    function_name: str | None = None  # None = whole file
    test_framework: str = "pytest"    # pytest, jest, vitest, etc.
    test_type: str = "unit"           # unit, integration, e2e
    coverage_target: float = 0.80

@dataclass
class TestResult:
    """Result of a test run."""
    test_file: Path
    total: int
    passed: int
    failed: int
    errors: list[str]
    coverage_percent: float
    duration_ms: float
```

---

### Domain 7: `mimir/` — Context & Memory (Cross-Cutting Domain Layer)
**Owner:** Memory Team  
**Python Path:** `mythic_vibe_cli/mimir/`  
**Status:** NEW — Must Be Built

#### Responsibility
- Memory anchors (CLAUDE.md, AGENTS.md management)
- Session continuity hooks
- Architecture Decision Records (ADR)
- Conversation compaction and summarization
- Project learning and error pattern recognition
- Preference adaptation

```python
# mythic_vibe_cli/mimir/memory.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
import json

@dataclass
class MemoryAnchor:
    """A persistent memory file for project context."""
    path: Path
    content: str
    last_updated: str = ""
    category: str = "general"  # standards, decisions, patterns, preferences

@dataclass
class ConversationSummary:
    """A compacted summary of a conversation session."""
    session_id: str
    start_time: str
    end_time: str
    key_decisions: list[str]
    code_changes: list[str]
    unresolved_questions: list[str]
    next_steps: list[str]

class MimirMemory:
    """Manages project memory across sessions."""

    def __init__(self, root: Path):
        self.root = root
        self.mimir_dir = root / ".mimir"
        self.mimir_dir.mkdir(parents=True, exist_ok=True)

    def create_anchor(self, name: str, content: str, category: str = "general") -> MemoryAnchor:
        """Create or update a memory anchor file."""
        anchor_path = self.mimir_dir / f"{name}.md"
        anchor = MemoryAnchor(
            path=anchor_path,
            content=content,
            last_updated=datetime.now(timezone.utc).isoformat(),
            category=category,
        )
        anchor_path.write_text(content, encoding="utf-8")
        return anchor

    def load_anchors(self, category: str | None = None) -> list[MemoryAnchor]:
        """Load all memory anchors, optionally filtered by category."""
        anchors: list[MemoryAnchor] = []
        for file in self.mimir_dir.glob("*.md"):
            anchors.append(MemoryAnchor(
                path=file,
                content=file.read_text(encoding="utf-8"),
                last_updated="",
                category=category or "general",
            ))
        return anchors

    def record_decision(self, decision_id: str, context: str, decision: str,
                        consequences: str) -> Path:
        """Record an Architecture Decision Record (ADR)."""
        adr_dir = self.root / "docs" / "DECISIONS"
        adr_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        adr_path = adr_dir / f"{timestamp}-{decision_id}.md"
        content = f"""# ADR: {decision_id}
**Date:** {datetime.now(timezone.utc).isoformat()}
**Status:** Proposed

## Context
{context}

## Decision
{decision}

## Consequences
{consequences}
"""
        adr_path.write_text(content, encoding="utf-8")
        return adr_path

    def compact_conversation(self, messages: list[dict], max_chars: int = 8000) -> ConversationSummary:
        """Generate a compacted summary from a long conversation."""
        # In full implementation, this uses an LLM to summarize
        # For now, structural extraction
        session_id = f"session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        return ConversationSummary(
            session_id=session_id,
            start_time=messages[0].get("time", "") if messages else "",
            end_time=messages[-1].get("time", "") if messages else "",
            key_decisions=[],
            code_changes=[],
            unresolved_questions=[],
            next_steps=[],
        )
```

---

### Domain 8: `rune/` — Persistence & Infrastructure (Persistence Layer)
**Owner:** Infrastructure Team  
**Python Path:** `mythic_vibe_cli/rune/`  
**Status:** Active — Modify (extracted from config + new database layer)

#### Responsibility
- SQLite-backed state persistence (`runes.db`)
- Configuration layering (user/project/env)
- Cache management
- Vector store for semantic search (WeaveDB)
- Plugin registry (`plugins.json`)

```python
# mythic_vibe_cli/rune/database.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Any

class RuneDB:
    """SQLite-backed persistence for all CLI state."""

    SCHEMA_VERSION = 1

    def __init__(self, project_root: Path):
        self.db_path = project_root / ".mythic" / "runes.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    phase TEXT NOT NULL,
                    goal TEXT,
                    summary TEXT,
                    token_usage INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phase_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    from_phase TEXT,
                    to_phase TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    update_text TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS code_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    description TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (self.SCHEMA_VERSION, datetime.now(timezone.utc).isoformat())
            )
```

---

## ᚦ III. Integration Layer — The Bridges

### MCP Bridge

```python
# mythic_vibe_cli/integration/mcp_bridge.py
"""Model Context Protocol integration for external tool access."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, AsyncIterator
import asyncio
import json

@dataclass
class MCPServerConfig:
    name: str
    command: str          # e.g., "npx", "python"
    args: list[str]       # e.g., ["-m", "mcp_server"]
    env: dict[str, str]   # Environment variables

class MCPClient:
    """Client for connecting to MCP servers."""

    def __init__(self, servers: list[MCPServerConfig]):
        self.servers = servers
        self._connections: dict[str, asyncio.subprocess.Process] = {}

    async def connect(self, server_name: str) -> None:
        """Establish connection to an MCP server."""
        config = next((s for s in self.servers if s.name == server_name), None)
        if config is None:
            raise ValueError(f"Unknown MCP server: {server_name}")
        # Launch subprocess with stdio transport
        process = await asyncio.create_subprocess_exec(
            config.command, *config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env={**__import__('os').environ, **config.env}
        )
        self._connections[server_name] = process

    async def call_tool(self, server_name: str, tool_name: str,
                        arguments: dict) -> dict:
        """Call a tool on an MCP server."""
        process = self._connections.get(server_name)
        if process is None:
            await self.connect(server_name)
            process = self._connections[server_name]
        request = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        })
        process.stdin.write(request.encode() + b"\n")
        await process.stdin.drain()
        response_line = await process.stdout.readline()
        return json.loads(response_line.decode())
```

### LLM Provider Gateway Implementations

```python
# mythic_vibe_cli/integration/llm_providers.py
"""Concrete LLM gateway implementations for each vendor."""
from __future__ import annotations
from mythic_vibe_cli.forge.gateway import (
    LLMGateway, GenerationRequest, GenerationResponse, ModelVendor
)
from typing import AsyncIterator

class AnthropicGateway(LLMGateway):
    """Anthropic Claude API gateway."""

    def __init__(self, api_key: str | None = None):
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        # Build messages with context
        messages = [{"role": "user", "content": request.prompt}]
        if request.context_files:
            context_text = "\n".join(
                Path(f).read_text(encoding="utf-8") for f in request.context_files
                if Path(f).exists()
            )
            messages[0]["content"] = f"{context_text}\n\n{request.prompt}"

        response = await client.messages.create(
            model=request.model,
            max_tokens=request.max_tokens,
            system=request.system_prompt,
            messages=messages,
            temperature=request.temperature,
        )
        return GenerationResponse(
            text=response.content[0].text,
            model=request.model,
            vendor=ModelVendor.ANTHROPIC,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason or "end_turn",
            latency_ms=0.0,  # Track via timing wrapper
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        async with client.messages.stream(
            model=request.model,
            max_tokens=request.max_tokens,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def count_tokens(self, text: str) -> int:
        # Approximate: Claude uses ~3.5 chars per token
        return len(text) // 3

class OpenAIGateway(LLMGateway):
    """OpenAI API gateway (ChatGPT, GPT-4, Codex)."""
    # Similar implementation pattern as Anthropic
    ...

class OllamaGateway(LLMGateway):
    """Local Ollama gateway for privacy-sensitive work."""
    # Uses aiohttp to call localhost:11434
    ...
```

---

## ᚲ IV. CLI Command Surface — The Complete Slash-Command Map

All commands from the aggregate report, mapped to domains:

### Phase Commands (`loop/`)
| Command | Function | Status |
|---|---|---|
| `mythic init --goal "..."` | Initialize project with full scaffold | Modify |
| `mythic checkin --phase X --update "..."` | Log phase transition | Modify |
| `mythic status [--json]` | Current loop state | Modify |
| `mythic doctor` | Diagnose missing files, drift | Enhance |

### Code Generation (`forge/`)
| Command | Function | Status |
|---|---|---|
| `mythic forge --task "..." [--lang py]` | Generate code from natural language | NEW |
| `mythic refactor --target "..." --goal "..."` | Multi-file refactoring | NEW |
| `mythic complete` | Start tab-completion daemon | NEW |
| `mythic scaffold --type web/api/mobile` | Generate full-stack scaffold | NEW |

### Prompt Bridge (`codex/`)
| Command | Function | Status |
|---|---|---|
| `mythic codex-pack --task "..." --phase X [--model claude]` | Generate prompt packet | Modify |
| `mythic codex-log --phase X --response "..."` | Log AI response | Modify |
| `mythic bridge --model claude/gpt/gemini` | Interactive AI chat | NEW |

### Security (`wardr/`)
| Command | Function | Status |
|---|---|---|
| `mythic wardr scan [--path .]` | Security vulnerability scan | NEW |
| `mythic wardr shield` | Generate security policy rules | NEW |
| `mythic wardr seal --secret KEY` | Zero-knowledge secret encryption | NEW |
| `mythic wardr audit` | Comprehensive codebase audit | NEW |

### Testing (`seidr/`)
| Command | Function | Status |
|---|---|---|
| `mythic seidr test [--framework pytest]` | Generate and run tests | NEW |
| `mythic seidr review` | AI code review of current changes | NEW |
| `mythic seidr debug "describe bug"` | Structured debugging session | NEW |
| `mythic seidr pr` | Generate PR description from diff | NEW |

### Memory (`mimir/`)
| Command | Function | Status |
|---|---|---|
| `mythic mimir anchor --name "..." --content "..."` | Create memory anchor | NEW |
| `mythic mimir recall [--category X]` | Load memory anchors | NEW |
| `mythic mimir decide --id "..." --context "..." --decision "..."` | Record ADR | NEW |
| `mythic mimir compact` | Compact conversation history | NEW |

### Persistence (`rune/`)
| Command | Function | Status |
|---|---|---|
| `mythic sync` | Sync method data from GitHub | Modify |
| `mythic import-md [--target ...]` | Import Markdown corpus | Modify |
| `mythic rune config [--explain]` | Show/explain configuration | NEW |
| `mythic rune health` | Configuration health scoring (0-100) | NEW |

---

## ᛞ V. Phase Plan — Forging the Complete System

### Phase 0: Stabilize (Week 1) — CURRENT STATE ENTRY POINT
**Goal:** Lock current product behavior and establish all guardrails.

**Work:**
1. Freeze current `mythic_vibe_cli` command behavior
2. Merge all architecture control docs (DOMAIN_MAP.md, this blueprint, CODE_REQUIREMENTS_MATRIX.md, ROBUSTNESS_ADVANCEMENT_ROADMAP.md)
3. Add static import boundary checker: `python -m mythic_vibe_cli.tools.check_boundaries`
4. Establish per-domain code owners

**Exit Criteria:**
- [x] Guardrail docs merged (done 2026-04-23)
- [ ] Boundary checker script functional
- [ ] All current commands pass regression
- [ ] No new cross-island imports introduced

### Phase 1: Extract Interfaces (Weeks 1-2)
**Goal:** Define all contract points before building new domains.

**Work:**
1. Refactor `cli.py` → `cli/` package with CommandHandler protocol
2. Extract `workflow.py` → `loop/` with versioned state machine
3. Define all abstract interfaces in `interfaces/`:
   - `LLMGateway` (forge/gateway.py)
   - `ContextProvider` (codex/providers.py)
   - `SecurityScanner` (wardr/scanner.py)
   - `TestGenerator` (seidr/test_gen.py)
4. Add adapter stubs for dormant island integration

**Key Python Files Created:**
```
mythic_vibe_cli/
├── cli/                  # Refactored from cli.py
│   ├── __init__.py       # build_parser(), main()
│   ├── commands/         # One module per command family
│   │   ├── __init__.py
│   │   ├── init_commands.py
│   │   ├── checkin_commands.py
│   │   ├── status_commands.py
│   │   ├── codex_commands.py
│   │   ├── forge_commands.py
│   │   ├── wardr_commands.py
│   │   ├── seidr_commands.py
│   │   ├── mimir_commands.py
│   │   └── rune_commands.py
│   └── exit_codes.py
├── loop/                 # Extracted from workflow.py
│   ├── __init__.py
│   ├── state_machine.py  # LoopState, Phase, transitions
│   └── project_init.py   # MythicWorkflow.init_project
├── codex/                # Extracted from codex_bridge.py
│   ├── __init__.py
│   ├── providers.py      # ContextProvider protocol + implementations
│   └── packet_builder.py # PacketBuilder with multi-model support
├── forge/                # NEW
│   ├── __init__.py
│   ├── gateway.py        # LLMGateway, GatewayRouter
│   └── code_gen.py       # CodeChange, GenerationPlan
├── wardr/                # NEW
│   ├── __init__.py
│   ├── scanner.py        # SecurityScanner
│   └── policy_gen.py     # Policy generation
├── seidr/                # NEW
│   ├── __init__.py
│   ├── test_gen.py       # Test generation
│   └── reviewer.py       # Code review automation
├── mimir/                # NEW
│   ├── __init__.py
│   └── memory.py         # MimirMemory, ADR, anchors
├── rune/                 # NEW (extracted from config.py + new)
│   ├── __init__.py
│   ├── database.py       # RuneDB
│   ├── config.py         # ConfigStore (moved)
│   └── vector_store.py   # Semantic search
├── integration/          # NEW
│   ├── __init__.py
│   ├── mcp_bridge.py     # MCP client
│   └── llm_providers.py  # Anthropic, OpenAI, Ollama gateways
├── tools/                # Developer tooling
│   ├── check_boundaries.py
│   └── schema_migrate.py
├── config.py             # Moved to rune/config.py, re-export
├── mythic_data.py        # Keep, enhance
└── __init__.py           # Keep, update version
```

### Phase 2: Isolate Legacy (Week 3)
**Goal:** Quarantine dormant islands and prevent accidental integration.

**Work:**
1. Tag dormant islands with `INTEGRATION_STATUS.md` metadata
2. Add `check_boundaries.py` to CI
3. Define "approved integration pathways"
4. Delete or archive unused vendor mirrors

### Phase 3: Harden Active Product (Weeks 3-6)
**Goal:** Production-grade reliability and observability.

**Work:**
1. Structured logging with `run_id`, phase, command, duration, result
2. Retry/backoff for all network calls (exponential backoff with jitter)
3. Schema validation for all persisted data
4. Golden-path tests reaching 90%+ coverage
5. Snapshot tests for prompt packet rendering

### Phase 4: Build New Domains (Weeks 6-16)
**Goal:** Implement the seven new domain packages.

**Sequence (dependency-ordered):**
1. `rune/` — Database and config (prerequisite for all)
2. `mimir/` — Memory (prerequisite for context)
3. `codex/` — Enhanced prompt bridge (prerequisite for forge)
4. `forge/` — Code generation (depends on codex + integration)
5. `integration/` — MCP + LLM providers (runs parallel to forge)
6. `wardr/` — Security (can run parallel)
7. `seidr/` — Testing (can run parallel)

### Phase 5: Advanced Features (Weeks 16+)
**Goal:** Implement the full aggregate feature set.

**Advanced Capabilities:**
- Adaptive context curation — smart ranking of doc sections by task intent
- Policy-aware command planning — guardrails for risky operations
- Local knowledge graph — persistent map of modules, docs, dependencies
- Drift detection engine — alert when docs and implementation diverge
- Resilience simulation mode — fault injection testing
- Multi-agent coordination via ACP
- Vector-based semantic code search (WeaveDB)
- Offline/local model support via Ollama

---

## ᛒ VI. Verification Gates

Every release candidate must pass:

### Architecture Gate
- [ ] `python -m mythic_vibe_cli.tools.check_boundaries` — zero violations
- [ ] `DOMAIN_MAP.md` updated for any ownership changes
- [ ] `ARCHITECTURE.md` reflects current layered structure

### Functional Gate
- [ ] `pytest tests/ -x --cov=mythic_vibe_cli --cov-report=term` — 90%+ pass
- [ ] All status/config schema validation tests pass
- [ ] Golden-path command tests pass (init, checkin, status, codex-pack, forge, wardr, seidr)

### Resilience Gate
- [ ] Network timeout/retry tests pass
- [ ] Malformed file recovery tests pass
- [ ] Schema migration tests pass (v1 → v2 → v3)

### Security Gate
- [ ] `mythic wardr scan` — zero critical findings
- [ ] Secret scanning passes
- [ ] Dependency audit (`pip-audit`) clean

---

## ᛟ VII. Dependency Law — What May Depend on What

```
mythic_vibe_cli/cli/*          MAY depend on: loop/, codex/, forge/, wardr/,
                                            seidr/, mimir/, rune/, integration/
                              MUST NOT depend on: ai/, core/, systems/, yggdrasil/,
                                                  WYRD-Protocol/, mindspark_thoughtform/,
                                                  ollama/, whisper/, chatterbox/

mythic_vibe_cli/loop/*         MAY depend on: rune/
                              MUST NOT depend on: cli/, codex/, forge/, wardr/, seidr/

mythic_vibe_cli/forge/*        MAY depend on: codex/, integration/, mimir/, rune/
                              MUST NOT depend on: cli/, wardr/, seidr/

mythic_vibe_cli/integration/*  MAY depend on: rune/
                              MUST NOT depend on: cli/, loop/, codex/, forge/,
                                                  wardr/, seidr/, mimir/

mythic_vibe_cli/rune/*         MAY depend on: Python stdlib only
                              MUST NOT depend on: any other domain
```

---

## ᚠ VIII. The Rust Acceleration Layer

For performance-critical paths, a companion Rust crate `mjollnir_core` provides:

```rust
// mjollnir_core/src/lib.rs — Python-callable via PyO3
use pyo3::prelude::*;

/// Fast token counting using tiktoken-rs
#[pyfunction]
fn count_tokens(text: &str, model: &str) -> PyResult<usize> {
    // tiktoken-rs implementation
    Ok(text.len() / 4) // placeholder
}

/// Ripgrep-powered code search
#[pyfunction]
fn search_code(root: &str, pattern: &str, file_types: Vec<String>) -> PyResult<Vec<String>> {
    // ripgrep crate integration
    Ok(vec![])
}

/// Tree-sitter AST parsing for multi-language support
#[pyfunction]
fn parse_ast(file_path: &str, language: &str) -> PyResult<String> {
    // tree-sitter integration
    Ok("{}".into())
}

#[pymodule]
fn mjollnir_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(count_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(search_code, m)?)?;
    m.add_function(wrap_pyfunction!(parse_ast, m)?)?;
    Ok(())
}
```

---

## Closing: The Architect's Benediction

This plan is a load-bearing structure, not a decoration. Every domain has an owner. Every boundary has a reason. Every contract has a verification gate. The forge is lit, the law is written, and the path from the current five-island sprawl to the unified Völuspá CLI is laid in stone.

The work is substantial. The sequence is non-negotiable. Phase 0 begins now.

*— Rúnhild Svartdóttir, The Architect*  
*Given on the day the boundaries were drawn, April 24, 2026*