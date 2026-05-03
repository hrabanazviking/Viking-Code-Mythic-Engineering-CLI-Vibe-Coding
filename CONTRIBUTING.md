# Contributing to the Mythic Vibe CLI

Thank you for your interest in contributing. This document explains how to file issues, submit PRs, write plugins, and propose architectural changes.

The Mythic Vibe CLI is built under the **Mythic Engineering** methodology — see [`MYTHIC_ENGINEERING.md`](MYTHIC_ENGINEERING.md) for the philosophy and the **Six Laws** every contribution must satisfy.

**Since v1.0.0**, all contributions also operate under the binding [`docs/compatibility_policy.md`](docs/compatibility_policy.md) — SemVer rules apply, deprecations follow the documented announce → wait one minor → remove cadence, and the public-surface tier table is the authoritative answer to "is X stable?". Changes that break a Stable surface require a major-version bump.

---

## Quick reference

| I want to... | Do this |
|---|---|
| Report a bug | Open an issue at https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/issues |
| Propose a feature | Open an issue **before** writing code; we'll discuss scope and check it doesn't conflict with the master roadmap |
| Submit a small fix | Fork → branch → PR; include a test |
| Submit a substantial change | Open an ADR draft first (see §3 below) |
| Author a plugin | Read [`docs/PLUGIN_AUTHORING_GUIDE.md`](docs/PLUGIN_AUTHORING_GUIDE.md); ship it as its own repo |
| List your plugin in the registry | PR to [`plugins/REGISTRY.md`](plugins/REGISTRY.md) — see inclusion criteria there |

---

## 1. Mythic Engineering laws

Every contribution must satisfy the **Six Laws**:

1. **Boundary Discipline** — `mythic_vibe_cli/` does not import from dormant in-tree paths (`yggdrasil/`, `core/`, `mindspark_thoughtform/`, vendor mirrors, etc.). Cross boundaries through reviewed adapters with ADRs.
2. **Stdlib First** — prefer Python's standard library. Optional deps go in `pyproject.toml [project.optional-dependencies]` and gate behind try-import + `MissingExtraError` with a clean install hint.
3. **Default Off** — feature flags / new behaviours / island activations are off by default. Operators opt in via env vars or explicit CLI flags.
4. **Cross-Platform** — code must work on Linux, macOS, and Windows. POSIX-only paths gate behind `hasattr(...)` or `platform.system()` checks. No bash assumptions.
5. **Verifiable** — every behaviour change ships with tests. The full `pytest tests/` must stay green. `ruff` and `mypy` must stay clean. Cover the failure modes, not just the happy path.
6. **AI Output Never Auto-Trusted** — diffs from a provider are reviewed before they land on disk. The forge's gate machinery is non-negotiable.

The longer form lives in [`MYTHIC_ENGINEERING.md`](MYTHIC_ENGINEERING.md).

---

## 2. Workflow for code changes

