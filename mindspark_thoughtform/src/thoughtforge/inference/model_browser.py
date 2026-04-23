"""HuggingFace GGUF model browser and downloader.

Provides a curated catalogue of well-tested GGUF models across hardware tiers,
plus helpers to download them and detect existing .gguf files on disk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Common search directories for GGUF files
_DEFAULT_SEARCH_DIRS: list[Path] = [
    Path.home() / "models",
    Path.home() / "Downloads",
    Path.home() / ".cache" / "huggingface" / "hub",
    Path("C:/models"),
    Path("/models"),
]


@dataclass
class ModelEntry:
    model_id: str       # e.g. "microsoft/Phi-3-mini-4k-instruct-gguf"
    filename: str       # e.g. "Phi-3-mini-4k-instruct-q4.gguf"
    size_gb: float
    tier: str           # "phone" | "pi" | "cpu" | "gpu" | "server"
    description: str
    quantization: str   # "Q4_K_M" | "Q5_K_M" | "Q8_0" etc.


class ModelBrowser:
    CURATED_MODELS: list[ModelEntry] = [
        # ── phone tier (< 2 GB) ───────────────────────────────────────────────
        ModelEntry(
            model_id="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
            filename="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
            size_gb=0.67,
            tier="phone",
            description="TinyLlama 1.1B — smallest viable chat model, fits on phones",
            quantization="Q4_K_M",
        ),
        ModelEntry(
            model_id="microsoft/Phi-3-mini-4k-instruct-gguf",
            filename="Phi-3-mini-4k-instruct-q4.gguf",
            size_gb=1.9,
            tier="phone",
            description="Phi-3 mini Q4 — surprisingly capable at 1.9 GB",
            quantization="Q4_K_M",
        ),
        # ── pi tier (< 4 GB) ─────────────────────────────────────────────────
        ModelEntry(
            model_id="microsoft/Phi-3-mini-4k-instruct-gguf",
            filename="Phi-3-mini-4k-instruct-q5.gguf",
            size_gb=2.5,
            tier="pi",
            description="Phi-3 mini Q5 — better quality, comfortable on Pi 5",
            quantization="Q5_K_M",
        ),
        ModelEntry(
            model_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
            filename="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            size_gb=2.0,
            tier="pi",
            description="Llama 3.2 3B — Meta's efficient 3B model",
            quantization="Q4_K_M",
        ),
        ModelEntry(
            model_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
            filename="Llama-3.2-3B-Instruct-Q5_K_M.gguf",
            size_gb=2.5,
            tier="pi",
            description="Llama 3.2 3B Q5 — higher fidelity for Pi 5 with 4 GB RAM",
            quantization="Q5_K_M",
        ),
        # ── cpu tier (< 8 GB) ────────────────────────────────────────────────
        ModelEntry(
            model_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            size_gb=4.4,
            tier="cpu",
            description="Mistral 7B Instruct v0.2 Q4 — strong general purpose, runs on 8 GB RAM",
            quantization="Q4_K_M",
        ),
        ModelEntry(
            model_id="bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
            filename="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            size_gb=4.9,
            tier="cpu",
            description="Llama 3.1 8B Q4 — Meta's 8B instruction model",
            quantization="Q4_K_M",
        ),
        # ── gpu tier (< 16 GB VRAM) ──────────────────────────────────────────
        ModelEntry(
            model_id="bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
            filename="Meta-Llama-3.1-8B-Instruct-Q8_0.gguf",
            size_gb=8.5,
            tier="gpu",
            description="Llama 3.1 8B Q8 — near full-precision quality for 12 GB GPUs",
            quantization="Q8_0",
        ),
        ModelEntry(
            model_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            filename="mistral-7b-instruct-v0.2.Q8_0.gguf",
            size_gb=7.7,
            tier="gpu",
            description="Mistral 7B Q8 — high fidelity inference for 10 GB+ VRAM",
            quantization="Q8_0",
        ),
        ModelEntry(
            model_id="bartowski/Qwen2.5-14B-Instruct-GGUF",
            filename="Qwen2.5-14B-Instruct-Q4_K_M.gguf",
            size_gb=9.0,
            tier="gpu",
            description="Qwen 2.5 14B Q4 — excellent reasoning, fits 12 GB VRAM at Q4",
            quantization="Q4_K_M",
        ),
        ModelEntry(
            model_id="bartowski/Mistral-Nemo-Instruct-2407-GGUF",
            filename="Mistral-Nemo-Instruct-2407-Q4_K_M.gguf",
            size_gb=7.5,
            tier="gpu",
            description="Mistral Nemo 12B Q4 — 128k context, strong multilingual",
            quantization="Q4_K_M",
        ),
        # ── server tier (24 GB+ VRAM) ─────────────────────────────────────────
        ModelEntry(
            model_id="bartowski/Meta-Llama-3.1-70B-Instruct-GGUF",
            filename="Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf",
            size_gb=40.0,
            tier="server",
            description="Llama 3.1 70B Q4 — top open-weights model for 48 GB+ VRAM",
            quantization="Q4_K_M",
        ),
        ModelEntry(
            model_id="bartowski/Qwen2.5-72B-Instruct-GGUF",
            filename="Qwen2.5-72B-Instruct-Q4_K_M.gguf",
            size_gb=43.0,
            tier="server",
            description="Qwen 2.5 72B Q4 — outstanding coding & reasoning for 48 GB+ servers",
            quantization="Q4_K_M",
        ),
        ModelEntry(
            model_id="bartowski/Qwen2.5-72B-Instruct-GGUF",
            filename="Qwen2.5-72B-Instruct-IQ2_XS.gguf",
            size_gb=19.0,
            tier="server",
            description="Qwen 2.5 72B IQ2 — extreme compression for 24 GB VRAM cards",
            quantization="IQ2_XS",
        ),
        ModelEntry(
            model_id="bartowski/Meta-Llama-3.1-70B-Instruct-GGUF",
            filename="Meta-Llama-3.1-70B-Instruct-IQ2_XS.gguf",
            size_gb=19.5,
            tier="server",
            description="Llama 3.1 70B IQ2 — 70B capability squeezed into 24 GB VRAM",
            quantization="IQ2_XS",
        ),
    ]

    def list_curated(self, tier: str | None = None) -> list[ModelEntry]:
        if tier is None:
            return list(self.CURATED_MODELS)
        return [m for m in self.CURATED_MODELS if m.tier == tier]

    def download(
        self,
        entry: ModelEntry,
        dest_dir: Path,
        show_progress: bool = True,
    ) -> Path:
        """
        Download a GGUF file to dest_dir.
        Uses huggingface_hub.hf_hub_download when available; otherwise streams via requests.
        Returns the local path of the downloaded file.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / entry.filename

        if dest_path.exists():
            logger.info("Model already exists at %s — skipping download", dest_path)
            return dest_path

        # Preferred path: huggingface_hub handles caching and partial resumption
        try:
            from huggingface_hub import hf_hub_download
            downloaded = hf_hub_download(
                repo_id=entry.model_id,
                filename=entry.filename,
                local_dir=str(dest_dir),
            )
            return Path(downloaded)
        except ImportError:
            logger.debug("huggingface_hub not installed — using streaming requests download")
        except Exception as exc:
            logger.warning("hf_hub_download failed (%s) — falling back to requests", exc)

        # Fallback: direct requests streaming download
        url = (
            f"https://huggingface.co/{entry.model_id}/resolve/main/{entry.filename}"
        )
        self._stream_download(url, dest_path, show_progress=show_progress)
        return dest_path

    def detect_existing_ggufs(
        self,
        search_dirs: list[Path] | None = None,
    ) -> list[Path]:
        dirs = search_dirs if search_dirs is not None else _DEFAULT_SEARCH_DIRS
        found: list[Path] = []
        for d in dirs:
            if not d.exists():
                continue
            try:
                found.extend(d.rglob("*.gguf"))
            except PermissionError:
                logger.debug("Permission denied scanning %s", d)
        return found

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _stream_download(url: str, dest: Path, show_progress: bool = True) -> None:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))

        tqdm_ok = False
        if show_progress:
            try:
                from tqdm import tqdm
                tqdm_ok = True
            except ImportError:
                logger.info("tqdm not installed — downloading without progress bar")

        if show_progress and tqdm_ok:
            from tqdm import tqdm
            with dest.open("wb") as fh, tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=dest.name,
            ) as bar:
                for chunk in resp.iter_content(chunk_size=65536):
                    fh.write(chunk)
                    bar.update(len(chunk))
        else:
            with dest.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=65536):
                    fh.write(chunk)

        logger.info("Downloaded %s → %s", url, dest)
