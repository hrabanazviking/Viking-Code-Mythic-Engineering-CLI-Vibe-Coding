# Mythic Vibe CLI Rebirth Roadmap
## Turning Mythic From a DevOps Command Tool Into a Coding Companion CLI
## 0. Core Product Correction
### What Mythic Is
Mythic is a terminal-based **coding companion CLI**.
It should feel closer to:
 * Claude Code
 * Codex CLI
 * OpenCode
 * Aider chat mode
The primary user experience is:
```bash
mythic

```
Then the user talks naturally to the model.
**Example:**
> "Fix the memory holes in Hermes Agent and write tests for the fix."
> 
Mythic should then inspect the repo, gather context, read memory, search knowledge, propose a plan, suggest patches, request approval, apply changes, run tests, and remember the session.
### What Mythic Is NOT
Mythic is **not** a DevOps command catalog. The user should not have to work mainly through commands like:
 * mythic packet create
 * mythic workflow run
 * mythic knowledge search
 * mythic branch create
 * mythic reflect
 * mythic patch apply
Those can exist internally, but they are not the main product. If the user must memorize many terminal commands to code, the design has failed.

## 1. Prime Directive
When the user types:
```bash
mythic

```
Mythic must launch an interactive coding companion shell. The user should see something like:
> **Mythic Vibe CLI**
>  * **Project:** current repo
>  * **Branch:** current branch
>  * **Model:** configured model
>  * **Knowledge:** connected or disconnected
> Volmarr >
> 
The user talks normally. Slash commands exist only as helper controls.

## 2. Correct Interaction Model
### Normal Use
 1. User types: mythic
 2. Then says: *"Fix the broken memory recall system."*
 3. Mythic internally performs:
   * repo scan
   * file relevance search
   * memory lookup
   * Tailscale knowledge lookup
   * Git status check
   * branch recommendation
   * model prompt construction
   * patch proposal
   * approval request
   * patch application
   * test run
   * session logging
The user should mostly talk, not operate machinery.

### Slash Commands
Slash commands are allowed, but secondary. They serve as control levers, not the main workflow.
| Command | Purpose |
|---|---|
| /help | Show help documentation |
| /status | View current system/repo status |
| /model | Check or switch active model |
| /context | Inspect current prompt context |
| /memory | Query or update long-term session memory |
| /knowledge | Trigger manual private knowledge retrieval |
| /files | List or add tracked files |
| /diff | View proposed modifications |
| /apply | Approve and apply the current patch |
| /reject | Reject the proposed patch |
| /test | Run the project test suite |
| /branch | Manage git branches |
| /commit | Commit approved changes |
| /pr | Draft a GitHub pull request |
| /tui | Launch the full terminal user interface |
| /exit | Safely close the interactive companion |

## 3. Reinterpret Existing Code
Existing command code should not be deleted just because the UX was wrong. Most existing commands should become internal tools used by the companion shell.
### Old Role to New Role
| Existing System | New Role |
|---|---|
| **packet commands** | internal context and prompt builder |
| **workflow commands** | internal planning engine |
| **reflect commands** | automatic session memory |
| **knowledge commands** | internal retrieval tool |
| **branch commands** | internal Git tool with approval |
| **patch commands** | internal edit proposal and approval system |
| **doctor commands** | internal health check |
| **status commands** | internal project state reader |
| **TUI** | core visual interface |

## 4. What Gets Quarantined
Only quarantine things that are not actually part of the usable code product.
 * **Quarantine Candidates:**
   * Unrelated images and old generated art
   * Huge unused media files
   * Duplicate documentation and random research dumps
   * Broken release artifacts and outdated packaging debris
   * Abandoned experiments not imported by runtime
   * Vendor copies not actually used
   * Dead generated output and obsolete CI artifacts
 * **Do NOT Quarantine:**
   * CLI shell code & TUI code
   * Model provider code
   * Packet, memory, and workflow systems
   * GitHub & patch code
   * Knowledge base and repo scanning code
   * Tests for active systems
   
## 5. Preservation Rule
> **Important:** No coded feature is deleted casually.
> 
If a coded feature is not part of the first working companion shell, it should be preserved as dormant code, documented, and possibly hidden from the default UX.
The goal is not to destroy the old build, but to turn it into engine parts behind the correct interface.
## Implementation Phases

### Phase 0: UX Reversal
 * **Goal:** Make the product definition unambiguous.
 * **Tasks:**
   * Create docs/PRODUCT_INTENT.md.
   * State clearly that Mythic is a Coding Companion CLI and DevOps-style subcommands are not the main UX.
   * Define mythic as the primary entrypoint, slash commands as secondary controls, and natural language prompting as the main interaction.
 * **Success Criteria:** Any coding AI reading the repo understands the user wants an interactive coding companion shell, not a pile of terminal subcommands.

