#!/bin/bash
# ============================================
# 服务器快速部署脚本 (使用预构建镜像)
# 在云服务器上运行
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
echo "   APIHub-Gateway 快速部署 (预构建镜像)"
echo "============================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行: sudo ./deploy-server.sh"
    exit 1
fi

# 创建目录
mkdir -p $INSTALL_DIR/data

cd $INSTALL_DIR

# 下载 docker-compose 文件
log_info "下载配置文件..."
curl -sO https://raw.githubusercontent.com/Likyliang/APIHub-Gateway/master/deploy/docker-compose.server.yml
mv docker-compose.server.yml docker-compose.yml

# 创建环境变量文件
if [ ! -f ".env" ]; then
    log_info "创建环境变量配置..."
    SECRET_KEY=$(openssl rand -hex 32)
    cat > .env << EOF
# APIHub-Gateway 配置
SECRET_KEY=$SECRET_KEY
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_EMAIL=admin@yourdomain.com

# 上游 CLIProxyAPI (容器名)
UPSTREAM_URL=http://cli-proxy-api:8317
UPSTREAM_API_KEY=

# 易支付 (可选)
EPAY_URL=
EPAY_PID=
EPAY_KEY=
EOF
    chmod 600 .env
    log_warn "请编辑 .env 修改管理员密码!"
fi

# 拉取镜像
log_info "拉取 Docker 镜像..."
docker compose pull

# 启动服务
log_info "启动服务..."
docker compose up -d

# 验证
sleep 5
log_info "验证服务状态..."
docker compose ps

echo ""
log_success "部署完成!"
echo ""
echo "后续步骤:"
echo "  1. 编辑 $INSTALL_DIR/.env 修改密码"
echo "  2. 在 Nginx Proxy Manager 添加代理:"
echo "     - Forward Hostname: apihub-frontend"
echo "     - Forward Port: 80"
echo ""
echo "更新命令:"
echo "  cd $INSTALL_DIR && docker compose pull && docker compose up -d"
echo ""
