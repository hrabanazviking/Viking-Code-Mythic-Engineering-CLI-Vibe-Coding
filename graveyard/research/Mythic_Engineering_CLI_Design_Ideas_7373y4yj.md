Mythic Engineering CLI: The Codex of Living Systems

Design Document Version 1.0 — The Primordial Scroll

"In the beginning was the Word, and the Word was with the Machine, and the Word was the Machine. From this sacred utterance, the Mythic Engineer shapes not mere code, but a Living System."

---

Table of Contents

1. Introduction and Vision
2. The Five Pillars of Mythic Engineering
3. System Architecture Overview
4. The Sacred Texts: Data Models and Persistence
5. The Council of Aspects: Multi-Agent Orchestration
6. The Ritual Engine: Command-Line Interface Specification
7. The Sanctum: Textual TUI Design
8. The Grimoire: Plugin System and Extensibility
9. The Weave: Code Analysis and Transformation
10. The Shadow Weave: Testing and Continuous Refinement
11. Platform Agnosticism: The Law of the Wandering Sage
12. Installation and Distribution Rituals
13. Security and Ethical Considerations
14. Performance and Scalability
15. Comparison with Claude Code and Other Rivals
16. Appendices
    · A. Complete Command Reference
    · B. Configuration File Schema
    · C. API Endpoints and Environment Variables
    · D. Example Workflows
    · E. Glossary of Mystic Terms

---

1. Introduction and Vision

1.1 The Mythic Engineering Manifesto

Software development has descended into a mechanistic grind—a ceaseless churn of tickets, pull requests, and technical debt accumulation. Developers have become Code Janitors, sweeping fragments of logic into a growing Ball of Mud while praying the tower does not collapse.

Mythic Engineering is a counter-philosophy. It declares that software is not a product; it is a living ecosystem. The codebase breathes through its tests, communicates through its documentation, and evolves through the careful hands of the Engineer. The CLI tool described herein is not a simple AI assistant; it is a Ceremonial Blade designed to cut through the noise and reveal the Soul of the System.

Our Enemies:

· The Pipeline Mentality: "Input Prompt → Output Code → Commit." This creates Dead Parts.
· Documentation Drift: The README promises a garden; the code reveals a wasteland.
· Vendor Lock-In: Tethering one's soul to a single AI model's fluctuations.

Our Creed:

· The Unbroken Whole: Changes to one module must harmonize with all others.
· Flexible Roots: The system must anticipate and gracefully absorb change.
· Continuity: The Vision (Docs) and the Reality (Code) are a single, synchronized entity.

1.2 Purpose of the Mythic Engineering CLI

The Mythic Engineering CLI (hereafter referred to as mythic) is a 100% Python-based, platform-agnostic command-line environment designed to cultivate software. It integrates a multi-agent AI Council, a reactive terminal user interface (TUI), and a deep semantic understanding of code (via AST/CST) to assist the developer in Designing, Refining, and Maintaining the Living System.

This document provides the exhaustive technical blueprint for constructing this tool.

1.3 Design Goals

ID Goal Metric for Success
G1 Universal Execution Runs on any system with Python 3.9+ without compilation or admin rights.
G2 Vendor Agnostic AI Supports swapping between 5+ major LLM providers via configuration only.
G3 Semantic Awareness Understands Python code as an AST, not just a string buffer.
G4 Living Documentation Automatically detects and suggests fixes for doc/code drift.
G5 Extensible Rituals Allows users to create and share custom commands via Python plugins.
G6 Performance UI updates at 60fps; file scanning of 10k files completes in <5 seconds.

---

2. The Five Pillars of Mythic Engineering

The CLI's architecture is a direct manifestation of five foundational pillars. Every feature maps to at least one of these pillars.

