# Mythic Engineering Plundering Workflow

## Metadata

```yaml
title: "Mythic Engineering Plundering Workflow"
version: "1.0.0"
status: "repo-ready"
license_context: "Designed for Apache-2.0-compatible reuse workflows"
primary_use_case: "Systematically studying, adapting, and integrating useful architecture/code from open-source AI CLI projects"
method: "Architecture-first, document-guided, role-orchestrated, verification-heavy plundering"
recommended_location: "docs/plunder/MYTHIC_ENGINEERING_PLUNDERING_WORKFLOW.md"
```

---

# 1. Purpose

This workflow defines a **Mythic Engineering method for lawful, structured open-source plundering**.

In this context, **plundering** does not mean blind copy-paste. It means:

- studying open-source systems deeply
- extracting reusable architectural patterns
- adapting compatible code lawfully
- preserving attribution
- keeping licenses clean
- integrating only what fits the receiving system
- documenting every decision so the project remembers what happened

The goal is to turn external open-source projects into **disciplined raw material**, not chaotic grafts.

> Take the steel.  
> Keep the maker’s mark.  
> Forge it into your own weapon.

---

# 2. Core Philosophy

Mythic Engineering treats software as a living system.

A plundering workflow must protect:

- **Vision**
- **Architecture**
- **Domain ownership**
- **Interface truth**
- **Continuity**
- **Licensing integrity**
- **Verification**
- **Long-term maintainability**

The purpose is not to make the project bigger.

The purpose is to make the project **stronger**.

---

# 3. Non-Negotiable Laws

## 3.1 Lawful Plundering Law

Only plunder from sources whose licenses allow reuse.

Preferred licenses:

- Apache License 2.0
- MIT
- BSD-style permissive licenses

For this workflow, the cleanest target is:

```text
Apache-2.0 upstream -> Apache-2.0 project
```

---

## 3.2 Attribution Law

Never hide upstream origin.

If code, architecture, prompts, config schemas, tests, or documentation structures are adapted from an upstream project, record it.

