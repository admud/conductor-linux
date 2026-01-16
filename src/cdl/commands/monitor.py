"""Monitoring commands: status, attach, logs, diff."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..core import git, tmux
from ..utils.colors import Colors, c
from .repo import get_active_agents
from .agent import resolve_session


def cmd_status(args) -> None:
    """Show detailed status of all agents."""
    agents = get_active_agents()

    print(c("\n+------------------------------------------------------------+", Colors.BOLD))
    print(c("|              CONDUCTOR LINUX - STATUS                      |", Colors.BOLD))
    print(c("+------------------------------------------------------------+", Colors.BOLD))

    if not agents:
        print(c("\n  No active agents.\n", Colors.DIM))
        print(f"  Start one with: {c('cdl spawn <repo> <branch>', Colors.CYAN)}\n")
        return

    for i, agent in enumerate(agents, 1):
        worktree = Path(agent["worktree"])

        # Get git status for this worktree
        git_result = git.status(worktree)
        changes = len([line for line in git_result.stdout.strip().split("\n") if line])

        # Get commit count ahead of origin
        try:
            commits_ahead = git.rev_list_count(worktree, f"origin/{agent['branch']}..HEAD")
        except Exception:
            commits_ahead = 0

        status_icon = c("*", Colors.GREEN)

        print(f"\n  {status_icon} {c(f'Agent #{i}', Colors.BOLD)}")
        print(f"    - Repo:      {c(agent['repo'], Colors.CYAN)}")
        print(f"    - Branch:    {c(agent['branch'], Colors.YELLOW)}")
        print(f"    - Workspace: {agent['worktree']}")
        if changes:
            print(f"    - Changes:   {c(f'{changes} files', Colors.GREEN)}")
        else:
            print(f"    - Changes:   {c('clean', Colors.DIM)}")
        print(f"    - Commits:   {commits_ahead} ahead")
        if agent["task"]:
            print(f"    - Task:      {agent['task'][:60]}")

    print(c("\n------------------------------------------------------------", Colors.DIM))
    print(f"  Total: {c(str(len(agents)), Colors.BOLD)} agent(s) running\n")


def cmd_attach(args) -> None:
    """Attach to an agent's tmux session."""
    session = resolve_session(args.session)
    if not session:
        return
    # This replaces the current process
    tmux.attach(session)


def cmd_logs(args) -> None:
    """Show recent output from an agent's tmux session."""
    session = resolve_session(args.session)
    if not session:
        return

    lines = args.lines or 50
    output = tmux.capture_pane(session, lines)
    print(output)


def cmd_diff(args) -> None:
    """Show diff for an agent's changes."""
    agents = get_active_agents()

    if args.session:
        session = resolve_session(args.session)
        if not session:
            return
        agent = next((a for a in agents if a["session"] == session), None)
        if agent:
            agents = [agent]

    for agent in agents:
        worktree = Path(agent["worktree"])
        print(c(f"\n=== {agent['repo']}:{agent['branch']} ===", Colors.BOLD))

        # Show unstaged changes
        result = git.diff(worktree, stat=True)
        if result.stdout.strip():
            print(c("\nUnstaged changes:", Colors.YELLOW))
            print(result.stdout)

        # Show staged changes
        result = git.diff(worktree, cached=True, stat=True)
        if result.stdout.strip():
            print(c("\nStaged changes:", Colors.GREEN))
            print(result.stdout)

        # Show untracked files
        untracked = git.ls_files_untracked(worktree)
        if untracked:
            print(c("\nUntracked files:", Colors.CYAN))
            for f in untracked:
                print(f"  + {f}")

        # Show recent commits
        result = git.log(worktree, oneline=True, count=5, range_spec=f"origin/{agent['branch']}..HEAD")
        if result.stdout.strip():
            print(c("\nNew commits:", Colors.GREEN))
            print(result.stdout)
