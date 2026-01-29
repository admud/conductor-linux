"""CLI argument parsing and command routing."""

from __future__ import annotations

import argparse
import sys

from .utils.colors import Colors, c
from .utils.process import check_command_exists
from .core.config import init_config
from .core.user_config import load_user_config
from .commands import repo, agent, monitor, sync, pr, workspace


def check_dependencies(agent_type: str = "claude") -> list[str]:
    """Check if required dependencies are installed."""
    deps = ["git", "tmux", agent_type]
    return [dep for dep in deps if not check_command_exists(dep)]


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    """Add --json flag to a parser."""
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format (for scripting)",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="cdl",
        description=c("CDL (Conductor Linux)", Colors.BOLD) + " - Manage multiple AI coding agents (Claude Code & Codex)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{c('Examples:', Colors.BOLD)}
  cdl add https://github.com/user/repo.git
  cdl spawn myrepo feature-auth --task "Implement OAuth login"
  cdl status --json | jq '.agents[]'
  cdl attach    # (fzf picker if no arg)
  cdl logs -f 1 # (live tail)
  cdl k 1 -c    # (short alias for kill --cleanup)

{c('Aliases:', Colors.BOLD)}
  s = status, a = attach, l = logs, k = kill, d = diff

{c('Config:', Colors.BOLD)}
  ~/.conductor/config.toml
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add
    p = subparsers.add_parser("add", help="Add/clone a repository")
    p.add_argument("repo", help="Git repository URL")
    p.add_argument("--name", help="Custom name for the repo")

    # list
    p = subparsers.add_parser("list", help="List repos and agents")
    add_json_flag(p)

    # spawn
    p = subparsers.add_parser("spawn", help="Spawn a new AI coding agent")
    p.add_argument("repo", nargs="?", help="Repository name (fzf picker if omitted)")
    p.add_argument("branch", nargs="?", help="Branch to work on")
    p.add_argument("--task", "-t", help="Task/prompt for the agent")
    p.add_argument("--from-pr", help="Create workspace from a GitHub PR (number or URL)")
    p.add_argument("--from-branch", help="Create workspace from a branch name")
    p.add_argument("--link-node-modules", action="store_true", help="Symlink node_modules from base repo")
    p.add_argument("--link-venv", action="store_true", help="Symlink .venv from base repo")
    p.add_argument("--copy-env", action="store_true", help="Copy .env from base repo if present")
    p.add_argument("--run-setup", action="store_true", help="Run setup scripts from .cdl.json")
    p.add_argument(
        "--agent", "-a",
        choices=["claude", "codex"],
        default="claude",
        help="Agent type: claude (default) or codex",
    )
    p.add_argument(
        "--auto-accept", "-y",
        action="store_true",
        default=None,
        help="Enable auto-accept mode (skip permission prompts)",
    )
    p.add_argument(
        "--no-auto-accept", "-n",
        action="store_false",
        dest="auto_accept",
        help="Disable auto-accept mode (interactive)",
    )
    p.add_argument("--label", "-l", help="Label for grouping agents")

    # status (alias: s)
    p = subparsers.add_parser("status", aliases=["s"], help="Show detailed agent status")
    add_json_flag(p)
    p.add_argument("--label", "-l", help="Filter by label")

    # attach (alias: a)
    p = subparsers.add_parser("attach", aliases=["a"], help="Attach to an agent's terminal")
    p.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")

    # diff (alias: d)
    p = subparsers.add_parser("diff", aliases=["d"], help="Show changes made by agents")
    p.add_argument("session", nargs="?", help="Agent number (optional, shows all if omitted)")
    p.add_argument("--tool", help="Diff tool (delta, difftastic, etc.)")

    # merge
    p = subparsers.add_parser("merge", help="Push agent's branch to origin")
    p.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    p.add_argument("--force", "-f", action="store_true", help="Merge even with uncommitted changes")

    # logs (alias: l)
    p = subparsers.add_parser("logs", aliases=["l"], help="Show agent's terminal output")
    p.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    p.add_argument("--lines", "-n", type=int, default=50, help="Number of lines")
    p.add_argument("--follow", "-f", action="store_true", help="Follow output (like tail -f)")

    # kill (alias: k)
    p = subparsers.add_parser("kill", aliases=["k"], help="Kill an agent")
    p.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    p.add_argument("--cleanup", "-c", action="store_true", help="Also remove worktree")

    # killall
    p = subparsers.add_parser("killall", help="Kill all agents")
    p.add_argument("--cleanup", "-c", action="store_true", help="Also remove all worktrees")
    p.add_argument("--label", "-l", help="Only kill agents with this label")

    # pick - fzf picker helper
    p = subparsers.add_parser("pick", help="Interactive agent picker (for scripting)")
    p.add_argument("--format", "-f", default="number", choices=["number", "session", "json"],
                   help="Output format")

    # completions
    p = subparsers.add_parser("completions", help="Generate shell completions")
    p.add_argument("shell", choices=["bash", "zsh", "fish"], help="Shell type")

    # archives
    p = subparsers.add_parser("archives", help="List archived workspaces")
    add_json_flag(p)

    # archive
    p = subparsers.add_parser("archive", help="Archive an agent workspace")
    p.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    p.add_argument("--keep-worktree", action="store_true", help="Keep worktree on disk")

    # restore
    p = subparsers.add_parser("restore", help="Restore an archived workspace")
    p.add_argument("name", nargs="?", help="Archive name (fzf picker if omitted)")
    p.add_argument("--recreate", action="store_true", help="Recreate worktree even if present")

    # open
    p = subparsers.add_parser("open", help="Open a worktree in an editor")
    p.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    p.add_argument("--editor", "-e", help="Editor command (code, nvim, idea, etc.)")

    # add-dir
    p = subparsers.add_parser("add-dir", help="Attach an extra repo/dir into a worktree")
    p.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    p.add_argument("path", help="Path to repo/dir to attach")
    p.add_argument("--name", help="Name for the attached dir (defaults to folder name)")

    # pr
    p = subparsers.add_parser("pr", help="GitHub pull request workflow")
    pr_sub = p.add_subparsers(dest="pr_command", help="PR commands")

    pr_create = pr_sub.add_parser("create", help="Create a PR for an agent branch")
    pr_create.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    pr_create.add_argument("--base", help="Base branch (default: repo default)")
    pr_create.add_argument("--title", help="PR title")
    pr_create.add_argument("--body", help="PR body")
    pr_create.add_argument("--fill", action="store_true", help="Auto-fill title/body from commits")
    pr_create.add_argument("--draft", action="store_true", help="Create as draft PR")
    pr_create.add_argument("--web", action="store_true", help="Open PR in browser")

    pr_view = pr_sub.add_parser("view", help="View a PR for an agent branch")
    pr_view.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    pr_view.add_argument("--web", action="store_true", help="Open PR in browser")

    pr_merge = pr_sub.add_parser("merge", help="Merge a PR for an agent branch")
    pr_merge.add_argument("session", nargs="?", help="Agent number (fzf picker if omitted)")
    pr_merge.add_argument("--merge", action="store_true", help="Use a merge commit")
    pr_merge.add_argument("--squash", action="store_true", help="Squash and merge")
    pr_merge.add_argument("--rebase", action="store_true", help="Rebase and merge")
    pr_merge.add_argument("--delete-branch", action="store_true", help="Delete branch after merge")
    pr_merge.add_argument("--auto", action="store_true", help="Enable auto-merge when checks pass")

    return parser