Required artifacts:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/<UPSTREAM>_PLUNDER_MAP.md
```

---

## 3.3 Boundary Law

Never graft foreign architecture into your project without assigning ownership.

Every imported idea must answer:

```text
What local domain owns this?
What local module should contain it?
What public interface will expose it?
What must it never control?
```

---

## 3.4 Verification Law

Do not trust copied code merely because it came from a respected project.

Every plundered subsystem must pass:

- license review
- architecture review
- security review
- tests
- manual diff inspection
- documentation update
- integration verification

---

## 3.5 No Branding Theft Law

Apache-2.0 allows reuse of code.

It does **not** allow stealing project identity, trademarks, logos, official names, or implied endorsement.

Safe:

```md
This project includes code adapted from OpenAI Codex CLI.
```

Unsafe:

```md
This is the official OpenAI Codex CLI fork.
```

---

# 4. Core Roles

Use the six Mythic Engineering roles as a plundering crew.

## 4.1 Skald

**Purpose:** Name and frame the plundering target.

Use when:

- deciding why a subsystem matters
- naming the local adaptation
- writing project-facing explanations
- turning vague interest into clear purpose

Outputs:

```text
docs/plunder/<TARGET>_VISION.md
README section
subsystem name
short conceptual framing
```

Example invocation:

```text
Skald, reveal the true purpose of adapting Aider's repository map into Mythic CLI and give this subsystem a clear name, identity, and README introduction.
```

---

## 4.2 Architect

**Purpose:** Define ownership, boundaries, and integration strategy.

Use when:

- deciding whether a subsystem belongs in the project
- assigning local domain ownership
- preventing architecture drift
- designing the target module structure
- creating the plunder map

Outputs:

```text
docs/plunder/<TARGET>_PLUNDER_MAP.md
DOMAIN_MAP.md updates
ARCHITECTURE.md updates
INTERFACE.md updates
refactor plan
```

Example invocation:

```text
Architect, define exact ownership and boundaries for adapting Qwen Code's subagent and skill systems into this project.
```

---

## 4.3 Cartographer

**Purpose:** Map upstream structure and local impact.

Use when:

- scanning an upstream repository
- identifying useful folders/files
- tracing dependencies
- mapping what would be affected locally

Outputs:

```text
upstream repo map
local impact map
dependency map
integration route
risk terrain
```

Example invocation:

```text
Cartographer, map the Goose repository and identify which parts are relevant to extensions, recipes, providers, permissions, and local agent architecture.
```

---

## 4.4 Forge Worker

**Purpose:** Implement the adaptation.

Use when:

- copying or rewriting code
- renaming modules
- integrating tests
- wiring local interfaces
- converting TypeScript/Rust/Python ideas into local style

Outputs:

```text
adapted code
tests
migration scripts
module README files
working implementation
```

Example invocation:

```text
Forge Worker, implement the local patch engine based on the selected ideas from Aider and Codex, preserving attribution and following our project style.
```

---

## 4.5 Auditor

**Purpose:** Verify legality, correctness, safety, and invariants.

Use when:

- checking license compliance
- reviewing attribution
- finding security risks
- inspecting copied code
- confirming tests
- rejecting unsafe grafts

Outputs:

```text
license review
security review
test results
invariant checklist
risk report
blocking issues
```

Example invocation:

```text
Auditor, review this plundered subsystem for license compliance, unsafe assumptions, missing attribution, hidden coupling, and failed invariants.
```

---

## 4.6 Scribe

**Purpose:** Preserve memory and documentation.

Use when:

- updating NOTICE files
- updating THIRD_PARTY_NOTICES.md
- writing DEVLOG entries
- documenting local changes
- maintaining plunder maps
- preserving rationale

Outputs:

```text
NOTICE
THIRD_PARTY_NOTICES.md
DEVLOG.md entry
DECISIONS entry
README updates
module docs
```

Example invocation:

```text
Scribe, capture this plundering session, update THIRD_PARTY_NOTICES.md, and write a clear DEVLOG entry explaining what was adapted and why.
```

---

# 5. Required Plundering Artifacts

Every plundering operation should create or update these files.

## 5.1 Global Files

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/PLUNDER_INDEX.md
docs/plunder/MYTHIC_ENGINEERING_PLUNDERING_WORKFLOW.md
```

---

## 5.2 Per-Upstream Files

For each upstream project:

```text
docs/plunder/<UPSTREAM>_PLUNDER_GUIDE.md
docs/plunder/<UPSTREAM>_PLUNDER_MAP.md
docs/plunder/<UPSTREAM>_LICENSE_REVIEW.md
docs/plunder/<UPSTREAM>_ADAPTATION_LOG.md
```

Example:

```text
docs/plunder/AIDER_PLUNDER_GUIDE.md
docs/plunder/AIDER_PLUNDER_MAP.md
docs/plunder/AIDER_LICENSE_REVIEW.md
docs/plunder/AIDER_ADAPTATION_LOG.md
```

---

## 5.3 Per-Subsystem Files

For each adapted subsystem:

```text
src/<domain>/<subsystem>/README.md
src/<domain>/<subsystem>/INTERFACE.md
src/<domain>/<subsystem>/ATTRIBUTION.md
tests/<domain>/<subsystem>/
```

---

# 6. The Plundering Lifecycle

## Phase 0: Wyrd Gate

**Question:** Should this be plundered at all?

Before touching code, define:

```text
What problem are we solving?
Why is this upstream project relevant?
What exact subsystem is interesting?
Is reuse better than building from scratch?
What would be dangerous to copy?
```

### Required Output

```md
## Plunder Intent

Upstream:
Target subsystem:
Local problem:
Reason to study:
Reason to adapt:
Reason not to blindly copy:
```

### Role

Primary: **Skald**  
Secondary: **Architect**

---

## Phase 1: License Gate

**Question:** Are we legally allowed to reuse this?

