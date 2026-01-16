"""CLI argument parsing and command routing."""

from __future__ import annotations

import argparse
import sys

from .utils.colors import Colors, c
from .utils.process import check_command_exists
from .core.config import init_config
from .commands import repo, agent, monitor, sync


def check_dependencies() -> list[str]:
    """Check if required dependencies are installed."""
    deps = ["git", "tmux", "claude"]
    return [dep for dep in deps if not check_command_exists(dep)]


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="cdl",
        description=c("CDL (Conductor Linux)", Colors.BOLD) + " - Manage multiple Claude Code agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{c('Examples:', Colors.BOLD)}
  cdl add https://github.com/user/repo.git
  cdl spawn myrepo feature-auth --task "Implement OAuth login"
  cdl spawn myrepo feature-tests --task "Add unit tests"
  cdl status
  cdl attach 1
  cdl diff
  cdl kill 1 --cleanup

{c('Workflow:', Colors.BOLD)}
  1. Add a repo:     cdl add <git-url>
  2. Spawn agents:   cdl spawn <repo> <branch> --task "..."
  3. Monitor:        cdl status
  4. Review:         cdl diff
  5. Merge:          cdl merge <agent>
  6. Cleanup:        cdl kill <agent> --cleanup
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add
    p = subparsers.add_parser("add", help="Add/clone a repository")
    p.add_argument("repo", help="Git repository URL")
    p.add_argument("--name", help="Custom name for the repo")

    # list
    subparsers.add_parser("list", help="List repos and agents")

    # spawn
    p = subparsers.add_parser("spawn", help="Spawn a new Claude Code agent")
    p.add_argument("repo", help="Repository name")
    p.add_argument("branch", help="Branch to work on")
    p.add_argument("--task", "-t", help="Task/prompt for the agent")
    p.add_argument(
        "--auto-accept",
        "-y",
        action="store_true",
        default=None,
        help="Enable auto-accept mode (skip permission prompts)",
    )
    p.add_argument(
        "--no-auto-accept",
        "-n",
        action="store_false",
        dest="auto_accept",
        help="Disable auto-accept mode (interactive)",
    )

    # status
    subparsers.add_parser("status", help="Show detailed agent status")

    # attach
    p = subparsers.add_parser("attach", help="Attach to an agent's terminal")
    p.add_argument("session", help="Agent number or session name")

    # diff
    p = subparsers.add_parser("diff", help="Show changes made by agents")
    p.add_argument("session", nargs="?", help="Agent number (optional, shows all if omitted)")

    # merge
    p = subparsers.add_parser("merge", help="Push agent's branch to origin")
    p.add_argument("session", help="Agent number or session name")
    p.add_argument("--force", "-f", action="store_true", help="Merge even with uncommitted changes")

    # logs
    p = subparsers.add_parser("logs", help="Show agent's terminal output")
    p.add_argument("session", help="Agent number or session name")
    p.add_argument("--lines", "-n", type=int, default=50, help="Number of lines")

    # kill
    p = subparsers.add_parser("kill", help="Kill an agent")
    p.add_argument("session", help="Agent number or session name")
    p.add_argument("--cleanup", "-c", action="store_true", help="Also remove worktree")

    # killall
    p = subparsers.add_parser("killall", help="Kill all agents")
    p.add_argument("--cleanup", "-c", action="store_true", help="Also remove all worktrees")

    return parser


def main() -> int:
    """Main CLI entry point."""
    init_config()

    parser = create_parser()
    args = parser.parse_args()

    # Check dependencies on first meaningful command
    if args.command in ["spawn", "add"]:
        missing = check_dependencies()
        if missing:
            print(c(f"Missing dependencies: {', '.join(missing)}", Colors.RED))
            print("Please install them first.")
            return 1

    if args.command is None:
        parser.print_help()
        return 0

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
    }

    if args.command in commands:
        commands[args.command](args)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