### Phase 1: Entrypoint Rebuild
 * **Goal:** Make mythic launch the companion shell by default.
 * **Current Problem:** The project currently behaves like a command catalog.
 * **Required Behavior:** mythic starts interactive mode. Optional admin mode remains available via mythic --help or mythic admin.
 * **Tasks:**
   * Update console entrypoint behavior.
   * Add interactive_shell.py.
   * Make default invocation start chat shell, moving old subcommands behind advanced/admin mode.
   * Preserve backwards compatibility where reasonable.
 * **Success Criteria:** Typing mythic opens an interactive prompt.

### Phase 2: Minimal Interactive Shell
 * **Goal:** Create the simplest useful companion loop.
 * **Required Features:** Startup banner, current directory/Git repo detection, configured model display, user input loop, slash command routing, normal prompt routing, and graceful exit.
 * **Minimum Commands:** /help, /status, /model, /exit.
 * **Success Criteria:** The user can type mythic, enter *"What project am I in?"*, and Mythic responds with useful project context.

### Phase 3: Context Builder
 * **Goal:** Make Mythic understand the current repo.
 * **Required Abilities:** Detect project root, read Git status, list important files, detect language/framework, identify tests/package files, and build compact context summaries.
 * **User Experience:** User says *"Find the memory system in this repo."* Mythic searches and summarizes relevant files automatically.
 * **Success Criteria:** Natural language requests can trigger repo inspection without the user typing manual scan commands.

### Phase 4: Model Router
 * **Goal:** Let Mythic talk to affordable models.
 * **Supported Backends:** OpenAI-compatible APIs, OpenRouter, Qwen, DeepSeek, Kimi, Alibaba coding models, LM Studio, Ollama, OpenCode Go, ChatGPT Codex AUTH, Gemini CLI AUTH, Grok AUTH, Mistral, Claude AUTH, another others not listed, Ollama, and other local servers.
 * **Requirements:** Provider-neutral interface, configuration file management, environment-variable API keys, model switching inside the shell, and zero provider lock-in.
 * **Slash Commands:** /model, /model list, /model set, /provider set.
 * **Success Criteria:** User can seamlessly talk to a configured model from inside Mythic.

### Phase 5: Memory Spine
 * **Goal:** Prevent memory holes.
 * **Required Memory:** Session summaries, project decisions, tasks, files touched, failed attempts, successful fixes, and designated next steps.
 * **Storage:** Use local SQLite first. Suggested path: .mythic/memory.sqlite.
 * **User Experience:** User says *"What were we doing last time?"* Mythic answers directly from memory.
 * **Success Criteria:** Mythic can accurately resume a project after days or weeks.

### Phase 6: Tailscale Knowledge Reader
 * **Goal:** Connect Mythic to Volmarr’s private coding knowledge.
 * **Requirements:** Read-only by default, SQLite support (and PostgreSQL if needed), configurable host/path, safe query interface, and summaries returned straight into context.
 * **Slash Commands:** /knowledge status, /knowledge search memory, /knowledge sources.
 * **User Experience:** User says: *"Search my knowledge database for earlier ideas about Hermes memory."* Mythic searches the Tailscale-accessible database and summarizes findings.
 * **Success Criteria:** Private knowledge can be used fluidly in coding conversations.

### Phase 7: GitHub Workspace System
 * **Goal:** Allow Mythic to manage local working directories.
 * **Requirements:** Clone repos into a Mythic workspace, open existing repos, detect current repo, create branches, track branches, and prepare PRs.
 * **Default Workspace:** ~/.mythic-vibe/workspaces/
 * **User Experience:** User says: *"Clone my Hermes fork and make a branch for fixing memory."* Mythic proposes the action and asks approval before making changes.
 * **Success Criteria:** GitHub workflows happen through conversation.

### Phase 8: Patch Proposal System
 * **Goal:** Let Mythic propose edits safely.
 * **Requirements:** Model proposes changes, Mythic shows a diff, user approves/rejects, no automatic destructive edits, edits are logged, and patches can be easily reverted.
 * **Slash Commands:** /diff, /apply, /reject.
 * **User Experience:** Mythic says: *"I found the likely fix. Here is the diff. Apply it?"* User says: *"yes"* or *"change it to use SQLite instead"*.
 * **Success Criteria:** Coding happens conversationally with clear approval checkpoints.