Check:

- license file
- NOTICE file
- SPDX headers
- third-party notices
- trademark/branding warnings
- copied dependency licenses
- generated code notices
- commercial restriction warnings

### Required Output

```md
# License Review

## Upstream

Project:
Repository:
License:
NOTICE file:
Third-party notices:
Trademark concerns:

## Compatibility

Local license:
Compatible:
Conditions:

## Required Actions

- [ ] Preserve license
- [ ] Preserve notices
- [ ] Mark modified files
- [ ] Add THIRD_PARTY_NOTICES.md entry
- [ ] Avoid upstream branding
```

### Role

Primary: **Auditor**  
Secondary: **Scribe**

---

## Phase 2: Cartography Gate

**Question:** What exactly exists upstream?

Map the upstream repository.

Capture:

- folder structure
- major modules
- CLI entry points
- core engine
- tool system
- config system
- tests
- docs
- license files
- interesting subsystems
- risky subsystems

### Suggested Commands

```bash
find . -maxdepth 2 -type d | sort
find . -maxdepth 3 -type f | sort
git log --oneline -n 20
```

### Required Output

```md
# Upstream Cartography

## Repository Shape

```text
<folder map>
```

## Major Domains

| Domain | Path | Purpose | Reuse Value |
|---|---|---|---|

## Interesting Plunder Targets

| Target | Path | Why Interesting | Risk |
|---|---|---|---|

## Do Not Copy Blindly

| Area | Reason |
|---|---|
```

### Role

Primary: **Cartographer**  
Secondary: **Architect**

---

## Phase 3: Plunder Target Selection

**Question:** What are we actually taking?

Every target must be categorized.

## 3.1 Target Categories

| Category | Meaning |
|---|---|
| `pattern` | Study and recreate the idea without copying code |
| `adaptation` | Copy/rework portions of implementation |
| `direct-copy` | Copy file or chunk with minimal changes |
| `rewrite` | Use upstream as reference, but implement locally from scratch |
| `avoid` | Do not use |

## 3.2 Target Table

```md
| Upstream Path | Local Target | Category | Reason | Attribution Needed | Risk |
|---|---|---|---|---|---|
| aider/repomap.py | mythic_cli/repomap/ | adaptation | repo map logic | yes | medium |
| codex-rs/apply-patch | mythic_cli/patching/ | pattern | patch safety | yes if code copied | medium |
| packages/core/src/skills | .mythic/skills | pattern/adaptation | skill architecture | yes | low |
```

### Role

Primary: **Architect**  
Secondary: **Auditor**

---

## Phase 4: Local Ownership Assignment

**Question:** Where does the plundered idea belong?

Before importing anything, update local ownership docs.

Required docs:

```text
DOMAIN_MAP.md
ARCHITECTURE.md
INTERFACE.md
COMPONENT_INDEX.md
```

### Ownership Template

```md
## Subsystem Ownership

Name:
Local path:
Owning domain:
Purpose:
Public interface:
Inputs:
Outputs:
Allowed side effects:
Forbidden responsibilities:
Upstream inspiration:
Attribution file:
Tests:
```

### Role

Primary: **Architect**  
Secondary: **Scribe**

---

## Phase 5: Adaptation Strategy

**Question:** How do we transform upstream code into local code?

Choose one strategy.

## 5.1 Strategy A: Pattern Extraction

Use when:

- upstream language differs from local language
- implementation is too tied to service-specific assumptions
- architecture is valuable but code is not directly reusable

Output:

```md
## Pattern Extracted

Upstream pattern:
Local reinterpretation:
What changed:
What was intentionally not copied:
```

---

## 5.2 Strategy B: Clean-Room Inspired Rewrite

Use when:

- you want lower licensing complexity
- the idea matters more than the code
- upstream implementation is overbuilt
- you need local style

Output:

```md
## Inspired Rewrite

Studied source:
Rewritten local file:
Shared concepts:
Copied code:
Attribution:
```

---

