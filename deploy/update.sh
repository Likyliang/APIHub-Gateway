#!/bin/bash
# ============================================
# APIHub-Gateway + CLIProxyAPI 更新脚本
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
echo "   APIHub-Gateway 更新程序"
echo "============================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行此脚本: sudo ./update.sh"
    exit 1
fi

# 检查安装目录
if [ ! -d "$INSTALL_DIR" ]; then
    log_error "未找到安装目录 $INSTALL_DIR，请先运行 install.sh"
    exit 1
fi

cd $INSTALL_DIR

# ============================================
# 检测部署方式
# ============================================
if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
    DEPLOY_METHOD="docker"
    log_info "检测到 Docker 部署方式"
else
    DEPLOY_METHOD="direct"
    log_info "检测到直接安装方式"
fi

# ============================================
# 备份当前配置
# ============================================
log_info "备份当前配置..."
BACKUP_DIR="$INSTALL_DIR/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

if [ "$DEPLOY_METHOD" == "docker" ]; then
    cp -r $INSTALL_DIR/.env $BACKUP_DIR/ 2>/dev/null || true
    cp -r $INSTALL_DIR/cliproxy/config.yaml $BACKUP_DIR/ 2>/dev/null || true
    cp -r $INSTALL_DIR/data $BACKUP_DIR/ 2>/dev/null || true
else
    cp -r $INSTALL_DIR/apihub/backend/.env $BACKUP_DIR/ 2>/dev/null || true
    cp -r $INSTALL_DIR/cliproxy/config.yaml $BACKUP_DIR/ 2>/dev/null || true
    cp -r $INSTALL_DIR/data $BACKUP_DIR/ 2>/dev/null || true
fi
log_success "配置已备份到 $BACKUP_DIR"

# ============================================
# 停止服务
# ============================================
log_info "停止服务..."
if [ "$DEPLOY_METHOD" == "docker" ]; then
    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
else
    systemctl stop apihub-backend 2>/dev/null || true
    systemctl stop cliproxy 2>/dev/null || true
fi

# ============================================
# 更新代码
# ============================================
log_info "更新 APIHub-Gateway 代码..."
cd $INSTALL_DIR/apihub

# 保存本地修改
git stash 2>/dev/null || true

# 拉取最新代码
git fetch origin
git reset --hard origin/master

log_success "代码更新完成"

# ============================================
# 重建/重新部署
# ============================================
if [ "$DEPLOY_METHOD" == "docker" ]; then
    log_info "重建 Docker 镜像..."
    cd $INSTALL_DIR

    # 重建镜像
    docker compose build --no-cache apihub-backend apihub-frontend

    log_info "启动服务..."
    docker compose up -d

    # 清理旧镜像
    log_info "清理旧镜像..."
    docker image prune -f

else
    # 更新后端依赖
    log_info "更新后端依赖..."
    cd $INSTALL_DIR/apihub/backend
    source venv/bin/activate
    pip install -r requirements.txt -q

    # 恢复环境变量
    if [ -f "$BACKUP_DIR/.env" ]; then
        cp $BACKUP_DIR/.env $INSTALL_DIR/apihub/backend/.env
    fi

    # 重建前端
    log_info "重建前端..."
    cd $INSTALL_DIR/apihub/frontend
    npm install --silent
    npm run build

    # 启动服务
    log_info "启动服务..."
    systemctl start cliproxy
    sleep 2
    systemctl start apihub-backend
fi

# ============================================
# 验证服务状态
# ============================================
log_info "验证服务状态..."
sleep 5

if [ "$DEPLOY_METHOD" == "docker" ]; then
    if docker compose ps | grep -q "Up"; then
        log_success "服务运行正常"
    else
        log_error "服务启动失败，请检查日志: docker compose logs"
        exit 1
    fi
else
    if systemctl is-active --quiet apihub-backend; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务启动失败"
        journalctl -u apihub-backend -n 20
        exit 1
    fi
fi

# 测试健康检查
log_info "测试健康检查..."
if curl -s http://127.0.0.1:8000/health | grep -q "healthy"; then
    log_success "健康检查通过"
else
    log_warn "健康检查未响应，服务可能仍在启动中"
fi

echo ""
log_success "更新完成！"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
echo "如需回滚，请运行:"
echo "  ./rollback.sh $BACKUP_DIR"
echo ""
