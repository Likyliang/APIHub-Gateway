#!/bin/bash
# ============================================
# APIHub-Gateway 回滚脚本
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
BACKUP_DIR="$1"

echo ""
echo "============================================"
echo "   APIHub-Gateway 回滚程序"
echo "============================================"
echo ""

# 检查参数
if [ -z "$BACKUP_DIR" ]; then
    echo "用法: ./rollback.sh <备份目录>"
    echo ""
    echo "可用的备份:"
    ls -la $INSTALL_DIR/backups/ 2>/dev/null || echo "  无备份"
    exit 1
fi

# 检查备份目录
if [ ! -d "$BACKUP_DIR" ]; then
    log_error "备份目录不存在: $BACKUP_DIR"
    exit 1
fi

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行此脚本: sudo ./rollback.sh $BACKUP_DIR"
    exit 1
fi

log_info "从备份恢复: $BACKUP_DIR"

# ============================================
# 停止服务
# ============================================
log_info "停止服务..."
if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
    cd $INSTALL_DIR
    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
else
    systemctl stop apihub-backend 2>/dev/null || true
fi

# ============================================
# 恢复配置文件
# ============================================
log_info "恢复配置文件..."

if [ -f "$BACKUP_DIR/.env" ]; then
    cp $BACKUP_DIR/.env $INSTALL_DIR/.env
    log_success "恢复 .env"
fi

if [ -f "$BACKUP_DIR/backend.env" ]; then
    cp $BACKUP_DIR/backend.env $INSTALL_DIR/apihub/backend/.env
    log_success "恢复 backend/.env"
fi

if [ -f "$BACKUP_DIR/config.yaml" ]; then
    cp $BACKUP_DIR/config.yaml $INSTALL_DIR/cliproxy/config.yaml
    log_success "恢复 cliproxy/config.yaml"
fi

# ============================================
# 恢复数据库
# ============================================
if [ -d "$BACKUP_DIR/data" ]; then
    log_info "恢复数据库..."
    rm -rf $INSTALL_DIR/data
    cp -r $BACKUP_DIR/data $INSTALL_DIR/data
    log_success "数据库已恢复"
fi

# ============================================
# 恢复认证文件
# ============================================
if [ -d "$BACKUP_DIR/auths" ]; then
    log_info "恢复认证文件..."
    cp -r $BACKUP_DIR/auths/* $INSTALL_DIR/cliproxy/auths/
    log_success "认证文件已恢复"
fi

# ============================================
# 重启服务
# ============================================
log_info "启动服务..."
if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
    cd $INSTALL_DIR
    docker compose up -d
else
    systemctl start cliproxy 2>/dev/null || true
    sleep 2
    systemctl start apihub-backend
fi

# ============================================
# 验证
# ============================================
sleep 5
log_info "验证服务状态..."

if curl -s http://127.0.0.1:8000/health | grep -q "healthy"; then
    log_success "服务恢复正常"
else
    log_warn "服务可能仍在启动中，请稍后检查"
fi

echo ""
log_success "回滚完成！"