## 5.3 Strategy C: Adapted Code

Use when:

- code is directly useful
- license allows it
- attribution is preserved
- file-level modification notices are added

Required file header:

```python
# Portions adapted from <UPSTREAM_REPO>.
# Upstream project licensed under Apache License 2.0.
# Modified by <YOUR_PROJECT>, 2026.
# Licensed under the Apache License, Version 2.0.
```

---

## 5.4 Strategy D: Direct Copy

Use rarely.

Only allowed when:

- license is verified
- file is needed mostly intact
- upstream notices are preserved
- local changes are documented
- purpose is clear

Direct-copy files must include:

```text
ATTRIBUTION.md
original source URL
commit hash
license
local modifications
```

### Role

Primary: **Forge Worker**  
Secondary: **Auditor**

---

## Phase 6: Branch and Commit Ritual

Never plunder directly on main.

### Branch Naming

```bash
git checkout -b plunder/<upstream>-<subsystem>
```

Examples:

```bash
git checkout -b plunder/aider-repomap
git checkout -b plunder/codex-patch-engine
git checkout -b plunder/goose-recipes
```

### Commit Message Template

```text
Adapt <subsystem> patterns from <upstream>

- Adds Apache-2.0 attribution
- Preserves upstream notices where applicable
- Marks modified files
- Updates THIRD_PARTY_NOTICES.md
- Updates plunder map
- Reworks implementation for local architecture
```

### Role

Primary: **Forge Worker**  
Secondary: **Scribe**

---

## Phase 7: Integration Gate

**Question:** Does it fit the local system?

Check:

- Does it belong in the assigned domain?
- Does it violate boundaries?
- Does it introduce foreign naming drift?
- Does it create dependency sprawl?
- Does it duplicate existing functionality?
- Does it make the project harder to explain?
- Does it preserve the local architecture’s identity?

### Integration Checklist

```md
## Integration Review

- [ ] Local domain ownership is clear
- [ ] Public interface is documented
- [ ] No hidden dependency sprawl
- [ ] No foreign branding leaked into runtime UX
- [ ] No upstream service-specific assumptions remain
- [ ] Tests exist
- [ ] Docs updated
- [ ] Attribution complete
```

### Role

Primary: **Architect**  
Secondary: **Auditor**

---

## Phase 8: Verification Gate

**Question:** Does it work?

Run the commands that apply to your repo:

```bash
pytest
npm test
cargo test
ruff check .
mypy .
```

### Verification Checklist

```md
## Verification

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Type checks pass
- [ ] Lint checks pass
- [ ] Manual smoke test passed
- [ ] Git diff inspected
- [ ] No secrets copied
- [ ] No generated junk copied
- [ ] No accidental branding copied
- [ ] No unwanted telemetry copied
```

### Role

Primary: **Auditor**  
Secondary: **Forge Worker**

---

## Phase 9: Documentation Gate

**Question:** Will future-you understand what happened?

Update:

```text
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/<UPSTREAM>_PLUNDER_MAP.md
docs/plunder/<UPSTREAM>_ADAPTATION_LOG.md
DEVLOG.md
ARCHITECTURE.md
DOMAIN_MAP.md
INTERFACE.md
README.md
```

### Adaptation Log Template

```md
# <Upstream> Adaptation Log

## Date

YYYY-MM-DD

## Upstream

Repository:
Commit:
License:
Docs:

## Adapted Subsystem

Name:
Local path:
Upstream path:
Strategy: pattern | rewrite | adaptation | direct-copy

## What Changed

## What Was Preserved

## What Was Rewritten

## What Was Rejected

## Tests Run

## Attribution Updated

- [ ] NOTICE
- [ ] THIRD_PARTY_NOTICES.md
- [ ] File headers
- [ ] README
```

### Role

Primary: **Scribe**  
Secondary: **Auditor**

---

## Phase 10: Final Merge Gate

**Question:** Is this ready to become part of the living system?

Before merging:

