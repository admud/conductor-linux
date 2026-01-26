"""GitHub PR workflow commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..core import git
from ..utils.colors import Colors, c
from ..utils.fzf import pick_agent
from ..utils.process import check_command_exists
from .agent import resolve_session
from .repo import get_active_agents


def _resolve_agent_session(session: Optional[str]) -> Optional[dict]:
    """Resolve an agent session via identifier or picker."""
    agents = get_active_agents()
    if not agents:
        print(c("No active agents.", Colors.YELLOW))
        return None

    if session:
        resolved = resolve_session(session)
        if not resolved:
            return None
        agent = next((a for a in agents if a["session"] == resolved), None)
        if not agent:
            print(c("Agent not found.", Colors.RED))
        return agent

    agent = pick_agent(agents, "Select agent for PR: ")
    if not agent:
        print(c("No agent selected.", Colors.YELLOW))
        return None
    return agent


def _check_gh_auth() -> bool:
    """Return True if gh is installed and authenticated."""
    if not check_command_exists("gh"):
        print(c("Missing dependency: gh (GitHub CLI).", Colors.RED))
        print("Install it from: https://cli.github.com/")
        return False
    result = git.run_raw(["gh", "auth", "status"], cwd=None)
    if result.returncode != 0:
        print(c("GitHub CLI is not authenticated.", Colors.RED))
        print("Run: gh auth login")
        return False
    return True


def _warn_if_dirty(worktree: Path) -> None:
    status = git.status(worktree)
    if status.stdout.strip():
        print(c("Warning: worktree has uncommitted changes.", Colors.YELLOW))


def cmd_pr_create(args) -> None:
    """Create a GitHub PR from an agent branch."""
    if not _check_gh_auth():
        return

    agent = _resolve_agent_session(args.session)
    if not agent:
        return

    worktree = Path(agent["worktree"])
    branch = agent["branch"]

    _warn_if_dirty(worktree)

    cmd = ["gh", "pr", "create", "--head", branch]
    if args.base:
        cmd.extend(["--base", args.base])
    if args.title:
        cmd.extend(["--title", args.title])
    if args.body:
        cmd.extend(["--body", args.body])
    if args.fill:
        cmd.append("--fill")
    if args.draft:
        cmd.append("--draft")
    if args.web:
        cmd.append("--web")

    print(c(f"Creating PR for {agent['repo']}:{branch}...", Colors.CYAN))
    result = git.run_raw(cmd, cwd=worktree)
    if result.returncode == 0:
        if result.stdout.strip():
            print(result.stdout.strip())
    else:
        err = result.stderr.strip() or "PR creation failed."
        print(c(err, Colors.RED))


def cmd_pr_view(args) -> None:
    """View a GitHub PR for an agent branch."""
    if not _check_gh_auth():
        return

    agent = _resolve_agent_session(args.session)
    if not agent:
        return

    worktree = Path(agent["worktree"])
    branch = agent["branch"]

    cmd = ["gh", "pr", "view", "--head", branch]
    if args.web:
        cmd.append("--web")

    print(c(f"Opening PR for {agent['repo']}:{branch}...", Colors.CYAN))
    result = git.run_raw(cmd, cwd=worktree)
    if result.returncode == 0:
        if result.stdout.strip():
            print(result.stdout.strip())
    else:
        err = result.stderr.strip() or "PR view failed."
        print(c(err, Colors.RED))


def cmd_pr_merge(args) -> None:
    """Merge a GitHub PR for an agent branch."""
    if not _check_gh_auth():
        return

    agent = _resolve_agent_session(args.session)
    if not agent:
        return

    worktree = Path(agent["worktree"])
    branch = agent["branch"]

    cmd = ["gh", "pr", "merge", "--head", branch]
    if args.merge:
        cmd.append("--merge")
    if args.squash:
        cmd.append("--squash")
    if args.rebase:
        cmd.append("--rebase")
    if args.delete_branch:
        cmd.append("--delete-branch")
    if args.auto:
        cmd.append("--auto")

    print(c(f"Merging PR for {agent['repo']}:{branch}...", Colors.CYAN))
    result = git.run_raw(cmd, cwd=worktree)
    if result.returncode == 0:
        if result.stdout.strip():
            print(result.stdout.strip())
    else:
        err = result.stderr.strip() or "PR merge failed."
        print(c(err, Colors.RED))