1. **Open an issue first** (unless it's a one-line typo fix). State what you want to change and why.
2. **Fork** the repo and create a branch from `development` (not `main`). Branch name format: `slice-NN-short-name` for roadmap slices, `fix/short-name` for bug fixes, `feat/short-name` for new capabilities.
3. **Write tests first** (or alongside the change). Look at neighbouring tests for the existing style.
4. **Run the gates** locally before pushing:

   ```bash
   python -m pytest tests/
   python -m ruff check mythic_vibe_cli tests scripts tools
   python -m mypy mythic_vibe_cli
   python tools/contract_audit.py --strict
   ```

5. **Open a PR against `development`**. PR description should include:
   - What changed and why.
   - Test count delta.
   - Any new env vars / CLI flags / config keys.
   - ADR reference if the change crosses a boundary.
   - Compatibility-policy assessment (PATCH / MINOR / MAJOR per §4 of `docs/compatibility_policy.md`).

6. **CI** runs the same gates across **3 OS × 3 Python + Linux aarch64**. Land only when green.

7. **Merge to `main`** is the maintainer's call — typically batched at phase boundaries.

---

## 3. ADR process

Architectural Decision Records live in [`docs/ADRS/`](docs/ADRS/). An ADR is required when:

- You're adding a new boundary (a new adapter, a new island integration, a new vendor wrap).
- You're changing the semantics of an existing public API surface.
- You're introducing a new feature flag, env var, or default-off behaviour that other contributors will need to know about.
- You're touching `MYTHIC_ENGINEERING.md`, `docs/ACTIVE_PRODUCT_BOUNDARY.md`, or `docs/DORMANT_ISLANDS.md`.

ADR shape (see ADR-0001..0008 for examples):

```markdown
# ADR-NNNN: Title

## Status

Proposed | Accepted | Superseded by ADR-MMMM

## Context

What problem are we solving? Why now?

## Decision

What did we decide?

## Provenance

If code is copied or adapted from elsewhere, name the source and license.

## Consequences

What does this make easier? What does it make harder?

## Verification

How can a reviewer confirm the decision is honoured?
```

Number the ADR sequentially (next free `ADR-NNNN`). Open the ADR in the same PR as the implementation.

---

## 4. Plugin contributions

The Mythic Vibe CLI has a first-class plugin layer (PH-10). Plugins live in **separate repositories** and ship as PyPI packages under the `mythic_vibe.plugins` entry-point group.

To author a plugin, read [`docs/PLUGIN_AUTHORING_GUIDE.md`](docs/PLUGIN_AUTHORING_GUIDE.md). The reference plugin in [`examples/plugins/mythic_vibe_example_plugin/`](examples/plugins/mythic_vibe_example_plugin/) is your starting template.

To get your plugin listed in the community registry:

1. Open-source license (MIT / Apache-2.0 / BSD).
2. ME laws compliance.
3. Tests pass on the latest tagged Mythic Vibe CLI release.
4. Author guide compliance.
5. ADR if the plugin crosses a non-trivial boundary.

PR your entry to [`plugins/REGISTRY.md`](plugins/REGISTRY.md).

---

## 5. Code style

- **Formatting**: ruff handles it. Don't hand-format; let the linter run.
- **Type hints**: required on public surfaces. Internal helpers can be untyped if mypy passes.
- **Docstrings**: required on every module, public class, and public function. The first line is a one-sentence summary.
- **Comments**: explain WHY, not WHAT. If a future maintainer would be surprised, document the surprise.
- **Imports**: stdlib first, then third-party, then `mythic_vibe_cli.*` last. Ruff enforces this via isort.
- **Line length**: 100 chars (ruff-enforced).

---

## 6. Test conventions

- Tests live in `tests/test_<module>.py`. One test class per logical concern; tests within a class share fixtures via `setUp`.
- Use `tempfile.TemporaryDirectory()` for project-root fixtures. Never write to the test runner's cwd.
- Mocks via `unittest.mock`. Pytest's `monkeypatch` is fine too.
- Hermetic env: capture + restore `os.environ` mutations per test (see `tests/test_island_isolation.py:_IslandEnvBase` for the pattern).
- Document **why** a test exists in its docstring when the assertion isn't self-explanatory.

---

## 7. Commit messages

Follow the project's existing style:

```
PH-NN slice N.M: One-line summary

Optional body explaining the context, the fix, the trade-offs.
Wrap at ~72 chars. Mention test deltas at the end.
```

For non-slice work, use **conventional-commit prefixes** so `python scripts/check_changelog.py --classify` (PH-20.F) can bucket entries automatically:

```
feat(api): one-line summary           # → CHANGELOG "Added"
fix(plugins): one-line summary        # → CHANGELOG "Fixed"
docs: one-line summary                # → CHANGELOG "Documentation"
refactor(state): one-line summary     # → CHANGELOG "Changed"
test(property): one-line summary      # → CHANGELOG "Tests"
chore(deps): one-line summary         # → CHANGELOG "Chore"
build(release): one-line summary      # → CHANGELOG "Build"
ci: one-line summary                  # → CHANGELOG "CI"
perf(packet): one-line summary        # → CHANGELOG "Changed"
revert: one-line summary              # → CHANGELOG "Removed"
```

The full mapping table is in `scripts/check_changelog.py:LABEL_TO_BUCKET`. Unknown labels surface in the classifier output (so typos don't disappear silently) but bucket as `Unclassified`.

We never sign commits with anyone's name other than the actual author + the AI co-author when applicable.

## 7a. Quarterly architecture review

Maintainers run `mythic-vibe review architecture` once per quarter (Jan / Apr / Jul / Oct). Each review's output gets captured under `mythic/governance/review-<YYYY-MM-DD>.md`. The cadence + agenda are in [`docs/governance/quarterly_review.md`](docs/governance/quarterly_review.md). Contributors don't need to run this directly, but ADR-touching PRs should expect the next review pass to revisit any decisions in flight.

---

## 8. Reporting security issues

Don't open a public issue for security reports. Email Volmarr directly (the maintainer's address is in the repo's `CODEOWNERS` or commit history). We aim to acknowledge within 48 hours and patch within 7 days for critical issues.

---

## 9. Code of conduct

Be kind. Disagree on technical merits, not on people. Assume good faith. The Mythic Engineering ethos values craft, clarity, and continuity — bring those to your interactions too.

---

Frith and forge,
the Mythic Vibe CLI maintainers.