```md
## Final Merge Checklist

- [ ] License reviewed
- [ ] Attribution added
- [ ] Plunder map updated
- [ ] Architecture updated
- [ ] Interface docs updated
- [ ] Tests pass
- [ ] Risk reviewed
- [ ] No secrets copied
- [ ] No branding misuse
- [ ] No telemetry surprise
- [ ] DEVLOG updated
- [ ] Decision recorded if major
```

### Role

Primary: **Auditor**  
Secondary: **Architect + Scribe**

---

# 7. Plunder Source Database

This table tracks high-value AI CLI projects and the likely useful steel inside each.

## 7.1 OpenAI Codex CLI

```yaml
name: "OpenAI Codex CLI"
repository: "https://github.com/openai/codex"
license: "Apache-2.0"
likely_plunder_targets:
  - "Rust CLI architecture"
  - "sandboxing"
  - "approval policy"
  - "patch application"
  - "Git utilities"
  - "MCP integration"
  - "TUI patterns"
  - "config.toml system"
  - "thread/session storage"
  - "skills"
primary_local_use:
  - "Patch Forge"
  - "Permission Law"
  - "CLI command structure"
  - "MCP bridge"
risk_notes:
  - "Avoid OpenAI branding"
  - "Rewrite service-specific auth"
  - "Preserve NOTICE"
```

---

## 7.2 Google Gemini CLI

```yaml
name: "Google Gemini CLI"
repository: "https://github.com/google-gemini/gemini-cli"
license: "Apache-2.0"
likely_plunder_targets:
  - "TypeScript core/CLI split"
  - "GEMINI.md context pattern"
  - "custom commands"
  - "MCP integration"
  - "config layering"
  - "approval modes"
  - "sandboxing"
  - "structured output"
  - "checkpointing"
  - "subagents"
  - "skills"
primary_local_use:
  - "MYTHIC.md context system"
  - ".mythic/commands"
  - ".mythic/agents"
  - ".mythic/skills"
risk_notes:
  - "Avoid Google/Gemini branding"
  - "Rewrite Google-specific auth"
```

---

## 7.3 Qwen Code

```yaml
name: "Qwen Code"
repository: "https://github.com/QwenLM/qwen-code"
license: "Apache-2.0"
based_on: "Google Gemini CLI"
likely_plunder_targets:
  - "Qwen parser adaptations"
  - "SubAgents"
  - "Skills"
  - "Headless mode"
  - "MCP"
  - "approval modes"
  - "sandboxing"
  - "hooks"
  - "scheduled tasks"
  - "LSP support"
  - "model provider system"
  - "extensions"
primary_local_use:
  - "Multi-provider parser layer"
  - "role agents"
  - "hook gates"
  - "LSP/code intelligence"
risk_notes:
  - "Preserve Qwen and inherited Gemini notices where relevant"
  - "Avoid Alibaba/Qwen branding"
  - "Rewrite provider-specific auth"
```

---

## 7.4 Aider

```yaml
name: "Aider"
repository: "https://github.com/Aider-AI/aider"
license: "Apache-2.0"
likely_plunder_targets:
  - "repository map"
  - "Tree-sitter symbol extraction"
  - "Git-aware editing"
  - "search/replace edit blocks"
  - "unified diff formats"
  - "architect/editor split"
  - "lint/test repair loop"
  - "slash commands"
  - "watch mode"
  - "model aliases"
primary_local_use:
  - "Repo Cartographer"
  - "Patch Forge"
  - "Git Safety Law"
  - "Repair Loop"
risk_notes:
  - "Avoid Aider branding"
  - "Review analytics defaults"
```

---

## 7.5 Goose

