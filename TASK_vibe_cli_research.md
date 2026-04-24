# TASK — Vibe Coding CLI Tools Feature Research

**Opened:** 2026-04-24
**Owner:** Runa (with dispatched research agent + later Skald synthesis)
**Purpose:** Produce a comprehensive feature/interface/function catalogue of existing AI "vibe coding" CLI tools, to feed a planning document for our own Mythic Engineering CLI (`mythic_vibe_cli/`) ambitions.

---

## Phase 1 — Raw Research (in flight)

**Agent:** `general-purpose` (needs WebSearch / WebFetch — ME agents lack these)
**Deliverable:** `research_data/vibe_coding_cli_tools_feature_research.md` in this repo.

### Tools to cover

**Tier 1 — direct CLI/agent coders (must cover deeply):**
- Claude Code (Anthropic)
- Aider
- Codex CLI (OpenAI)
- Gemini CLI (Google)
- Cline / Roo Code (VS Code)
- Continue.dev
- Cursor
- Windsurf (Codeium)
- Kilo Code
- Goose (Block)
- OpenHands (ex-OpenDevin)
- Plandex
- Amp (Sourcegraph)
- Factory.ai
- Charm CRUSH

**Tier 2 — relevant / adjacent:**
- GitHub Copilot CLI + Workspace
- Amazon Q Developer CLI
- Warp AI terminal
- Jules (Google)
- Anti-Gravity (Google)
- Zed AI
- Open Interpreter
- Sweep, Mentat, GPT Pilot, Devin, SWE-agent
- Tabby, Codebuff, Cody

**Tier 3 — web AI coders (for UX inspiration only):**
- Bolt.new, v0, Lovable, Replit Agent

### Dimensions to capture per tool
- Interface type (CLI / TUI / IDE plugin / web / desktop)
- Agent loop model (single-shot / react / planner-executor / multi-agent)
- File editing strategy (whole-file / diff / patch / line-replace)
- Context system (repo index / RAG / repo map / manual @)
- Memory & persistence (session / project / long-term)
- Tool-use system (MCP / custom tools / native bash)
- Permission / approval model
- Slash commands, hooks, extensions
- Model support (multi-provider / local / switching)
- Multimodal (image / voice)
- Subagents / parallelism / worktrees
- Git integration
- Test / build integration
- Background / scheduled tasks
- Cost, caching, telemetry
- Terminal UX (statusline, themes, keybindings)
- Collaboration / sharing
- Persona / custom agent definitions
- Unique signature features

---

## Phase 2 — Synthesis (Skald)

**Agent:** Skald (Sigrún Ljósbrá)
**Input:** raw research MD from Phase 1.
**Deliverable:** planning MD — feature ambition matrix, must-haves vs stretch goals, differentiators for our own CLI, naming/framing language.

---

## Progress

- [x] Task file written + pushed
- [ ] Phase 1 research agent dispatched
- [ ] Phase 1 deliverable reviewed
- [ ] Phase 2 Skald synthesis dispatched
- [ ] Final planning doc landed
