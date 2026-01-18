"""Monitoring commands: status, attach, logs, diff, pick."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

from ..core import git, tmux
from ..utils.colors import Colors, c
from ..utils.fzf import pick_agent, has_fzf
from .repo import get_active_agents
from .agent import resolve_session


def cmd_status(args) -> None:
    """Show detailed status of all agents."""
    agents = get_active_agents()

    # Filter by label if specified
    if hasattr(args, 'label') and args.label:
        agents = [a for a in agents if a.get('label') == args.label]

    # JSON output mode
    if hasattr(args, 'json') and args.json:
        output = {
            "agents": {
                str(i): {
                    "session": a["session"],
                    "repo": a["repo"],
                    "branch": a["branch"],
                    "worktree": a["worktree"],
                    "task": a.get("task", ""),
                    "label": a.get("label", ""),
                    "started": a.get("started", ""),
                }
                for i, a in enumerate(agents, 1)
            },
            "count": len(agents),
        }
        print(json.dumps(output, indent=2))
        return

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
        if agent.get("label"):
            print(f"    - Label:     {c(agent['label'], Colors.BLUE)}")
        if agent["task"]:
            print(f"    - Task:      {agent['task'][:60]}")

    print(c("\n------------------------------------------------------------", Colors.DIM))
    print(f"  Total: {c(str(len(agents)), Colors.BOLD)} agent(s) running\n")


def cmd_attach(args) -> None:
    """Attach to an agent's tmux session."""
    session = args.session if hasattr(args, 'session') else None

    # If no session specified, use fzf picker
    if not session:
        agents = get_active_agents()
        if not agents:
            print(c("No active agents.", Colors.YELLOW))
            return
        agent = pick_agent(agents, "Attach to: ")
        if not agent:
            return
        session = agent["session"]
    else:
        session = resolve_session(session)
        if not session:
            return

    # This replaces the current process
    tmux.attach(session)


def cmd_logs(args) -> None:
    """Show recent output from an agent's tmux session."""
    session = args.session if hasattr(args, 'session') else None

    # If no session specified, use fzf picker
    if not session:
        agents = get_active_agents()
        if not agents:
            print(c("No active agents.", Colors.YELLOW))
            return
        agent = pick_agent(agents, "Show logs for: ")
        if not agent:
            return
        session = agent["session"]
    else:
        session = resolve_session(session)
        if not session:
            return

    lines = args.lines if hasattr(args, 'lines') else 50
    follow = args.follow if hasattr(args, 'follow') else False

    if follow:
        # Live tail mode
        print(c(f"Following logs for {session} (Ctrl+C to stop)...\n", Colors.DIM))
        last_output = ""
        try:
            while True:
                output = tmux.capture_pane(session, lines)
                if output != last_output:
                    # Clear screen and reprint
                    print("\033[2J\033[H", end="")  # Clear screen, move to top
                    print(c(f"=== {session} (live) ===\n", Colors.BOLD))
                    print(output)
                    last_output = output
                time.sleep(0.5)
        except KeyboardInterrupt:
            print(c("\nStopped following.", Colors.DIM))
    else:
        output = tmux.capture_pane(session, lines)
        print(output)


def cmd_diff(args) -> None:
    """Show diff for an agent's changes."""
    agents = get_active_agents()
    diff_tool = args.tool if hasattr(args, 'tool') else None

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

        # If using external diff tool, pipe to it
        if diff_tool:
            import subprocess
            result = git.diff(worktree)
            if result.stdout.strip():
                try:
                    subprocess.run([diff_tool], input=result.stdout, text=True)
                except FileNotFoundError:
                    print(c(f"Diff tool '{diff_tool}' not found", Colors.RED))
                    print(result.stdout)
            continue

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


def cmd_pick(args) -> None:
    """Interactive agent picker for scripting."""
    agents = get_active_agents()

    if not agents:
        print(c("No active agents.", Colors.YELLOW), file=sys.stderr)
        sys.exit(1)

    agent = pick_agent(agents, "Select agent: ")

    if not agent:
        sys.exit(1)

    fmt = args.format if hasattr(args, 'format') else "number"

    if fmt == "json":
        print(json.dumps(agent, indent=2))
    elif fmt == "session":
        print(agent["session"])
    else:  # number
        idx = next(i for i, a in enumerate(agents, 1) if a["session"] == agent["session"])
        print(idx)