```yaml
name: "goose"
repository: "https://github.com/aaif-goose/goose"
license: "Apache-2.0"
likely_plunder_targets:
  - "local agent platform architecture"
  - "desktop/CLI/API split"
  - "MCP extensions"
  - "provider system"
  - "custom distributions"
  - "recipes"
  - "subagents"
  - "skills"
  - "permission modes"
  - "prompt templates"
  - "project hints"
  - "security layers"
primary_local_use:
  - "Mythic Recipes"
  - "Extension ecosystem"
  - "provider abstraction"
  - "custom distro architecture"
risk_notes:
  - "Avoid Goose/AAIF/Linux Foundation/Block branding"
  - "Do not silently inherit autonomous defaults"
  - "Review telemetry"
```

---

## 7.6 Mistral Vibe

```yaml
name: "Mistral Vibe"
repository: "https://github.com/mistralai/mistral-vibe"
license: "Apache-2.0"
likely_plunder_targets:
  - "Python agent loop"
  - "programmatic mode"
  - "Textual-style terminal UI"
  - "built-in tools"
  - "tool permissions"
  - "agent profiles"
  - "subagents"
  - "structured user questions"
  - "skills"
  - "MCP"
  - "ACP"
  - "local/offline model support"
  - "trusted folders"
  - "session logging/resume"
primary_local_use:
  - "Python Mythic CLI core"
  - "agent profile system"
  - "skills"
  - "ACP bridge"
risk_notes:
  - "Avoid Mistral/Devstral branding"
  - "Review telemetry and auto-update behavior"
```

---

## 7.7 Kimi CLI

```yaml
name: "Kimi CLI / Kimi Code CLI"
repository: "https://github.com/MoonshotAI/kimi-cli"
license: "Apache-2.0"
likely_plunder_targets:
  - "CLI agent architecture"
  - "skills"
  - "MCP"
  - "ACP"
  - "terminal UX"
  - "config/provider architecture"
  - "tests"
  - "web UI/session management"
primary_local_use:
  - "skills"
  - "terminal agent UX"
  - "MCP/ACP polish"
risk_notes:
  - "Preserve MoonshotAI notice"
  - "Preserve inherited OpenAI Codex attribution where applicable"
  - "Avoid Kimi/Moonshot branding"
```

---

# 8. Standard Plunder Map Template

Use this for every upstream project.

```md
# <UPSTREAM> Plunder Map

## Metadata

```yaml
upstream_name: ""
repository: ""
license: ""
notice_file: ""
checked_date: "YYYY-MM-DD"
local_project: ""
local_license: ""
status: "studying | adapting | integrated | rejected"
```

---

## 1. Why This Upstream Matters

## 2. License Review

## 3. Upstream Repo Map

```text
<folder map>
```

## 4. Interesting Targets

| Upstream Path | Local Target | Strategy | Value | Risk |
|---|---|---|---|---|

## 5. Do Not Copy Blindly

| Area | Reason |
|---|---|

## 6. Local Ownership

| Local Domain | Local Path | Responsibility |
|---|---|---|

## 7. Adaptation Plan

## 8. Attribution Requirements

## 9. Tests Required

## 10. Final Decision

```yaml
decision: "adapt | pattern-only | reject | postpone"
reason: ""
approved_by:
  - "Architect"
  - "Auditor"
  - "Scribe"
```
```

---

# 9. Standard License Review Template

```md
# <UPSTREAM> License Review

## Upstream

Project:
Repository:
License:
License URL:
NOTICE file:
Third-party notices:
SPDX headers:

## Local Project

Project:
License:
Compatible:

## Obligations

- [ ] Preserve Apache-2.0 license
- [ ] Preserve upstream copyright notices
- [ ] Preserve NOTICE contents where applicable
- [ ] Mark modified files
- [ ] Add THIRD_PARTY_NOTICES.md entry
- [ ] Avoid trademark misuse
- [ ] Avoid false endorsement
- [ ] Review third-party dependencies

## Risk Notes

## Decision

```yaml
approved_for_reuse: true
approved_reuse_types:
  - pattern
  - adaptation
  - direct-copy
restrictions:
  - ""
```
```

---

# 10. Standard File Header Templates

## Python

