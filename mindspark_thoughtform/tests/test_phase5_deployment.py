"""
Phase 5 test suite — Edge + Cross-Platform Deployment.

Tests:
  - OnnxExporter: API contract, graceful import handling
  - ONNXEmbedder: API contract, file-not-found handling
  - EdgeSubsetBuilder: profile validation, result structure, supported_profiles
  - SubsetResult: dataclass fields, size_mb property
  - Deployment files: Dockerfile, docker-compose, .dockerignore, scripts exist
  - Dockerfile content: FROM, ARG PROFILE, HEALTHCHECK, ENTRYPOINT
  - docker-compose content: service names, build args, volumes
  - Install scripts: platform-specific required commands/keywords
  - Hardware profile deployment sections: all 6 profiles have deployment key
  - ExportResult: dataclass fields
"""

import json
import re
from pathlib import Path

import pytest

# ── Repo root ─────────────────────────────────────────────────────────────────

_REPO = Path(__file__).parents[1]
_SCRIPTS = _REPO / "scripts"
_PROFILES_DIR = _REPO / "hardware_profiles"


# ── OnnxExporter ─────────────────────────────────────────────────────────────

class TestOnnxExporterAPI:
    def setup_method(self):
        from thoughtforge.inference.onnx_export import OnnxExporter
        self.exporter = OnnxExporter()

    def test_exporter_instantiates(self):
        from thoughtforge.inference.onnx_export import OnnxExporter
        assert OnnxExporter() is not None

    def test_export_embedder_method_exists(self):
        assert callable(getattr(self.exporter, "export_embedder", None))

    def test_export_embedder_raises_import_error_without_libs(self, tmp_path, monkeypatch):
        """Should raise ImportError (not crash) when neither optimum nor torch is available."""
        import thoughtforge.inference.onnx_export as mod
        # Patch both private methods to raise ImportError
        monkeypatch.setattr(
            self.exporter, "_export_with_optimum",
            lambda *a, **kw: (_ for _ in ()).throw(ImportError("no optimum")),
        )
        monkeypatch.setattr(
            self.exporter, "_export_with_torch",
            lambda *a, **kw: (_ for _ in ()).throw(ImportError("no torch")),
        )
        with pytest.raises(ImportError, match="ONNX export requires"):
            self.exporter.export_embedder(output_dir=tmp_path)

    def test_export_result_dataclass_fields(self):
        from thoughtforge.inference.onnx_export import ExportResult
        result = ExportResult(
            model_name="test-model",
            output_dir=Path("/tmp"),
            onnx_path=Path("/tmp/model.onnx"),
            quantized=False,
            vocab_size=30522,
            embedding_dim=384,
            exporter_used="optimum",
        )
        assert result.model_name == "test-model"
        assert result.embedding_dim == 384
        assert result.quantized is False
        assert result.exporter_used == "optimum"

    def test_private_methods_exist(self):
        assert hasattr(self.exporter, "_export_with_optimum")
        assert hasattr(self.exporter, "_export_with_torch")
        assert hasattr(self.exporter, "_quantize_optimum")