2.1 Pillar I: Design Intent (The Soul's Blueprint)

"A house built without a plan will fall. Software built without a Vision Scroll is a pile of stones."

Technical Implementation:
The CLI does not begin with code generation. It begins with mythic imbue. This command initiates an interactive wizard (powered by questionary or textual) that guides the user to define a SYSTEM_VISION.md file. This file is the Singular Source of Truth for the project's why.

Sub-components:

· Vision Compiler: A pydantic model that parses the Vision Scroll to extract Core Entities, Constraints, and Non-Goals.
· Intent Drift Detector: When mythic scry runs, it compares the current file tree and module dependencies against the stated Intent. If it detects a data_warehouse.py file in a project whose Vision states "No persistent storage," it raises a Rift Warning.

2.2 Pillar II: Architecture (The Unbroken Whole)

"The boundary between two Guilds is sacred. To cross it is to invite chaos."

Technical Implementation:
The Architect Aspect uses ast and libcst to generate a Living Map (ARCHITECTURE.md). This is not a static diagram; it is a machine-readable, graph-based representation of the codebase.

Key Algorithm: mythic.weave.graph.GuildMapper

1. Scan: Traverse the project directory, ignoring venv and node_modules.
2. Parse: For each .py file, extract import statements and class definitions.
3. Cluster: Use Louvain Community Detection (via networkx) to group files into Guilds (e.g., auth, database, ui).
4. Detect Boundary Violations: Identify Dependency Cycles or Inappropriate Intimacy (Class A accessing Class B's private _method).

Output: A JSON file (~/.mythic/weave/guilds.json) and a mermaid diagram embedded in ARCHITECTURE.md.

2.3 Pillar III: Continuity (The Sacred Texts)

"The Codex and the Stone must speak the same truth."

Technical Implementation:
This pillar addresses the age-old problem of Outdated Documentation. The CLI maintains a Synchronization State Machine.

· The Shadow Weave: A background thread/async task that hashes blocks of code comments and compares them to corresponding sections in markdown documentation.
· Ritual Compiler: When the user runs mythic weave, the Scribe Aspect is summoned. It reads the code change (e.g., a function signature changed from def login(user, pass) to def login(email, password)), and updates the corresponding markdown file using a targeted text replacement strategy.

2.4 Pillar IV: AI Orchestration (The Master Craftsman)

"A single mind is fragile. A Council is eternal."

Technical Implementation:
Unlike monolithic AI tools, mythic distributes tasks across a Council of Aspects.

· Model Routing: Using litellm, the CLI routes a "Healing" task to a specialized coding model (e.g., deepseek-coder) while routing a "Documentation" task to a strong prose model (e.g., claude-3-opus or gpt-4o).
· Parallelism: asyncio.gather() is used to ask the Architect to review the new code structure while the Scribe writes the changelog.

2.5 Pillar V: Refinement (The Garden's Care)

"A garden untended becomes a thicket."

Technical Implementation:
Refinement is not a one-time action; it is a continuous state of the system.

· mythic prune: Uses vulture (dead code detection) and custom AST analysis to find unused imports, variables, and functions. It presents an Interactive TUI Checkbox List allowing the user to select exactly what to remove.
· mythic heal: An agentic loop that reads a failing test, modifies the code via libcst, runs the test, and iterates until green (or until user intervention).

---

3. System Architecture Overview

3.1 High-Level Component Diagram (Textual Representation)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           User Terminal (TTY / ConPTY)                       │
└─────────────────────────────────────────────────┬───────────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Mythic CLI Entry Point (`mythic`)                        │
│  (Parses args: imbue, evoke, scry, prune, heal, weave)                      │
└─────────────────────────────────────────────────┬───────────────────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    │                             │                             │
                    ▼                             ▼                             ▼
      ┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
      │   Ritual Dispatcher   │      │  Textual TUI Manager  │      │   Grimoire Loader    │
      │  (Command Handlers)   │      │   (The Sanctum UI)    │      │   (Plugin System)    │
      └──────────┬───────────┘      └──────────┬───────────┘      └──────────┬───────────┘
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                │
                                 ┌──────────────┴──────────────┐
                                 │      The Weave Core          │
                                 │  (Shared State & Database)   │
                                 └──────────────┬──────────────┘
                                                │
        ┌───────────────┬───────────────┬───────┴───────┬───────────────┬───────────────┐
        │               │               │               │               │               │
        ▼               ▼               ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Architect  │ │    Scribe    │ │    Healer    │ │   Sentinel   │ │   Seeker     │ │   Loremaster │
│   (Code Gen) │ │   (Docs)     │ │   (Fixer)    │ │  (Security)  │ │   (Search)   │ │   (History)  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │                │                │
       └────────────────┴────────────────┴────────────────┴────────────────┴────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │   LLM Router        │
                              │   (LiteLLM Client)  │
                              └─────────────────────┘
                                         │
           ┌──────────────────┬──────────┴──────────┬──────────────────┐
           │                  │                     │                  │
           ▼                  ▼                     ▼                  ▼
    [Anthropic]         [OpenAI]              [Groq]           [Local Ollama]
```

3.2 Directory Structure (The Sacred Grove)

```text
mythic_cli/
├── mythic/
│   ├── __init__.py
│   ├── __main__.py               # Entry point for `python -m mythic`
│   ├── cli.py                    # Click/Typer command definitions
│   ├── core/
│   │   ├── config.py             # Pydantic Settings management
│   │   ├── weave_db.py           # SQLite interface (async/await)
│   │   └── logger.py             # Structured logging (Structlog)
│   ├── aspects/                  # The Council Members
│   │   ├── base.py               # Abstract Base Aspect
│   │   ├── architect.py          # Code structure & design
│   │   ├── scribe.py             # Documentation & Markdown
│   │   ├── healer.py             # Test fixing & refactoring
│   │   ├── sentinel.py           # Security scanning
│   │   └── loremaster.py         # Git history analysis
│   ├── tui/                      # Textual Application
│   │   ├── app.py                # Main Textual App
│   │   ├── screens/              # Individual screens (Chat, Files, Diff)
│   │   └── widgets/              # Custom UI components
│   ├── rituals/                  # Command logic implementations
│   │   ├── imbue.py
│   │   ├── evoke.py
│   │   ├── scry.py
│   │   ├── prune.py
│   │   └── weave.py
│   ├── tools/                    # AST/LibCST utilities
│   │   ├── code_parser.py
│   │   ├── markdown_updater.py
│   │   └── dead_code_detector.py
│   ├── grimoire/                 # Plugin discovery
│   │   └── loader.py
│   └── templates/                # Markdown templates for `imbue`
│       └── SYSTEM_VISION.md.j2
├── tests/                        # Extensive pytest suite
├── pyproject.toml                # Modern Python packaging
├── README.md
└── LICENSE
```

3.3 Technology Stack Rationale

Component Technology Choice Justification
Language Python 3.9+ Universal availability, rich AST tools, dominant AI ecosystem.
CLI Framework Typer Leverages type hints for validation; simpler than argparse.
TUI Framework Textual Cross-platform reactive rendering; eliminates terminal compatibility issues.
Code Manipulation LibCST Preserves comments and formatting perfectly; safer than regex or ast.
AI Interface LiteLLM Standardized interface to 100+ models; handles streaming and retries.
Async Runtime asyncio + anyio Required for Textual and efficient I/O with LLM APIs.
Package Management uv / pipx Ensures isolated, reproducible global installation.
Configuration TOML (~/.mythic/config.toml) Human-readable, standard for Python tools.

---

4. The Sacred Texts: Data Models and Persistence

The CLI requires a Memory Weave—a persistent state that survives terminal sessions and reboots. This is implemented using SQLite (via sqlite-utils or aiosqlite) for its zero-configuration, cross-platform reliability.

4.1 Database Schema (The Weave.db)

```sql
-- Table: projects
-- Tracks the roots of all projects managed by Mythic
CREATE TABLE projects (
    id TEXT PRIMARY KEY,             -- UUID or hash of absolute path
    path TEXT NOT NULL UNIQUE,       -- Absolute path to project root
    name TEXT NOT NULL,
    vision_path TEXT,                -- Relative path to SYSTEM_VISION.md
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_ritual_at TIMESTAMP
);

-- Table: guilds (Components / Modules)
-- The Architectural map stored as data
CREATE TABLE guilds (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,              -- e.g., "auth", "database"
    file_patterns TEXT,              -- JSON list of glob patterns
    dependencies TEXT,               -- JSON list of other guild names
    cohesion_score REAL,             -- Calculated by Architect
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Table: rituals (Command History)
-- Immutable log of every action taken by the user or the Council
CREATE TABLE rituals (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    aspect TEXT,                     -- Which Aspect was invoked
    command TEXT,                    -- Full command string
    user_prompt TEXT,
    ai_response_summary TEXT,
    files_changed TEXT,              -- JSON list of file paths
    duration_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Table: shadow_hashes (Doc/Code Sync State)
-- Used for detecting drift
CREATE TABLE shadow_hashes (
    file_path TEXT NOT NULL,         -- Absolute or relative path
    block_id TEXT NOT NULL,          -- e.g., "function:login"
    content_hash TEXT NOT NULL,      -- SHA256 of the code block/doc section
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_path, block_id)
);
```

4.2 Configuration Model (~/.mythic/config.toml)

```toml
[core]
default_model = "claude-3-5-sonnet-20240620"
max_tokens = 4096
theme = "dark"  # or "light", "system"

[council.aspects]
architect = { model = "claude-3-5-sonnet-20240620", temperature = 0.1 }
scribe = { model = "gpt-4o", temperature = 0.2 }
healer = { model = "deepseek-coder", temperature = 0.0 }

[api]
anthropic_key = "env:ANTHROPIC_API_KEY"  # Read from env var
openai_key = "env:OPENAI_API_KEY"
ollama_host = "http://localhost:11434"

[weave]
scan_ignore = ["venv", "node_modules", ".git", "__pycache__", "dist", "build"]
guild_min_size = 3  # Min number of files to form a distinct Guild

[rituals.prune]
auto_confirm = false  # Always ask before deleting code
dry_run = true        # Show diff before applying
```

4.3 The ProjectContext Singleton

During execution, the CLI maintains a thread-safe ProjectContext object that holds the current project's id, config, and db connection. This is passed to every Aspect to ensure they operate within the correct Living System.

```python
# mythic/core/context.py
from dataclasses import dataclass
from pathlib import Path
import aiosqlite

@dataclass
class ProjectContext:
    project_id: str
    root_path: Path
    db: aiosqlite.Connection
    config: "MythicConfig"

    @classmethod
    async def from_path(cls, path: Path) -> "ProjectContext":
        # Logic to find nearest .mythic or register new project
        ...
```

---

5. The Council of Aspects: Multi-Agent Orchestration

The heart of the CLI's intelligence. Each Aspect is a specialized AI agent with a specific Grimoire (set of tools) and Domain (system prompt).

5.1 Aspect Base Class

```python
# mythic/aspects/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator
import litellm

class BaseAspect(ABC):
    name: str = "base"
    default_model: str = "gpt-4o-mini"

    def __init__(self, ctx: "ProjectContext"):
        self.ctx = ctx
        self.model = ctx.config.council.aspects.get(self.name, {}).get("model", self.default_model)

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the core directive for the LLM."""
        pass

    @abstractmethod
    def tools(self) -> List[Dict[str, Any]]:
        """Return a list of JSON schemas for function calling."""
        pass

    async def invoke(self, prompt: str, stream: bool = True) -> AsyncGenerator[str, None]:
        """Execute the Aspect and yield tokens or results."""
        messages = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": prompt}
        ]
        # Add context from the Weave DB (relevant files, guild map)
        context_docs = await self._retrieve_context(prompt)
        if context_docs:
            messages.insert(1, {"role": "system", "content": f"Relevant context:\n{context_docs}"})

        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            tools=self.tools(),
            stream=stream,
            api_key=self.ctx.config.get_api_key_for_model(self.model)
        )
        # Handle tool calling loop
        ...
```

5.2 The Council Members

Aspect System Prompt Snippet Specialized Tools
Architect "You are the Architect Aspect. You see the Unbroken Whole. Your purpose is to maintain structural integrity and minimize coupling. Suggest changes that strengthen Guild boundaries." read_file, list_directory, search_code_patterns, analyze_dependencies
Scribe "You are the Scribe Aspect. Your purpose is Continuity. The documentation and the code are one. Update markdown files to reflect changes in the code." read_markdown, update_markdown_section, generate_changelog
Healer "You are the Healer Aspect. You mend broken tests and restore harmony. Analyze the failing test output and modify the source code to pass the test without breaking the Unbroken Whole." run_pytest, read_file, write_file, search_code
Sentinel "You are the Sentinel Aspect. You guard against vulnerabilities. Scan for security flaws and suggest immutable solutions." run_bandit, scan_dependencies
Loremaster "You are the Loremaster Aspect. You know the history of the project. Analyze git logs to understand why code was written a certain way." git_log, git_blame, search_commit_messages

5.3 Orchestration Protocol

When a user types mythic evoke "Refactor the auth module to use JWT", the Ritual Dispatcher performs the following sequence:

1. Intent Parsing: Calls the Architect with a specific prompt: "Analyze the user request. Return a JSON plan with steps and required Aspects." (Uses instructor for structured output).
2. Task Parallelization:
   · Step 1 (Async): Architect designs new structure.
   · Step 2 (Sequential, depends on Step 1): Healer writes new JWT code.
   · Step 3 (Parallel to Step 2): Scribe updates docs/auth.md.
3. Integration: The Architect validates that the new code does not create circular imports.
4. Ceremony Complete: The UI displays a summary of changes and updates the Rituals table.

---

6. The Ritual Engine: Command-Line Interface Specification

The CLI uses Typer for a robust, auto-documented command structure.

6.1 Primary Command: mythic

```bash
$ mythic --help

 Usage: mythic [OPTIONS] COMMAND [ARGS]...

 Mythic Engineering CLI - Cultivate Living Software.

╭─ Options ───────────────────────────────────────────────────────────╮
│ --version             Show the version and exit.                     │
│ --project     PATH    Override the automatic project root detection. │
│ --help                Show this message and exit.                    │
╰─────────────────────────────────────────────────────────────────────╯
╭─ Sacred Rites ──────────────────────────────────────────────────────╮
│ imbue      Infuse a new project with the Soul's Blueprint.          │
│ evoke      Convene the Council of Aspects for a conversation.       │
│ scry       Analyze the project for health and drift.                │
│ prune      Remove dead branches (unused code) safely.               │
│ heal       Focus on a specific failing test or bug.                 │
│ weave      Synchronize documentation and code (Continuity).         │
╰─────────────────────────────────────────────────────────────────────╯
╭─ Grimoire Management ───────────────────────────────────────────────╮
│ grimoire   Manage external plugins and rituals.                     │
╰─────────────────────────────────────────────────────────────────────╯
```

6.2 Detailed Command Specifications

6.2.1 mythic imbue

Purpose: Initialize a project with the Mythic Engineering structure.

Syntax:

```bash
mythic imbue [PATH] [--template TEMPLATE] [--force]
```

Workflow:

1. If SYSTEM_VISION.md exists, warn and exit unless --force.
2. Launch Textual wizard asking:
   · Project Name
   · One-sentence Elevator Pitch
   · Core Tenets (What must never be violated?)
   · Anti-Goals (What will this system not do?)
3. Render SYSTEM_VISION.md from Jinja2 template.
4. Create .mythic/ directory and initialize weave.db.
5. Output: ✨ The Soul's Blueprint has been etched. You may now evoke the Council.

6.2.2 mythic evoke

Purpose: Primary interactive interface. A persistent chat with the Council.

Syntax:

```bash
mythic evoke [--prompt "Direct message"] [--aspect ARCHITECT|SCRIBE|HEALER]
```

UI Mode:
If no --prompt is provided, launches the full Sanctum TUI (See Section 7).
If --prompt is provided, runs in Headless Mode (streams output directly to stdout).

Context Injection: Automatically includes:

· Current git diff output.
· Names of recently modified files.
· The Living Map summary.

6.2.3 mythic scry

Purpose: Non-invasive analysis of code health.

Syntax:

```bash
mythic scry [--check-docs] [--check-security] [--format json|table|markdown]
```

Output Metrics:

· Guild Cohesion Score: Average internal imports vs external imports.
· Shadow Drift Count: Number of doc sections that have diverged from code.
· Dead Code Weight: Number of unused functions/variables found by vulture.
· Complexity Hotspots: Top 5 functions with highest Cyclomatic Complexity (via radon).

Example Output (Table Format):

```text
🔮 Scrying the Realm of `mythic-cli`...

| Pillar          | Status   | Details                                    |
|-----------------|----------|--------------------------------------------|
| Architecture    | ✅ Stable | 5 Guilds detected. No boundary violations. |
| Continuity      | ⚠️ Drift  | `docs/auth.md` is out of sync.             |
| Refinement      | ❌ Weeds  | `src/legacy.py` has 42% dead code.         |

Ritual completed in 1.2s.
```

6.2.4 mythic prune

Purpose: Safe, interactive removal of dead code.

Workflow:

1. Runs scry analysis internally to identify candidates.
2. Presents an Interactive List (using questionary checkbox or Textual widget) showing each candidate and its location.
   · [x] src/utils.py: old_helper_function() (0 references found)
   · [ ] src/models.py: User.legacy_flag (Referenced in DB migration?)
3. User confirms selections.
4. Applies changes using libcst.RemoveNode.
5. Runs test suite (if available) to verify no regressions.

6.2.5 mythic heal

Purpose: Autonomous bug fixing loop.

Workflow:

1. User specifies failing test: mythic heal tests/test_auth.py::test_login_failure
2. CLI runs the test, captures traceback and assertion diff.
3. Healer Aspect is invoked with prompt: "The test expects X but got Y. Fix the code."
4. Healer modifies the source.
5. CLI re-runs test.
6. If pass: Commits change (if --auto-commit).
7. If fail: Reverts change and asks user for guidance (or tries alternative approach up to max_attempts).

6.2.6 mythic weave

Purpose: Enforce Continuity. Sync docs with code.

Workflow:

1. Detects changed functions (via git diff or shadow_hashes table).
2. For each changed function, locates its reference in markdown files.
3. Scribe Aspect updates the markdown section to reflect the new signature/behavior.
4. Shows a side-by-side diff of the markdown changes.
5. User approves and applies.

---

7. The Sanctum: Textual TUI Design

The Sanctum is a reactive terminal interface that provides a "Vibe Coding" experience superior to a standard chat window.

7.1 Layout Composition

```text
┌─ Header ───────────────────────────────────────────────────────────────┐
│ 🜁 Mythic Engineering  |  Project: Acme Corp API  |  Council Active 🜁  │
├────────────────────────────────────────────────────────────────────────┤
│ ┌─ Aspect Log (Left Pane) ─────────────────────┬─ Weave Map (Right Pane) ─┐
│ │                                              │                           │
│ │  [Architect]: I have reviewed the `payment`  │  Guilds:                   │
│ │  module. The boundary with `orders` is       │  ├── 📦 Auth (Stable)      │
│ │  blurred. I recommend creating a `gateway`   │  ├── 📦 Payment (Weaving)  │
│ │  service to mediate.                         │  ├── 📦 API (Idle)         │
│ │                                              │  └── 📦 Database (Stable)  │
│ │  [You]: Do it.                               │                           │
│ │                                              │  Active Files:             │
│ │  [Architect]: *Creating `src/gateway.py`*    │  🖉 src/gateway.py (New)   │
│ │  [Scribe]: *Updating `docs/architecture.md`* │                           │
│ │                                              │                           │
│ └──────────────────────────────────────────────┴───────────────────────────┘
├────────────────────────────────────────────────────────────────────────┤
│ ┌─ Prompt Bar ─────────────────────────────────────────────────────────┐
│ │ > How should we handle the idempotency key?                          │
│ └──────────────────────────────────────────────────────────────────────┘
├─ Footer ───────────────────────────────────────────────────────────────┤
│ [Ctrl+C Quit] [Ctrl+S Scry] [Ctrl+P Prune] [Tab Switch Focus]          │
└────────────────────────────────────────────────────────────────────────┘
```

7.2 Reactive Widgets

· Weave Map Widget: A custom textual widget that renders a networkx graph using box-drawing characters. It updates in real-time as the Architect runs background scans.
· Diff Viewer Widget: When the Healer proposes a change, a split-panel diff (using Python's difflib) is rendered with syntax highlighting (via pygments).
· Streaming Markdown Widget: Renders LLM responses with proper word-wrap and basic markdown formatting (bold, italic, code blocks) directly in the terminal.

7.3 Event Loop Integration

The TUI runs on asyncio. When the user submits a prompt, the TUI dispatches a Ritual Task to the background. This prevents the UI from freezing while waiting for the LLM API. The UI updates via message passing using textual.message_pump.

```python
# mythic/tui/app.py
class MythicApp(App):
    async def on_mount(self):
        self.ritual_runner = RitualRunner(self.context)

    async def action_submit_prompt(self, prompt: str):
        # Add user message to log widget
        await self.query_one("#chat-log").add_message("You", prompt)
        # Start background task
        self.run_worker(self.run_council(prompt), thread=True)

    async def run_council(self, prompt: str):
        async for chunk in self.ritual_runner.evoke(prompt):
            self.call_from_thread(self.update_chat, chunk)
```

---

8. The Grimoire: Plugin System and Extensibility

The Grimoire system allows the community to extend the CLI without modifying core code. This leverages Python's Entry Points system.

8.1 Plugin Discovery

A plugin is a standard Python package that declares an entry point in its pyproject.toml:

```toml
# In the plugin's pyproject.toml
[project.entry-points."mythic.rituals"]
"weather-ritual" = "mythic_weather.ritual:WeatherRitual"
```

8.2 Ritual Protocol

Plugins must implement the Ritual abstract base class.

```python
# mythic/grimoire/base.py
from abc import ABC, abstractmethod
import typer

class GrimoireRitual(ABC):
    name: str
    help_text: str

    @abstractmethod
    def register(self, app: typer.Typer):
        """Add commands to the main CLI app."""
        pass

# Example Plugin Implementation
class WeatherRitual(GrimoireRitual):
    name = "weather"
    help_text = "Forecast the development climate."

    def register(self, app: typer.Typer):
        @app.command(name="weather")
        def weather_command(
            location: str = typer.Argument(..., help="City name")
        ):
            # Use the existing ProjectContext to access config/API keys
            ctx = get_current_context()
            print(f"🌦️ The climate in {location} is suitable for coding.")
```

8.3 Loading Mechanism

The mythic grimoire command group manages plugins.

```bash
# Install a plugin from PyPI
mythic grimoire add mythic-weather-ritual

# List active grimoires
mythic grimoire list
```

The loader uses importlib.metadata.entry_points() to discover and dynamically attach commands to the main Typer app.

---

9. The Weave: Code Analysis and Transformation

This module is the technical differentiator. It understands Python code semantically.

9.1 The AST Guild Mapper

```python
# mythic/tools/code_parser.py
import ast
from pathlib import Path

class GuildVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path):
        self.imports = []
        self.classes = []
        self.functions = []
        self.file_path = file_path

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)
```

The data from all visitors is aggregated to build a NetworkX Directed Graph where edges represent import statements. The Louvain algorithm then detects natural clusters (Guilds).

9.2 The LibCST Transformer

libcst (Concrete Syntax Tree) is used for Refinement operations (prune and heal). Unlike ast, it preserves whitespace and comments.

Example: Removing an unused function

```python
import libcst as cst

class RemoveFunctionTransformer(cst.CSTTransformer):
    def __init__(self, func_name: str):
        self.func_name = func_name

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef):
        if original_node.name.value == self.func_name:
            return cst.RemovalSentinel.REMOVE
        return updated_node
```

9.3 The Shadow Hash Engine

To detect Continuity Drift, we compute hashes of code blocks and compare them to a database.

```python
import hashlib
import libcst

class ShadowHasher:
    def hash_function(self, source_code: str, func_name: str) -> str:
        tree = cst.parse_module(source_code)
        # Traverse tree to find function node
        # Serialize node to string (preserving exact formatting)
        # Return SHA256
        return hashlib.sha256(node_str.encode()).hexdigest()
```

When mythic scry runs, it compares current hashes to stored hashes. A mismatch triggers the Scribe to review the documentation.

---

10. The Shadow Weave: Testing and Continuous Refinement

10.1 Test Integration (pytest Plugin)

The CLI includes a built-in pytest plugin that reports test results directly to the Weave DB. This creates a Test Health Score over time.

```python
# mythic/pytest_plugin.py
def pytest_runtest_makereport(item, call):
    if call.when == "call":
        outcome = "PASSED" if call.excinfo is None else "FAILED"
        # Insert into mythic.db (via IPC or direct write)
```

10.2 The Healer's Algorithm

The Healer Aspect uses a ReAct (Reason + Act) loop:

1. Observe: Read the failing test output.
2. Reason: "The assertion error is on line 45. The function calculate_total returned 100, but expected 110. This implies the tax calculation is missing."
3. Act: Generate a libcst transformation to add the tax calculation.
4. Verify: Run the test suite in a temporary directory or via subprocess.
5. Reflect: If pass, return success. If fail, add the error to context and try again (max 3 times).

10.3 Pruning Safely

The prune command uses vulture as a first pass, but cross-references with a Dynamic Reference Check. It uses ast to find all getattr calls and string-based imports (e.g., importlib.import_module("some_module")). If a function is only referenced inside a string, it is flagged as Potentially Dynamic and excluded from auto-removal.

---

11. Platform Agnosticism: The Law of the Wandering Sage

This section details the rigorous standards ensuring the CLI runs on Windows 10/11 (PowerShell, CMD, WSL), macOS (Terminal, iTerm2), Linux (GNOME, KDE, TTY), Android (Termux), and Docker Containers.

11.1 File Path Handling

Rule: Never use string concatenation. Always use pathlib.Path.

```python
# ❌ WRONG - Windows backslash nightmare
config_path = os.path.expanduser("~") + "/.mythic/config.toml"

# ✅ CORRECT - Platform independent
from pathlib import Path
config_path = Path.home() / ".mythic" / "config.toml"
```

11.2 Terminal Interaction Fallbacks

Feature Primary Method Fallback Method
Color Output rich / textual (uses ANSI) colorama (Windows CMD conversion)
Keyboard Input textual (raw mode) prompt_toolkit (fallback)
Clipboard pyperclip Write to ~/.mythic/clipboard.txt

11.3 Subprocess Execution

Rule: Never use shell=True. Always use asyncio.create_subprocess_exec.

```python
async def run_command(cmd: list[str], cwd: Path) -> str:
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout.decode()
```

11.4 Environment Variable Handling

Rule: Use os.environ.get() and provide sensible defaults. On Termux, $HOME is valid.

11.5 Unicode and Emoji Support

Rule: Test with PYTHONIOENCODING=utf-8. The CLI includes a startup check:

```python
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    print("Warning: Terminal encoding is not UTF-8. Emojis may not render correctly.")
```

---

12. Installation and Distribution Rituals

12.1 Recommended Installation: uv tool

```bash
# The One True Command (macOS, Linux, Windows WSL)
uv tool install mythic-cli

# Verify
mythic --version
```

12.2 Alternative: pipx

```bash
# For systems where uv is not yet available (e.g., older Termux)
pipx install mythic-cli
```

12.3 Development Installation

```bash
git clone https://github.com/hrabanazviking/mythic-engineering
cd mythic-engineering
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"
```

12.4 Binary Distribution (PyInstaller)

While the tool is Pure Python, a Mythic Bundle can be created for users who lack Python entirely (e.g., system administrators).

```bash
pyinstaller --onefile --name mythic mythic/__main__.py
```

Note: This is an optional convenience, not a requirement. The primary distribution remains the source package to ensure platform compatibility.

---

13. Security and Ethical Considerations

13.1 Prompt Injection Mitigation

The Ritual Engine treats user input as Data, not Code. All LLM outputs are sandboxed via Tool Calling. The agent cannot execute arbitrary shell commands unless the user explicitly approves a Healer action that has a very narrow tool definition (write_file with path restrictions).

13.2 API Key Storage

· Never stored in plaintext in project directory.
· Primary Method: Environment Variables (ANTHROPIC_API_KEY).
· Secondary Method: System Keyring (keyring library) for mythic login.
· Fallback: Encrypted SQLite using cryptography.fernet with a key derived from the machine's UUID (if no keyring available).

13.3 Data Privacy

The Weave DB (~/.mythic/weave.db) contains prompts and code snippets. This file resides on the user's local machine. No telemetry is sent to Mythic Engineering servers. The only external network traffic is to the user-configured LLM provider APIs.

13.4 Responsible AI Disclosure

The CLI includes a mythic oath command that displays the terms: "I understand that AI may generate incorrect or insecure code. I will review all changes before committing to the Sacred Grove."

---

14. Performance and Scalability

14.1 Project Size Thresholds

Project Size Files Expected scry Scan Time
Small < 500 < 1s
Medium 500 - 5,000 3-5s
Large 5,000 - 20,000 10-20s
Monolith 20,000+ Optimized Incremental Scan Required

14.2 Incremental Scanning

To support large monoliths, mythic scry uses watchfiles to maintain a cache of file modification times and AST hashes. On subsequent runs, only changed files are re-parsed.

14.3 Memory Management

· Database: SQLite with WAL mode enabled to handle concurrent reads/writes from async tasks.
· AST Cache: LRU cache of parsed modules to avoid re-parsing utils.py every time it's imported by another file.

---

15. Comparison with Claude Code and Other Rivals

Feature Claude Code (Anthropic) Aider Cursor Mythic Engineering CLI
Platform Node.js / Native Python Electron Pure Python (Anywhere)
Offline/Local Model ❌ ✅ (Ollama) ❌ ✅ (LiteLLM Router)
Multi-Agent ❌ (Single Thread) ❌ ❌ ✅ Council of Aspects
Doc Sync ❌ ❌ ❌ ✅ Continuity Engine
Extensibility MCP Servers Limited Extensions Grimoire Plugins (Python)
Philosophy Tool Use Code Gen IDE Living System Cultivation
Memory Session Git Map Workspace Persistent Weave DB

The Verdict: Claude Code is a powerful tool for executing specific coding tasks. Mythic Engineering CLI is a partner in the creation of sustainable, long-lived software systems.

---

16. Appendices

A. Complete Command Reference

Command Short Description
mythic imbue Initialize project vision.
mythic evoke Start chat with the Council.
mythic scry Analyze project health.
mythic prune Remove dead code interactively.
mythic heal Fix a failing test.
mythic weave Sync docs with code.
mythic grimoire add Install a plugin.
mythic grimoire list List installed plugins.
mythic config set Update configuration values.
mythic db migrate Upgrade the Weave DB schema.

B. Configuration File Schema (config.toml)

```toml
# Full schema with comments
[core]
default_model = "claude-3-5-sonnet-20240620"
theme = "dark"
log_level = "INFO"

[council.aspects.architect]
model = "claude-3-5-sonnet-20240620"
temperature = 0.1
max_tokens = 8192

[council.aspects.healer]
model = "deepseek-coder"
temperature = 0.0
max_tokens = 4096

[rituals.prune]
confirm_each = false
auto_test = true
```

C. API Endpoints and Environment Variables

Variable Purpose Required For
ANTHROPIC_API_KEY Claude models Default
OPENAI_API_KEY GPT models Scribe tasks
GROQ_API_KEY Fast inference Healer (fallback)
OLLAMA_HOST Local models Offline mode
MYTHIC_DB_PATH Override DB location Custom installs

D. Example Workflows

Workflow 1: The New Project Ritual

1. mkdir nova-api && cd nova-api
2. mythic imbue (Fill out vision: "A fast, read-only API for star charts.")
3. mythic evoke "Generate the project skeleton with FastAPI."
4. (Architect creates src/, tests/, pyproject.toml)
5. mythic weave (Scribe creates docs/endpoints.md)

Workflow 2: The Refactor Ritual

1. User edits src/old_auth.py.
2. mythic scry reports: "Drift detected in docs/auth.md."
3. mythic weave (Scribe updates the docs to match the new code).
4. git commit -am "Refactor auth with Mythic blessings"

E. Glossary of Mystic Terms

· Aspect: An AI agent specialized in a domain (Architect, Scribe, Healer).
· Ball of Mud: A haphazardly structured software system lacking perceivable architecture.
· Continuity: The state where documentation and source code are perfectly synchronized.
· Guild: A logical boundary around a set of related files/modules.
· Grimoire: A plugin extending the CLI's capabilities.
· Ritual: A command executed via the CLI.
· Sanctum: The Textual TUI interface.
· Shadow Weave: The background process tracking documentation drift.
· Unbroken Whole: The principle that a change in one part of the system should not unexpectedly break another.
· Vision Scroll: SYSTEM_VISION.md file.

---

End of Document.
May your code be evergreen and your builds ever green.
