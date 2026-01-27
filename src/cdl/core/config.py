"""Configuration management for CDL."""

from __future__ import annotations

import json
import os
import tempfile
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
        return {"repos": {}, "agents": {}, "archives": {}}

    try:
        data = json.loads(CONFIG_FILE.read_text())
        if "repos" not in data:
            data["repos"] = {}
        if "agents" not in data:
            data["agents"] = {}
        if "archives" not in data:
            data["archives"] = {}
        return data
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
        config_text = json.dumps(config, indent=2)
        config_dir = CONFIG_FILE.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=config_dir,
            delete=False,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(config_text)
            temp_path = Path(temp_file.name)
        os.replace(temp_path, CONFIG_FILE)
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass
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
