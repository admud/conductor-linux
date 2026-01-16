"""Path constants for CDL."""

from pathlib import Path

CONDUCTOR_HOME = Path.home() / ".conductor"
CONFIG_FILE = CONDUCTOR_HOME / "config.json"
REPOS_DIR = CONDUCTOR_HOME / "repos"
WORKTREES_DIR = CONDUCTOR_HOME / "worktrees"


def init_dirs() -> None:
    """Initialize conductor directories."""
    CONDUCTOR_HOME.mkdir(mode=0o700, exist_ok=True)
    REPOS_DIR.mkdir(mode=0o700, exist_ok=True)
    WORKTREES_DIR.mkdir(mode=0o700, exist_ok=True)
