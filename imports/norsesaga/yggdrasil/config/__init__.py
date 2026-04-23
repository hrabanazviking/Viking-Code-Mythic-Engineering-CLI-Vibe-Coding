"""
Yggdrasil Configuration Module
==============================

Handles loading and management of Yggdrasil configuration.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default configuration path
DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.yaml"


class YggdrasilConfig:
    """Configuration manager for Yggdrasil."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config file (uses default if None)
        """
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Loaded config from {self.config_path}")
            else:
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                self._config = self._get_defaults()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = self._get_defaults()
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "general": {"name": "Yggdrasil", "version": "1.0.0"},
            "world_tree": {"execution_mode": "sequential", "max_iterations": 3},
            "llm_queue": {"max_queue_size": 100},
            "realms": {},
            "ravens": {},
            "rag": {"max_context_tokens": 4000},
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "world_tree.max_iterations")
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value.
        
        Args:
            key: Configuration key (dot notation)
            value: Value to set
        """
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, path: str = None):
        """Save configuration to file."""
        save_path = Path(path) if path else self.config_path
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False)
        
        logger.info(f"Saved config to {save_path}")
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self._config.copy()


# Global config instance
_config: Optional[YggdrasilConfig] = None


def get_config(config_path: str = None) -> YggdrasilConfig:
    """
    Get or create global configuration instance.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        YggdrasilConfig instance
    """
    global _config
    
    if _config is None or config_path:
        _config = YggdrasilConfig(config_path)
    
    return _config


__all__ = ["YggdrasilConfig", "get_config"]
