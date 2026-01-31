#!/bin/bash
# ============================================
# APIHub-Gateway + CLIProxyAPI 卸载脚本
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

INSTALL_DIR="/opt/apihub"

echo ""
echo "============================================"
echo "   APIHub-Gateway 卸载程序"
echo "============================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行此脚本: sudo ./uninstall.sh"
    exit 1
fi

# 确认卸载
echo -e "${YELLOW}警告: 此操作将删除 APIHub-Gateway 和所有相关数据！${NC}"
echo ""
read -p "是否保留数据库和配置文件？[y/N]: " KEEP_DATA
read -p "确定要卸载吗？输入 'YES' 确认: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    log_info "已取消卸载"
    exit 0
fi

# ============================================
# 停止并移除服务
# ============================================
log_info "停止服务..."

# Docker 方式
if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
    cd $INSTALL_DIR
    docker compose down --rmi local -v 2>/dev/null || docker-compose down --rmi local -v 2>/dev/null || true
    log_success "Docker 容器已停止并移除"
fi

# Systemd 服务
for service in apihub apihub-backend cliproxy; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        systemctl stop $service
        log_info "已停止 $service"
    fi
    if [ -f "/etc/systemd/system/$service.service" ]; then
        systemctl disable $service 2>/dev/null || true
        rm -f /etc/systemd/system/$service.service
        log_info "已移除 $service 服务"
    fi
done

systemctl daemon-reload

# ============================================
# 移除 Nginx 配置
# ============================================
if [ -f "/etc/nginx/sites-enabled/apihub" ]; then
    rm -f /etc/nginx/sites-enabled/apihub
    rm -f /etc/nginx/sites-available/apihub
    systemctl reload nginx 2>/dev/null || true
    log_info "已移除 Nginx 配置"
fi

# ============================================
# 备份或删除数据
# ============================================
if [ "$KEEP_DATA" == "y" ] || [ "$KEEP_DATA" == "Y" ]; then
    BACKUP_DIR="/opt/apihub-backup-$(date +%Y%m%d_%H%M%S)"
    log_info "备份数据到 $BACKUP_DIR..."
    mkdir -p $BACKUP_DIR

    # 备份数据库
    if [ -d "$INSTALL_DIR/data" ]; then
        cp -r $INSTALL_DIR/data $BACKUP_DIR/
    fi

    # 备份配置
    if [ -f "$INSTALL_DIR/.env" ]; then
        cp $INSTALL_DIR/.env $BACKUP_DIR/
    fi
    if [ -f "$INSTALL_DIR/apihub/backend/.env" ]; then
        cp $INSTALL_DIR/apihub/backend/.env $BACKUP_DIR/backend.env
    fi
    if [ -f "$INSTALL_DIR/cliproxy/config.yaml" ]; then
        cp $INSTALL_DIR/cliproxy/config.yaml $BACKUP_DIR/
    fi
    if [ -d "$INSTALL_DIR/cliproxy/auths" ]; then
        cp -r $INSTALL_DIR/cliproxy/auths $BACKUP_DIR/
    fi

    log_success "数据已备份到 $BACKUP_DIR"
fi

# ============================================
# 删除安装目录
# ============================================
log_info "删除安装目录..."
rm -rf $INSTALL_DIR

# ============================================
# 清理 Docker 资源 (可选)
# ============================================
echo ""
read -p "是否清理未使用的 Docker 镜像？[y/N]: " CLEAN_DOCKER
if [ "$CLEAN_DOCKER" == "y" ] || [ "$CLEAN_DOCKER" == "Y" ]; then
    docker system prune -f 2>/dev/null || true
    log_success "Docker 资源已清理"
fi

echo ""
log_success "卸载完成！"
echo ""

if [ "$KEEP_DATA" == "y" ] || [ "$KEEP_DATA" == "Y" ]; then
    echo "数据备份位置: $BACKUP_DIR"
    echo ""
    echo "如需重新安装并恢复数据，请将备份文件复制回相应位置"
fi
