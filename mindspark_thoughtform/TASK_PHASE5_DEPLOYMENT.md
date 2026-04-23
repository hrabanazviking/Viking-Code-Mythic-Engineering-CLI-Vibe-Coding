# TASK: Phase 5 — Edge + Cross-Platform Deployment

**Created:** 2026-03-31
**Phase:** 5 of 6
**Branch:** development
**Status:** IN PROGRESS

---

## Goal

Single codebase, all platforms. ThoughtForge running on phone (Termux/Android),
Raspberry Pi (Pi Zero + Pi 5), desktop (Linux/macOS/Windows), and in Docker.
Plus ONNX embedding export for edge devices and knowledge subset tooling
for memory-constrained targets.

---

## Deliverables

| File | Status |
|---|---|
| `TASK_PHASE5_DEPLOYMENT.md` | ✅ (this file) |
| `Dockerfile` | ✅ |
| `docker-compose.yml` | ✅ |
| `.dockerignore` | ✅ |
| `scripts/install_linux.sh` | ✅ |
| `scripts/install_mac.sh` | ✅ |
| `scripts/install_windows.ps1` | ✅ |
| `scripts/install_termux.sh` | ✅ |
| `scripts/install_pi.sh` | ✅ |
| `src/thoughtforge/inference/onnx_export.py` | ✅ |
| `src/thoughtforge/etl/subset.py` | ✅ |
| `tests/test_phase5_deployment.py` | ✅ |

---

## Module Descriptions

### `src/thoughtforge/inference/onnx_export.py`
- `OnnxExporter` — exports sentence-transformer embedding model to ONNX format
  - `export_embedder(model_name, output_dir, quantize=False) -> Path`
  - Uses `optimum.exporters.onnx` if available, falls back to `torch.onnx`
  - Graceful `ImportError` with install hint if neither available
- `ONNXEmbedder` — ONNX-based embedding inference
  - `__init__(model_dir)` — loads tokenizer + ONNX session
  - `encode(texts, batch_size=32) -> np.ndarray`
  - Drop-in replacement for sentence-transformers on edge devices

### `src/thoughtforge/etl/subset.py`
- `EdgeSubsetBuilder` — builds reduced knowledge DB for edge profiles
  - `build(source_db, output_path, profile_id, max_entities=None) -> SubsetResult`
  - Reads profile JSON to get default entity limit
  - Copies top-N entities by popularity_score from source DB
  - Copies associated statements, reference chunks, FTS rows
  - Returns `SubsetResult` with counts + output path

### Deployment Assets
- `Dockerfile` — multi-stage Python 3.11-slim, profile via `--build-arg PROFILE=desktop_cpu`
- `docker-compose.yml` — named services: thoughtforge-desktop, thoughtforge-pi, thoughtforge-phone
- `.dockerignore` — excludes data/, docs/, .git/, *.jsonl, *.gz
- `scripts/install_*.sh|.ps1` — one-command platform setup scripts

---

## Test Strategy (`tests/test_phase5_deployment.py`)

- `TestONNXExporterAPI` — OnnxExporter/ONNXEmbedder method signatures, graceful import handling
- `TestEdgeSubsetBuilder` — SubsetResult dataclass, profile parsing, method signatures
- `TestDeploymentFiles` — Dockerfile/docker-compose/scripts exist and contain required directives
- `TestHardwareProfileDeployment` — all 6 profiles have valid `deployment` section
- `TestInstallScriptContent` — scripts contain required install commands for each platform

---

## Pipeline

Phase 5 adds zero new Python runtime dependencies — all new modules have
graceful fallbacks for `optimum` and `onnxruntime` (edge-only optional deps).
The 238 existing tests continue to pass unmodified.

---

## Next: Phase 6

Testing, Benchmarking, Personality Layer + v1.0 Release.
