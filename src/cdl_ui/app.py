#!/usr/bin/env python3
"""
CDL (Conductor Linux) - TUI Dashboard
A visual interface to monitor and manage Claude Code agents.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, RichLog
from textual.reactive import reactive

# Add src to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cdl.core.config import load_config, save_config
from cdl.core import git, tmux


def get_active_agents() -> list[dict]:
    """Get list of active conductor tmux sessions with status."""
    sessions = tmux.list_sessions()
    config = load_config()
    agents = []

    for session in sessions:
        if session.startswith("conductor-") and session in config.get("agents", {}):
            agent_info = config["agents"][session]
            worktree = Path(agent_info["worktree"])

            # Get change count
            git_result = git.status(worktree)
            changes = len([line for line in git_result.stdout.strip().split("\n") if line])

            agents.append({
                "session": session,
                "repo": agent_info["repo"],
                "branch": agent_info["branch"],
                "worktree": agent_info["worktree"],
                "task": agent_info.get("task", ""),
                "changes": changes,
            })
    return agents


class AgentItem(ListItem):
    """List item representing an agent."""

    def __init__(self, agent: dict, index: int):
        super().__init__()
        self.agent = agent
        self.index = index

    def compose(self) -> ComposeResult:
        changes = f"[yellow]+{self.agent['changes']}[/]" if self.agent["changes"] else "[dim]ok[/]"
        yield Label(
            f"[green]\u25cf[/] [{self.index}] [cyan]{self.agent['repo']}[/]:[yellow]{self.agent['branch']}[/] {changes}"
        )


class ConductorUI(App):
    """TUI Dashboard for Conductor Linux."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 40;
        height: 100%;
        border: solid green;
        padding: 0 1;
    }

    #sidebar-title {
        text-align: center;
        text-style: bold;
        padding: 1 0;
        color: cyan;
    }

    #main {
        width: 1fr;
        height: 100%;
        border: solid cyan;
    }

    #main-header {
        height: 3;
        padding: 1;
        background: $surface;
    }

    #log-view {
        height: 1fr;
        padding: 0 1;
    }

    ListView {
        height: 1fr;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem:hover {
        background: $surface-lighten-1;
    }

    ListView > ListItem.--highlight {
        background: $primary 30%;
    }

    Footer {
        background: $surface;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("a", "attach", "Attach"),
        ("k", "kill_agent", "Kill"),
        ("escape", "quit", "Quit"),
    ]

    selected_agent = reactive(None)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("AGENTS", id="sidebar-title")
                yield ListView(id="agent-list")
            with Vertical(id="main"):
                yield Static("[bold]Select an agent to view logs[/]", id="main-header")
                yield RichLog(id="log-view", highlight=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._agents: list[dict] = []
        self.refresh_agents()
        self.set_interval(2, self.refresh_agents)
        self.set_interval(1, self.refresh_logs)

    def refresh_agents(self) -> None:
        self._agents = get_active_agents()
        agent_list = self.query_one("#agent-list", ListView)
        agent_list.clear()

        for i, agent in enumerate(self._agents, 1):
            agent_list.append(AgentItem(agent, i))

        self.sub_title = f"{len(self._agents)} agent(s) running"

    def refresh_logs(self) -> None:
        if self.selected_agent:
            logs = tmux.capture_pane(self.selected_agent["session"])
            log_view = self.query_one("#log-view", RichLog)
            log_view.clear()
            for line in logs.split("\n"):
                log_view.write(line)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, AgentItem):
            self.selected_agent = event.item.agent
            header = self.query_one("#main-header", Static)
            task = self.selected_agent.get("task", "No task")[:60]
            header.update(
                f"[bold cyan]{self.selected_agent['repo']}[/]:[yellow]{self.selected_agent['branch']}[/] - {task}"
            )
            self.refresh_logs()

    def action_refresh(self) -> None:
        self.refresh_agents()
        if self.selected_agent:
            self.refresh_logs()

    def action_attach(self) -> None:
        if self.selected_agent:
            self.exit()
            # Use execvp for safety
            os.execvp("tmux", ["tmux", "attach", "-t", self.selected_agent["session"]])

    def action_kill_agent(self) -> None:
        if self.selected_agent:
            tmux.kill_session(self.selected_agent["session"])

            config = load_config()
            if self.selected_agent["session"] in config.get("agents", {}):
                del config["agents"][self.selected_agent["session"]]
                save_config(config)

            self.selected_agent = None
            self.refresh_agents()

            header = self.query_one("#main-header", Static)
            header.update("[bold]Agent killed. Select another.[/]")
            log_view = self.query_one("#log-view", RichLog)
            log_view.clear()


def main() -> None:
    """Run the TUI application."""
    app = ConductorUI()
    app.run()


if __name__ == "__main__":
    main()
