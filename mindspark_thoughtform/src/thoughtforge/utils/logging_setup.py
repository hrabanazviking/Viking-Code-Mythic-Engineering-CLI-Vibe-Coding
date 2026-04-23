"""Logging configuration for ThoughtForge."""

import logging
import logging.handlers
from pathlib import Path
from typing import Any

from thoughtforge.utils.paths import get_logs_dir

_configured = False


def setup_logging(config: dict[str, Any] | None = None) -> None:
    """Configure root logger based on config dict (from default.yaml)."""
    global _configured
    if _configured:
        return

    log_cfg = (config or {}).get("logging", {})
    level_name: str = log_cfg.get("level", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)
    log_to_file: bool = log_cfg.get("log_to_file", True)
    log_to_console: bool = log_cfg.get("log_to_console", True)

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if log_to_console:
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(fmt)
        root.addHandler(console)

    if log_to_file:
        log_dir: Path = Path(log_cfg.get("log_dir", "")) or get_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "thoughtforge.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

    _configured = True
    logging.getLogger(__name__).debug("Logging configured at level %s", level_name)
