#!/bin/bash
# ============================================
# APIHub-Gateway 安装脚本 (集成到现有 CLIProxyAPI)
# 适用于已有 Docker CLIProxyAPI 的服务器
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

# 配置
INSTALL_DIR="/opt/apihub"
APIHUB_REPO="https://github.com/Likyliang/APIHub-Gateway.git"

# 检测现有的 CLIProxyAPI 配置
CLIPROXY_CONTAINER="cli-proxy-api"
CLIPROXY_NETWORK="nginx-proxy-manager_default"

echo ""
echo "============================================"
echo "   APIHub-Gateway 安装程序"
echo "   (集成到现有 CLIProxyAPI Docker 环境)"
echo "============================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行: sudo ./install-existing.sh"
    exit 1
fi

# 检测现有 CLIProxyAPI
log_info "检测现有 CLIProxyAPI..."
if docker ps | grep -q "$CLIPROXY_CONTAINER"; then
    log_success "检测到 CLIProxyAPI 容器正在运行"

    # 获取容器所在的网络
    DETECTED_NETWORK=$(docker inspect $CLIPROXY_CONTAINER --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' | head -1)
    if [ -n "$DETECTED_NETWORK" ]; then
        CLIPROXY_NETWORK=$DETECTED_NETWORK
        log_info "检测到网络: $CLIPROXY_NETWORK"
    fi
else
    log_warn "未检测到运行中的 CLIProxyAPI 容器"
    log_warn "将使用默认配置连接到 cli-proxy-api:8317"
fi

# ============================================
# 安装基础依赖
# ============================================
log_info "安装基础依赖..."
apt-get update -qq
apt-get install -y -qq git curl

# ============================================
# 创建目录并克隆代码
# ============================================
log_info "创建安装目录..."
mkdir -p $INSTALL_DIR/{data,logs}

log_info "克隆 APIHub-Gateway..."
if [ -d "$INSTALL_DIR/apihub/.git" ]; then
    cd $INSTALL_DIR/apihub && git pull
else
    rm -rf $INSTALL_DIR/apihub
    git clone $APIHUB_REPO $INSTALL_DIR/apihub
fi

# ============================================
# 创建环境变量文件
# ============================================
if [ ! -f "$INSTALL_DIR/.env" ]; then
    log_info "创建环境变量配置..."
    SECRET_KEY=$(openssl rand -hex 32)
    cat > $INSTALL_DIR/.env << ENV_EOF
# APIHub-Gateway 配置
# 生成时间: $(date)

# 安全密钥 (已自动生成)
SECRET_KEY=$SECRET_KEY

# 管理员账户 (请修改默认密码!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_EMAIL=admin@yourdomain.com

# 上游 CLIProxyAPI 配置
# 容器内部连接使用容器名
UPSTREAM_URL=http://$CLIPROXY_CONTAINER:8317

# 上游 API Key (如果 CLIProxyAPI 配置了认证则填写)
UPSTREAM_API_KEY=

# 易支付配置 (可选，用于在线充值)
EPAY_URL=
EPAY_PID=
EPAY_KEY=
ENV_EOF
    chmod 600 $INSTALL_DIR/.env
    log_warn "请编辑 $INSTALL_DIR/.env 修改管理员密码！"
fi

# ============================================
# 创建 Docker Compose 配置
# ============================================
log_info "创建 Docker Compose 配置..."
cat > $INSTALL_DIR/docker-compose.yml << DOCKER_EOF
version: '3.8'

services:
  # APIHub-Gateway 后端
  apihub-backend:
    build: ./apihub/backend
    container_name: apihub-backend
    restart: unless-stopped
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/apihub.db
      - SECRET_KEY=\${SECRET_KEY}
      - ADMIN_USERNAME=\${ADMIN_USERNAME:-admin}
      - ADMIN_PASSWORD=\${ADMIN_PASSWORD:-admin123}
      - ADMIN_EMAIL=\${ADMIN_EMAIL:-admin@apihub.local}
      - UPSTREAM_URL=\${UPSTREAM_URL:-http://$CLIPROXY_CONTAINER:8317}
      - UPSTREAM_API_KEY=\${UPSTREAM_API_KEY:-}
      - EPAY_URL=\${EPAY_URL:-}
      - EPAY_PID=\${EPAY_PID:-}
      - EPAY_KEY=\${EPAY_KEY:-}
    volumes:
      - ./data:/data
      - ./logs:/app/logs
    expose:
      - "8000"
    networks:
      - $CLIPROXY_NETWORK
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  # APIHub-Gateway 前端
  apihub-frontend:
    build: ./apihub/frontend
    container_name: apihub-frontend
    restart: unless-stopped
    # 如果使用 Nginx Proxy Manager，只需要 expose
    # 如果直接访问，改为 ports: - "3000:80"
    expose:
      - "80"
    # 直接访问时使用这个:
    # ports:
    #   - "3000:80"
    depends_on:
      - apihub-backend
    networks:
      - $CLIPROXY_NETWORK
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

networks:
  $CLIPROXY_NETWORK:
    external: true
DOCKER_EOF

# ============================================
# 修复前端 nginx 配置以使用容器名
# ============================================
log_info "配置前端反向代理..."
cat > $INSTALL_DIR/apihub/frontend/nginx.conf << 'NGINX_EOF'
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # API proxy - 使用容器名
    location /api/ {
        proxy_pass http://apihub-backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    # OpenAI compatible API endpoints
    location /v1/ {
        proxy_pass http://apihub-backend:8000/v1/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    # Health check
    location /health {
        proxy_pass http://apihub-backend:8000/health;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
NGINX_EOF

# ============================================
# 构建并启动
# ============================================
log_info "构建 Docker 镜像..."
cd $INSTALL_DIR
docker compose build

log_info "启动服务..."
docker compose up -d

# ============================================
# 验证
# ============================================
log_info "等待服务启动..."
sleep 10

log_info "验证服务状态..."
docker compose ps

# 测试健康检查
if docker exec apihub-backend curl -s http://localhost:8000/health 2>/dev/null | grep -q "healthy"; then
    log_success "后端服务正常"
else
    log_warn "后端服务可能仍在启动中"
fi

echo ""
echo "============================================"
log_success "安装完成！"
echo "============================================"
echo ""
echo "后续步骤:"
echo ""
echo "1. 修改管理员密码:"
echo "   nano $INSTALL_DIR/.env"
echo "   然后重启: cd $INSTALL_DIR && docker compose restart"
echo ""
echo "2. 在 Nginx Proxy Manager 中添加代理:"
echo "   - 域名: api.yourdomain.com (或你的域名)"
echo "   - Forward Hostname: apihub-frontend"
echo "   - Forward Port: 80"
echo "   - 启用 Websockets Support"
echo ""
echo "3. 或者直接访问 (需要修改 docker-compose.yml 开放端口):"
echo "   - 前端: http://服务器IP:3000"
echo ""
echo "4. 查看日志:"
echo "   cd $INSTALL_DIR && docker compose logs -f"
echo ""
echo "5. 默认管理员账户:"
echo "   用户名: admin"
echo "   密码: changeme123 (请立即修改!)"
echo ""
