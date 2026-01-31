#!/bin/bash
# ============================================
# 快速同步脚本 - 从本地推送更新到云服务器
# 在本地开发机上运行
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# 配置 (请修改为你的服务器信息)
# ============================================
SERVER_HOST="${SERVER_HOST:-your-server-ip}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_PORT="${SERVER_PORT:-22}"
INSTALL_DIR="/opt/apihub"

# 检查配置
if [ "$SERVER_HOST" == "your-server-ip" ]; then
    echo "请设置服务器信息:"
    echo "  export SERVER_HOST=你的服务器IP"
    echo "  export SERVER_USER=root"
    echo "  export SERVER_PORT=22"
    echo ""
    echo "或编辑此脚本修改 SERVER_HOST 变量"
    exit 1
fi

SSH_CMD="ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST"

echo ""
echo "============================================"
echo "   推送更新到云服务器"
echo "============================================"
echo ""
echo "服务器: $SERVER_USER@$SERVER_HOST:$SERVER_PORT"
echo ""

# ============================================
# 选择操作
# ============================================
echo "请选择操作:"
echo "  1) 完整更新 (git push + 服务器 pull + 重建)"
echo "  2) 仅推送代码 (git push)"
echo "  3) 仅更新服务器 (服务器 pull + 重建)"
echo "  4) 快速重启服务"
echo "  5) 查看服务器日志"
echo "  6) 查看服务器状态"
echo ""
read -p "请输入选项 [1-6]: " ACTION

case $ACTION in
    1)
        # 完整更新
        log_info "提交并推送本地更改..."
        git add -A
        git commit -m "Deploy update $(date +%Y%m%d_%H%M%S)" || true
        git push origin master

        log_info "更新服务器..."
        $SSH_CMD "cd $INSTALL_DIR && ./apihub/deploy/update.sh"
        ;;

    2)
        # 仅推送代码
        log_info "提交并推送本地更改..."
        git add -A
        read -p "请输入提交信息: " COMMIT_MSG
        git commit -m "$COMMIT_MSG" || true
        git push origin master
        log_success "代码已推送，请在服务器上运行 update.sh"
        ;;

    3)
        # 仅更新服务器
        log_info "更新服务器..."
        $SSH_CMD "cd $INSTALL_DIR && ./apihub/deploy/update.sh"
        ;;

    4)
        # 快速重启
        log_info "重启服务..."
        $SSH_CMD "cd $INSTALL_DIR && docker compose restart || systemctl restart apihub-backend"
        log_success "服务已重启"
        ;;

    5)
        # 查看日志
        echo "选择日志:"
        echo "  1) 后端日志"
        echo "  2) 前端日志"
        echo "  3) CLIProxyAPI 日志"
        echo "  4) 所有日志"
        read -p "请选择 [1-4]: " LOG_CHOICE

        case $LOG_CHOICE in
            1) $SSH_CMD "cd $INSTALL_DIR && docker compose logs -f apihub-backend --tail=100 || journalctl -u apihub-backend -f" ;;
            2) $SSH_CMD "cd $INSTALL_DIR && docker compose logs -f apihub-frontend --tail=100" ;;
            3) $SSH_CMD "cd $INSTALL_DIR && docker compose logs -f cliproxy --tail=100 || journalctl -u cliproxy -f" ;;
            4) $SSH_CMD "cd $INSTALL_DIR && docker compose logs -f --tail=50" ;;
        esac
        ;;

    6)
        # 查看状态
        log_info "服务器状态:"
        $SSH_CMD "cd $INSTALL_DIR && docker compose ps 2>/dev/null || systemctl status apihub-backend cliproxy --no-pager"
        echo ""
        log_info "健康检查:"
        $SSH_CMD "curl -s http://127.0.0.1:8000/health || echo '服务未响应'"
        ;;

    *)
        log_error "无效选项"
        exit 1
        ;;
esac

echo ""
log_success "操作完成！"
