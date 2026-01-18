"""fzf integration for interactive selection."""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

from .process import check_command_exists


def has_fzf() -> bool:
    """Check if fzf is available."""
    return check_command_exists("fzf")


def pick_agent(agents: list[dict], prompt: str = "Select agent: ") -> Optional[dict]:
    """
    Use fzf to pick an agent from a list.

    Returns the selected agent dict, or None if cancelled.
    """
    if not agents:
        return None

    if not has_fzf():
        # Fall back to simple numbered selection
        return pick_agent_simple(agents, prompt)

    # Build fzf input: "number: repo/branch - task"
    lines = []
    for i, agent in enumerate(agents, 1):
        task = agent.get("task", "")[:40]
        task_str = f" - {task}" if task else ""
        lines.append(f"{i}: {agent['repo']}/{agent['branch']}{task_str}")

    try:
        result = subprocess.run(
            ["fzf", "--prompt", prompt, "--height", "40%", "--reverse"],
            input="\n".join(lines),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        # Parse selection
        selected = result.stdout.strip()
        if not selected:
            return None

        # Extract number from "N: ..."
        num = int(selected.split(":")[0])
        return agents[num - 1]

    except (subprocess.SubprocessError, ValueError, IndexError):
        return None


def pick_agent_simple(agents: list[dict], prompt: str = "Select agent: ") -> Optional[dict]:
    """Simple numbered selection without fzf."""
    print(prompt)
    for i, agent in enumerate(agents, 1):
        task = agent.get("task", "")[:40]
        task_str = f" - {task}" if task else ""
        print(f"  {i}: {agent['repo']}/{agent['branch']}{task_str}")

    try:
        choice = input("\nEnter number (or 'q' to cancel): ").strip()
        if choice.lower() == 'q':
            return None
        num = int(choice)
        if 1 <= num <= len(agents):
            return agents[num - 1]
    except (ValueError, EOFError, KeyboardInterrupt):
        pass

    return None


def pick_repo(repos: dict, prompt: str = "Select repository: ") -> Optional[str]:
    """
    Use fzf to pick a repository from the config.

    Returns the repo name, or None if cancelled.
    """
    if not repos:
        return None

    repo_names = list(repos.keys())

    if not has_fzf():
        # Fall back to simple selection
        print(prompt)
        for i, name in enumerate(repo_names, 1):
            print(f"  {i}: {name}")
        try:
            choice = input("\nEnter number (or 'q' to cancel): ").strip()
            if choice.lower() == 'q':
                return None
            num = int(choice)
            if 1 <= num <= len(repo_names):
                return repo_names[num - 1]
        except (ValueError, EOFError, KeyboardInterrupt):
            pass
        return None

    try:
        result = subprocess.run(
            ["fzf", "--prompt", prompt, "--height", "40%", "--reverse"],
            input="\n".join(repo_names),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip() or None

    except subprocess.SubprocessError:
        return None
