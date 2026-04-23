# Hardware Profiles

ThoughtForge auto-detects your hardware and selects the appropriate profile.
You can override manually with `--profile` or `-profile`.

---

## Profile Overview

| Profile | RAM | VRAM | Model Size | Quantization | Context | Draft Count |
|---|---|---|---|---|---|---|
| `phone_low` | 2 GB | — | 1.1B (TinyLlama) | Q2_K | 512 tokens | 2 |
| `pi_zero` | 512 MB | — | 1B subset | Q2_K ultra | 256 tokens | 1 |
| `pi_5` | 4 GB | — | 1B–3B | Q4_K_M | 1024 tokens | 2 |
| `desktop_cpu` | 8 GB+ | — | 3B–7B | Q4_K_M / Q8 | 2048 tokens | 3 |
| `desktop_gpu` | — | 8–16 GB | 7B–13B | Q8 / fp16 | 4096 tokens | 3 |
| `server_gpu` | — | 24 GB+ | 30B–70B | fp16 / bf16 | 8192 tokens | 4 |

---

## Profile Details

### `phone_low` — Smartphones

**Target:** Android (Termux), iOS (MLC LLM), low-power ARM devices

```json
{
  "hardware": { "ram_gb": 2, "cpu_arch": ["arm64", "armv8"] },
  "model": { "max_params_b": 1.1, "quantization": "q2_k", "token_budget_per_turn": 180 },
  "deployment": { "platforms": ["android", "ios"], "runtime": ["termux", "mlc-llm"], "onnx_export": true }
}
```

**Recommended models:**
- `TinyLlama-1.1B-Chat-v1.0.Q2_K.gguf` (~500 MB)
- `Granite-1B-Instruct.Q3_K_S.gguf` (~600 MB)

**Install:**
```bash
./scripts/install_termux.sh --profile phone_low --onnx
```

---

### `pi_zero` — Raspberry Pi Zero 2W

**Target:** 512 MB RAM single-board computers. Ultra-constrained.

```json
{
  "hardware": { "ram_gb": 0.5, "cpu_arch": ["armv7l", "arm64"] },
  "model": { "max_params_b": 1.1, "quantization": "q2_k", "token_budget_per_turn": 120 },
  "deployment": { "platforms": ["linux-arm"], "onnx_export": true, "knowledge_subset": true }
}
```

**Notes:**
- Use `--subset` flag during Pi install to build reduced knowledge DB (50K entities)
- Knowledge-only mode recommended — inference is very slow on Pi Zero
- Increase swap to 1 GB before compiling llama-cpp-python

---

### `pi_5` — Raspberry Pi 4 / 5

**Target:** 4 GB ARM board, optional Vulkan VideoCore VII (Pi 5)

```json
{
  "hardware": { "ram_gb": 4, "cpu_arch": ["arm64"] },
  "model": { "max_params_b": 3, "quantization": "q4_k_m", "token_budget_per_turn": 200 },
  "deployment": { "platforms": ["linux-arm"], "runtime": ["docker", "native"] }
}
```

**Recommended models:**
- `Phi-3-mini-128k-instruct.Q4_K_M.gguf` (~2.2 GB)
- `Gemma-2B-it.Q4_K_M.gguf` (~1.5 GB)

**Install with Vulkan (Pi 5):**
```bash
./scripts/install_pi.sh --profile pi_5 --vulkan
```

---

### `desktop_cpu` — Desktop / Laptop (CPU)

**Target:** 8–32 GB RAM, x86_64 or ARM64, no discrete GPU required.

```json
{
  "hardware": { "ram_gb": 8, "inference_backend": "cpu" },
  "model": { "max_params_b": 7, "quantization": "q4_k_m", "token_budget_per_turn": 220 }
}
```

**Recommended models:**
- `Mistral-7B-Instruct-v0.3.Q4_K_M.gguf` (~4.1 GB)
- `LLaMA-3-8B-Instruct.Q4_K_M.gguf` (~4.6 GB)
- `Phi-3-mini-128k-instruct.Q8_0.gguf` (~4.0 GB)

---

### `desktop_gpu` — Desktop / Workstation GPU

**Target:** NVIDIA (CUDA), AMD (ROCm), Intel Arc (Vulkan). 8–16 GB VRAM.

```json
{
  "hardware": { "vram_gb": 12, "inference_backend": "cuda" },
  "model": { "max_params_b": 13, "quantization": "q8_0", "token_budget_per_turn": 240 }
}
```

**Recommended models:**
- `LLaMA-3-8B-Instruct.Q8_0.gguf` (8 GB VRAM)
- `Mistral-7B-Instruct-v0.3.fp16.gguf` (14 GB VRAM — requires 16 GB card)

**GPU backend auto-detection priority:** CUDA → ROCm → Vulkan → Metal → CPU

---

### `server_gpu` — Server / Cloud GPU

**Target:** 24 GB+ VRAM. A100, H100, RTX 3090+, RTX 4090.

```json
{
  "hardware": { "vram_gb": 24, "inference_backend": "cuda" },
  "model": { "max_params_b": 70, "quantization": "fp16", "token_budget_per_turn": 250 },
  "deployment": { "multi_gpu": true }
}
```

**Recommended models:**
- `LLaMA-3-70B-Instruct.fp16` (requires 140 GB VRAM across 2× A100 80GB)
- `Mixtral-8x7B-Instruct.Q4_K_M.gguf` (24 GB single GPU)
- `LLaMA-3-70B-Instruct.Q4_K_M.gguf` (40 GB — 2× 24GB)

---

## Overriding the Profile

```bash
# CLI
python run_thoughtforge.py --profile pi_5

# Python API
from thoughtforge.cognition.core import ThoughtForgeCore
core = ThoughtForgeCore(model_path=None)  # auto-detect
```

## Manual Profile Tuning

Profiles are JSON files in `hardware_profiles/`. You can add a custom profile:

```json
{
  "profile_id": "my_workstation",
  "display_name": "My Workstation",
  "hardware": { "ram_gb": 32, "vram_gb": 24, "inference_backend": "cuda" },
  "model": { "max_params_b": 13, "quantization": "q8_0", "token_budget_per_turn": 240 },
  "memory": { "episodic_store_cap_soft": 2048, "episodic_store_cap_hard": 4096 },
  "retrieval": { "sql_max_results": 15, "vector_top_k": 10 },
  "generation": { "max_response_tokens": 500, "temperature": 0.7, "max_refinement_passes": 2 },
  "deployment": { "platforms": ["linux", "windows"], "runtime": ["native"], "onnx_export": false }
}
```
