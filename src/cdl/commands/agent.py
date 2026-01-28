"""Agent management commands: spawn, kill, killall."""

from __future__ import annotations

from datetime import datetime
import os
import json
from pathlib import Path
from typing import Optional

from ..core import git, tmux
from ..core.config import load_config, save_config
from ..core.paths import WORKTREES_DIR
from ..utils.colors import Colors, c
from ..utils.fzf import pick_repo
from ..utils.process import check_command_exists
from .repo import get_active_agents


def _ensure_context_dir(worktree_path: Path) -> None:
    """Create .context and add it to the worktree git exclude."""
    context_dir = worktree_path / ".context"
    context_dir.mkdir(parents=True, exist_ok=True)

    git_dir = git.get_common_git_dir(worktree_path)
    if not git_dir:
        return

    exclude_path = git_dir / "info" / "exclude"
    try:
        if exclude_path.exists():
            contents = exclude_path.read_text()
        else:
            contents = ""
        if ".context/" not in contents:
            with open(exclude_path, "a", encoding="utf-8") as f:
                if contents and not contents.endswith("\n"):
                    f.write("\n")
                f.write(".context/\n")
    except OSError:
        return


def _safe_symlink(src: Path, dest: Path) -> None:
    """Create a symlink if possible, without overwriting existing files."""
    try:
        if dest.exists() or dest.is_symlink():
            try:
                if dest.is_symlink() and dest.resolve() == src.resolve():
                    return
            except OSError:
                return
            return
        dest.symlink_to(src)
    except OSError:
        return


def _copy_file(src: Path, dest: Path) -> None:
    """Copy a file if destination doesn't exist."""
    try:
        if dest.exists():
            return
        dest.write_bytes(src.read_bytes())
    except OSError:
        return


def _link_shared_paths(
    base_path: Path,
    worktree_path: Path,
    link_node_modules: bool,
    link_venv: bool,
    copy_env: bool,
) -> None:
    """Optionally link shared dependency folders or copy .env."""
    if link_node_modules:
        src = base_path / "node_modules"
        dest = worktree_path / "node_modules"
        if src.exists() and src.is_dir():
            _safe_symlink(src, dest)

    if link_venv:
        src = base_path / ".venv"
        dest = worktree_path / ".venv"
        if src.exists() and src.is_dir():
            _safe_symlink(src, dest)

    if copy_env:
        src = base_path / ".env"
        dest = worktree_path / ".env"
        if src.exists() and src.is_file():
            _copy_file(src, dest)


def _find_repo_by_full_name(config: dict, full_name: str) -> Optional[str]:
    """Find a registered repo by GitHub full name (owner/name)."""
    full_name = full_name.lower().strip()
    for name, info in config.get("repos", {}).items():
        url = info.get("url", "").lower()
        if full_name in url:
            return name
    return None


def _resolve_from_pr(pr_ref: str, config: dict) -> tuple[Optional[str], Optional[str]]:
    """Resolve repo and branch from a GitHub PR reference using gh."""
    if not check_command_exists("gh"):
        print(c("Missing dependency: gh (GitHub CLI).", Colors.RED))
        print("Install it from: https://cli.github.com/")
        return None, None

    auth = git.run_raw(["gh", "auth", "status"], cwd=None)
    if auth.returncode != 0:
        print(c("GitHub CLI is not authenticated.", Colors.RED))
        print("Run: gh auth login")
        return None, None

    result = git.run_raw(
        ["gh", "pr", "view", pr_ref, "--json", "headRefName,headRepositoryOwner,headRepository"],
        cwd=None,
    )
    if result.returncode != 0:
        print(c("Failed to resolve PR via gh.", Colors.RED))
        if result.stderr.strip():
            print(result.stderr.strip())
        return None, None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(c("Unexpected gh output while resolving PR.", Colors.RED))
        return None, None

    branch = data.get("headRefName")
    owner = data.get("headRepositoryOwner", {}).get("login") if isinstance(
        data.get("headRepositoryOwner"), dict
    ) else None
    repo = data.get("headRepository", {}).get("name") if isinstance(
        data.get("headRepository"), dict
    ) else None

    if not branch or not owner or not repo:
        print(c("Could not determine PR branch/repo from gh output.", Colors.RED))
        return None, None

    full_name = f"{owner}/{repo}"
    repo_name = _find_repo_by_full_name(config, full_name)
    if not repo_name:
        print(c(f"PR repo {full_name} not registered. Select a repo.", Colors.YELLOW))
        repo_name = pick_repo(config.get("repos", {}), "Select repository: ")
        if not repo_name:
            return None, None

    return repo_name, branch


