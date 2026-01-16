"""Configuration management for CDL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import CONFIG_FILE, init_dirs


def load_config() -> dict[str, Any]:
    """
    Load conductor configuration with error handling.

    Returns:
        Configuration dict with 'repos' and 'agents' keys.
        Returns empty config if file doesn't exist or is corrupted.
    """
    if not CONFIG_FILE.exists():
        return {"repos": {}, "agents": {}}

    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        # Backup corrupted config and return empty
        backup = CONFIG_FILE.with_suffix(".json.bak")
        try:
            CONFIG_FILE.rename(backup)
        except OSError:
            pass
        return {"repos": {}, "agents": {}}
    except OSError:
        return {"repos": {}, "agents": {}}


def save_config(config: dict[str, Any]) -> bool:
    """
    Save conductor configuration.

    Args:
        config: Configuration dict to save

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        init_dirs()
        CONFIG_FILE.write_text(json.dumps(config, indent=2))
        return True
    except OSError:
        return False


def init_config() -> dict[str, Any]:
    """
    Initialize conductor directories and config.

    Returns:
        The loaded or newly created configuration
    """
    init_dirs()
    config = load_config()
    if not CONFIG_FILE.exists():
        save_config(config)
    return config
