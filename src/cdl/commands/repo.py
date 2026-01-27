"""Repository management commands: add, list."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..core import git
from ..core.config import load_config, save_config
from ..core.paths import REPOS_DIR
from ..core.tmux import list_sessions
from ..utils.colors import Colors, c


def cmd_add(args) -> None:
    """Add/clone a repository."""
    repo_url = args.repo
    clean_url = repo_url.rstrip("/")
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]
    name = args.name or Path(clean_url).name
    repo_path = REPOS_DIR / name

    if repo_path.exists():
        print(c(f"Repository '{name}' already exists at {repo_path}", Colors.YELLOW))
        return

    print(c(f"Cloning {repo_url}...", Colors.CYAN))
    result = git.clone(repo_url, repo_path)

    if result.returncode != 0:
        print(c(f"Failed to clone: {result.stderr}", Colors.RED))
        return

    config = load_config()
    config["repos"][name] = {
        "path": str(repo_path),
        "url": repo_url,
        "added": datetime.now().isoformat(),
    }
    save_config(config)
    print(c(f"+ Added repository: {name}", Colors.GREEN))


def get_active_agents() -> list[dict]:
    """Get list of active conductor tmux sessions."""
    sessions = list_sessions()
    config = load_config()
    agents = []

    for session in sessions:
        if session.startswith("conductor-") and session in config.get("agents", {}):
            agent_info = config["agents"][session]
            agents.append({
                "session": session,
                "repo": agent_info["repo"],
                "branch": agent_info["branch"],
                "worktree": agent_info["worktree"],
                "task": agent_info.get("task", ""),
                "label": agent_info.get("label", ""),
                "started": agent_info.get("started", ""),
            })

    return agents


def cmd_list(args) -> None:
    """List repositories and agents."""
    config = load_config()
    agents = get_active_agents()

    # JSON output mode
    if hasattr(args, 'json') and args.json:
        output = {
            "repos": {
                name: {
                    "path": info["path"],
                    "url": info.get("url", ""),
                    "added": info.get("added", ""),
                }
                for name, info in config["repos"].items()
            },
            "agents": [
                {
                    "number": i,
                    "session": a["session"],
                    "repo": a["repo"],
                    "branch": a["branch"],
                    "task": a.get("task", ""),
                }
                for i, a in enumerate(agents, 1)
            ],
        }
        print(json.dumps(output, indent=2))
        return

    print(c("\n=== REPOSITORIES ===", Colors.BOLD))
    if not config["repos"]:
        print(c("  No repositories. Use 'cdl add <repo-url>'", Colors.DIM))
    for name, info in config["repos"].items():
        print(f"  {c(name, Colors.CYAN)}: {info['path']}")

    print(c("\n=== ACTIVE AGENTS ===", Colors.BOLD))
    if not agents:
        print(c("  No active agents. Use 'cdl spawn <repo> <branch>'", Colors.DIM))
    for i, agent in enumerate(agents, 1):
        status = c("*", Colors.GREEN)
        print(f"  {status} [{i}] {c(agent['repo'], Colors.CYAN)}:{c(agent['branch'], Colors.YELLOW)}")
        if agent.get("task"):
            task_preview = agent["task"][:50]
            print(f"       task: {task_preview}...")
    print()
