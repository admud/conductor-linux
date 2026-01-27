#!/usr/bin/env python3
"""
CDL (Conductor Linux) - TUI Dashboard
A visual interface to monitor and manage Claude Code agents.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
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
from types import SimpleNamespace

# Add src to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cdl.core.config import load_config, save_config
from cdl.core import git, tmux
from cdl.core.paths import WORKTREES_DIR
from cdl.commands.agent import _ensure_context_dir
from cdl.commands.agent import cmd_spawn


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


def get_archived_workspaces() -> list[dict]:
    """Get list of archived workspaces from config."""
    config = load_config()
    archives = []
    for key, entry in config.get("archives", {}).items():
        archives.append({
            "key": key,
            "repo": entry.get("repo", ""),
            "branch": entry.get("branch", ""),
            "worktree": entry.get("worktree", ""),
            "archived_at": entry.get("archived_at", ""),
            "task": entry.get("task", ""),
            "agent_type": entry.get("agent_type", "claude"),
            "started": entry.get("started", ""),
        })
    return archives


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


class SpawnPRDialog(ModalScreen):
    """Modal dialog to spawn a workspace from a PR."""

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Spawn from PR", id="dialog-message")
            yield Input(placeholder="PR number or URL", id="pr-input")
            yield Input(placeholder="Task (optional)", id="task-input")
            yield Input(placeholder="Agent: claude or codex (default: claude)", id="agent-input")
            with Horizontal(id="dialog-buttons"):
                yield Button("Spawn", id="spawn", variant="primary")
                yield Button("Cancel", id="cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "spawn":
            pr_input = self.query_one("#pr-input", Input).value.strip()
            task_input = self.query_one("#task-input", Input).value.strip()
            agent_input = self.query_one("#agent-input", Input).value.strip().lower()
            agent_type = agent_input if agent_input in ("claude", "codex") else "claude"
            self.dismiss({
                "pr": pr_input,
                "task": task_input,
                "agent_type": agent_type,
            })
        else:
            self.dismiss(None)

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


class ArchiveCard(Static):
    """A clickable card representing an archived workspace."""

    class Selected(Message):
        """Message sent when archive is selected."""
        def __init__(self, archive: dict, index: int):
            super().__init__()
            self.archive = archive
            self.index = index

    def __init__(self, archive: dict, index: int):
        super().__init__()
        self.archive = archive
        self.index = index

    def compose(self) -> ComposeResult:
        archived_at = self.archive.get("archived_at", "")
        label = archived_at.split("T")[0] if archived_at else "archived"
        yield Static(
            f"[bold blue]{self.index}[/] "
            f"[cyan]{self.archive['repo']}[/]/[yellow]{self.archive['branch']}[/] "
            f"[dim]({label})[/]",
            classes="archive-title"
        )
        if self.archive.get("task"):
            yield Static(f"[dim]{self.archive['task'][:50]}...[/]", classes="archive-task")

    def on_click(self) -> None:
        self.post_message(self.Selected(self.archive, self.index))


class ActionBar(Horizontal):
    """Action buttons for the selected agent."""

    def compose(self) -> ComposeResult:
        yield Button("Attach", id="btn-attach", variant="primary")
        yield Button("Logs", id="btn-logs", variant="default")
        yield Button("Diff", id="btn-diff", variant="default")
        yield Button("Context", id="btn-context", variant="default")
        yield Button("Archive", id="btn-archive", variant="warning")
        yield Button("Restore", id="btn-restore", variant="success")
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
        height: 2fr;
        overflow-y: auto;
    }

    #archives-header {
        margin-top: 1;
        text-align: center;
        text-style: bold;
        padding: 1 0;
        color: $text;
        background: $surface;
        border-top: solid $surface-lighten-1;
    }

    #archives-container {
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

    .archive-title {
        text-style: bold;
    }

    .archive-task {
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
        height: 16;
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
        Binding("x", "archive_agent", "Archive"),
        Binding("v", "restore_archive", "Restore"),
        Binding("c", "show_context", "Context"),
        Binding("p", "spawn_pr", "Spawn PR"),
        Binding("escape", "quit", "Quit"),
        Binding("1", "select_1", "Agent 1", show=False),
        Binding("2", "select_2", "Agent 2", show=False),
        Binding("3", "select_3", "Agent 3", show=False),
        Binding("4", "select_4", "Agent 4", show=False),
        Binding("5", "select_5", "Agent 5", show=False),
    ]

    selected_agent: reactive[dict | None] = reactive(None)
    selected_archive: reactive[dict | None] = reactive(None)
    view_mode: reactive[str] = reactive("logs")  # "logs" | "diff" | "context"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("AGENTS", id="sidebar-header")
                yield ScrollableContainer(id="agents-container")
                yield Static("ARCHIVES", id="archives-header")
                yield ScrollableContainer(id="archives-container")
            with Vertical(id="main"):
                yield Static("[b]Select an agent to view details[/]", id="main-header")
                yield ActionBar()
                yield RichLog(id="log-view", highlight=True, wrap=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._agents: list[dict] = []
        self._archives: list[dict] = []
        self.refresh_agents()
        self.refresh_archives()
        self.set_interval(2, self.refresh_agents)
        self.set_interval(3, self.refresh_archives)
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

    def refresh_archives(self) -> None:
        self._archives = get_archived_workspaces()
        container = self.query_one("#archives-container", ScrollableContainer)
        container.remove_children()

        if not self._archives:
            container.mount(Static(
                "[dim]No archives[/]",
                classes="empty-state"
            ))
        else:
            for i, archive in enumerate(self._archives, 1):
                container.mount(ArchiveCard(archive, i))

    def refresh_view(self) -> None:
        """Refresh the current view (logs or diff)."""
        if not self.selected_agent and not self.selected_archive:
            return

        if self.selected_agent:
            if self.view_mode == "logs":
                self._show_logs()
            elif self.view_mode == "diff":
                self._show_diff()
            else:
                self._show_context()
            return

        if self.selected_archive:
            self._show_archive_details()
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

    def _show_context(self) -> None:
        """Display .context contents for selected agent."""
        if not self.selected_agent:
            return

        worktree = Path(self.selected_agent["worktree"])
        context_dir = worktree / ".context"
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()

        if not context_dir.exists():
            log_view.write("[dim].context directory not found.[/]")
            return

        files = sorted([p for p in context_dir.rglob("*") if p.is_file()])
        if not files:
            log_view.write("[dim].context is empty.[/]")
            return

        log_view.write("[bold cyan].context files[/]")
        log_view.write("-" * 40)

        for path in files[:5]:
            rel = path.relative_to(worktree)
            log_view.write(f"[yellow]{rel}[/]")
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                log_view.write("[dim]<unreadable>[/]\n")
                continue
            lines = text.splitlines()
            preview = lines[:40]
            for line in preview:
                log_view.write(f"  {line}")
            if len(lines) > 40:
                log_view.write("  [dim]...[/]")
            log_view.write("")

    def _show_archive_details(self) -> None:
        """Display details for selected archive."""
        if not self.selected_archive:
            return

        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        archive = self.selected_archive
        log_view.write("[bold cyan]Archived workspace[/]")
        log_view.write("-" * 40)
        log_view.write(f"Repo:   {archive.get('repo', '')}")
        log_view.write(f"Branch: {archive.get('branch', '')}")
        log_view.write(f"Path:   {archive.get('worktree', '')}")
        log_view.write(f"Saved:  {archive.get('archived_at', '')}")
        if archive.get("task"):
            log_view.write("")
            log_view.write("[bold]Task[/]")
            log_view.write(archive.get("task", ""))
        log_view.write("")
        log_view.write("[dim]Press Restore to bring this workspace back.[/]")

    def on_agent_card_selected(self, event: AgentCard.Selected) -> None:
        self.selected_agent = event.agent
        self.selected_archive = None
        self._update_header()
        self.view_mode = "logs"
        self.refresh_view()

    def on_archive_card_selected(self, event: ArchiveCard.Selected) -> None:
        self.selected_archive = event.archive
        self.selected_agent = None
        self._update_header()
        self.view_mode = "logs"
        self.refresh_view()

    def _update_header(self) -> None:
        header = self.query_one("#main-header", Static)
        if self.selected_agent:
            task = self.selected_agent.get("task", "No task")[:50]
            if self.view_mode == "logs":
                mode = "[cyan]LOGS[/]"
            elif self.view_mode == "diff":
                mode = "[yellow]DIFF[/]"
            else:
                mode = "[blue]CONTEXT[/]"
            header.update(
                f"[bold]{self.selected_agent['repo']}[/]/"
                f"[yellow]{self.selected_agent['branch']}[/] "
                f"| {mode} | {task}"
            )
        elif self.selected_archive:
            archived_at = self.selected_archive.get("archived_at", "")
            header.update(
                f"[bold]{self.selected_archive['repo']}[/]/"
                f"[yellow]{self.selected_archive['branch']}[/] "
                f"| [blue]ARCHIVE[/] | {archived_at}"
            )
        else:
            header.update("[b]Select an agent to view details[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn-refresh":
            self.refresh_agents()
            self.refresh_archives()
            self.refresh_view()
        elif button_id == "btn-attach":
            self.action_attach()
        elif button_id == "btn-logs":
            self.action_show_logs()
        elif button_id == "btn-diff":
            self.action_show_diff()
        elif button_id == "btn-context":
            self.action_show_context()
        elif button_id == "btn-archive":
            self.action_archive_agent()
        elif button_id == "btn-restore":
            self.action_restore_archive()
        elif button_id == "btn-kill":
            self.action_kill_agent()

    def action_refresh(self) -> None:
        self.refresh_agents()
        self.refresh_archives()
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

    def action_show_context(self) -> None:
        self.view_mode = "context"
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

    def action_spawn_pr(self) -> None:
        async def handle_spawn(data) -> None:
            if not data or not data.get("pr"):
                return
            args = SimpleNamespace(
                repo=None,
                branch=None,
                task=data.get("task", ""),
                auto_accept=False,
                agent=data.get("agent_type", "claude"),
                label=None,
                from_pr=data.get("pr"),
                from_branch=None,
            )
            cmd_spawn(args)
            self.refresh_agents()
            self.refresh_archives()
            self._update_header()

        self.push_screen(SpawnPRDialog(), handle_spawn)

    def action_archive_agent(self) -> None:
        if not self.selected_agent:
            return

        async def confirm_archive(confirmed: bool) -> None:
            if confirmed and self.selected_agent:
                session = self.selected_agent["session"]
                config = load_config()
                agent_info = config.get("agents", {}).get(session)
                if not agent_info:
                    return
                tmux.kill_session(session)
                repo_path = Path(config["repos"][agent_info["repo"]]["path"])
                worktree_path = Path(agent_info["worktree"])
                result = git.worktree_remove(repo_path, worktree_path, force=True)
                if result.returncode != 0:
                    log_view = self.query_one("#log-view", RichLog)
                    log_view.clear()
                    log_view.write("[bold red]Archive failed.[/]")
                    if result.stderr.strip():
                        log_view.write(result.stderr.strip())
                    return
                archive_entry = {
                    "repo": agent_info["repo"],
                    "branch": agent_info["branch"],
                    "worktree": str(worktree_path),
                    "task": agent_info.get("task", ""),
                    "agent_type": agent_info.get("agent_type", "claude"),
                    "started": agent_info.get("started", ""),
                    "archived_at": datetime.now().isoformat(),
                }
                config.setdefault("archives", {})
                config["archives"][session] = archive_entry
                del config["agents"][session]
                save_config(config)
                self.selected_agent = None
                self.refresh_agents()
                self.refresh_archives()
                self._update_header()
                log_view = self.query_one("#log-view", RichLog)
                log_view.clear()
                log_view.write("[bold yellow]Workspace archived.[/]")

        self.push_screen(
            ConfirmDialog(
                f"Archive {self.selected_agent['repo']}/{self.selected_agent['branch']}? "
                "This removes the worktree."
            ),
            confirm_archive
        )

    def action_restore_archive(self) -> None:
        if not self.selected_archive:
            return

        archive = self.selected_archive
        config = load_config()
        repo_name = archive.get("repo")
        if repo_name not in config.get("repos", {}):
            return

        repo_path = Path(config["repos"][repo_name]["path"])
        branch = archive.get("branch")
        worktree_path = Path(archive.get("worktree", ""))

        if not worktree_path.exists():
            if not worktree_path.parent.exists():
                worktree_path = WORKTREES_DIR / worktree_path.name
            result = git.worktree_add(repo_path, worktree_path, branch)
            if result.returncode != 0:
                result = git.worktree_add(repo_path, worktree_path, branch, force_branch=True)
                if result.returncode != 0:
                    log_view = self.query_one("#log-view", RichLog)
                    log_view.clear()
                    log_view.write("[bold red]Restore failed.[/]")
                    return

        _ensure_context_dir(worktree_path)
        session_name = f"conductor-{worktree_path.name}"
        if not tmux.session_exists(session_name):
            tmux.new_session(session_name, worktree_path)

        config["agents"][session_name] = {
            "repo": repo_name,
            "branch": branch,
            "worktree": str(worktree_path),
            "task": archive.get("task", ""),
            "agent_type": archive.get("agent_type", "claude"),
            "started": archive.get("started", ""),
        }
        if archive.get("worktree") != str(worktree_path):
            archive["worktree"] = str(worktree_path)
        del config["archives"][archive["key"]]
        save_config(config)

        self.selected_archive = None
        self.refresh_archives()
        self.refresh_agents()
        self._update_header()
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        log_view.write("[bold green]Workspace restored.[/]")

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
