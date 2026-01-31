#!/bin/bash
# ============================================
# APIHub-Gateway + CLIProxyAPI 安装脚本
# 适用于 Ubuntu/Debian 云服务器
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
CLIPROXY_REPO="https://github.com/anthropics/claude-code-sastic/CLIProxyAPI.git"
APIHUB_REPO="https://github.com/Likyliang/APIHub-Gateway.git"
GO_VERSION="1.22.0"

echo ""
echo "============================================"
echo "   APIHub-Gateway + CLIProxyAPI 安装程序"
echo "============================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行此脚本: sudo ./install.sh"
    exit 1
fi

# ============================================
# 1. 选择部署方式
# ============================================
echo "请选择部署方式："
echo "  1) Docker 部署 (推荐，更简单)"
echo "  2) 直接安装 (需要手动管理依赖)"
echo ""
read -p "请输入选项 [1/2]: " DEPLOY_METHOD

if [ "$DEPLOY_METHOD" != "1" ] && [ "$DEPLOY_METHOD" != "2" ]; then
    DEPLOY_METHOD="1"
fi

# ============================================
# 2. 安装基础依赖
# ============================================
log_info "安装基础依赖..."
apt-get update -qq
apt-get install -y -qq git curl wget

# ============================================
# 3. 创建目录结构
# ============================================
log_info "创建目录结构..."
mkdir -p $INSTALL_DIR/{cliproxy,apihub,data,logs}
cd $INSTALL_DIR

# ============================================
# Docker 部署
# ============================================
if [ "$DEPLOY_METHOD" == "1" ]; then
    log_info "使用 Docker 部署..."

    # 安装 Docker
    if ! command -v docker &> /dev/null; then
        log_info "安装 Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
    else
        log_success "Docker 已安装"
    fi

    # 安装 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_info "安装 Docker Compose..."
        apt-get install -y -qq docker-compose-plugin || \
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
        chmod +x /usr/local/bin/docker-compose
    else
        log_success "Docker Compose 已安装"
    fi

    # 克隆 APIHub-Gateway
    log_info "克隆 APIHub-Gateway..."
    if [ -d "$INSTALL_DIR/apihub/.git" ]; then
        cd $INSTALL_DIR/apihub && git pull
    else
        rm -rf $INSTALL_DIR/apihub
        git clone $APIHUB_REPO $INSTALL_DIR/apihub
    fi

    # 创建统一的 docker-compose.yml
    log_info "创建 Docker Compose 配置..."
    cat > $INSTALL_DIR/docker-compose.yml << 'DOCKER_EOF'
version: '3.8'

services:
  # CLIProxyAPI - 上游服务
  cliproxy:
    image: ghcr.io/anthropics/cliproxyapi:latest
    container_name: cliproxy
    restart: unless-stopped
    volumes:
      - ./cliproxy/config.yaml:/app/config.yaml:ro
      - ./cliproxy/auths:/app/auths
    ports:
      - "127.0.0.1:8317:8317"
    networks:
      - apihub-network

  # APIHub-Gateway 后端
  apihub-backend:
    build: ./apihub/backend
    container_name: apihub-backend
    restart: unless-stopped
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/apihub.db
      - SECRET_KEY=${SECRET_KEY}
      - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
      - ADMIN_EMAIL=${ADMIN_EMAIL:-admin@apihub.local}
      - UPSTREAM_URL=http://cliproxy:8317
      - UPSTREAM_API_KEY=${UPSTREAM_API_KEY:-}
      - EPAY_URL=${EPAY_URL:-}
      - EPAY_PID=${EPAY_PID:-}
      - EPAY_KEY=${EPAY_KEY:-}
    volumes:
      - ./data:/data
    depends_on:
      - cliproxy
    networks:
      - apihub-network

  # APIHub-Gateway 前端
  apihub-frontend:
    build: ./apihub/frontend
    container_name: apihub-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      - apihub-backend
    networks:
      - apihub-network

  # Nginx 反向代理 (可选，用于生产环境 HTTPS)
  nginx:
    image: nginx:alpine
    container_name: apihub-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - apihub-frontend
    networks:
      - apihub-network
    profiles:
      - production

