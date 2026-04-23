# __init__.py — INTERFACE.md

## Class: `YggdrasilConfig`

Configuration manager for Yggdrasil.

### `load()`
Load configuration from file.

### `get(key, default)`
Get configuration value using dot notation.

Args:
    key: Configuration key (e.g., "world_tree.max_iterations")
    default: Default value if not found
    
Returns:
    Configuration value

### `set(key, value)`
Set configuration value.

Args:
    key: Configuration key (dot notation)
    value: Value to set

### `save(path)`
Save configuration to file.

### `all()`
Get all configuration.

## Module Functions

### `get_config(config_path)`
Get or create global configuration instance.

Args:
    config_path: Optional path to config file
    
Returns:
    YggdrasilConfig instance

---
**Contract Version**: 1.0 | v8.0.0
