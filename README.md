# CDL (Conductor Linux)

A CLI tool to manage multiple AI coding agents ([Claude Code](https://claude.ai/code) and [Codex](https://openai.com/codex/)) working in parallel on isolated git worktrees.

Inspired by [Conductor](https://conductor.build/) for Mac.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/admud/conductor-linux/main/install.sh | bash
```

## Features

- Run multiple AI coding agents simultaneously (Claude Code & Codex)
- Each agent gets an isolated git worktree (no conflicts)
- Monitor all agents from a single dashboard
- **TUI Dashboard** - Visual interface with clickable buttons
- **JSON output** - Scriptable with `jq`
- **Shell completions** - bash, zsh, fish
- **fzf integration** - Interactive agent picker
- **Config file** - Customize defaults
- View diffs and changes across all agents
- Push agent branches back when ready

## Requirements

- Python 3.10+
- git
- tmux
- [Claude Code CLI](https://claude.ai/code) (`claude`) and/or [Codex CLI](https://openai.com/codex/) (`codex`)
- Optional: [GitHub CLI](https://cli.github.com/) (`gh`) for PR workflow
- Optional: `fzf` for interactive picker

## Agent Authentication

Both Claude Code and Codex require authentication before use. Credentials are stored locally on your machine.

### Claude Code

```bash
# Login (opens browser for OAuth or prompts for API key)
claude login

# Or set API key directly
export ANTHROPIC_API_KEY=sk-ant-...

# Verify
claude whoami
```

Credentials stored in: `~/.config/.claude/`

### Codex

```bash
# Login (opens browser for ChatGPT auth or prompts for API key)
codex login

# Or set API key directly
export OPENAI_API_KEY=sk-...

# Verify
codex --version
```

Credentials stored in: `~/.codex/`

> **Note:** CDL does not store or manage API keys. Each agent CLI handles its own authentication locally.

## Manual Installation

```bash
git clone https://github.com/admud/conductor-linux.git ~/.cdl
cd ~/.cdl
pip install -r requirements.txt

# Add to PATH (add to your .bashrc or .zshrc)
export PATH="$HOME/.cdl/bin:$PATH"

# Enable shell completions (optional)
eval "$(cdl completions bash)"  # for bash
eval "$(cdl completions zsh)"   # for zsh
```

## Quick Start

```bash
# 1. Add a repository
cdl add https://github.com/user/repo.git

# 2. Spawn agents on different branches
cdl spawn myrepo feature-auth --task "Implement OAuth login"
cdl spawn myrepo feature-tests --task "Add unit tests"

# 3. Monitor all agents
cdl status          # or: cdl s
cdl status --json   # JSON output for scripting

# 4. Launch TUI dashboard
cdl-ui

# 5. View an agent's terminal
cdl attach 1        # or: cdl a 1
cdl attach          # fzf picker if no arg

# 6. Follow logs live
cdl logs -f 1       # like tail -f

# 7. Review changes
cdl diff            # or: cdl d
cdl diff --tool delta  # use external diff tool

# 8. Push changes when ready
cdl merge 1

# 8b. Create a PR
cdl pr create 1 --fill

# 9. Cleanup
cdl kill 1 --cleanup   # or: cdl k 1 -c
```

## Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `cdl add <url>` | | Clone and register a repository |
| `cdl list` | | List all repos and active agents |
| `cdl spawn <repo> <branch>` | | Start a new Claude Code agent |
| `cdl status` | `s` | Show detailed status of all agents |
| `cdl attach [n]` | `a` | Attach to agent's tmux session |
| `cdl diff [n]` | `d` | Show git diff for agent(s) |
| `cdl logs [n]` | `l` | View agent's terminal output |
| `cdl merge <n>` | | Push agent's branch to origin |
| `cdl kill [n]` | `k` | Stop an agent |
| `cdl killall` | | Stop all agents |
| `cdl pick` | | Interactive agent picker (for scripting) |
| `cdl completions <shell>` | | Generate shell completions |
| `cdl pr <create|view|merge>` | | Create/view/merge GitHub PRs for agent branches |
| `cdl-ui` | | Launch TUI dashboard |

> **Note:** Commands without `[n]` argument will show an interactive picker (requires `fzf` or falls back to numbered menu).

### Common Flags

```bash
--json, -j          # Output in JSON format (for scripting)
--follow, -f        # Follow logs (like tail -f)
--cleanup, -c       # Remove worktree when killing agent
--tool <name>       # Use external diff tool (delta, difftastic, etc.)
```

### PR Workflow

```bash
# Create a PR for an agent branch (auto-fill from commits)
cdl pr create 1 --fill

# Create as draft, target a base branch, and open in browser
cdl pr create 1 --base main --draft --web

# View PR details or open in browser
cdl pr view 1
cdl pr view 1 --web

# Merge a PR (squash by default if you pass --squash)
cdl pr merge 1 --squash --delete-branch
```

### Spawn Options

```bash
cdl spawn <repo> <branch> [options]

Options:
  -t, --task "..."     Task/prompt for the agent
  -a, --agent <type>   Agent type: claude (default) or codex
  -y, --auto-accept    Enable auto-accept mode (no permission prompts)
  -n, --no-auto-accept Run in interactive/print mode (default)
  -l, --label <name>   Label for grouping agents
```

> **Tip:** If you omit `<repo>` or `<branch>`, CDL will prompt you to select a repo and enter a branch name (defaults to the current branch).

### Using Different Agents

```bash
# Spawn a Claude Code agent (default)
cdl spawn myrepo feature-auth --task "Implement OAuth login"

# Spawn a Codex agent
cdl spawn myrepo feature-api --agent codex --task "Create REST API"

# Mix both agents on the same repo
cdl spawn myrepo auth-claude --task "Add authentication" --agent claude
cdl spawn myrepo api-codex --task "Build API endpoints" --agent codex
```

## Shell Completions

Enable tab completion for commands, repos, and agents:

```bash
# Bash (add to ~/.bashrc)
eval "$(cdl completions bash)"

# Zsh (add to ~/.zshrc)
eval "$(cdl completions zsh)"

# Fish
cdl completions fish > ~/.config/fish/completions/cdl.fish
```

## JSON Output

All list/status commands support JSON output for scripting:

```bash
# Get list of agents
cdl status --json | jq '.agents'

# Get repo names
cdl list --json | jq -r '.repos | keys[]'

# Use with fzf
cdl status --json | jq -r '.agents[] | "\(.number): \(.repo)/\(.branch)"' | fzf
```

## Config File

Create `~/.conductor/config.toml` to customize defaults:

```toml
[defaults]
auto_accept = false      # Default auto-accept mode
diff_tool = "delta"      # Default diff tool
notify = false           # Desktop notifications

[hooks]
post_spawn = "notify-send 'CDL' 'Agent spawned'"
post_complete = "~/.local/bin/on-agent-done.sh"
```

## How It Works

1. **Repositories** are cloned to `~/.conductor/repos/`
2. **Worktrees** are created in `~/.conductor/worktrees/` for isolation
3. **Agents** run Claude Code inside tmux sessions
4. **Config** is stored in `~/.conductor/config.json`

```
~/.conductor/
├── config.json          # Tracks repos and agents
├── config.toml          # User preferences (optional)
├── repos/
│   └── myrepo/          # Cloned repositories
└── worktrees/
    ├── myrepo-feature-1-143022/   # Isolated worktree
    └── myrepo-feature-2-143045/   # Another worktree
```

## TUI Dashboard

Launch the visual dashboard to monitor all agents in real-time:

```bash
cdl-ui
```

### Features

- **Clickable agent cards** - Click to select
- **Action buttons** - Attach, Logs, Diff, Kill, Refresh
- **Keyboard shortcuts** - Full keyboard navigation
- **Live updates** - Auto-refresh every second
- **Confirmation dialogs** - Safe kill with confirmation

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-5` | Select agent by number |
| `r` | Refresh |
| `a` | Attach to selected agent |
| `l` | Show logs |
| `d` | Show diff |
| `k` | Kill agent (with confirmation) |
| `q` / `Esc` | Quit |

### Screenshot

```
┌─────────────────────────────────┐┌────────────────────────────────────────────┐
│ AGENTS                          ││ myrepo/feature-1 | LOGS | Add authentication│
│                                 │├────────────────────────────────────────────┤
│ ┌─────────────────────────────┐ ││ [Attach] [Logs] [Diff] [Kill] [Refresh]    │
│ │ 1 myrepo/feature-1 (clean)  │ │├────────────────────────────────────────────┤
│ │   Add authentication...     │ ││                                            │
│ └─────────────────────────────┘ ││ I'll help you implement authentication...  │
│ ┌─────────────────────────────┐ ││                                            │
│ │ 2 myrepo/feature-2 (+3)     │ ││ Let me check the existing code first...    │
│ │   Create REST API...        │ ││                                            │
│ └─────────────────────────────┘ ││ > Reading src/auth/...                     │
│                                 ││                                            │
└─────────────────────────────────┘└────────────────────────────────────────────┘
 q Quit | r Refresh | a Attach | l Logs | d Diff | k Kill
```

## Tips

### Detach from tmux
When attached to an agent, press `Ctrl+B` then `D` to detach without killing it.

### Run multiple agents
```bash
# Spawn 3 agents working on different features
cdl spawn myrepo auth --task "Add authentication" -n
cdl spawn myrepo api --task "Create REST API" -n
cdl spawn myrepo tests --task "Write tests" -n

# Watch them all
cdl-ui
```

### Follow logs in real-time
```bash
cdl logs -f 1  # Like tail -f, updates every 0.5s
```

### Use with external diff tools
```bash
cdl diff --tool delta      # Use delta for syntax highlighting
cdl diff --tool difftastic # Use difftastic for structural diff
```

### Scripting with JSON
```bash
# Kill all agents with changes
cdl status --json | jq -r '.agents[] | select(.changes > 0) | .number' | xargs -I{} cdl kill {}

# Get agent count
cdl status --json | jq '.count'
```

## License

MIT
