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
- **Install via the offline wheelhouse** (PH-19.7) rather than `pip install` over a thin Pi Zero link — the wheelhouse bundles pre-built wheels so install never has to run a build toolchain. See [`packaging/WHEELHOUSE.md`](../packaging/WHEELHOUSE.md).

### `pi_5`

- Use compact models and moderate context.
- Limit concurrent services while running local inference.
- Consider lightweight batching only if thermals stay controlled.
- **Install via the offline wheelhouse** (PH-19.7) — same reasoning as `pi_zero`, faster than `pip install` over a constrained network and dependency-free of a build toolchain.
- The CI matrix (`.github/workflows/ci.yml`) includes a dedicated `ubuntu-24.04-arm` row that exercises the Linux aarch64 install path Pi 5 uses. Test failures on that row block release.

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

## 7) v1.0 install paths by profile

The PH-19.7 distribution work added several install routes; pick the one that matches your tier:

| Profile | Recommended install | Why |
|---|---|---|
| `phone_low`, `pi_zero`, `pi_5` | Wheelhouse (`packaging/WHEELHOUSE.md`) | Pre-built wheels; no build toolchain; works offline |
| `desktop_cpu`, `desktop_gpu` | `pipx install mythic-vibe-cli` (PyPI) | Isolated user install, easy upgrade |
| `server_gpu` (shared) | Editable install in a managed venv per service | Lets you pin dep floors per service tier |
| Air-gapped / compliance-restricted | Wheelhouse via `pip install --no-index --find-links wheelhouse` | Network-free, vendored, SBOM-trackable |

For the full install matrix (Homebrew, Scoop, contributor, pre-release), see [`docs/INSTALL.md`](INSTALL.md).

---

## 8) AI provider routing by profile

`mythic-vibe ai recommend` (PH-20.4) helps pick a model for the work at hand. Pair it with the hardware profile:

```bash
# Pi-tier: ask for a small / fast model
mythic-vibe ai recommend --cost-class cheap --max-context 32000

# Desktop: ask for the strongest model that fits a long-context task
mythic-vibe ai recommend --task "Refactor the auth subsystem" --max-context 200000

# Vision-on (`--vision`) for image-bearing tasks
mythic-vibe ai recommend --task "Analyse this screenshot" --vision
```

The `recommend` command makes zero provider calls — it just scores the static catalog. Use it to plan, then switch your `--provider` accordingly.

---

## 9) Related docs

- [Quickstart](quickstart.md)
- [Install Guide](INSTALL.md)
- [API Reference](api.md)
- [Architecture](ARCHITECTURE.md)
- [Wheelhouse Operator Guide](../packaging/WHEELHOUSE.md)
- [Compatibility Policy](compatibility_policy.md) (Python + OS support window)