class TestONNXEmbedderAPI:
    def test_onnx_embedder_raises_import_error_without_onnxruntime(self, tmp_path, monkeypatch):
        """Should raise ImportError if onnxruntime is not installed."""
        import sys
        # Remove onnxruntime from sys.modules and block future import
        sys.modules.pop("onnxruntime", None)
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else None

        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "onnxruntime":
                raise ImportError("No module named 'onnxruntime'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        from thoughtforge.inference.onnx_export import ONNXEmbedder
        with pytest.raises(ImportError):
            ONNXEmbedder(tmp_path)

    def test_onnx_embedder_raises_file_not_found_when_no_model(self, tmp_path, monkeypatch):
        """Should raise FileNotFoundError if model.onnx missing from directory."""
        try:
            import onnxruntime  # noqa: F401
        except ImportError:
            pytest.skip("onnxruntime not installed")
        try:
            from transformers import AutoTokenizer  # noqa: F401
        except ImportError:
            pytest.skip("transformers not installed")

        from thoughtforge.inference.onnx_export import ONNXEmbedder
        with pytest.raises(FileNotFoundError):
            ONNXEmbedder(tmp_path)

    def test_onnx_embedder_embedding_dim_default(self, tmp_path, monkeypatch):
        """embedding_dim property should return 384 as fallback."""
        from thoughtforge.inference.onnx_export import ONNXEmbedder

        class MockSession:
            def get_outputs(self):
                class O:
                    shape = []
                return [O()]

        class MockTokenizer:
            pass

        embedder = object.__new__(ONNXEmbedder)
        embedder._session = MockSession()
        embedder._tokenizer = MockTokenizer()
        embedder._model_dir = tmp_path

        assert embedder.embedding_dim == 384

    def test_encode_empty_list_returns_empty_array(self, tmp_path, monkeypatch):
        """encode([]) should return an empty numpy array."""
        import numpy as np
        from thoughtforge.inference.onnx_export import ONNXEmbedder

        class MockSession:
            def get_outputs(self):
                class O:
                    shape = [None, None, 384]
                return [O()]

        class MockTokenizer:
            pass

        embedder = object.__new__(ONNXEmbedder)
        embedder._session = MockSession()
        embedder._tokenizer = MockTokenizer()
        embedder._model_dir = tmp_path

        result = embedder.encode([])
        assert result.shape[0] == 0


# ── EdgeSubsetBuilder ─────────────────────────────────────────────────────────

class TestEdgeSubsetBuilderAPI:
    def setup_method(self):
        from thoughtforge.etl.subset import EdgeSubsetBuilder
        self.builder = EdgeSubsetBuilder()

    def test_builder_instantiates(self):
        from thoughtforge.etl.subset import EdgeSubsetBuilder
        assert EdgeSubsetBuilder() is not None

    def test_build_method_exists(self):
        assert callable(getattr(self.builder, "build", None))

    def test_supported_profiles_returns_all_six(self):
        from thoughtforge.etl.subset import EdgeSubsetBuilder
        profiles = EdgeSubsetBuilder.supported_profiles()
        expected = {"pi_zero", "phone_low", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"}
        assert expected.issubset(set(profiles))

    def test_build_raises_for_missing_source_db(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            self.builder.build(
                source_db=tmp_path / "nonexistent.db",
                profile_id="pi_zero",
            )

    def test_build_raises_for_unknown_profile(self, tmp_path):
        db_path = tmp_path / "empty.db"
        db_path.touch()
        with pytest.raises(ValueError, match="Unknown profile_id"):
            self.builder.build(
                source_db=db_path,
                profile_id="neptune_ufo",
            )

    def test_build_succeeds_on_empty_db(self, tmp_path):
        """Building a subset from an empty (schema-less) DB should succeed without crash."""
        db_path = tmp_path / "empty.db"
        import sqlite3
        sqlite3.connect(str(db_path)).close()

        result = self.builder.build(
            source_db=db_path,
            output_path=tmp_path / "subset.db",
            profile_id="pi_zero",
        )
        assert result.profile_id == "pi_zero"
        assert result.entities_copied == 0
        assert result.statements_copied == 0
        assert isinstance(result.notes, list)

    def test_build_copies_entities_from_populated_db(self, tmp_path):
        """Build should copy entities from a DB that has the schema."""
        import sqlite3
        db_path = tmp_path / "full.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE entities (
                qid TEXT PRIMARY KEY,
                label_en TEXT,
                description_en TEXT,
                aliases_en TEXT,
                instance_of TEXT,
                popularity_score REAL DEFAULT 0.0,
                source TEXT DEFAULT 'test'
            )
        """)
        for i in range(10):
            conn.execute(
                "INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"Q{i+1}", f"entity_{i}", f"desc_{i}", "", "item", float(i), "test"),
            )
        conn.commit()
        conn.close()

        result = self.builder.build(
            source_db=db_path,
            output_path=tmp_path / "subset.db",
            profile_id="pi_zero",
            max_entities=5,
        )
        assert result.entities_copied == 5
        assert result.success is True
        assert result.output_path.exists()

    def test_entity_limit_loaded_from_profile(self):
        """_load_entity_limit should return a non-negative integer for all profiles."""
        from thoughtforge.etl.subset import EdgeSubsetBuilder
        b = EdgeSubsetBuilder()
        for pid in EdgeSubsetBuilder.supported_profiles():
            limit = b._load_entity_limit(pid)
            assert isinstance(limit, int)
            assert limit >= 0


class TestSubsetResultDataclass:
    def _make_result(self, tmp_path):
        from thoughtforge.etl.subset import SubsetResult
        return SubsetResult(
            profile_id="pi_zero",
            source_db=tmp_path / "source.db",
            output_path=tmp_path / "subset.db",
            entities_copied=1000,
            statements_copied=5000,
            reference_chunks_copied=200,
            entity_limit=50000,
            success=True,
        )

    def test_dataclass_fields(self, tmp_path):
        r = self._make_result(tmp_path)
        assert r.profile_id == "pi_zero"
        assert r.entities_copied == 1000
        assert r.statements_copied == 5000
        assert r.success is True

    def test_size_mb_zero_when_file_missing(self, tmp_path):
        r = self._make_result(tmp_path)
        assert r.size_mb == 0.0

    def test_size_mb_nonzero_when_file_exists(self, tmp_path):
        from thoughtforge.etl.subset import SubsetResult
        out = tmp_path / "subset.db"
        out.write_bytes(b"x" * 1024 * 1024)  # 1MB
        r = SubsetResult(
            profile_id="pi_zero",
            source_db=tmp_path / "source.db",
            output_path=out,
            entities_copied=0,
            statements_copied=0,
            reference_chunks_copied=0,
            entity_limit=50000,
            success=True,
        )
        assert r.size_mb > 0.0

    def test_notes_default_empty(self, tmp_path):
        r = self._make_result(tmp_path)
        assert r.notes == []


# ── Deployment files ──────────────────────────────────────────────────────────

class TestDeploymentFilesExist:
    def test_dockerfile_exists(self):
        assert (_REPO / "Dockerfile").is_file()

    def test_dockercompose_exists(self):
        assert (_REPO / "docker-compose.yml").is_file()

    def test_dockerignore_exists(self):
        assert (_REPO / ".dockerignore").is_file()

    def test_install_linux_exists(self):
        assert (_SCRIPTS / "install_linux.sh").is_file()

    def test_install_mac_exists(self):
        assert (_SCRIPTS / "install_mac.sh").is_file()

    def test_install_windows_exists(self):
        assert (_SCRIPTS / "install_windows.ps1").is_file()

    def test_install_termux_exists(self):
        assert (_SCRIPTS / "install_termux.sh").is_file()

    def test_install_pi_exists(self):
        assert (_SCRIPTS / "install_pi.sh").is_file()


class TestDockerfileContent:
    def setup_method(self):
        self.text = (_REPO / "Dockerfile").read_text(encoding="utf-8")

    def test_has_from_directive(self):
        assert "FROM" in self.text

    def test_has_profile_arg(self):
        assert "ARG PROFILE" in self.text

    def test_has_healthcheck(self):
        assert "HEALTHCHECK" in self.text

    def test_has_entrypoint(self):
        assert "ENTRYPOINT" in self.text

    def test_has_workdir(self):
        assert "WORKDIR" in self.text

    def test_has_multistage_build(self):
        # Two FROM statements = multi-stage
        from_count = len(re.findall(r"^FROM ", self.text, re.MULTILINE))
        assert from_count >= 2

    def test_has_volume_directive(self):
        assert "VOLUME" in self.text

    def test_references_run_thoughtforge(self):
        assert "run_thoughtforge" in self.text


class TestDockerComposeContent:
    def setup_method(self):
        self.text = (_REPO / "docker-compose.yml").read_text(encoding="utf-8")

    def test_has_services_section(self):
        assert "services:" in self.text

    def test_has_desktop_service(self):
        assert "thoughtforge-desktop" in self.text

    def test_has_pi_service(self):
        assert "thoughtforge-pi" in self.text

    def test_has_phone_service(self):
        assert "thoughtforge-phone" in self.text

    def test_references_profile_build_arg(self):
        assert "PROFILE" in self.text

    def test_has_volumes_section(self):
        assert "volumes:" in self.text

    def test_references_data_volume(self):
        assert "thoughtforge-data" in self.text


class TestDockerignoreContent:
    def setup_method(self):
        self.text = (_REPO / ".dockerignore").read_text(encoding="utf-8")

    def test_excludes_data_dir(self):
        assert "data/" in self.text

    def test_excludes_gguf_files(self):
        assert "*.gguf" in self.text

    def test_excludes_git(self):
        assert ".git/" in self.text

    def test_excludes_pycache(self):
        assert "__pycache__/" in self.text

    def test_excludes_venv(self):
        assert ".venv/" in self.text or "venv/" in self.text


# ── Install script content ────────────────────────────────────────────────────

class TestInstallScriptContent:
    def test_linux_installs_python(self):
        text = (_SCRIPTS / "install_linux.sh").read_text(encoding="utf-8")
        assert "python3" in text or "python" in text

    def test_linux_installs_pip(self):
        text = (_SCRIPTS / "install_linux.sh").read_text(encoding="utf-8")
        assert "pip install" in text

    def test_linux_handles_multiple_distros(self):
        text = (_SCRIPTS / "install_linux.sh").read_text(encoding="utf-8")
        assert "ubuntu" in text.lower() or "debian" in text.lower()
        assert "arch" in text.lower()

    def test_linux_creates_virtualenv(self):
        text = (_SCRIPTS / "install_linux.sh").read_text(encoding="utf-8")
        assert "venv" in text

    def test_mac_references_homebrew(self):
        text = (_SCRIPTS / "install_mac.sh").read_text(encoding="utf-8")
        assert "brew" in text

    def test_mac_handles_apple_silicon(self):
        text = (_SCRIPTS / "install_mac.sh").read_text(encoding="utf-8")
        assert "arm64" in text or "Metal" in text or "metal" in text

    def test_windows_is_powershell(self):
        text = (_SCRIPTS / "install_windows.ps1").read_text(encoding="utf-8")
        assert "param(" in text or "Param(" in text

    def test_windows_references_venv(self):
        text = (_SCRIPTS / "install_windows.ps1").read_text(encoding="utf-8")
        assert ".venv" in text

    def test_windows_references_vulkan(self):
        text = (_SCRIPTS / "install_windows.ps1").read_text(encoding="utf-8")
        assert "Vulkan" in text or "vulkan" in text or "DirectML" in text

    def test_termux_references_pkg(self):
        text = (_SCRIPTS / "install_termux.sh").read_text(encoding="utf-8")
        assert "pkg" in text

    def test_termux_targets_phone_low(self):
        text = (_SCRIPTS / "install_termux.sh").read_text(encoding="utf-8")
        assert "phone_low" in text

    def test_termux_mentions_tinyllama(self):
        text = (_SCRIPTS / "install_termux.sh").read_text(encoding="utf-8")
        assert "TinyLlama" in text or "tinyllama" in text.lower()

    def test_pi_auto_detects_profile(self):
        text = (_SCRIPTS / "install_pi.sh").read_text(encoding="utf-8")
        assert "pi_zero" in text
        assert "pi_5" in text

    def test_pi_detects_ram(self):
        text = (_SCRIPTS / "install_pi.sh").read_text(encoding="utf-8")
        assert "MemTotal" in text or "meminfo" in text

    def test_pi_references_vulkan(self):
        text = (_SCRIPTS / "install_pi.sh").read_text(encoding="utf-8")
        assert "VULKAN" in text or "vulkan" in text.lower()


# ── Hardware profile deployment sections ──────────────────────────────────────

class TestHardwareProfileDeploymentSections:
    @pytest.mark.parametrize("profile_name", [
        "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
    ])
    def test_profile_has_deployment_section(self, profile_name):
        profile_path = _PROFILES_DIR / f"{profile_name}.json"
        assert profile_path.exists(), f"Profile file missing: {profile_path}"
        data = json.loads(profile_path.read_text())
        assert "deployment" in data, f"Profile {profile_name} missing 'deployment' section"

    @pytest.mark.parametrize("profile_name", [
        "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
    ])
    def test_profile_deployment_has_platforms(self, profile_name):
        data = json.loads((_PROFILES_DIR / f"{profile_name}.json").read_text())
        deployment = data.get("deployment", {})
        assert "platforms" in deployment, f"{profile_name} deployment missing 'platforms'"
        assert isinstance(deployment["platforms"], list)

    @pytest.mark.parametrize("profile_name", [
        "phone_low", "pi_zero", "pi_5", "desktop_cpu", "desktop_gpu", "server_gpu"
    ])
    def test_profile_deployment_has_runtime(self, profile_name):
        data = json.loads((_PROFILES_DIR / f"{profile_name}.json").read_text())
        deployment = data.get("deployment", {})
        assert "runtime" in deployment, f"{profile_name} deployment missing 'runtime'"

    def test_phone_profile_has_onnx_export_flag(self):
        data = json.loads((_PROFILES_DIR / "phone_low.json").read_text())
        assert data["deployment"].get("onnx_export") is True

    def test_pi_zero_profile_has_onnx_export_flag(self):
        data = json.loads((_PROFILES_DIR / "pi_zero.json").read_text())
        assert data["deployment"].get("onnx_export") is True


# ── ONNX export module exports ────────────────────────────────────────────────

class TestOnnxModuleExports:
    def test_module_imports_cleanly(self):
        import thoughtforge.inference.onnx_export as mod
        assert hasattr(mod, "OnnxExporter")
        assert hasattr(mod, "ONNXEmbedder")
        assert hasattr(mod, "ExportResult")

    def test_constants_defined(self):
        from thoughtforge.inference.onnx_export import (
            _DEFAULT_MODEL,
            _ONNX_MODEL_FILENAME,
            _EXPORT_OPSET,
        )
        assert _DEFAULT_MODEL.startswith("sentence-transformers") or "/" in _DEFAULT_MODEL
        assert _ONNX_MODEL_FILENAME.endswith(".onnx")
        assert isinstance(_EXPORT_OPSET, int)


# ── Subset module exports ──────────────────────────────────────────────────────

class TestSubsetModuleExports:
    def test_module_imports_cleanly(self):
        import thoughtforge.etl.subset as mod
        assert hasattr(mod, "EdgeSubsetBuilder")
        assert hasattr(mod, "SubsetResult")
        assert hasattr(mod, "_PROFILE_ENTITY_LIMITS")

    def test_profile_entity_limits_all_non_negative(self):
        from thoughtforge.etl.subset import _PROFILE_ENTITY_LIMITS
        for pid, limit in _PROFILE_ENTITY_LIMITS.items():
            assert limit >= 0, f"Profile {pid} has negative entity limit"

    def test_server_gpu_has_no_limit(self):
        from thoughtforge.etl.subset import _PROFILE_ENTITY_LIMITS
        assert _PROFILE_ENTITY_LIMITS["server_gpu"] == 0
