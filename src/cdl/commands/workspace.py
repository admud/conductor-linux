"""Workspace lifecycle commands: archive, restore, list, open."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess
from typing import Optional

from ..core import git, tmux
from ..core.config import load_config, save_config
from ..core.paths import WORKTREES_DIR
from ..utils.colors import Colors, c
from ..utils.fzf import pick_archive, pick_agent
from .agent import _ensure_context_dir, resolve_session
from .repo import get_active_agents


def _resolve_active_agent(session: Optional[str]) -> Optional[dict]:
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

    agent = pick_agent(agents, "Select agent to archive: ")
    if not agent:
        print(c("No agent selected.", Colors.YELLOW))
        return None
    return agent


def cmd_archive(args) -> None:
    """Archive an agent workspace."""
    agent = _resolve_active_agent(args.session)
    if not agent:
        return

    config = load_config()
    session = agent["session"]
    agent_info = config.get("agents", {}).get(session)
    if not agent_info:
        print(c("Agent not found in config.", Colors.RED))
        return

    # Kill tmux session
    tmux.kill_session(session)

    repo_path = Path(config["repos"][agent_info["repo"]]["path"])
    worktree_path = Path(agent_info["worktree"])
    notes_path = worktree_path / ".context" / "notes.md"
    notes_text = ""
    if notes_path.exists():
        try:
            notes_text = notes_path.read_text(encoding="utf-8")
        except OSError:
            notes_text = ""

    if not args.keep_worktree:
        print(c("Removing worktree...", Colors.CYAN))
        git.worktree_remove(repo_path, worktree_path, force=True)

    archived = {
        "repo": agent_info["repo"],
        "branch": agent_info["branch"],
        "worktree": str(worktree_path),
        "task": agent_info.get("task", ""),
        "agent_type": agent_info.get("agent_type", "claude"),
        "started": agent_info.get("started", ""),
        "notes": notes_text,
        "archived_at": datetime.now().isoformat(),
    }

    config.setdefault("archives", {})
    config["archives"][session] = archived
    del config["agents"][session]
    save_config(config)

    print(c(f"+ Archived {session}", Colors.GREEN))


def cmd_restore(args) -> None:
    """Restore an archived workspace."""
    config = load_config()
    archives = config.get("archives", {})
    if not archives:
        print(c("No archived workspaces.", Colors.YELLOW))
        return

    archive_key = args.name
    if not archive_key:
        archive_key = pick_archive(archives, "Select archive to restore: ")
        if not archive_key:
            print(c("No archive selected.", Colors.YELLOW))
            return

    entry = archives.get(archive_key)
    if not entry:
        print(c("Archive not found.", Colors.RED))
        return

    repo_name = entry["repo"]
    if repo_name not in config.get("repos", {}):
        print(c(f"Repository '{repo_name}' not found. Use 'cdl add' first.", Colors.RED))
        return

    repo_path = Path(config["repos"][repo_name]["path"])
    branch_name = entry["branch"]
    worktree_path = Path(entry["worktree"])

    if not worktree_path.exists() or args.recreate:
        # If worktree path is missing, recreate under WORKTREES_DIR
        if not worktree_path.parent.exists():
            worktree_path = WORKTREES_DIR / worktree_path.name
        print(c("Recreating worktree...", Colors.CYAN))
        result = git.worktree_add(repo_path, worktree_path, branch_name)
        if result.returncode != 0:
            result = git.worktree_add(repo_path, worktree_path, branch_name, force_branch=True)
            if result.returncode != 0:
                print(c(f"Failed to restore worktree: {result.stderr}", Colors.RED))
                return

    # Ensure .context exists
    _ensure_context_dir(worktree_path)
    notes_text = entry.get("notes", "")
    if notes_text:
        notes_path = worktree_path / ".context" / "notes.md"
        try:
            notes_path.write_text(notes_text, encoding="utf-8")
        except OSError:
            pass

    session_name = f"conductor-{worktree_path.name}"
    if tmux.session_exists(session_name):
        print(c(f"Session already exists: {session_name}", Colors.YELLOW))
    else:
        tmux.new_session(session_name, worktree_path)
    config["agents"][session_name] = {
        "repo": repo_name,
        "branch": branch_name,
        "worktree": str(worktree_path),
        "task": entry.get("task", ""),
        "agent_type": entry.get("agent_type", "claude"),
        "started": entry.get("started", ""),
    }

    del config["archives"][archive_key]
    save_config(config)

    print(c(f"+ Restored {session_name}", Colors.GREEN))
    print(f"  Workspace: {worktree_path}")


def cmd_archives(args) -> None:
    """List archived workspaces."""
    config = load_config()
    archives = config.get("archives", {})

    if getattr(args, "json", False):
        import json
        print(json.dumps(archives, indent=2))
        return

    if not archives:
        print(c("No archived workspaces.", Colors.DIM))
        return

    print(c("\n=== ARCHIVED WORKSPACES ===", Colors.BOLD))
    for i, (key, entry) in enumerate(archives.items(), 1):
        repo = entry.get("repo", "")
        branch = entry.get("branch", "")
        archived_at = entry.get("archived_at", "")
        print(f"  [{i}] {c(repo, Colors.CYAN)}:{c(branch, Colors.YELLOW)}  {archived_at}")


def cmd_open(args) -> None:
    """Open a worktree in an editor."""
    agent = _resolve_active_agent(args.session)
    if not agent:
        return

    editor = args.editor
    if not editor:
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "code"

    worktree_path = Path(agent["worktree"])
    try:
        subprocess.Popen([editor, str(worktree_path)])
        print(c(f"+ Opened {worktree_path} in {editor}", Colors.GREEN))
    except FileNotFoundError:
        print(c(f"Editor not found: {editor}", Colors.RED))