### Phase 9: Test Runner
 * **Goal:** Let Mythic run project tests.
 * **Requirements:** Detect likely test commands, ask before running long commands, capture output, summarize failures, and feed failures back into the model loop for self-healing.
 * **Slash Commands:** /test, /test last, /test command.
 * **User Experience:** User says: *"Run the tests and fix what fails."* Mythic runs tests, summarizes errors, and proposes the next fix.
 * **Success Criteria:** Mythic can complete inspect, patch, test, and fix loops on its own.

### Phase 10: TUI Integration
 * **Goal:** Keep TUI as core, not optional. It is the visual cockpit for the companion shell.
 * **Required Views:** Chat, files, diff, memory, knowledge, Git status, tasks, and model status.
 * **User Experience:** User types /tui and Mythic opens the unified layout.
 * **Success Criteria:** TUI assists the companion workflow instead of acting like a detached DevOps dashboard.

### Phase 11: Legacy Command Demotion
 * **Goal:** Stop exposing old command-catalog UX as the primary product.
 * **Actions:** Keep old commands if useful but hide them behind mythic admin, use them internally as tools, remove them from primary README flows, and stop documenting them as the main interface.
 * **Success Criteria:** Project onboarding documentation teaches users to simply type mythic and talk.

### Phase 12: Documentation Rewrite
 * **Goal:** Make the project impossible for future coding AIs to misunderstand.
 * **Required Docs:**
   * docs/PRODUCT_INTENT.md
   * docs/INTERACTIVE_SHELL.md
   * docs/SLASH_COMMANDS.md
   * docs/INTERNAL_TOOLS.md
   * docs/MEMORY.md
   * docs/KNOWLEDGE.md
   * docs/GITHUB_WORKSPACE.md
   * docs/TUI.md
   * docs/DAILY_WORKFLOW.md
 * **README Core Instruction:** Mythic is used like this:
   ```bash
   
   ```
mythic
```
  Then talk to it.
* **Success Criteria:** No future AI model mistakes Mythic for a DevOps command toolkit.

### Phase 13: Quarantine Non-Code Debris
* **Goal:** Clean repo without damaging useful systems.
* **Move Destination:** `graveyard/`
* **Quarantine Criteria:** Move only unused media, duplicate docs, obsolete release artifacts, unused packaging output, dead experiments, and unused research dumps. Do not move any code that could become part of the companion shell.
* **Success Criteria:** The repo becomes clean and streamlined without sacrificing valuable code assets.

### Phase 14: Internal Tool Registry
* **Goal:** Turn old subcommands into callable tools for the agent.
* **Tool Examples:** Repo scanner, memory search, knowledge search, packet builder, branch manager, patch applier, test runner, and reflection logger.
* **User Experience:** User talks naturally; Mythic decides behind the scenes which internal tool to execute.
* **Success Criteria:** The old codebase successfully becomes the functional machinery of the new companion.

### Phase 15: Companion Planning Loop
* **Goal:** Make Mythic reason before editing.
* **Execution Loop:**
  1. Understand request
  2. Inspect repo
  3. Retrieve memory & knowledge
  4. Propose structured plan
  5. Ask approval if needed
  6. Edit, test, and summarize
  7. Remember the results
* **Success Criteria:** Mythic behaves like an actual coding partner rather than a command runner.

### Phase 16: Commit and PR Workflow
* **Goal:** Add a safe GitHub completion flow.
* **Requirements:** Show diff before commit, ask before commit/push/PR, generate automated PR titles/descriptions, and preserve clean branch history.
* **User Experience:** User says: *"Commit this and make a PR."* Mythic shows the planned actions and requests confirmation.
* **Success Criteria:** Complete repository synchronization is safely handled through conversation.

### Phase 17: Affordable Model Optimization
* **Goal:** Make Mythic highly performant with cost-effective models.
* **Features:** Compact context building, file relevance filtering, memory summarization, knowledge excerpts, patch-only formatting prompts, automatic retry loops, and backup model fallbacks.
* **Success Criteria:** Mythic functions perfectly with Qwen, DeepSeek, Kimi, OpenRouter, Alibaba, and local LLM endpoints.

### Phase 18: Reintegrate Advanced Existing Features
* **Goal:** Re-introduce complex legacy features once the core companion works.
* **Candidates:** Advanced workflow/packet systems, agent control planes, release tooling, richer provider adapters, advanced TUI views, and automation helpers.
* **Core Rule:** One feature at a time. Each reintegrated component must directly serve the interactive companion shell.
* **Success Criteria:** Old complex code returns only when it strengthens the companion UX.

---

## Final Success State

The final user workflow is clean, unified, and powerful:

```bash
cd ~/Projects/Hermes-Fork
mythic

```
> *"Fix the memory recall holes. Use my knowledge database if needed. Make a branch, propose a patch, run tests, and help me get this ready for a PR."*
> 
Mythic handles the machinery. The user talks. The forge remembers.

