# Mythic Vibe CLI Reforge Roadmap
**Version:** Rebirth Plan

## Vision
Mythic Vibe CLI becomes Volmarr's personal coding forge.
 * Not another generic AI agent.
 * Not another coding framework.
 * Not another wrapper around ChatGPT.
A persistent coding environment designed around:
 * Mythic Engineering
 * Vibe Coding
 * Long-term project continuity
 * Tailscale-connected knowledge
 * GitHub-native workflows
 * TUI-first operation
 * Memory preservation
 * Affordable AI models
 * Human-in-command architecture
 * 
## Phase 0: Reforge Charter
### Goal
Define what is sacred.
### Core Pillars
These are **NEVER** removed:
 * **CLI**
   * mythic
   * mythic-vibe
 * **TUI**
   * Textual interface
   * Dashboard
   * Project browser
   * Workflow views
   * Memory views
 * **Memory**
   * Persistent memory
   * Session continuity
   * Project continuity
   * Decision tracking
 * **Packet System**
   * Prompt packets
   * Codex packets
   * OpenCode packets
   * Research packets
 * **GitHub**
   * Clone
   * Branch
   * Commit
   * Push
   * PR workflows
 * **Knowledge Layer**
   * Local memory
   * Tailscale databases
   * Project archives
  
## Phase 1: Reality Audit
### Goal
Determine what currently works.
### Run:
```bash
pip install -e ".[dev]"
mythic-vibe --help
mythic --help
pytest

```
### Create:
 * docs/REFORGE_LOG.md
### Record:
 * Installs
 * Failures
 * Test status
 * Startup status
## Phase 2: Establish Active Runtime Boundary
### Goal
Map the living kingdom.
### Create:
 * docs/ACTIVE_RUNTIME_MAP.md
### Classify:
 * **Core Runtime**
   * mythic_vibe_cli/
   * tests/
   * TUI
   * Memory
   * Workflow
   * Packet
   * GitHub
   * Knowledge
 * **Auxiliary Runtime**
   * Providers
   * AI adapters
   * Optional integrations
 * **Dormant Islands**
   * Android
   * WASI
   * Launchers
   * Distribution experiments
> **Note:** Nothing is deleted.
>

## Phase 3: Restore Reliable Installation
### Goal
Make installation boring.
### Success Condition:
Running the following commands works every time:
```bash
pip install -e .
mythic-vibe --help

```
### Verify:
 * Windows
 * Linux
 * Fedora
 * Ubuntu

## Phase 4: Stabilize Command Surface
### Goal
Identify daily-use commands.
### Required Commands:
 * mythic doctor
 * mythic status
 * mythic scan
 * mythic packet
 * mythic reflect
 * mythic workflow
 * mythic memory
 * mythic github
 * mythic knowledge
*Everything else becomes secondary.*

## Phase 5: Stabilize TUI
### Goal
Make TUI usable every day.
### Required Views:
 * **Dashboard**
   * Projects
   * Memory
   * Workflows
   * GitHub
   * Knowledge
 * **Project View**
   * Current repo
   * Branch
   * Recent work
   * Open tasks
 * **Memory View**
   * Sessions
   * Decisions
   * Artifacts
 * **Knowledge View**
   * Search
   * Browse
   * Sources
   
## Phase 6: Memory Spine
### Goal
Prevent Hermes-style memory collapse.
### Database:
 * .mythic/memory.sqlite
### Tables:
 * sessions
 * events
 * tasks
 * files
 * decisions
 * artifacts
 * summaries
### Required Commands:
 * mythic memory add
 * mythic memory search
 * mythic memory recent
 * mythic memory project

## Phase 7: GitHub Workspace System
### Goal
Give Mythic its own forge.
### Workspace:
 * ~/.mythic-vibe/workspaces/
### Commands:
 * mythic repo clone
 * mythic repo list
 * mythic repo open
 * mythic repo status
## Phase 8: Branch Workflow System
### Goal
Safe coding branches.
### Commands:
 * mythic branch create
 * mythic branch current
 * mythic branch list