def _build_claude_command(task: str, auto_accept: bool) -> list[str]:
    """Build the Claude Code CLI command."""
    if task:
        runner = "claude --dangerously-skip-permissions" if auto_accept else "claude -p"
        return [
            "bash", "-lc",
            f'{runner} "$1"; '
            'echo "\\n[Agent finished. Press Enter for shell or Ctrl+D to exit]"; '
            "read; exec bash",
            "--",
            task,
        ]
    return ["claude"]


def _build_codex_command(task: str, auto_accept: bool) -> list[str]:
    """Build the Codex CLI command."""
    if task:
        # Codex uses --full-auto for autonomous mode, or -a for approval policy
        # --full-auto = -a on-request --sandbox workspace-write
        runner = "codex --full-auto" if auto_accept else "codex"
        return [
            "bash", "-lc",
            f'{runner} "$1"; '
            'echo "\\n[Agent finished. Press Enter for shell or Ctrl+D to exit]"; '
            "read; exec bash",
            "--",
            task,
        ]
    return ["codex"]


def cmd_spawn(args) -> None:
    """Spawn a new AI coding agent on a worktree."""
    repo_name = args.repo
    branch_name = args.branch
    task = args.task or ""
    auto_accept = args.auto_accept
    agent_type = getattr(args, 'agent', 'claude')
    link_node_modules = getattr(args, "link_node_modules", False)
    link_venv = getattr(args, "link_venv", False)
    copy_env = getattr(args, "copy_env", False)

    config = load_config()

    if getattr(args, "from_pr", None) and getattr(args, "from_branch", None):
        print(c("Use only one of --from-pr or --from-branch.", Colors.RED))
        return

    if getattr(args, "from_pr", None):
        repo_name, branch_name = _resolve_from_pr(args.from_pr, config)
        if not repo_name or not branch_name:
            return

    if getattr(args, "from_branch", None):
        if not repo_name:
            repo_name = pick_repo(config.get("repos", {}), "Select repository: ")
            if not repo_name:
                print(c("No repository selected.", Colors.YELLOW))
                return
        branch_name = args.from_branch

    if not repo_name:
        repo_name = pick_repo(config.get("repos", {}), "Select repository: ")
        if not repo_name:
            print(c("No repository selected.", Colors.YELLOW))
            return

    if repo_name not in config["repos"]:
        print(c(f"Repository '{repo_name}' not found. Use 'cdl add' first.", Colors.RED))
        return

    repo_path = Path(config["repos"][repo_name]["path"])
    repo_url = config["repos"][repo_name].get("url", "")
    base_path = repo_path
    if repo_url and os.path.exists(repo_url):
        base_path = Path(repo_url)
    if not branch_name:
        default_branch = git.get_current_branch(repo_path) or "main"
        prompt = c(f"Branch name [{default_branch}]: ", Colors.BOLD)
        response = input(prompt).strip()
        branch_name = response or default_branch

    timestamp = datetime.now().strftime("%H%M%S")
    worktree_name = f"{repo_name}-{branch_name}-{timestamp}"
    worktree_path = WORKTREES_DIR / worktree_name

    # Check if branch exists
    if not git.branch_exists(repo_path, branch_name):
        print(c(f"Creating new branch: {branch_name}", Colors.YELLOW))
        base_branch = git.get_current_branch(repo_path)
        git.create_branch(repo_path, branch_name, base_branch)

    # Create worktree
    print(c("Creating isolated workspace...", Colors.CYAN))
    result = git.worktree_add(repo_path, worktree_path, branch_name)

    if result.returncode != 0:
        # Try with -B to force create/reset branch
        result = git.worktree_add(repo_path, worktree_path, branch_name, force_branch=True)
        if result.returncode != 0:
            print(c(f"Failed to create worktree: {result.stderr}", Colors.RED))
            return

    # Create tmux session for the agent
    session_name = f"conductor-{worktree_name}"

    # Ask about auto-accept mode if task provided and not already set via flag
    if task and auto_accept is None:
        agent_name = "Claude" if agent_type == "claude" else "Codex"
        print(c(f"\nAuto-accept mode allows {agent_name} to run without permission prompts.", Colors.YELLOW))
        print(c("WARNING: This gives the agent full control to modify files and run commands.", Colors.RED))
        response = input(c("Enable auto-accept mode? [y/N]: ", Colors.BOLD)).strip().lower()
        auto_accept = response in ("y", "yes")

    # Build agent command - wrap in bash to keep session alive
    if agent_type == "codex":
        agent_cmd = _build_codex_command(task, auto_accept)
    else:
        agent_cmd = _build_claude_command(task, auto_accept)

    agent_label = "Codex" if agent_type == "codex" else "Claude Code"
    print(c(f"Spawning {agent_label} agent...", Colors.CYAN))
    tmux.new_session(session_name, worktree_path, agent_cmd)

    # Create shared context directory (gitignored)
    _ensure_context_dir(worktree_path)

    # Optional shared deps
    _link_shared_paths(
        base_path=base_path,
        worktree_path=worktree_path,
        link_node_modules=link_node_modules,
        link_venv=link_venv,
        copy_env=copy_env,
    )

    # Track the agent
    config["agents"][session_name] = {
        "repo": repo_name,
        "branch": branch_name,
        "worktree": str(worktree_path),
        "task": task,
        "agent_type": agent_type,
        "started": datetime.now().isoformat(),
    }
    save_config(config)

    agent_count = len(get_active_agents())
    print(c("\n+ Agent spawned!", Colors.GREEN))
    print(f"  Session:   {c(session_name, Colors.CYAN)}")
    print(f"  Workspace: {worktree_path}")
    print(f"\n  {c('cdl attach', Colors.YELLOW)} {agent_count}  - View agent")
    print(f"  {c('cdl status', Colors.YELLOW)}      - See all agents")
    print(f"  {c('cdl diff', Colors.YELLOW)} {agent_count}    - View changes\n")