```python
# Portions adapted from <UPSTREAM_REPO>.
# Upstream project licensed under Apache License 2.0.
# Modified by <LOCAL_PROJECT>, 2026.
# Licensed under the Apache License, Version 2.0.
```

## TypeScript

```ts
// Portions adapted from <UPSTREAM_REPO>.
// Upstream project licensed under Apache License 2.0.
// Modified by <LOCAL_PROJECT>, 2026.
// Licensed under the Apache License, Version 2.0.
```

## Rust

```rust
// Portions adapted from <UPSTREAM_REPO>.
// Upstream project licensed under Apache License 2.0.
// Modified by <LOCAL_PROJECT>, 2026.
// Licensed under the Apache License, Version 2.0.
```

## Markdown

```md
<!--
Portions adapted from <UPSTREAM_REPO>.
Upstream project licensed under Apache License 2.0.
Modified by <LOCAL_PROJECT>, 2026.
Licensed under the Apache License, Version 2.0.
-->
```

---

# 11. Standard THIRD_PARTY_NOTICES Entry

```md
## <UPSTREAM_PROJECT>

Project: <UPSTREAM_PROJECT>  
Repository: <UPSTREAM_REPO>  
License: Apache License 2.0  

Usage:

This project includes or adapts selected portions of <UPSTREAM_PROJECT>, especially architectural patterns related to:

- <target 1>
- <target 2>
- <target 3>

This project is independent and is not affiliated with, endorsed by, or sponsored by <UPSTREAM_OWNER>.
```

---

# 12. Standard NOTICE Entry

```md
## <UPSTREAM_PROJECT>

This project includes or adapts selected portions of software from:

Project: <UPSTREAM_PROJECT>  
Repository: <UPSTREAM_REPO>  
License: Apache License 2.0

This project is independent and is not affiliated with, endorsed by, or sponsored by <UPSTREAM_OWNER>.
```

---

# 13. Mythic Engineering Plundering Checklist

Use this checklist before every merge.

```md
# Plundering Merge Checklist

## Intent

- [ ] The purpose of this plunder is clear
- [ ] The local problem is documented
- [ ] The upstream target is specific
- [ ] The target is worth adapting instead of rebuilding

## License

- [ ] License verified
- [ ] NOTICE checked
- [ ] Third-party notices checked
- [ ] Trademark/branding risk checked
- [ ] Modified files marked
- [ ] THIRD_PARTY_NOTICES.md updated

## Architecture

- [ ] Local owning domain assigned
- [ ] DOMAIN_MAP.md updated
- [ ] ARCHITECTURE.md updated
- [ ] INTERFACE.md updated
- [ ] No boundary violation introduced
- [ ] No duplicate subsystem created

## Code

- [ ] Adapted code follows local style
- [ ] Upstream-specific names removed where inappropriate
- [ ] Provider/auth/service assumptions rewritten
- [ ] Telemetry reviewed
- [ ] Auto-update behavior reviewed
- [ ] Dangerous defaults reviewed

## Verification

- [ ] Unit tests added
- [ ] Integration tests added if needed
- [ ] Lint/type checks pass
- [ ] Manual smoke test done
- [ ] Diff reviewed
- [ ] No secrets copied
- [ ] No generated junk copied

## Documentation

- [ ] Plunder map updated
- [ ] Adaptation log updated
- [ ] README updated if user-facing
- [ ] DEVLOG updated
- [ ] DECISIONS entry added if architectural
- [ ] Scribe pass complete
```

---

# 14. Recommended Repository Layout

```text
project/
├── LICENSE
├── NOTICE
├── THIRD_PARTY_NOTICES.md
├── README.md
├── MYTHIC_ENGINEERING.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_MAP.md
│   ├── COMPONENT_INDEX.md
│   ├── DATA_FLOW.md
│   ├── DEVLOG.md
│   ├── DECISIONS/
│   └── plunder/
│       ├── PLUNDER_INDEX.md
│       ├── MYTHIC_ENGINEERING_PLUNDERING_WORKFLOW.md
│       ├── AIDER_PLUNDER_GUIDE.md
│       ├── AIDER_PLUNDER_MAP.md
│       ├── CODEX_PLUNDER_GUIDE.md
│       ├── CODEX_PLUNDER_MAP.md
│       └── ...
├── src/
│   └── <domain>/
│       ├── README.md
│       ├── INTERFACE.md
│       └── ATTRIBUTION.md
├── tests/
└── tasks/
    └── <task>_GOALS.md
```

