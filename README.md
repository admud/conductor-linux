# Conductor Linux

A CLI tool to manage multiple [Claude Code](https://claude.ai/code) agents working in parallel on isolated git worktrees.

Inspired by [Conductor](https://conductor.build/) for Mac.

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

## Installation

```bash
# Clone the repo
git clone https://github.com/admud/conductor-linux.git
cd conductor-linux

# Install dependencies (for TUI dashboard)
pip install -r requirements.txt

# Make executable and add to PATH
chmod +x conductor-linux conductor-ui
sudo ln -sf $(pwd)/conductor-linux /usr/local/bin/conductor-linux
sudo ln -sf $(pwd)/conductor-ui /usr/local/bin/conductor-ui

# Or add to your local bin
mkdir -p ~/.local/bin
ln -sf $(pwd)/conductor-linux ~/.local/bin/conductor-linux
ln -sf $(pwd)/conductor-ui ~/.local/bin/conductor-ui
```

## Quick Start

```bash
# 1. Add a repository
conductor-linux add https://github.com/user/repo.git

# 2. Spawn agents on different branches
conductor-linux spawn myrepo feature-auth --task "Implement OAuth login"
conductor-linux spawn myrepo feature-tests --task "Add unit tests"
conductor-linux spawn myrepo bugfix-123 --task "Fix the login bug"

# 3. Monitor all agents
conductor-linux status

# 4. View an agent's terminal
conductor-linux attach 1

# 5. Review changes
conductor-linux diff

# 6. Push changes when ready
conductor-linux merge 1

# 7. Cleanup
conductor-linux kill 1 --cleanup
```

## Commands

| Command | Description |
|---------|-------------|
| `add <url>` | Clone and register a repository |
| `list` | List all repos and active agents |
| `spawn <repo> <branch> [options]` | Start a new Claude Code agent |
| `status` | Show detailed status of all agents |
| `attach <n>` | Attach to agent's tmux session |
| `diff [n]` | Show git diff for agent(s) |
| `logs <n>` | View agent's terminal output |
| `merge <n>` | Push agent's branch to origin |
| `kill <n>` | Stop an agent |
| `killall` | Stop all agents |

### Spawn Options

```bash
conductor-linux spawn <repo> <branch> [options]

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
conductor-ui
```

```
┌─────────────────────────────────────┬──────────────────────────────────────────────┐
│ AGENTS                              │ myrepo:feature-1 - Add authentication        │
│─────────────────────────────────────│──────────────────────────────────────────────│
│ ● [1] myrepo:feature-1 clean        │                                              │
│ ● [2] myrepo:feature-2 +3           │ I'll help you implement authentication...    │
│ ● [3] myrepo:bugfix-99 clean        │                                              │
│                                     │ Let me first check the existing code...      │
│                                     │                                              │
├─────────────────────────────────────┴──────────────────────────────────────────────┤
│ 3 agent(s) running | r=refresh a=attach k=kill q=quit                              │
└────────────────────────────────────────────────────────────────────────────────────┘
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
conductor-linux spawn myrepo auth --task "Add authentication" -n
conductor-linux spawn myrepo api --task "Create REST API" -n
conductor-linux spawn myrepo tests --task "Write tests" -n

# Watch them all
watch -n 5 conductor-linux status
```

### View without attaching
```bash
# See recent output
conductor-linux logs 1 --lines 100
```

## License

MIT