### Naming Convention:
 * mythic/YYYY-MM-DD/task-name

## Phase 9: Packet Engine
### Goal
Generate model-ready packets.
### Commands:
 * mythic packet create
 * mythic packet show
 * mythic packet list
### Packet Sections:
 * Task
 * Context
 * Files
 * Knowledge
 * Constraints
 * Expected Output
 * Tests
   
## Phase 10: Knowledge Layer
### Goal
Connect private knowledge.
### Supported Databases:
 * **SQLite**
   * Local database
   * Tailscale-mounted database
 * **PostgreSQL**
   * Remote tailscale host
### Commands:
 * mythic knowledge test
 * mythic knowledge search
 * mythic knowledge recent
 * mythic knowledge sources
### Default State:
 * Read-only

## Phase 11: Knowledge-Augmented Packets
### Goal
Inject project wisdom into prompts.
### Command:
```bash
mythic packet create --knowledge

```
### Sources:
 * Repo
 * Memory
 * Knowledge DB
 * Workflow history

## Phase 12: Model Configuration System
### Goal
Provider-neutral architecture.
### Configuration Fields:
 * provider
 * base_url
 * model
 * api_key_env
### Supported Engines:
 * OpenAI
 * OpenRouter
 * Qwen
 * DeepSeek
 * Kimi
 * Alibaba
 * LM Studio
 * Ollama
 * Future providers
   
## Phase 13: Direct Model Calls
### Goal
Optional automation.
### Modes:
 * **Packet Mode**
   * mythic packet create
 * **Model Mode**
   * mythic ask
*Default remains packet mode.*

## Phase 14: Patch Workflow
### Goal
Controlled code modifications.
### Commands:
 * mythic patch create
 * mythic patch show
 * mythic patch apply
 * mythic patch reject
> **Note:** No automatic writes.
>

## Phase 15: Project Continuity System
### Goal
Resume work after weeks or months.
### Command:
```bash
mythic resume

```
### Shows:
 * Last session
 * Open tasks
 * Pending branches
 * Recent decisions
 * Knowledge links
   
## Phase 16: Reintegrate Valuable Dormant Systems
### Goal
Bring back useful advanced features.
### Sources:
 * graveyard/
 * Dormant islands/
 * Experimental branches/
### Rules:
 1. Core stable first.
 2. One feature at a time.
 3. Add tests.
 4. Add docs.
 5. Reintegrate.

## Phase 17: Advanced Forge Restoration
### Potential Returns:
 * Hermes control plane
 * Agent API
 * Workflow automation
 * Advanced packet analysis
 * Provider adapters
 * Research systems
*Only if useful.*

## Phase 18: Documentation Pass
### Create:
 * QUICKSTART.md
 * DAILY_WORKFLOW.md
 * MEMORY.md
 * KNOWLEDGE.md
 * TUI.md
 * GITHUB.md
### Most Important Asset:
 * DAILY_WORKFLOW.md
Must answer the question:
> "I forgot everything. What do I type today?"
>

## Phase 19: Packaging and Distribution
### Verify:
```bash
python -m build
twine check dist/*

```
### Test Installation:
```bash
pip install mythic-vibe-cli

```
### Required Commands Available:
 * mythic
 * mythic-vibe
   
## Phase 20: Version 2.0 Rebirth
### Release Criteria:
 * [ ] Installs cleanly
 * [ ] TUI works
 * [ ] Memory works
 * [ ] GitHub works
 * [ ] Knowledge works
 * [ ] Packet generation works
 * [ ] Model integration works
 * [ ] Continuity works
 * [ ] Documentation exists
## Final Success State
A typical work session looks like this:
```bash
mythic repo clone hrabanazviking/Hermes-Agent
mythic branch create fix-memory-spine

mythic knowledge search "memory"

mythic packet create "Fix Hermes memory recall"

mythic ask

mythic patch apply

mythic reflect

mythic resume

```
 * The forge remembers.
 * The knowledge survives.
 * The AI becomes replaceable.
 * The workflow remains.
