"""Safe subprocess execution utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Union


def run(
    args: list[str],
    cwd: Optional[Union[str, Path]] = None,
    capture: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run command safely with argument list (no shell injection).

    Args:
        args: Command and arguments as a list (e.g., ["git", "clone", url])
        cwd: Working directory for the command
        capture: Whether to capture stdout/stderr
        check: Whether to raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess with returncode, stdout, stderr
    """
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=capture,
        text=True,
        check=check,
    )


def run_silent(
    args: list[str],
    cwd: Optional[Union[str, Path]] = None,
) -> int:
    """
    Run command silently, returning only the exit code.

    Args:
        args: Command and arguments as a list
        cwd: Working directory for the command

    Returns:
        Exit code (0 for success)
    """
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    return result.returncode


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    result = subprocess.run(
        ["which", command],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
