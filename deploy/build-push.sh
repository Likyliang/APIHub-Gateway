#!/bin/bash
# ============================================
# 本地构建并推送镜像到 Docker Hub
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
# 配置 (请修改为你的信息)
# ============================================
DOCKER_USERNAME="${DOCKER_USERNAME:-likyliang}"
IMAGE_NAME="apihub-gateway"
VERSION="${1:-latest}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "============================================"
echo "   本地构建并推送 Docker 镜像"
echo "============================================"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

# 检查登录状态
if ! docker info 2>/dev/null | grep -q "Username"; then
    log_info "请先登录 Docker Hub..."
    docker login
fi

cd "$PROJECT_DIR"

# ============================================
# 构建后端镜像
# ============================================
log_info "构建后端镜像..."
docker build -t $DOCKER_USERNAME/$IMAGE_NAME-backend:$VERSION ./backend
docker tag $DOCKER_USERNAME/$IMAGE_NAME-backend:$VERSION $DOCKER_USERNAME/$IMAGE_NAME-backend:latest
log_success "后端镜像构建完成"

# ============================================
# 构建前端镜像
# ============================================
log_info "构建前端镜像..."
docker build -t $DOCKER_USERNAME/$IMAGE_NAME-frontend:$VERSION ./frontend
docker tag $DOCKER_USERNAME/$IMAGE_NAME-frontend:$VERSION $DOCKER_USERNAME/$IMAGE_NAME-frontend:latest
log_success "前端镜像构建完成"

# ============================================
# 推送镜像
# ============================================
log_info "推送后端镜像..."
docker push $DOCKER_USERNAME/$IMAGE_NAME-backend:$VERSION
docker push $DOCKER_USERNAME/$IMAGE_NAME-backend:latest

log_info "推送前端镜像..."
docker push $DOCKER_USERNAME/$IMAGE_NAME-frontend:$VERSION
docker push $DOCKER_USERNAME/$IMAGE_NAME-frontend:latest

echo ""
log_success "镜像已推送到 Docker Hub!"
echo ""
echo "镜像地址:"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME-backend:$VERSION"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME-frontend:$VERSION"
echo ""
echo "在服务器上运行以下命令更新:"
echo "  cd /opt/apihub && docker compose pull && docker compose up -d"
echo ""
