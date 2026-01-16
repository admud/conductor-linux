"""Safe tmux operations (no shell=True)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from ..utils.process import run


def new_session(
    name: str,
    cwd: Path,
    command: Optional[list[str]] = None,
) -> subprocess.CompletedProcess:
    """
    Create a new tmux session.

    Args:
        name: Session name
        cwd: Working directory for the session
        command: Optional command to run (as list of args)
    """
    args = ["tmux", "new-session", "-d", "-s", name, "-c", str(cwd)]
    if command:
        # Join command args for tmux (tmux expects a single command string)
        args.extend(command)
    return run(args)


def kill_session(name: str) -> subprocess.CompletedProcess:
    """Kill a tmux session."""
    return run(["tmux", "kill-session", "-t", name])


def list_sessions() -> list[str]:
    """List all tmux session names."""
    result = run(["tmux", "list-sessions", "-F", "#{session_name}"])
    if result.returncode != 0:
        return []
    return [s for s in result.stdout.strip().split("\n") if s]


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    result = run(["tmux", "has-session", "-t", name])
    return result.returncode == 0


def capture_pane(session: str, lines: int = 50) -> str:
    """Capture output from a tmux pane."""
    result = run(
        ["tmux", "capture-pane", "-t", session, "-p", "-S", f"-{lines}"]
    )
    if result.returncode == 0:
        return result.stdout
    return ""


def attach(session: str) -> None:
    """
    Attach to a tmux session.

    Uses os.execvp for safety - replaces current process.
    """
    os.execvp("tmux", ["tmux", "attach", "-t", session])


def send_keys(session: str, keys: str) -> subprocess.CompletedProcess:
    """Send keys to a tmux session."""
    return run(["tmux", "send-keys", "-t", session, keys, "Enter"])
