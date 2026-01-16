"""Sync commands: merge (push to origin)."""

from __future__ import annotations

from pathlib import Path

from ..core import git
from ..core.config import load_config
from ..utils.colors import Colors, c
from .agent import resolve_session


def cmd_merge(args) -> None:
    """Merge an agent's changes back to origin branch (push)."""
    session = resolve_session(args.session)
    if not session:
        return

    config = load_config()
    agent = config["agents"].get(session)
    if not agent:
        print(c("Agent not found", Colors.RED))
        return

    worktree_path = Path(agent["worktree"])
    branch = agent["branch"]

    print(c(f"\nMerging changes from {branch}...", Colors.CYAN))

    # First, ensure all changes are committed in worktree
    status_result = git.status(worktree_path)
    if status_result.stdout.strip():
        print(c("Warning: Uncommitted changes in worktree", Colors.YELLOW))
        if not args.force:
            print("Use --force to merge anyway")
            return

    # Push the branch
    result = git.push(worktree_path, branch=branch)
    if result.returncode == 0:
        print(c(f"+ Pushed {branch} to origin", Colors.GREEN))
    else:
        print(c(f"Push failed: {result.stderr}", Colors.RED))
