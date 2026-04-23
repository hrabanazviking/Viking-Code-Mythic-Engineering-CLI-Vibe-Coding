"""
setup_thoughtforge.py — MindSpark: ThoughtForge interactive setup wizard.

Usage:
  python setup_thoughtforge.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ── ANSI colour support ────────────────────────────────────────────────────────

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t: str) -> str:  return _c("32", t)
def yellow(t: str) -> str: return _c("33", t)
def cyan(t: str) -> str:   return _c("36", t)
def bold(t: str) -> str:   return _c("1", t)
def dim(t: str) -> str:    return _c("2", t)
def red(t: str) -> str:    return _c("31", t)


# ── Project root (same logic as paths.py) ─────────────────────────────────────

def _find_project_root() -> Path:
    candidate = Path(__file__).resolve().parent
    for p in [candidate] + list(candidate.parents):
        if (p / "pyproject.toml").exists():
            return p
    return candidate


PROJECT_ROOT = _find_project_root()
CONFIGS_DIR = PROJECT_ROOT / "configs"

# ── Curated model lists ────────────────────────────────────────────────────────

OLLAMA_MODELS = [
    ("tinyllama:latest",  "~637 MB",  "ultra-fast, any hardware"),
    ("phi3:mini",         "~2.3 GB",  "fast + smart, good for CPU"),
    ("llama3.2:3b",       "~2.0 GB",  "balanced quality/speed"),
    ("mistral:7b",        "~4.1 GB",  "strong reasoning, needs 8 GB RAM"),
    ("llama3.1:8b",       "~4.7 GB",  "excellent quality, needs 8 GB RAM"),
    ("qwen2.5:14b",       "~8.7 GB",  "top quality, needs 16 GB RAM"),
]

GGUF_MODELS = [
    (
        "Phi-3-mini Q4_K_M",
        "~2.2 GB",
        "microsoft/Phi-3-mini-4k-instruct-gguf",
        "Phi-3-mini-4k-instruct-q4.gguf",
    ),
    (
        "Llama-3.2-3B Q4_K_M",
        "~2.0 GB",
        "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    ),
    (
        "Mistral-7B Q4_K_M",
        "~4.1 GB",
        "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    ),
    (
        "Llama-3.1-8B Q4_K_M",
        "~4.7 GB",
        "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    ),
]

# ── HTTP helper (stdlib only) ──────────────────────────────────────────────────

def _http_get(url: str, timeout: float = 3.0) -> tuple[int, Any]:
    """GET url. Returns (status_code, parsed_json_or_None). Never raises."""
    try:
        import json
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "ThoughtForge-Setup/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except Exception:
                return resp.status, None
    except Exception:
        return 0, None


# ── Input helpers ──────────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    bracket = f" [{default}]" if default else ""
    try:
        raw = input(f"{prompt}{bracket}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return raw if raw else default


def _ask_yn(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    try:
        raw = input(f"{prompt} {hint}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not raw:
        return default
    return raw.startswith("y")


def _pick(prompt: str, options: list[str], default: int = 1) -> int:
    """Show numbered menu and return 1-based index (or default on bad input)."""
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    raw = _ask(prompt, str(default))
    try:
        choice = int(raw)
        if 1 <= choice <= len(options):
            return choice
    except ValueError:
        pass
    print(f"  Invalid choice — using {default}")
    return default


# ── Banner ─────────────────────────────────────────────────────────────────────

def _print_banner() -> None:
    print()
    print(bold(cyan("╔══════════════════════════════════════════════════╗")))
    print(bold(cyan("║   MindSpark: ThoughtForge — Setup Wizard         ║")))
    print(bold(cyan("║   Cognitive enhancement layer for any LLM        ║")))
    print(bold(cyan("╚══════════════════════════════════════════════════╝")))
    print()


# ── System detection ───────────────────────────────────────────────────────────

def _detect_python() -> str:
    v = sys.version_info
    return f"{v.major}.{v.minor}.{v.micro}"


def _detect_cuda() -> bool:
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _detect_ollama() -> tuple[bool, list[str]]:
    status, data = _http_get("http://localhost:11434/api/tags")
    if status == 200 and isinstance(data, dict):
        models = [m.get("name", "") for m in data.get("models", [])]
        return True, [m for m in models if m]
    return False, []


def _detect_lmstudio(base_url: str = "http://localhost:1234") -> tuple[bool, list[str]]:
    status, data = _http_get(f"{base_url}/v1/models")
    if status == 200 and isinstance(data, dict):
        models = [m.get("id", "") for m in data.get("data", [])]
        return True, [m for m in models if m]
    return False, []


def _detect_llama_cpp() -> bool:
    try:
        import importlib
        return importlib.util.find_spec("llama_cpp") is not None
    except Exception:
        return False


def _run_detection() -> dict:
    print(bold("Detecting your system..."))
    print()

    python_ver = _detect_python()
    print(f"  Python         : {green(python_ver)}")

    cuda = _detect_cuda()
    cuda_str = green("available (NVIDIA GPU detected)") if cuda else dim("not found")
    print(f"  CUDA/nvidia-smi: {cuda_str}")

    print(f"  Ollama         : ", end="", flush=True)
    ollama_running, ollama_models = _detect_ollama()
    if ollama_running:
        model_count = f"{len(ollama_models)} model(s) loaded"
        print(green(f"running — {model_count}"))
    else:
        print(dim("not running (or not installed)"))

    print(f"  LM Studio      : ", end="", flush=True)
    lms_running, lms_models = _detect_lmstudio()
    if lms_running:
        print(green(f"running — {len(lms_models)} model(s) available"))
    else:
        print(dim("not running (or not installed)"))

    llama_cpp = _detect_llama_cpp()
    llama_str = green("importable") if llama_cpp else dim("not installed")
    print(f"  llama-cpp-python: {llama_str}")
    print()

    return {
        "python_ver": python_ver,
        "cuda": cuda,
        "ollama_running": ollama_running,
        "ollama_models": ollama_models,
        "lms_running": lms_running,
        "lms_models": lms_models,
        "llama_cpp": llama_cpp,
    }


# ── Backend setup handlers ─────────────────────────────────────────────────────

def _setup_ollama(detected: dict) -> dict | None:
    """Configure Ollama backend. Returns config dict or None on abort."""
    ollama_url = "http://localhost:11434"

    if not detected["ollama_running"]:
        print(yellow("Ollama is not running. Attempting to start it..."))
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(2)
            ollama_running, ollama_models = _detect_ollama()
            if ollama_running:
                print(green("Ollama started successfully."))
                detected["ollama_running"] = True
                detected["ollama_models"] = ollama_models
            else:
                print(red("Could not start Ollama. Is it installed?"))
                print("  Install: https://ollama.com/download")
                if not _ask_yn("Continue anyway (configure for later)?", default=False):
                    return None
        except FileNotFoundError:
            print(red("'ollama' command not found."))
            print("  Install: https://ollama.com/download")
            if not _ask_yn("Continue anyway (configure for later)?", default=False):
                return None

    local_models = detected.get("ollama_models", [])

    if local_models:
        print(bold("Local Ollama models found:"))
        for i, m in enumerate(local_models, 1):
            print(f"  {i}. {m}")
        print()
        options = local_models + ["Pull a new model"]
        choice = _pick("Choose model", options, default=1)
        if choice <= len(local_models):
            selected_model = local_models[choice - 1]
        else:
            selected_model = _pull_ollama_model()
            if selected_model is None:
                return None
    else:
        print(dim("No local Ollama models found."))
        selected_model = _pull_ollama_model()
        if selected_model is None:
            return None

    if selected_model is None:
        return None

    return {
        "backend": "ollama",
        "ollama_url": ollama_url,
        "ollama_model": selected_model,
    }


def _pull_ollama_model() -> str | None:
    print(bold("Curated Ollama models:"))
    labels = [f"{name:25s} {size:9s}  {desc}" for name, size, desc in OLLAMA_MODELS]
    choice = _pick("Choose a model to pull", labels, default=1)
    model_name = OLLAMA_MODELS[choice - 1][0]

    print(f"\nPulling {cyan(model_name)} — this may take a while...")
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            timeout=600,
        )
        if result.returncode == 0:
            print(green(f"Model '{model_name}' pulled successfully."))
            return model_name
        else:
            print(red(f"Pull failed (exit code {result.returncode})."))
            manual = _ask("Enter model name manually (or press Enter to skip)", "")
            return manual if manual else None
    except FileNotFoundError:
        print(red("'ollama' command not found."))
        return None
    except subprocess.TimeoutExpired:
        print(red("Pull timed out. Try running manually: ollama pull " + model_name))
        return None


def _setup_lmstudio(detected: dict) -> dict | None:
    default_url = "http://localhost:1234"
    url = _ask("LM Studio URL", default_url)

    if not url.startswith("http"):
        url = "http://" + url

    running, models = _detect_lmstudio(url)

    if not running:
        print(yellow("LM Studio not reachable at that URL."))
        print("  Make sure LM Studio is running and the API server is enabled.")
        if not _ask_yn("Continue anyway?", default=False):
            return None
        model = _ask("Model name to use", "")
    elif models:
        print(bold("Available LM Studio models:"))
        choice = _pick("Choose model", models, default=1)
        model = models[choice - 1]
    else:
        print(yellow("LM Studio is running but reports no loaded models."))
        print("  Load a model in the LM Studio UI first.")
        model = _ask("Model identifier to use (or press Enter to skip)", "")

    return {
        "backend": "lmstudio",
        "lmstudio_url": url,
        "lmstudio_model": model,
    }


def _setup_openai_compatible() -> dict | None:
    print("Configure any OpenAI-compatible API endpoint.")
    print()
    base_url = _ask("Base URL", "https://api.openai.com/v1")
    api_key = _ask("API key (leave blank to use env var OPENAI_API_KEY)", "")
    model = _ask("Model name", "gpt-4o-mini")

    if not model:
        print(red("Model name is required."))
        return None

    return {
        "backend": "openai_compatible",
        "openai_base_url": base_url,
        "openai_api_key": api_key,
        "openai_model": model,
    }


def _setup_huggingface() -> dict | None:
    print("Configure HuggingFace Inference API.")
    print()
    print(bold("Suggested models (public, no token needed):"))
    suggestions = [
        "mistralai/Mistral-7B-Instruct-v0.3",
        "HuggingFaceH4/zephyr-7b-beta",
        "microsoft/Phi-3-mini-4k-instruct",
        "meta-llama/Meta-Llama-3-8B-Instruct  (requires HF token + access)",
    ]
    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. {s}")
    print()

    model = _ask("HuggingFace model repo", "mistralai/Mistral-7B-Instruct-v0.3")
    token = _ask("HuggingFace token (optional — press Enter to skip)", "")

    if not model:
        print(red("Model name is required."))
        return None

    return {
        "backend": "huggingface",
        "hf_model": model,
        "hf_token": token,
    }


def _setup_local_gguf(detected: dict) -> dict | None:
    print("Configure local GGUF model.")
    print()

    # Scan common directories for .gguf files
    search_dirs = [
        PROJECT_ROOT / "models",
        Path.home() / "models",
        Path.home() / ".cache" / "huggingface",
        Path("C:/models") if sys.platform == "win32" else Path("/models"),
    ]
    found_ggufs: list[Path] = []
    for d in search_dirs:
        if d.exists():
            found_ggufs.extend(sorted(d.glob("**/*.gguf"))[:10])

    if found_ggufs:
        print(bold("GGUF files found:"))
        labels = [str(p) for p in found_ggufs]
        labels.append("Enter a different path")
        labels.append("Download from curated list")
        choice = _pick("Choose a file", labels, default=1)

        if choice <= len(found_ggufs):
            return {
                "backend": "turboquant",
                "gguf_model_path": str(found_ggufs[choice - 1]),
            }
        elif choice == len(found_ggufs) + 1:
            path_str = _ask("Path to .gguf file", "")
            if not path_str:
                return None
            p = Path(path_str)
            if not p.exists():
                print(yellow(f"Warning: file not found at {p}"))
                if not _ask_yn("Use this path anyway?", default=False):
                    return None
            return {"backend": "turboquant", "gguf_model_path": str(p)}
        else:
            return _download_gguf_model()
    else:
        print(dim("No .gguf files found in common locations."))
        print()
        print(bold("Options:"))
        opts = ["Enter path to existing .gguf file", "Download from curated list"]
        choice = _pick("Choose", opts, default=2)

        if choice == 1:
            path_str = _ask("Path to .gguf file", "")
            if not path_str:
                return None
            p = Path(path_str)
            if not p.exists():
                print(yellow(f"Warning: file not found at {p}"))
                if not _ask_yn("Use this path anyway?", default=False):
                    return None
            return {"backend": "turboquant", "gguf_model_path": str(p)}
        else:
            return _download_gguf_model()


def _download_gguf_model() -> dict | None:
    print()
    print(bold("Curated GGUF models (downloaded via huggingface-hub):"))
    labels = [f"{name:28s} {size:9s}  {repo}" for name, size, repo, _ in GGUF_MODELS]
    choice = _pick("Choose a model", labels, default=1)
    _, _, repo, filename = GGUF_MODELS[choice - 1]

    save_dir = PROJECT_ROOT / "models"
    save_dir.mkdir(parents=True, exist_ok=True)
    dest = save_dir / filename

    if dest.exists():
        print(green(f"Model already exists at {dest}"))
        return {"backend": "turboquant", "gguf_model_path": str(dest)}

    print(f"\nDownloading {cyan(filename)} from {repo}...")
    print("This requires the 'huggingface_hub' package.")

    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=str(save_dir),
        )
        print(green(f"Downloaded to {path}"))
        return {"backend": "turboquant", "gguf_model_path": str(path)}
    except ImportError:
        print(red("huggingface_hub not installed."))
        print("  Run: pip install huggingface-hub")
        manual = _ask("Or enter path to model once downloaded", "")
        return {"backend": "turboquant", "gguf_model_path": manual} if manual else None
    except Exception as e:
        print(red(f"Download failed: {e}"))
        manual = _ask("Enter path to model if already downloaded", "")
        return {"backend": "turboquant", "gguf_model_path": manual} if manual else None


# ── Backend selection menu ─────────────────────────────────────────────────────

def _choose_backend(detected: dict) -> dict | None:
    print(bold("Choose your backend:"))
    print()

    options = [
        "Ollama        — local server, easiest setup",
        "LM Studio     — local server with GUI",
        "OpenAI-compat — any OpenAI-compatible API (OpenAI, Together, etc.)",
        "HuggingFace   — HuggingFace Inference API",
        "Local GGUF    — direct llama-cpp-python (no server needed)",
        "None          — knowledge-only mode (no generation)",
    ]
    choice = _pick("Backend", options, default=1)
    print()

    if choice == 1:
        return _setup_ollama(detected)
    elif choice == 2:
        return _setup_lmstudio(detected)
    elif choice == 3:
        return _setup_openai_compatible()
    elif choice == 4:
        return _setup_huggingface()
    elif choice == 5:
        return _setup_local_gguf(detected)
    else:
        return {"backend": "none"}


# ── Optional API keys ──────────────────────────────────────────────────────────

def _ask_optional_keys(config: dict) -> None:
    print(bold("Optional API keys:"))
    print(dim("  Press Enter to skip any you don't need."))
    print()

    if not config.get("hf_token"):
        token = _ask("HuggingFace token (for gated models)", "")
        if token:
            config["hf_token"] = token

    print()


# ── Knowledge base build ───────────────────────────────────────────────────────

def _build_knowledge_base() -> bool:
    print(bold("Building knowledge base from reference data..."))
    print(dim("  (This indexes built-in reference documents — usually fast)"))
    print()

    forge_script = PROJECT_ROOT / "forge_memory.py"
    if not forge_script.exists():
        print(yellow("forge_memory.py not found — skipping knowledge base build."))
        return False

    try:
        proc = subprocess.Popen(
            [sys.executable, str(forge_script), "reference"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        spinner = ["|", "/", "-", "\\"]
        i = 0
        while True:
            if proc.stdout:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line.strip():
                    # Show last status line compactly
                    short = line.strip()[:65]
                    print(f"\r  {spinner[i % 4]}  {short:<65}", end="", flush=True)
                    i += 1
        print("\r" + " " * 72 + "\r", end="")
        rc = proc.wait()
        if rc == 0:
            print(green("Knowledge base built successfully."))
            return True
        else:
            print(yellow(f"Knowledge base build exited with code {rc}."))
            return False
    except Exception as e:
        print(yellow(f"Knowledge base build failed: {e}"))
        return False


# ── Test query ─────────────────────────────────────────────────────────────────

def _run_test_query(config: dict) -> bool:
    print(bold("Running a test query..."))
    print()

    # Add project src to path so we can import thoughtforge
    src_path = str(PROJECT_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    try:
        from thoughtforge.cognition.core import ThoughtForgeCore
        from thoughtforge.inference.unified_backend import load_backend_from_config

        # Temporarily write config so load_backend_from_config picks it up
        _write_config(config)

        backend = load_backend_from_config()
        core = ThoughtForgeCore(backend=backend)
        result = core.think("What is MindSpark ThoughtForge?")
        if result and result.text:
            print(green("Test query succeeded."))
            print(dim(f"  Response: {result.text[:120]}..."))
            return True
        else:
            print(yellow("Test query returned an empty response."))
            return False
    except Exception as e:
        print(yellow(f"Test query failed: {e}"))
        print(dim("  This may be normal if the backend is not yet running."))
        return False


# ── Config writer ──────────────────────────────────────────────────────────────

def _write_config(config: dict) -> Path:
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    config_path = CONFIGS_DIR / "user_config.yaml"

    lines: list[str] = [
        "# MindSpark: ThoughtForge — User Configuration",
        "# Generated by setup_thoughtforge.py",
        "# Edit this file to change backend settings.",
        "",
    ]

    # Emit known keys in a sensible order
    key_order = [
        "backend",
        "ollama_url", "ollama_model",
        "lmstudio_url", "lmstudio_model",
        "openai_base_url", "openai_api_key", "openai_model",
        "hf_model", "hf_token",
        "gguf_model_path",
    ]
    emitted: set[str] = set()
    for k in key_order:
        if k in config:
            v = config[k]
            lines.append(f"{k}: {_yaml_scalar(v)}")
            emitted.add(k)

    # Any remaining keys not in the order list
    for k, v in config.items():
        if k not in emitted:
            lines.append(f"{k}: {_yaml_scalar(v)}")

    lines.append("")
    content = "\n".join(lines)
    config_path.write_text(content, encoding="utf-8")
    return config_path


def _yaml_scalar(v: Any) -> str:
    if v is None or v == "":
        return '""'
    s = str(v)
    # Quote if contains special YAML chars or spaces
    if any(c in s for c in (": ", "#", "'", '"', "{", "}", "[", "]", ",")):
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s


# ── Main wizard ────────────────────────────────────────────────────────────────

def main() -> None:
    _print_banner()

    # Check for existing config
    config_path = CONFIGS_DIR / "user_config.yaml"
    if config_path.exists():
        print(yellow("Existing configuration found at:"))
        print(f"  {config_path}")
        print()
        if not _ask_yn("Reconfigure?", default=False):
            print("Setup cancelled — existing config kept.")
            print()
            print(f"Run your forge with: {bold('python run_thoughtforge.py')}")
            return
        print()

    # System detection
    detected = _run_detection()

    # Backend selection
    config = _choose_backend(detected)
    if config is None:
        print(red("Setup aborted."))
        return

    # Optional API keys
    _ask_optional_keys(config)

    # Knowledge base
    if _ask_yn("Build knowledge base from reference data?", default=True):
        print()
        _build_knowledge_base()
        print()

    # Test query
    if config.get("backend", "none") != "none":
        if _ask_yn("Run a test query to verify the backend?", default=True):
            print()
            _run_test_query(config)
            print()

    # Write config
    written_path = _write_config(config)

    # Success
    print()
    print(bold(green("╔══════════════════════════════════════════════════╗")))
    print(bold(green("║   Setup complete!                                ║")))
    print(bold(green("╚══════════════════════════════════════════════════╝")))
    print()
    print(f"Configuration written to:")
    print(f"  {cyan(str(written_path))}")
    print()
    print("Run the forge:")
    print(f"  {bold('python run_thoughtforge.py')}               — interactive REPL")
    print(f"  {bold('python run_thoughtforge.py --chat')}        — persistent chat mode")
    _single_query_cmd = bold('python run_thoughtforge.py "your query"')
    print(f"  {_single_query_cmd}  — single query")
    print(f"  {bold('python run_thoughtforge.py --backend')}     — show backend status")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted.")
        sys.exit(0)
