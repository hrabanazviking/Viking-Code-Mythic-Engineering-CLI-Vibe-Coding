"""Cross-platform path resolution for ThoughtForge."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT: Path | None = None


def get_project_root() -> Path:
    """Return the project root directory (contains pyproject.toml)."""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        candidate = Path(__file__).resolve()
        for parent in candidate.parents:
            if (parent / "pyproject.toml").exists():
                _PROJECT_ROOT = parent
                return _PROJECT_ROOT
        # Fallback: assume cwd is project root
        _PROJECT_ROOT = Path.cwd()
        logger.warning("Could not locate pyproject.toml — using cwd as project root: %s", _PROJECT_ROOT)
    return _PROJECT_ROOT


def get_data_dir() -> Path:
    """Return the data/ directory, creating it if absent."""
    path = get_project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_knowledge_db_path() -> Path:
    """Return the path to the main SQLite knowledge database."""
    return get_data_dir() / "knowledge.db"


def get_embeddings_dir() -> Path:
    """Return the embeddings cache directory."""
    path = get_data_dir() / "embeddings"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_memory_dir() -> Path:
    """Return the conversation memory directory."""
    path = get_data_dir() / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_knowledge_reference_dir() -> Path:
    """Return the built-in knowledge reference documents directory."""
    return get_data_dir() / "knowledge_reference"


def get_configs_dir() -> Path:
    """Return the configs/ directory."""
    return get_project_root() / "configs"


def get_hardware_profiles_dir() -> Path:
    """Return the hardware_profiles/ directory."""
    return get_project_root() / "hardware_profiles"


def get_logs_dir() -> Path:
    """Return the logs/ directory, creating it if absent."""
    path = get_project_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
