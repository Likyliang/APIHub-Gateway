#!/bin/bash
# ============================================
# 本地构建并推送到 GitHub Container Registry
# 然后服务器从 GitHub 拉取镜像
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
# 配置
# ============================================
GITHUB_USERNAME="${GITHUB_USERNAME:-likyliang}"
REPO_NAME="apihub-gateway"
VERSION="${1:-latest}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

REGISTRY="ghcr.io"
IMAGE_PREFIX="$REGISTRY/$GITHUB_USERNAME/$REPO_NAME"

echo ""
echo "============================================"
echo "   构建并推送到 GitHub Container Registry"
echo "============================================"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

# ============================================
# 登录 GitHub Container Registry
# ============================================
log_info "检查 GitHub Container Registry 登录状态..."

if ! docker pull $REGISTRY/$GITHUB_USERNAME/test-auth 2>&1 | grep -q "unauthorized"; then
    log_info "尝试登录..."
    echo ""
    echo "请输入 GitHub Personal Access Token (需要 write:packages 权限)"
    echo "创建 Token: https://github.com/settings/tokens/new"
    echo "  - 勾选 'write:packages'"
    echo "  - 勾选 'read:packages'"
    echo "  - 勾选 'delete:packages' (可选)"
    echo ""
    read -sp "Token: " GITHUB_TOKEN
    echo ""

    echo $GITHUB_TOKEN | docker login $REGISTRY -u $GITHUB_USERNAME --password-stdin

    if [ $? -ne 0 ]; then
        log_error "登录失败，请检查 Token"
        exit 1
    fi
    log_success "登录成功"
fi

cd "$PROJECT_DIR"

# ============================================
# 构建镜像
# ============================================
log_info "构建后端镜像..."
docker build -t $IMAGE_PREFIX-backend:$VERSION ./backend
docker tag $IMAGE_PREFIX-backend:$VERSION $IMAGE_PREFIX-backend:latest
log_success "后端镜像构建完成"

log_info "构建前端镜像..."
docker build -t $IMAGE_PREFIX-frontend:$VERSION ./frontend
docker tag $IMAGE_PREFIX-frontend:$VERSION $IMAGE_PREFIX-frontend:latest
log_success "前端镜像构建完成"

# ============================================
# 推送镜像
# ============================================
log_info "推送后端镜像到 GitHub..."
docker push $IMAGE_PREFIX-backend:$VERSION
docker push $IMAGE_PREFIX-backend:latest

log_info "推送前端镜像到 GitHub..."
docker push $IMAGE_PREFIX-frontend:$VERSION
docker push $IMAGE_PREFIX-frontend:latest

echo ""
log_success "镜像已推送到 GitHub Container Registry!"
echo ""
echo "镜像地址:"
echo "  - $IMAGE_PREFIX-backend:$VERSION"
echo "  - $IMAGE_PREFIX-frontend:$VERSION"
echo ""
echo "============================================"
echo "在服务器上执行以下命令:"
echo "============================================"
echo ""
echo "# 1. 登录 GitHub Container Registry (只需一次)"
echo "echo 你的TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin"
echo ""
echo "# 2. 拉取并启动"
echo "cd /opt/apihub && docker compose pull && docker compose up -d"
echo ""
