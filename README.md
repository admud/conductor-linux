# CDL (Conductor Linux)

A CLI tool to manage multiple [Claude Code](https://claude.ai/code) agents working in parallel on isolated git worktrees.

Inspired by [Conductor](https://conductor.build/) for Mac.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/admud/conductor-linux/main/install.sh | bash
```

## Features

- Run multiple Claude Code instances simultaneously
- Each agent gets an isolated git worktree (no conflicts)
- Monitor all agents from a single dashboard
- **TUI Dashboard** - Visual interface to monitor agents in real-time
- View diffs and changes across all agents
- Merge changes back when ready

## Requirements

- Python 3.7+
- git
- tmux
- [Claude Code CLI](https://claude.ai/code) (`claude`)

## Manual Installation

```bash
git clone https://github.com/admud/conductor-linux.git ~/.cdl
cd ~/.cdl
pip install -r requirements.txt
chmod +x cdl cdl-ui

# Add to PATH (add to your .bashrc or .zshrc)
export PATH="$HOME/.cdl:$PATH"
```

## Quick Start

```bash
# 1. Add a repository
cdl add https://github.com/user/repo.git

# 2. Spawn agents on different branches
cdl spawn myrepo feature-auth --task "Implement OAuth login"
cdl spawn myrepo feature-tests --task "Add unit tests"

# 3. Monitor all agents
cdl status

# 4. Launch TUI dashboard
cdl-ui

# 5. View an agent's terminal
cdl attach 1

# 6. Review changes
cdl diff

# 7. Push changes when ready
cdl merge 1

# 8. Cleanup
cdl kill 1 --cleanup
```

## Commands

| Command | Description |
|---------|-------------|
| `cdl add <url>` | Clone and register a repository |
| `cdl list` | List all repos and active agents |
| `cdl spawn <repo> <branch> [options]` | Start a new Claude Code agent |
| `cdl status` | Show detailed status of all agents |
| `cdl attach <n>` | Attach to agent's tmux session |
| `cdl diff [n]` | Show git diff for agent(s) |
| `cdl logs <n>` | View agent's terminal output |
| `cdl merge <n>` | Push agent's branch to origin |
| `cdl kill <n>` | Stop an agent |
| `cdl killall` | Stop all agents |
| `cdl-ui` | Launch TUI dashboard |

### Spawn Options

```bash
cdl spawn <repo> <branch> [options]

Options:
  -t, --task "..."     Task/prompt for the agent
  -y, --auto-accept    Enable auto-accept mode (no permission prompts)
  -n, --no-auto-accept Run in interactive/print mode (default)
```

## How It Works

1. **Repositories** are cloned to `~/.conductor/repos/`
2. **Worktrees** are created in `~/.conductor/worktrees/` for isolation
3. **Agents** run Claude Code inside tmux sessions
4. **Config** is stored in `~/.conductor/config.json`

```
~/.conductor/
├── config.json          # Tracks repos and agents
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

```
┌──────────────────────────────────────┐┌──────────────────────────────────────┐
│ AGENTS                               ││ myrepo:feature-1 - Add authentication│
│                                      ││                                      │
│ ● [1] myrepo:feature-1 ok            ││ I'll help you implement auth...      │
│ ● [2] myrepo:feature-2 +3            ││                                      │
│ ● [3] myrepo:bugfix-99 ok            ││ Let me check the existing code...    │
│                                      ││                                      │
└──────────────────────────────────────┘└──────────────────────────────────────┘
 q Quit  r Refresh  a Attach  k Kill
```

**Keyboard shortcuts:**
- `↑/↓` - Select agent
- `r` - Refresh status
- `a` - Attach to selected agent's terminal
- `k` - Kill selected agent
- `q` - Quit dashboard

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

### View without attaching
```bash
# See recent output
cdl logs 1 --lines 100
```

## License

MIT
