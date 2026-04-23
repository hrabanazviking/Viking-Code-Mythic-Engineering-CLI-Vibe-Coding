"""
onnx_export.py — ONNX export path for ThoughtForge embedding models.

Provides two classes:
  - OnnxExporter: exports a sentence-transformer model to ONNX format
  - ONNXEmbedder: runs inference on an exported ONNX embedding model

Both classes degrade gracefully when `optimum` or `onnxruntime` are not
installed — appropriate for edge deployments where dependencies vary.

Usage:
    # Export once (requires optimum or torch):
    exporter = OnnxExporter()
    onnx_dir = exporter.export_embedder("all-MiniLM-L6-v2", Path("/models/onnx"))

    # Embed at runtime (requires onnxruntime + transformers):
    embedder = ONNXEmbedder(onnx_dir)
    vectors = embedder.encode(["Norse mythology", "Yggdrasil"])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Export constants ───────────────────────────────────────────────────────────

_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_ONNX_MODEL_FILENAME = "model.onnx"
_ONNX_QUANTIZED_FILENAME = "model_quantized.onnx"
_EXPORT_OPSET = 14


# ── Result type ────────────────────────────────────────────────────────────────

@dataclass
class ExportResult:
    """Result of an ONNX export operation."""
    model_name: str
    output_dir: Path
    onnx_path: Path
    quantized: bool
    vocab_size: int
    embedding_dim: int
    exporter_used: str          # "optimum" | "torch" | "mock"


# ── OnnxExporter ──────────────────────────────────────────────────────────────

class OnnxExporter:
    """
    Exports a sentence-transformer embedding model to ONNX format.

    Export priority:
      1. `optimum.exporters.onnx` — best quality, quantization support
      2. `torch.onnx.export` — manual export, no quantization
      3. Raises `ImportError` with install hint if neither is available
    """

    def export_embedder(
        self,
        model_name: str = _DEFAULT_MODEL,
        output_dir: Path | str = Path("models/onnx"),
        quantize: bool = False,
        opset: int = _EXPORT_OPSET,
    ) -> ExportResult:
        """
        Export a sentence-transformer model to ONNX.

        Args:
            model_name: HuggingFace model name or local path.
            output_dir: Directory to write ONNX files.
            quantize:   Whether to also produce a quantized (int8) model.
            opset:      ONNX opset version (default 14).

        Returns:
            ExportResult with output path and metadata.

        Raises:
            ImportError: If neither optimum nor torch is installed.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Try optimum first (best quality + quantization support)
        try:
            return self._export_with_optimum(model_name, output_dir, quantize, opset)
        except ImportError:
            logger.debug("optimum not available — trying torch.onnx export")

        # Fall back to torch
        try:
            return self._export_with_torch(model_name, output_dir, opset)
        except ImportError:
            pass

        raise ImportError(
            "ONNX export requires either 'optimum' or 'torch'.\n"
            "Install: pip install optimum[exporters]   (recommended)\n"
            "     or: pip install torch                (basic export)"
        )

    def _export_with_optimum(
        self,
        model_name: str,
        output_dir: Path,
        quantize: bool,
        opset: int,
    ) -> ExportResult:
        """Export via Hugging Face Optimum."""
        try:
            from optimum.exporters.onnx import main_export
        except ImportError as e:
            raise ImportError("optimum not installed") from e

        try:
            from transformers import AutoTokenizer
        except ImportError as e:
            raise ImportError("transformers not installed") from e

        logger.info("OnnxExporter: exporting %s via optimum → %s", model_name, output_dir)
        main_export(
            model_name_or_path=model_name,
            output=output_dir,
            task="feature-extraction",
            opset=opset,
            optimize=None,
        )

        onnx_path = output_dir / _ONNX_MODEL_FILENAME

        if quantize:
            onnx_path = self._quantize_optimum(output_dir)

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        vocab_size = tokenizer.vocab_size

        return ExportResult(
            model_name=model_name,
            output_dir=output_dir,
            onnx_path=onnx_path,
            quantized=quantize,
            vocab_size=vocab_size,
            embedding_dim=384,          # all-MiniLM-L6-v2 default; probed at runtime
            exporter_used="optimum",
        )

    def _quantize_optimum(self, output_dir: Path) -> Path:
        """Apply int8 quantization to the exported ONNX model."""
        try:
            from optimum.onnxruntime import ORTQuantizer
            from optimum.onnxruntime.configuration import AutoQuantizationConfig
        except ImportError as e:
            logger.warning("ORTQuantizer not available — skipping quantization: %s", e)
            return output_dir / _ONNX_MODEL_FILENAME

        quantizer = ORTQuantizer.from_pretrained(output_dir)
        qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False)
        quantizer.quantize(
            save_dir=output_dir,
            quantization_config=qconfig,
        )
        q_path = output_dir / _ONNX_QUANTIZED_FILENAME
        if not q_path.exists():
            q_path = output_dir / _ONNX_MODEL_FILENAME
        return q_path

    def _export_with_torch(
        self,
        model_name: str,
        output_dir: Path,
        opset: int,
    ) -> ExportResult:
        """Export via torch.onnx.export (no quantization support)."""
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            raise ImportError("torch or transformers not installed") from e

        logger.info("OnnxExporter: exporting %s via torch.onnx → %s", model_name, output_dir)

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        model.eval()

        dummy_input = tokenizer(
            "ThoughtForge embedding export",
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        )

        onnx_path = output_dir / _ONNX_MODEL_FILENAME
        with torch.no_grad():
            torch.onnx.export(
                model,
                args=(dummy_input["input_ids"], dummy_input["attention_mask"]),
                f=str(onnx_path),
                opset_version=opset,
                input_names=["input_ids", "attention_mask"],
                output_names=["last_hidden_state", "pooler_output"],
                dynamic_axes={
                    "input_ids": {0: "batch", 1: "seq"},
                    "attention_mask": {0: "batch", 1: "seq"},
                    "last_hidden_state": {0: "batch", 1: "seq"},
                },
            )

        tokenizer.save_pretrained(str(output_dir))

        return ExportResult(
            model_name=model_name,
            output_dir=output_dir,
            onnx_path=onnx_path,
            quantized=False,
            vocab_size=tokenizer.vocab_size,
            embedding_dim=model.config.hidden_size,
            exporter_used="torch",
        )