networks:
  apihub-network:
    driver: bridge
DOCKER_EOF

    # 创建环境变量文件
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        log_info "创建环境变量配置..."
        SECRET_KEY=$(openssl rand -hex 32)
        cat > $INSTALL_DIR/.env << ENV_EOF
# APIHub-Gateway 配置
SECRET_KEY=$SECRET_KEY
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_EMAIL=admin@yourdomain.com

# 上游 API Key (如果 CLIProxyAPI 需要认证)
UPSTREAM_API_KEY=

# 易支付配置 (可选)
EPAY_URL=
EPAY_PID=
EPAY_KEY=
ENV_EOF
        chmod 600 $INSTALL_DIR/.env
        log_warn "请编辑 $INSTALL_DIR/.env 修改管理员密码！"
    fi

    # 创建 CLIProxyAPI 配置目录
    mkdir -p $INSTALL_DIR/cliproxy/auths
    if [ ! -f "$INSTALL_DIR/cliproxy/config.yaml" ]; then
        log_info "创建 CLIProxyAPI 配置..."
        cat > $INSTALL_DIR/cliproxy/config.yaml << 'CONFIG_EOF'
# CLIProxyAPI 配置
# 详细配置请参考: https://github.com/anthropics/claude-code-sastic/CLIProxyAPI

server:
  host: 0.0.0.0
  port: 8317

# 添加你的 AI 服务账户配置
# 例如:
# gemini:
#   accounts:
#     - auth_file: auths/gemini_account1.json
#
# claude:
#   accounts:
#     - auth_file: auths/claude_account1.json
CONFIG_EOF
        log_warn "请编辑 $INSTALL_DIR/cliproxy/config.yaml 添加 AI 账户配置！"
    fi

    # 创建 Nginx 配置 (用于生产环境)
    mkdir -p $INSTALL_DIR/nginx/ssl
    cat > $INSTALL_DIR/nginx/nginx.conf << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream frontend {
        server apihub-frontend:80;
    }

    server {
        listen 80;
        server_name _;

        # 重定向到 HTTPS (生产环境取消注释)
        # return 301 https://$host$request_uri;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_buffering off;
        }
    }

    # HTTPS 配置 (生产环境取消注释并配置证书)
    # server {
    #     listen 443 ssl http2;
    #     server_name yourdomain.com;
    #
    #     ssl_certificate /etc/nginx/ssl/fullchain.pem;
    #     ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    #
    #     location / {
    #         proxy_pass http://frontend;
    #         # ... 同上
    #     }
    # }
}
NGINX_EOF

    # 创建 systemd 服务
    log_info "创建系统服务..."
    cat > /etc/systemd/system/apihub.service << 'SERVICE_EOF'
[Unit]
Description=APIHub-Gateway with CLIProxyAPI
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/apihub
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    systemctl daemon-reload
    systemctl enable apihub

    log_success "Docker 部署配置完成！"
    echo ""
    echo "后续步骤："
    echo "  1. 编辑配置文件:"
    echo "     - $INSTALL_DIR/.env (修改管理员密码)"
    echo "     - $INSTALL_DIR/cliproxy/config.yaml (添加 AI 账户)"
    echo ""
    echo "  2. 启动服务:"
    echo "     cd $INSTALL_DIR && docker compose up -d"
    echo "     或: systemctl start apihub"
    echo ""
    echo "  3. 访问:"
    echo "     - 前端: http://your-server-ip:3000"
    echo "     - API: http://your-server-ip:3000/v1/..."
    echo ""

