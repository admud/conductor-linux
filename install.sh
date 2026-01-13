#!/bin/bash
# CDL (Conductor Linux) - One-command installer
# Usage: curl -fsSL https://raw.githubusercontent.com/admud/conductor-linux/main/install.sh | bash

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${CYAN}Installing CDL (Conductor Linux)...${NC}"

INSTALL_DIR="$HOME/.cdl"

# Check dependencies
for cmd in git tmux python3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${YELLOW}Warning: $cmd not found. Please install it.${NC}"
    fi
done

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --quiet
else
    echo "Cloning repository..."
    git clone --quiet https://github.com/admud/conductor-linux.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Make executable
chmod +x cdl cdl-ui

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt 2>/dev/null || pip3 install -q -r requirements.txt 2>/dev/null || echo -e "${YELLOW}Could not install deps. Run: pip install textual${NC}"

# Detect shell config
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
else
    SHELL_RC="$HOME/.bashrc"
fi

# Add to PATH if not already
if ! grep -q ".cdl" "$SHELL_RC" 2>/dev/null; then
    echo '' >> "$SHELL_RC"
    echo '# CDL (Conductor Linux)' >> "$SHELL_RC"
    echo 'export PATH="$HOME/.cdl:$PATH"' >> "$SHELL_RC"
fi

# Create symlinks if possible
if [ -w /usr/local/bin ]; then
    ln -sf "$INSTALL_DIR/cdl" /usr/local/bin/cdl 2>/dev/null || true
    ln -sf "$INSTALL_DIR/cdl-ui" /usr/local/bin/cdl-ui 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✓ CDL installed successfully!${NC}"
echo ""
echo -e "Commands:"
echo -e "  ${CYAN}cdl add <repo-url>${NC}              Clone a repository"
echo -e "  ${CYAN}cdl spawn <repo> <branch> -t \"...\"${NC}  Start an agent"
echo -e "  ${CYAN}cdl status${NC}                      View all agents"
echo -e "  ${CYAN}cdl-ui${NC}                          Launch TUI dashboard"
echo ""
echo -e "${YELLOW}Restart your terminal or run:${NC} source $SHELL_RC"
