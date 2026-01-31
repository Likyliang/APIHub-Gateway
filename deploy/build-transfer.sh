#!/bin/bash
# ============================================
# 本地构建并直接传输到服务器 (不需要 Docker Hub)
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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "============================================"
echo "   本地构建并传输到服务器"
echo "============================================"
echo ""

# 检查服务器配置
if [ "$SERVER_HOST" == "your-server-ip" ]; then
    echo "请设置服务器信息后再运行:"
    echo ""
    echo "  export SERVER_HOST=你的服务器IP"
    echo "  export SERVER_USER=root"
    echo "  ./deploy/build-transfer.sh"
    echo ""
    exit 1
fi

SSH_CMD="ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST"
SCP_CMD="scp -P $SERVER_PORT"

echo "服务器: $SERVER_USER@$SERVER_HOST"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "本地未安装 Docker"
    exit 1
fi

cd "$PROJECT_DIR"

# ============================================
# 构建镜像
# ============================================
log_info "构建后端镜像..."
docker build -t apihub-backend:latest ./backend
log_success "后端镜像构建完成"

log_info "构建前端镜像..."
docker build -t apihub-frontend:latest ./frontend
log_success "前端镜像构建完成"

# ============================================
# 导出镜像为文件
# ============================================
log_info "导出镜像文件..."
mkdir -p /tmp/apihub-images

docker save apihub-backend:latest | gzip > /tmp/apihub-images/backend.tar.gz
log_success "后端镜像已导出 ($(du -h /tmp/apihub-images/backend.tar.gz | cut -f1))"

docker save apihub-frontend:latest | gzip > /tmp/apihub-images/frontend.tar.gz
log_success "前端镜像已导出 ($(du -h /tmp/apihub-images/frontend.tar.gz | cut -f1))"

# ============================================
# 传输到服务器
# ============================================
log_info "传输镜像到服务器..."
$SSH_CMD "mkdir -p $INSTALL_DIR/images"

$SCP_CMD /tmp/apihub-images/backend.tar.gz $SERVER_USER@$SERVER_HOST:$INSTALL_DIR/images/
log_success "后端镜像已传输"

$SCP_CMD /tmp/apihub-images/frontend.tar.gz $SERVER_USER@$SERVER_HOST:$INSTALL_DIR/images/
log_success "前端镜像已传输"

# ============================================
# 在服务器上加载镜像
# ============================================
log_info "在服务器上加载镜像..."

$SSH_CMD << 'REMOTE_EOF'
cd /opt/apihub

echo "加载后端镜像..."
gunzip -c images/backend.tar.gz | docker load

echo "加载前端镜像..."
gunzip -c images/frontend.tar.gz | docker load

echo "清理镜像文件..."
rm -rf images/

echo "镜像加载完成!"
docker images | grep apihub
REMOTE_EOF

# ============================================
# 创建/更新 docker-compose.yml
# ============================================
log_info "配置服务器 docker-compose..."

$SSH_CMD << 'COMPOSE_EOF'
cd /opt/apihub
mkdir -p data

# 创建 docker-compose.yml (使用本地镜像)
cat > docker-compose.yml << 'YAML_EOF'
version: '3.8'

services:
  apihub-backend:
    image: apihub-backend:latest
    container_name: apihub-backend
    restart: unless-stopped
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/apihub.db
      - SECRET_KEY=${SECRET_KEY}
      - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
      - ADMIN_EMAIL=${ADMIN_EMAIL:-admin@apihub.local}
      - UPSTREAM_URL=${UPSTREAM_URL:-http://cli-proxy-api:8317}
      - UPSTREAM_API_KEY=${UPSTREAM_API_KEY:-}
      - EPAY_URL=${EPAY_URL:-}
      - EPAY_PID=${EPAY_PID:-}
      - EPAY_KEY=${EPAY_KEY:-}
    volumes:
      - ./data:/data
    expose:
      - "8000"
    networks:
      - nginx-proxy-manager_default
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  apihub-frontend:
    image: apihub-frontend:latest
    container_name: apihub-frontend
    restart: unless-stopped
    expose:
      - "80"
    depends_on:
      - apihub-backend
    networks:
      - nginx-proxy-manager_default
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

networks:
  nginx-proxy-manager_default:
    external: true
YAML_EOF

# 创建 .env 如果不存在
if [ ! -f ".env" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    cat > .env << ENV_EOF
SECRET_KEY=$SECRET_KEY
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_EMAIL=admin@yourdomain.com
UPSTREAM_URL=http://cli-proxy-api:8317
UPSTREAM_API_KEY=
EPAY_URL=
EPAY_PID=
EPAY_KEY=
ENV_EOF
    chmod 600 .env
    echo "已创建 .env 文件，请修改管理员密码!"
fi

echo "配置完成!"
COMPOSE_EOF

# ============================================
# 启动服务
# ============================================
log_info "启动服务..."
$SSH_CMD "cd $INSTALL_DIR && docker compose down 2>/dev/null || true && docker compose up -d"

# 等待启动
sleep 5

log_info "验证服务状态..."
$SSH_CMD "cd $INSTALL_DIR && docker compose ps"

# 清理本地临时文件
rm -rf /tmp/apihub-images

echo ""
log_success "部署完成!"
echo ""
echo "后续步骤:"
echo "  1. SSH 到服务器修改密码:"
echo "     ssh $SERVER_USER@$SERVER_HOST"
echo "     nano $INSTALL_DIR/.env"
echo "     cd $INSTALL_DIR && docker compose restart"
echo ""
echo "  2. 在 Nginx Proxy Manager 添加代理:"
echo "     - Forward Hostname: apihub-frontend"
echo "     - Forward Port: 80"
echo ""
echo "下次更新只需再次运行此脚本即可!"
echo ""