# ============================================
# 直接安装
# ============================================
else
    log_info "使用直接安装方式..."

    # 安装 Go
    if ! command -v go &> /dev/null; then
        log_info "安装 Go $GO_VERSION..."
        wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
        rm -rf /usr/local/go
        tar -C /usr/local -xzf /tmp/go.tar.gz
        echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile
        export PATH=$PATH:/usr/local/go/bin
    fi
    log_success "Go 已安装: $(go version)"

    # 安装 Python
    if ! command -v python3 &> /dev/null; then
        log_info "安装 Python..."
        apt-get install -y -qq python3 python3-pip python3-venv
    fi
    log_success "Python 已安装: $(python3 --version)"

    # 安装 Node.js
    if ! command -v node &> /dev/null; then
        log_info "安装 Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y -qq nodejs
    fi
    log_success "Node.js 已安装: $(node --version)"

    # 克隆 CLIProxyAPI
    log_info "克隆 CLIProxyAPI..."
    if [ -d "$INSTALL_DIR/cliproxy/.git" ]; then
        cd $INSTALL_DIR/cliproxy && git pull
    else
        rm -rf $INSTALL_DIR/cliproxy
        # 注意: 替换为实际的 CLIProxyAPI 仓库地址
        git clone https://github.com/anthropics/CLIProxyAPI.git $INSTALL_DIR/cliproxy || \
        log_warn "CLIProxyAPI 仓库克隆失败，请手动下载"
    fi

    # 克隆 APIHub-Gateway
    log_info "克隆 APIHub-Gateway..."
    if [ -d "$INSTALL_DIR/apihub/.git" ]; then
        cd $INSTALL_DIR/apihub && git pull
    else
        rm -rf $INSTALL_DIR/apihub
        git clone $APIHUB_REPO $INSTALL_DIR/apihub
    fi

    # 构建 CLIProxyAPI
    log_info "构建 CLIProxyAPI..."
    cd $INSTALL_DIR/cliproxy
    export GOPROXY="https://goproxy.cn,direct"
    go build -o server ./cmd/server 2>&1 || log_warn "CLIProxyAPI 构建失败"

    # 安装 APIHub-Gateway 后端依赖
    log_info "安装 APIHub-Gateway 后端依赖..."
    cd $INSTALL_DIR/apihub/backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q

    # 复制环境变量文件
    if [ ! -f ".env" ]; then
        cp .env.example .env
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i "s/your-super-secret-key-change-in-production/$SECRET_KEY/" .env
        log_warn "请编辑 $INSTALL_DIR/apihub/backend/.env 修改配置！"
    fi

    # 构建前端
    log_info "构建 APIHub-Gateway 前端..."
    cd $INSTALL_DIR/apihub/frontend
    npm install --silent
    npm run build

    # 创建 systemd 服务 - CLIProxyAPI
    cat > /etc/systemd/system/cliproxy.service << 'SERVICE_EOF'
[Unit]
Description=CLIProxyAPI Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/apihub/cliproxy
ExecStart=/opt/apihub/cliproxy/server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    # 创建 systemd 服务 - APIHub Backend
    cat > /etc/systemd/system/apihub-backend.service << 'SERVICE_EOF'
[Unit]
Description=APIHub-Gateway Backend
After=network.target cliproxy.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/apihub/apihub/backend
Environment="PATH=/opt/apihub/apihub/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/apihub/apihub/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    # 安装 Nginx
    if ! command -v nginx &> /dev/null; then
        apt-get install -y -qq nginx
    fi

    # 配置 Nginx
    cat > /etc/nginx/sites-available/apihub << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    root /opt/apihub/apihub/frontend/dist;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    # OpenAI compatible API
    location /v1/ {
        proxy_pass http://127.0.0.1:8000/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX_EOF

    ln -sf /etc/nginx/sites-available/apihub /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx

    systemctl daemon-reload
    systemctl enable cliproxy apihub-backend nginx

    log_success "直接安装完成！"
    echo ""
    echo "后续步骤："
    echo "  1. 编辑配置文件:"
    echo "     - $INSTALL_DIR/cliproxy/config.yaml (添加 AI 账户)"
    echo "     - $INSTALL_DIR/apihub/backend/.env (修改管理员密码)"
    echo ""
    echo "  2. 启动服务:"
    echo "     systemctl start cliproxy apihub-backend"
    echo ""
    echo "  3. 访问:"
    echo "     - 前端: http://your-server-ip"
    echo "     - API: http://your-server-ip/v1/..."
    echo ""
fi

log_success "安装完成！"
