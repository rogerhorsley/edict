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

# ── 4. 创建快捷命令 ──
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

# ac-dashboard 启动命令
cat > "$BIN_DIR/ac-dashboard" << DEOF
#!/bin/bash
cd "$INSTALL_DIR"
echo "Starting 三省七部 Dashboard on http://127.0.0.1:7891"
python3 dashboard/server.py "\$@"
DEOF
chmod +x "$BIN_DIR/ac-dashboard"

# ac-sync 后台同步命令
cat > "$BIN_DIR/ac-sync" << SEOF
#!/bin/bash
cd "$INSTALL_DIR"
echo "Starting background sync loop..."
bash scripts/run_loop.sh "\$@"
SEOF
chmod +x "$BIN_DIR/ac-sync"

# ac-update 更新命令
cat > "$BIN_DIR/ac-update" << UEOF
#!/bin/bash
cd "$INSTALL_DIR"
echo "Updating project..."
git pull --ff-only origin main && bash install.sh
UEOF
chmod +x "$BIN_DIR/ac-update"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Installation complete!                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "Quick commands (add ~/.local/bin to PATH if needed):"
echo "  ac-dashboard     Start the dashboard (port 7891)"
echo "  ac-sync          Start background data sync"
echo "  ac-update        Pull latest and reinstall"
echo ""
echo "Or manually:"
echo "  cd $INSTALL_DIR"
echo "  python3 dashboard/server.py          # Start dashboard"
echo "  bash scripts/run_loop.sh &           # Background sync"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo -e "${YELLOW}Add to your shell profile:${NC}"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi
