#!/bin/bash
# ══════════════════════════════════════════════════════════════
# 三省七部 · 远程一键安装脚本
# curl -fsSL https://raw.githubusercontent.com/rogerhorsley/agents_company_for_happycapy/main/setup.sh | bash
# ══════════════════════════════════════════════════════════════
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  三省七部 · Sanshen-Qibu Installer              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. 检查基本依赖 ──
for cmd in git python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}Missing: $cmd. Please install it first.${NC}"
    exit 1
  fi
done

# ── 2. 选择安装目录 ──
INSTALL_DIR="${AC_DIR:-$HOME/agents_company_for_happycapy}"

if [ -d "$INSTALL_DIR/.git" ]; then
  echo -e "${YELLOW}Existing installation found at $INSTALL_DIR${NC}"
  echo -e "${BLUE}Pulling latest changes...${NC}"
  cd "$INSTALL_DIR"
  git pull --ff-only origin main || {
    echo -e "${YELLOW}Fast-forward failed, resetting to latest...${NC}"
    git fetch origin main
    git reset --hard origin/main
  }
else
  echo -e "${BLUE}Cloning into $INSTALL_DIR ...${NC}"
  git clone https://github.com/rogerhorsley/agents_company_for_happycapy.git "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

echo -e "${GREEN}Source ready at: $INSTALL_DIR${NC}"

# ── 3. 运行本地 install.sh ──
if [ -f install.sh ]; then
  echo ""
  echo -e "${BLUE}Running install.sh ...${NC}"
  bash install.sh
else
  echo -e "${RED}install.sh not found in repo!${NC}"
  exit 1
fi

# ── 4. 安装 CLI ──
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

# Unified CLI
cat > "$BIN_DIR/ac" << ACEOF
#!/usr/bin/env python3
import os, sys
os.environ.setdefault('AC_REPO_DIR', '$INSTALL_DIR')
sys.path.insert(0, '$INSTALL_DIR')
exec(open('$INSTALL_DIR/cli.py').read())
ACEOF
chmod +x "$BIN_DIR/ac"

# Backward-compatible aliases
cat > "$BIN_DIR/ac-dashboard" << DEOF
#!/bin/bash
exec ac dashboard "\$@"
DEOF
chmod +x "$BIN_DIR/ac-dashboard"

cat > "$BIN_DIR/ac-sync" << SEOF
#!/bin/bash
exec ac sync "\$@"
SEOF
chmod +x "$BIN_DIR/ac-sync"

cat > "$BIN_DIR/ac-update" << UEOF
#!/bin/bash
exec ac update "\$@"
UEOF
chmod +x "$BIN_DIR/ac-update"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Installation complete!                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "Unified CLI (add ~/.local/bin to PATH if needed):"
echo ""
echo "  ac dashboard          Start dashboard (port 7891)"
echo "  ac sync               Start background data sync"
echo "  ac update             Pull latest and reinstall"
echo "  ac task list          List tasks"
echo "  ac agent status       Show agent status"
echo "  ac channel list       List channels"
echo "  ac login              Login to dashboard"
echo "  ac --help             See all commands"
echo ""
echo "Or manually:"
echo "  cd $INSTALL_DIR"
echo "  python3 dashboard/server.py"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo -e "${YELLOW}Add to your shell profile:${NC}"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi
