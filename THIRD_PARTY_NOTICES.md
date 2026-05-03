# Third-Party Notices

This project includes or adapts material from third-party open-source projects.
Each entry below names the upstream project, links to its source, records its
license, and reproduces the upstream license/permission text where the license
requires it.

This project's own license is **Apache License, Version 2.0**. See `LICENSE`
and `NOTICE` at the repository root.

---

## Pi (pi-coding-agent)

- **Project:** pi (pi-coding-agent)
- **Repository:** [badlogic/pi-mono](https://github.com/badlogic/pi-mono) — package `packages/coding-agent`
- **License:** MIT License
- **Copyright:** Copyright (c) 2025 Mario Zechner

This project includes or adapts selected portions of pi-coding-agent. Adapted
material is marked with a per-file header naming the upstream source and is
listed in the plunder map below.

### Plunder Map

| Mythic file | Pi upstream file | Slice landed |
|---|---|---|
| `mythic_vibe_cli/runtime/file_mutation_queue.py` | `packages/coding-agent/src/core/tools/file-mutation-queue.ts` | 2026-04-29 |
| `tests/test_file_mutation_queue.py` | `packages/coding-agent/test/file-mutation-queue.test.ts` | 2026-04-29 |
| `mythic_vibe_cli/runtime/output_guard.py` | `packages/coding-agent/src/core/output-guard.ts` | 2026-04-29 |
| `tests/test_output_guard.py` | `packages/coding-agent/test/stdout-cleanliness.test.ts` (adapted to unit-test shape) | 2026-04-29 |
| `mythic_vibe_cli/runtime/event_bus.py` | `packages/coding-agent/src/core/event-bus.ts` | 2026-04-29 |
| `tests/test_event_bus.py` | (no upstream unit-test analog; integration via agent-session-runtime-events.test.ts) | 2026-04-29 |
| `mythic_vibe_cli/runtime/timings.py` | `packages/coding-agent/src/core/timings.ts` | 2026-04-29 |
| `tests/test_timings.py` | (no upstream unit-test analog) | 2026-04-29 |
| `mythic_vibe_cli/runtime/slash_commands.py` | `packages/coding-agent/src/core/slash-commands.ts` | 2026-04-29 |
| `tests/test_slash_commands.py` | (no upstream unit-test analog) | 2026-04-29 |
| `mythic_vibe_cli/runtime/source_info.py` | `packages/coding-agent/src/core/source-info.ts` (synthetic factory only; PathMetadata-dependent factory not ported) | 2026-04-29 |
| `tests/test_source_info.py` | (no upstream unit-test analog) | 2026-04-29 |
| `mythic_vibe_cli/runtime/exec.py` | `packages/coding-agent/src/core/exec.ts` (waitForChildProcess Node-stdio quirk handler not needed in Python) | 2026-04-29 |
| `tests/test_exec.py` | (no upstream unit-test analog; pi exercises exec via agent-session integration) | 2026-04-29 |

This project is independent and is not affiliated with, endorsed by, or
sponsored by Mario Zechner, the pi-mono authors, or pi.dev.

### Original-to-this-project runtime primitives (NOT plundered)

For attribution clarity, the following modules in `mythic_vibe_cli/runtime/` are **original** to this project (Apache-2.0 under the project's own license; no third-party attribution applies):

| Mythic file | Origin | Notes |
|---|---|---|
| `mythic_vibe_cli/runtime/event_log.py` | Original (PH-09 era) | Bounded JSONL append-and-tail at `mythic/events.jsonl` |
| `mythic_vibe_cli/runtime/cross_process_lock.py` | Original (v1.0 / PH-19.0 / BS-6) | OS-level fcntl/msvcrt lock with auto-release on process death |
| `mythic_vibe_cli/runtime/atomic_write.py` | Original (v1.0 / PH-19.0 / L-10) | Write-tmp + os.replace with Windows PermissionError retry |

These modules carry no upstream attribution and require no third-party license text. They are listed here so anyone auditing the runtime layer's provenance gets a complete picture: 7 plundered primitives + 3 originals = 10 total at v1.0.0.

### Upstream MIT Permission Text

Reproduced verbatim from the upstream `LICENSE` at
`https://github.com/badlogic/pi-mono/blob/main/LICENSE`:

```
MIT License

Copyright (c) 2025 Mario Zechner

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