---

# 15. The Daily Plundering Ritual

Use this for active integration days.

## Opening

1. **Cartographer** reads the current plunder map.
2. **Scribe** reads the latest DEVLOG entry.
3. **Architect** restates the local boundary.
4. **Auditor** restates the license obligations.

## Main Work

1. **Cartographer** maps upstream target files.
2. **Architect** selects strategy: pattern, rewrite, adaptation, or direct copy.
3. **Forge Worker** implements only the scoped change.
4. **Auditor** checks tests, license, and invariants.
5. **Scribe** updates docs.

## Closing

1. Inspect diff.
2. Run tests.
3. Update plunder map.
4. Update THIRD_PARTY_NOTICES.md.
5. Update DEVLOG.md.
6. Commit with attribution.

---

# 16. Example Invocation Chain

```text
Skald, frame why Aider's repository map matters for Mythic CLI and give the local subsystem a true name.

Architect, define exact ownership boundaries for this subsystem and where it belongs locally.

Cartographer, map Aider's repomap.py, query resources, dependencies, and test coverage.

Auditor, review the Aider license, attribution needs, and risks of adapting this subsystem.

Forge Worker, implement the first local version as a clean adaptation, preserving attribution and matching our code style.

Auditor, run verification and identify any failures, risks, or missing tests.

Scribe, update NOTICE, THIRD_PARTY_NOTICES.md, PLUNDER_MAP.md, DEVLOG.md, and the subsystem README.
```

---

# 17. Common Failure Modes

## 17.1 Blind Copy-Paste

Symptom:

```text
Code appears in the project with no ownership, no attribution, and no local purpose.
```

Fix:

```text
Stop. Create plunder map. Assign domain. Add attribution. Rewrite if needed.
```

---

## 17.2 Foreign Architecture Infection

Symptom:

```text
The local project starts adopting upstream assumptions that do not fit.
```

Fix:

```text
Architect review. Extract pattern, reject foreign service assumptions, restore local boundary.
```

---

## 17.3 License Fog

Symptom:

```text
No one remembers which files came from where.
```

Fix:

```text
Scribe updates ATTRIBUTION.md, THIRD_PARTY_NOTICES.md, and adaptation logs immediately.
```

---

## 17.4 Branding Leak

Symptom:

```text
Runtime output, docs, commands, or names imply affiliation with upstream.
```

Fix:

```text
Replace branding. Keep only attribution.
```

---

## 17.5 Over-Plundering

Symptom:

```text
The project bloats because every interesting upstream feature gets imported.
```

Fix:

```text
Return to Wyrd Gate. Ask whether this strengthens the living system.
```

---

## 17.6 Unverified Trust

Symptom:

```text
A respected upstream system is assumed to be correct without tests.
```

Fix:

```text
Auditor pass. Tests. Manual review. Runtime smoke test.
```

---

# 18. Final Definition

**Mythic Engineering Plundering** is the disciplined practice of studying and adapting open-source systems through lawful attribution, architectural ownership, role-based AI orchestration, documentation continuity, and continuous verification.

It is not theft.

It is not chaos.

It is not blind copy-paste.

It is **craft**.

A strong plundered subsystem should end with:

```text
clear purpose
clean attribution
local ownership
documented interface
passing tests
updated memory
stronger architecture
```

---

# 19. Core Maxim

> Plunder like a Viking.  
> Document like a Scribe.  
> Verify like an Auditor.  
> Build like a Forge Worker.  
> Map like a Cartographer.  
> Shape like an Architect.  
> Name like a Skald.
