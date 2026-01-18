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
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Label, RichLog,
    DataTable, Input, Rule,
)
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen

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


class ConfirmDialog(ModalScreen):
    """A modal confirmation dialog."""

    def __init__(self, message: str, action: str = "confirm"):
        super().__init__()
        self.message = message
        self.action = action

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.message, id="dialog-message")
            with Horizontal(id="dialog-buttons"):
                yield Button("Yes", id="yes", variant="error")
                yield Button("No", id="no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class AgentCard(Static):
    """A clickable card representing an agent."""

    class Selected(Message):
        """Message sent when agent is selected."""
        def __init__(self, agent: dict, index: int):
            super().__init__()
            self.agent = agent
            self.index = index

    def __init__(self, agent: dict, index: int):
        super().__init__()
        self.agent = agent
        self.index = index

    def compose(self) -> ComposeResult:
        changes = self.agent.get("changes", 0)
        status_color = "green" if changes == 0 else "yellow"
        changes_text = f"+{changes}" if changes else "clean"

        yield Static(
            f"[bold {status_color}]{self.index}[/] "
            f"[cyan]{self.agent['repo']}[/]/[yellow]{self.agent['branch']}[/] "
            f"[dim]({changes_text})[/]",
            classes="agent-title"
        )
        if self.agent.get("task"):
            yield Static(f"[dim]{self.agent['task'][:50]}...[/]", classes="agent-task")

    def on_click(self) -> None:
        self.post_message(self.Selected(self.agent, self.index))


class ActionBar(Horizontal):
    """Action buttons for the selected agent."""

    def compose(self) -> ComposeResult:
        yield Button("Attach", id="btn-attach", variant="primary")
        yield Button("Logs", id="btn-logs", variant="default")
        yield Button("Diff", id="btn-diff", variant="default")
        yield Button("Kill", id="btn-kill", variant="error")
        yield Button("Refresh", id="btn-refresh", variant="success")


class ConductorUI(App):
    """TUI Dashboard for Conductor Linux."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 35;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #sidebar-header {
        text-align: center;
        text-style: bold;
        padding: 0 0 1 0;
        color: $text;
        background: $primary;
    }

    #agents-container {
        height: 1fr;
        overflow-y: auto;
    }

    AgentCard {
        padding: 1;
        margin: 0 0 1 0;
        border: solid $surface-lighten-1;
        height: auto;
    }

    AgentCard:hover {
        background: $surface-lighten-1;
        border: solid $primary;
    }

    AgentCard:focus {
        background: $primary 20%;
        border: solid $primary;
    }

    .agent-title {
        text-style: bold;
    }

    .agent-task {
        margin-top: 1;
    }

    #main {
        width: 1fr;
        height: 100%;
        border: solid $secondary;
    }

    #main-header {
        height: 3;
        padding: 1;
        background: $surface;
        border-bottom: solid $surface-lighten-1;
    }

    ActionBar {
        height: 3;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $surface-lighten-1;
        align: center middle;
    }

    ActionBar Button {
        margin: 0 1;
        min-width: 10;
    }

    #log-view {
        height: 1fr;
        padding: 1;
        border: none;
    }

    #no-agent-message {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }

    #dialog {
        width: 50;
        height: 10;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        align: center middle;
    }

    #dialog-message {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-align: center;
    }

    #dialog-buttons {
        width: 100%;
        height: 3;
        align: center middle;
    }

    #dialog-buttons Button {
        margin: 0 2;
    }

    Footer {
        background: $surface;
    }

    .empty-state {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "attach", "Attach"),
        Binding("l", "show_logs", "Logs"),
        Binding("d", "show_diff", "Diff"),
        Binding("k", "kill_agent", "Kill"),
        Binding("escape", "quit", "Quit"),
        Binding("1", "select_1", "Agent 1", show=False),
        Binding("2", "select_2", "Agent 2", show=False),
        Binding("3", "select_3", "Agent 3", show=False),
        Binding("4", "select_4", "Agent 4", show=False),
        Binding("5", "select_5", "Agent 5", show=False),
    ]

    selected_agent: reactive[dict | None] = reactive(None)
    view_mode: reactive[str] = reactive("logs")  # "logs" or "diff"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("AGENTS", id="sidebar-header")
                yield ScrollableContainer(id="agents-container")
            with Vertical(id="main"):
                yield Static("[b]Select an agent to view details[/]", id="main-header")
                yield ActionBar()
                yield RichLog(id="log-view", highlight=True, wrap=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._agents: list[dict] = []
        self.refresh_agents()
        self.set_interval(2, self.refresh_agents)
        self.set_interval(1, self.refresh_view)

    def refresh_agents(self) -> None:
        self._agents = get_active_agents()
        container = self.query_one("#agents-container", ScrollableContainer)

        # Clear existing cards
        container.remove_children()

        if not self._agents:
            container.mount(Static(
                "[dim]No active agents\n\n"
                "Use [cyan]cdl spawn[/] to start one[/]",
                classes="empty-state"
            ))
        else:
            for i, agent in enumerate(self._agents, 1):
                container.mount(AgentCard(agent, i))

        self.sub_title = f"{len(self._agents)} agent(s)"

    def refresh_view(self) -> None:
        """Refresh the current view (logs or diff)."""
        if not self.selected_agent:
            return

        if self.view_mode == "logs":
            self._show_logs()
        else:
            self._show_diff()

    def _show_logs(self) -> None:
        """Display logs for selected agent."""
        if not self.selected_agent:
            return
        logs = tmux.capture_pane(self.selected_agent["session"], 100)
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        for line in logs.split("\n"):
            log_view.write(line)

    def _show_diff(self) -> None:
        """Display diff for selected agent."""
        if not self.selected_agent:
            return

        worktree = Path(self.selected_agent["worktree"])
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()

        log_view.write("[bold cyan]Git Status[/]")
        log_view.write("-" * 40)

        # Unstaged changes
        result = git.diff(worktree, stat=True)
        if result.stdout.strip():
            log_view.write("[yellow]Unstaged changes:[/]")
            for line in result.stdout.strip().split("\n"):
                log_view.write(f"  {line}")
            log_view.write("")

        # Staged changes
        result = git.diff(worktree, cached=True, stat=True)
        if result.stdout.strip():
            log_view.write("[green]Staged changes:[/]")
            for line in result.stdout.strip().split("\n"):
                log_view.write(f"  {line}")
            log_view.write("")

        # Untracked files
        untracked = git.ls_files_untracked(worktree)
        if untracked:
            log_view.write("[cyan]Untracked files:[/]")
            for f in untracked:
                log_view.write(f"  + {f}")

    def on_agent_card_selected(self, event: AgentCard.Selected) -> None:
        self.selected_agent = event.agent
        self._update_header()
        self.view_mode = "logs"
        self.refresh_view()

    def _update_header(self) -> None:
        header = self.query_one("#main-header", Static)
        if self.selected_agent:
            task = self.selected_agent.get("task", "No task")[:50]
            mode = "[cyan]LOGS[/]" if self.view_mode == "logs" else "[yellow]DIFF[/]"
            header.update(
                f"[bold]{self.selected_agent['repo']}[/]/"
                f"[yellow]{self.selected_agent['branch']}[/] "
                f"| {mode} | {task}"
            )
        else:
            header.update("[b]Select an agent to view details[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn-refresh":
            self.refresh_agents()
            self.refresh_view()
        elif button_id == "btn-attach":
            self.action_attach()
        elif button_id == "btn-logs":
            self.action_show_logs()
        elif button_id == "btn-diff":
            self.action_show_diff()
        elif button_id == "btn-kill":
            self.action_kill_agent()

    def action_refresh(self) -> None:
        self.refresh_agents()
        self.refresh_view()

    def action_attach(self) -> None:
        if self.selected_agent:
            self.exit()
            os.execvp("tmux", ["tmux", "attach", "-t", self.selected_agent["session"]])

    def action_show_logs(self) -> None:
        self.view_mode = "logs"
        self._update_header()
        self.refresh_view()

    def action_show_diff(self) -> None:
        self.view_mode = "diff"
        self._update_header()
        self.refresh_view()

    def action_kill_agent(self) -> None:
        if not self.selected_agent:
            return

        async def confirm_kill(confirmed: bool) -> None:
            if confirmed and self.selected_agent:
                tmux.kill_session(self.selected_agent["session"])
                config = load_config()
                if self.selected_agent["session"] in config.get("agents", {}):
                    del config["agents"][self.selected_agent["session"]]
                    save_config(config)
                self.selected_agent = None
                self.refresh_agents()
                self._update_header()
                log_view = self.query_one("#log-view", RichLog)
                log_view.clear()
                log_view.write("[bold red]Agent killed.[/]")

        self.push_screen(
            ConfirmDialog(
                f"Kill agent {self.selected_agent['repo']}/{self.selected_agent['branch']}?"
            ),
            confirm_kill
        )

    def _select_agent(self, num: int) -> None:
        if 0 < num <= len(self._agents):
            self.selected_agent = self._agents[num - 1]
            self._update_header()
            self.view_mode = "logs"
            self.refresh_view()

    def action_select_1(self) -> None: self._select_agent(1)
    def action_select_2(self) -> None: self._select_agent(2)
    def action_select_3(self) -> None: self._select_agent(3)
    def action_select_4(self) -> None: self._select_agent(4)
    def action_select_5(self) -> None: self._select_agent(5)


def main() -> None:
    """Run the TUI application."""
    app = ConductorUI()
    app.run()


if __name__ == "__main__":
    main()
