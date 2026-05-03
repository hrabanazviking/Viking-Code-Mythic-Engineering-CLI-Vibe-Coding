# AI is never to change the following files in this repo.

**Reading them is allowed and encouraged.**
**Changing them is not allowed without an explicit Volmarr directive.**

## Locked Files

- `README.md`
- Any picture files (unless Volmarr the Human directly tells you to change certain ones)
- `LICENSE`
- `NOTICE`
- `RULES.AI.md`

## When the lock can be lifted

The lock applies to **unsolicited AI edits** — an AI working on a task that does not specifically name one of these files must not modify it. The lock can be lifted by:

1. **An explicit Volmarr directive naming the file.** Example: "do a complete look over the README.md and all other project documents to make sure they are accurate" (the 2026-05-03 v1.0.0 doc audit directive).
2. **A maintainer-approved PR** that touches one of these files with documented justification.

If you are an AI uncertain whether the lock applies to your current task, the default is **don't change it** and ask Volmarr for explicit clarification.

## v1.0.0 doc audit exception (2026-05-03)

During the v1.0.0 launch documentation audit, Volmarr explicitly directed comprehensive updates across all project documents including `README.md`. The README was refreshed to reflect v1.0.0 reality (version, test count, install paths, command surface, etc.). This was an **explicit-directive exception** to the lock above; the lock remains in force for subsequent unsolicited edits.

The v1.0 changes to README.md are recorded in commits `a8788b1` and downstream.

## See also

- [`RULES.AI.md`](RULES.AI.md) — Volmarr's broader project laws (also locked).
- [`INSTRUCTIONS_FOR_AI.md`](INSTRUCTIONS_FOR_AI.md) — AI-facing operational instructions for this repo.
- [`docs/compatibility_policy.md`](docs/compatibility_policy.md) — v1.0 SemVer + deprecation cadence (binding from v1.0.0; complements the lock list above).