def resolve_session(identifier: str) -> Optional[str]:
    """Resolve a session identifier (number or name) to session name."""
    if identifier.isdigit():
        agents = get_active_agents()
        idx = int(identifier) - 1
        if 0 <= idx < len(agents):
            return agents[idx]["session"]
        print(c(f"Invalid agent number: {identifier}", Colors.RED))
        return None

    if not identifier.startswith("conductor-"):
        identifier = f"conductor-{identifier}"
    return identifier


def cmd_kill(args) -> None:
    """Kill an agent and optionally clean up its worktree."""
    session = resolve_session(args.session)
    if not session:
        return

    config = load_config()

    # Kill tmux session
    tmux.kill_session(session)
    print(c(f"+ Killed session: {session}", Colors.GREEN))

    # Clean up worktree if requested
    if session in config.get("agents", {}):
        agent_info = config["agents"][session]
        worktree_path = Path(agent_info["worktree"])
        repo_path = Path(config["repos"][agent_info["repo"]]["path"])

        if args.cleanup:
            print(c("Removing worktree...", Colors.CYAN))
            git.worktree_remove(repo_path, worktree_path, force=True)
            print(c(f"+ Removed: {worktree_path}", Colors.GREEN))

        del config["agents"][session]
        save_config(config)


def cmd_killall(args) -> None:
    """Kill all agents."""
    agents = get_active_agents()
    config = load_config()

    for agent in agents:
        print(f"Killing {agent['session']}...")
        tmux.kill_session(agent["session"])

        if args.cleanup and agent["session"] in config.get("agents", {}):
            agent_info = config["agents"][agent["session"]]
            repo_path = Path(config["repos"][agent_info["repo"]]["path"])
            worktree_path = Path(agent_info["worktree"])
            git.worktree_remove(repo_path, worktree_path, force=True)

    config["agents"] = {}
    save_config(config)
    print(c(f"+ Killed {len(agents)} agent(s)", Colors.GREEN))