# ── ONNXEmbedder ──────────────────────────────────────────────────────────────

class ONNXEmbedder:
    """
    Drop-in embedding encoder backed by an ONNX model.

    Designed as a memory-efficient alternative to sentence-transformers for
    edge devices (phone, Pi Zero) where the full PyTorch stack is unavailable
    or too heavy.

    Requires: onnxruntime (+ onnxruntime-gpu for GPU), transformers (tokenizer only).

    Usage:
        embedder = ONNXEmbedder(Path("/models/onnx/all-MiniLM-L6-v2"))
        vectors = embedder.encode(["Yggdrasil", "Midgard"])
        # vectors.shape == (2, 384)
    """

    def __init__(self, model_dir: Path | str, use_gpu: bool = False) -> None:
        """
        Load tokenizer and ONNX inference session.

        Args:
            model_dir:  Directory containing model.onnx + tokenizer files.
            use_gpu:    Use CUDA execution provider if available (default False).

        Raises:
            ImportError:   If onnxruntime or transformers is not installed.
            FileNotFoundError: If model.onnx is not found in model_dir.
        """
        self._model_dir = Path(model_dir)
        self._session = self._load_session(use_gpu)
        self._tokenizer = self._load_tokenizer()

    def _load_session(self, use_gpu: bool):
        """Load ONNX runtime session."""
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise ImportError(
                "onnxruntime is required for ONNXEmbedder.\n"
                "Install: pip install onnxruntime          (CPU)\n"
                "     or: pip install onnxruntime-gpu      (CUDA)"
            ) from e

        onnx_path = self._model_dir / _ONNX_MODEL_FILENAME
        if not onnx_path.exists():
            # try quantized
            q_path = self._model_dir / _ONNX_QUANTIZED_FILENAME
            if q_path.exists():
                onnx_path = q_path
            else:
                raise FileNotFoundError(
                    f"No ONNX model found in {self._model_dir}. "
                    f"Run OnnxExporter.export_embedder() first."
                )

        providers = ["CPUExecutionProvider"]
        if use_gpu:
            providers = ["CUDAExecutionProvider"] + providers

        session = ort.InferenceSession(str(onnx_path), providers=providers)
        logger.debug("ONNXEmbedder: loaded session from %s", onnx_path)
        return session

    def _load_tokenizer(self):
        """Load tokenizer from model directory."""
        try:
            from transformers import AutoTokenizer
        except ImportError as e:
            raise ImportError(
                "transformers is required for ONNXEmbedder tokenization.\n"
                "Install: pip install transformers"
            ) from e

        return AutoTokenizer.from_pretrained(str(self._model_dir))

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        max_length: int = 128,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode a list of texts into embedding vectors.

        Args:
            texts:      Input strings.
            batch_size: Tokenization batch size.
            max_length: Max token length per text.
            normalize:  L2-normalize output vectors (recommended for cosine similarity).

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.empty((0, self.embedding_dim), dtype=np.float32)

        all_embeddings: list[np.ndarray] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="np",
            )

            inputs = {
                "input_ids": encoded["input_ids"].astype(np.int64),
                "attention_mask": encoded["attention_mask"].astype(np.int64),
            }

            outputs = self._session.run(None, inputs)
            # outputs[0] = last_hidden_state: (batch, seq, hidden)
            # Mean pool over non-padding tokens
            hidden = outputs[0]                                 # (B, S, H)
            mask = encoded["attention_mask"][..., np.newaxis]   # (B, S, 1)
            pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1e-9)

            all_embeddings.append(pooled.astype(np.float32))

        result = np.concatenate(all_embeddings, axis=0)

        if normalize:
            norms = np.linalg.norm(result, axis=1, keepdims=True).clip(min=1e-9)
            result = result / norms

        return result

    @property
    def embedding_dim(self) -> int:
        """Infer embedding dimension from ONNX session output shape."""
        try:
            output_meta = self._session.get_outputs()[0]
            shape = output_meta.shape
            if shape and len(shape) >= 3:
                return shape[-1]
        except Exception:
            pass
        return 384      # all-MiniLM-L6-v2 default
