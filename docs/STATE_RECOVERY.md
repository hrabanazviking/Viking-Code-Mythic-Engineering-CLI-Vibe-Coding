# State Recovery

Mythic Vibe CLI treats runtime state as recoverable. A corrupt file should not prevent the `mythic` command from starting, and recovery must preserve the damaged bytes for inspection.

## Protected State

- `mythic/status.json` is written with an atomic replace and an OS-level cross-process lock at `mythic/status.json.lock`.
- Before normal state replacement, the previous `status.json` is copied into `mythic/backups/`.
- During migration recovery, unreadable or corrupt `status.json` is moved to `mythic/backups/status.json.<timestamp>.corrupt`, then a fresh schema-valid state file is created.
- `.mythic/memory.sqlite` is initialized through SQLite WAL mode. If the database cannot be opened as SQLite, it is moved to `.mythic/backups/memory.sqlite.<timestamp>.corrupt`, then recreated.
- `mythic/ai/provider_calls.jsonl` appends are serialized with an OS-level sidecar lock at `provider_calls.jsonl.lock`. Provider telemetry failures are best-effort and must not crash provider execution.

## Operator Guidance

Quarantined `*.corrupt` files are never deleted automatically. They are evidence for diagnosis. Inspect them manually, extract anything useful, then remove them when they are no longer needed.

Use these checks after recovery-sensitive work:

```bash
mythic db migrate --path .
mythic state validate --path .
mythic simulate --json
```
