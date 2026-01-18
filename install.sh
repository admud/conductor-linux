#!/bin/bash
# CDL (Conductor Linux) - One-command installer
# Usage: curl -fsSL https://raw.githubusercontent.com/admud/conductor-linux/main/install.sh | bash

set -euo pipefail

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

echo -e "${CYAN}Installing CDL (Conductor Linux)...${NC}"

INSTALL_DIR="$HOME/.cdl"

# Check dependencies
missing_deps=()
for cmd in git tmux python3; do
    if ! command -v "$cmd" &> /dev/null; then
        missing_deps+=("$cmd")
    fi
done

# Check for claude CLI
if ! command -v claude &> /dev/null; then
    echo -e "${YELLOW}Warning: 'claude' CLI not found.${NC}"
    echo -e "${YELLOW}CDL requires Claude Code CLI to function.${NC}"
    echo -e "${YELLOW}Install it from: https://claude.ai/code${NC}"
fi

# Check for optional fzf
if command -v fzf &> /dev/null; then
    echo -e "${DIM}Found fzf - interactive picker enabled${NC}"
else
    echo -e "${DIM}Optional: Install 'fzf' for interactive agent picker${NC}"
fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required dependencies: ${missing_deps[*]}${NC}"
    echo -e "Please install them first."
    exit 1
fi

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR" || exit 1
    git pull --quiet
else
    echo "Cloning repository..."
    git clone --quiet https://github.com/admud/conductor-linux.git "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit 1
fi

# Set restrictive permissions on config directory
mkdir -p "$HOME/.conductor"
chmod 700 "$HOME/.conductor"

# Make wrapper scripts executable
chmod +x bin/cdl bin/cdl-ui

# Install Python dependencies
echo "Installing Python dependencies..."
if pip install -q -r requirements.txt 2>/dev/null; then
    :
elif pip3 install -q -r requirements.txt 2>/dev/null; then
    :
else
    echo -e "${YELLOW}Could not install deps. Run: pip install textual${NC}"
fi

# Detect shell config
if [ -n "${ZSH_VERSION:-}" ] || [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_TYPE="zsh"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_TYPE="bash"
else
    SHELL_RC="$HOME/.profile"
    SHELL_TYPE="bash"
fi

# Add to PATH and completions if not already
if ! grep -q ".cdl/bin" "$SHELL_RC" 2>/dev/null; then
    {
        echo ''
        echo '# CDL (Conductor Linux)'
        echo 'export PATH="$HOME/.cdl/bin:$PATH"'
        echo ''
        echo '# CDL shell completions'
        if [ "$SHELL_TYPE" = "zsh" ]; then
            echo 'eval "$(cdl completions zsh)"'
        else
            echo 'eval "$(cdl completions bash)"'
        fi
    } >> "$SHELL_RC"
fi

# Fish completions (if fish is installed)
if command -v fish &> /dev/null; then
    FISH_COMP_DIR="$HOME/.config/fish/completions"
    if [ -d "$HOME/.config/fish" ]; then
        mkdir -p "$FISH_COMP_DIR"
        "$INSTALL_DIR/bin/cdl" completions fish > "$FISH_COMP_DIR/cdl.fish" 2>/dev/null || true
        echo -e "${DIM}Fish completions installed${NC}"
    fi
fi

# Create symlinks if possible
if [ -w /usr/local/bin ]; then
    ln -sf "$INSTALL_DIR/bin/cdl" /usr/local/bin/cdl 2>/dev/null || true
    ln -sf "$INSTALL_DIR/bin/cdl-ui" /usr/local/bin/cdl-ui 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}CDL installed successfully!${NC}"
echo ""
echo -e "Commands:"
echo -e "  ${CYAN}cdl add <repo-url>${NC}                  Clone a repository"
echo -e "  ${CYAN}cdl spawn <repo> <branch> -t \"...\"${NC}  Start an agent"
echo -e "  ${CYAN}cdl status${NC}  or  ${CYAN}cdl s${NC}               View all agents"
echo -e "  ${CYAN}cdl status --json${NC}                   JSON output for scripting"
echo -e "  ${CYAN}cdl attach${NC}  or  ${CYAN}cdl a${NC}               Attach to agent (fzf picker)"
echo -e "  ${CYAN}cdl logs -f 1${NC}                       Follow logs (like tail -f)"
echo -e "  ${CYAN}cdl-ui${NC}                              Launch TUI dashboard"
echo ""
echo -e "Aliases: ${DIM}s=status, a=attach, l=logs, k=kill, d=diff${NC}"
echo ""
echo -e "${YELLOW}Restart your terminal or run:${NC} source $SHELL_RC"
