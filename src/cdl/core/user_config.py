"""User configuration file support (~/.conductor/config.toml)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .paths import CONDUCTOR_HOME

USER_CONFIG_FILE = CONDUCTOR_HOME / "config.toml"

# Default configuration
DEFAULT_CONFIG = {
    "defaults": {
        "auto_accept": False,
        "diff_tool": None,
        "notify": False,
    },
    "aliases": {},
    "hooks": {
        "post_spawn": None,
        "post_complete": None,
    },
}


def load_user_config() -> dict[str, Any]:
    """Load user configuration from TOML file."""
    if not USER_CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    try:
        # Try tomllib (Python 3.11+) first, fall back to tomli
        try:
            import tomllib
            with open(USER_CONFIG_FILE, "rb") as f:
                return tomllib.load(f)
        except ImportError:
            try:
                import tomli
                with open(USER_CONFIG_FILE, "rb") as f:
                    return tomli.load(f)
            except ImportError:
                # No TOML parser available, return defaults
                return DEFAULT_CONFIG.copy()
    except Exception:
        return DEFAULT_CONFIG.copy()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a config value by dot-notation key (e.g., 'defaults.auto_accept')."""
    config = load_user_config()
    keys = key.split(".")
    value = config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value


def create_example_config() -> str:
    """Generate example config file content."""
    return '''# CDL Configuration File
# Location: ~/.conductor/config.toml

[defaults]
# auto_accept = false      # Auto-accept mode for agents
# diff_tool = "delta"      # Diff tool (delta, difftastic, etc.)
# notify = false           # Desktop notifications on completion

[aliases]
# Custom command aliases
# deploy = "spawn myrepo deploy-branch --task 'Deploy to production'"

[hooks]
# Shell commands to run on events
# post_spawn = "notify-send 'CDL' 'Agent spawned'"
# post_complete = "~/.local/bin/on-agent-done.sh"
'''
