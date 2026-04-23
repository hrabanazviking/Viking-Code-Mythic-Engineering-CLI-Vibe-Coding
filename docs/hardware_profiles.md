# Hardware Profiles

This guide maps typical machine classes to practical operating profiles for local AI-assisted workflows in this repository ecosystem.

> Use this as planning guidance. Actual performance depends on model choice, quantization, context length, and concurrent workload.

---

## 1) Profile quick matrix

| Profile | RAM | VRAM | Typical model band | Suggested context budget | Suggested draft count | Best use case |
|---|---:|---:|---|---:|---:|---|
| `phone_low` | ~2 GB | — | 1B class (aggressively quantized) | 256–512 | 1–2 | mobile experimentation, lightweight prompts |
| `pi_zero` | ~0.5 GB | — | 1B subset / knowledge-only | 128–256 | 1 | ultra-constrained edge and kiosk-style automation |
| `pi_5` | ~4 GB | — | 1B–3B | 512–1024 | 1–2 | low-power local assistant workflows |
| `desktop_cpu` | 8+ GB | — | 3B–7B | 1024–2048 | 2–3 | general daily development on CPU |
| `desktop_gpu` | 16+ GB RAM | 8–16 GB | 7B–13B | 2048–4096 | 2–3 | high-throughput local development |
| `server_gpu` | 64+ GB RAM | 24+ GB | 30B+ or multi-model serving | 4096–8192 | 3–4 | team/shared inference and deep context workloads |

---

## 2) How to choose a profile

Prioritize in this order:

1. **Stability first:** choose the profile that avoids swapping/OOM under expected load.
2. **Latency target second:** reduce model size/context before increasing hardware complexity.
3. **Quality tuning third:** increase draft count/context gradually after stability is proven.

---

## 3) Practical recommendations by profile

### `phone_low`

- Use short prompts and constrained output lengths.
- Prefer quantized 1B-class models.
- Keep background apps minimal to reduce OS memory pressure.

### `pi_zero`

- Treat this as knowledge-only or narrowly scoped inference.
- Build reduced datasets/subsets where applicable.
- Avoid large context windows and multi-draft generation.

### `pi_5`

- Use compact models and moderate context.
- Limit concurrent services while running local inference.
- Consider lightweight batching only if thermals stay controlled.

### `desktop_cpu`

- Best balance for many contributors.
- Prefer mid-size quantized models and 2–3 draft loops.
- If latency is high, reduce context before changing profile.

### `desktop_gpu`

- Strong default for advanced local workflows.
- Monitor VRAM fragmentation when switching models repeatedly.
- Keep fallback CPU profile available for reliability.

### `server_gpu`

- Use for heavy-context or team-serving scenarios.
- Enforce resource quotas and concurrency limits.
- Document model routing and failover behavior.

---

## 4) Override strategy

When profile auto-selection is available, it should be considered a baseline. Override only when you have measured reason to do so.

Common override triggers:

- predictable OOM events,
- unacceptable latency for your loop,
- specific model constraints requiring alternate quantization.

---

## 5) Custom profile governance

If you add custom profiles in code/config:

- Include explicit memory and context ceilings.
- Document expected model band and fallback behavior.
- Add a short benchmark note (latency + stability observation).
- Keep naming stable and human-readable.

---

## 6) Operational warning signs

Re-tune profile selection when you observe:

- repeated OOM/swap spikes,
- severe p95 latency regressions,
- unstable generation quality from over-aggressive quantization,
- thermal throttling on edge devices.

---

## 7) Related docs

- [Quickstart](quickstart.md)
- [API Reference](api.md)
- [Architecture](ARCHITECTURE.md)