def main() -> int:
    """Main CLI entry point."""
    init_config()
    user_config = load_user_config()

    parser = create_parser()
    args = parser.parse_args()

    # Apply user config defaults
    if hasattr(args, 'auto_accept') and args.auto_accept is None:
        args.auto_accept = user_config.get("defaults", {}).get("auto_accept", None)

    # Check dependencies on first meaningful command
    if args.command in ["spawn", "add"]:
        agent_type = getattr(args, 'agent', 'claude')
        missing = check_dependencies(agent_type)
        if missing:
            print(c(f"Missing dependencies: {', '.join(missing)}", Colors.RED))
            print("Please install them first.")
            return 1

    if args.command is None:
        parser.print_help()
        return 0

    # Map aliases to canonical commands
    command = args.command
    alias_map = {"s": "status", "a": "attach", "l": "logs", "k": "kill", "d": "diff"}
    command = alias_map.get(command, command)

    commands = {
        "add": repo.cmd_add,
        "list": repo.cmd_list,
        "spawn": agent.cmd_spawn,
        "status": monitor.cmd_status,
        "attach": monitor.cmd_attach,
        "diff": monitor.cmd_diff,
        "merge": sync.cmd_merge,
        "logs": monitor.cmd_logs,
        "kill": agent.cmd_kill,
        "killall": agent.cmd_killall,
        "pick": monitor.cmd_pick,
        "completions": cmd_completions,
        "pr": cmd_pr,
        "archives": workspace.cmd_archives,
        "archive": workspace.cmd_archive,
        "restore": workspace.cmd_restore,
        "open": workspace.cmd_open,
        "add-dir": workspace.cmd_add_dir,
    }

    if command in commands:
        result = commands[command](args)
        return result if isinstance(result, int) else 0

    parser.print_help()
    return 1


def cmd_completions(args) -> int:
    """Generate shell completions."""
    from .utils.completions import generate_completions
    print(generate_completions(args.shell))
    return 0


def cmd_pr(args) -> int:
    """Dispatch PR subcommands."""
    if args.pr_command == "create":
        pr.cmd_pr_create(args)
        return 0
    if args.pr_command == "view":
        pr.cmd_pr_view(args)
        return 0
    if args.pr_command == "merge":
        pr.cmd_pr_merge(args)
        return 0
    print("Usage: cdl pr <create|view> [options]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
