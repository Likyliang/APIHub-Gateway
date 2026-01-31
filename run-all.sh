#!/bin/bash
# APIHub-Gateway + CLIProxyAPI 联合启动脚本
# 同时启动两个项目进行本地测试（无需 sudo）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIPROXY_DIR="$HOME/workspace/CLIProxyAPI-sastic"
APIHUB_DIR="$SCRIPT_DIR"

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

echo ""
echo "================================================"
echo "   APIHub-Gateway + CLIProxyAPI 联合测试"
echo "================================================"
echo ""

# 存储进程ID
CLIPROXY_PID=""
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    log_info "正在停止所有服务..."
    [ -n "$CLIPROXY_PID" ] && kill $CLIPROXY_PID 2>/dev/null
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================
# 1. 安装 Go 到用户目录（无需 sudo）
# ============================================
install_go_local() {
    GO_VERSION="1.24.0"
    GO_DIR="$HOME/.local/go"
    GO_ARCHIVE="go${GO_VERSION}.linux-amd64.tar.gz"

    if [ -x "$GO_DIR/bin/go" ]; then
        export PATH="$GO_DIR/bin:$PATH"
        export GOPATH="$HOME/go"
        # 使用国内 Go 代理，绕过本地代理
        export GOPROXY="https://goproxy.cn,direct"
        log_success "Go 已安装: $($GO_DIR/bin/go version)"
        return 0
    fi

    log_info "正在安装 Go 到 $GO_DIR ..."
    mkdir -p "$HOME/.local"
    cd /tmp

    # 临时禁用代理下载 Go
    if [ ! -f "$GO_ARCHIVE" ]; then
        log_info "下载 Go ${GO_VERSION}..."
        (unset HTTP_PROXY http_proxy HTTPS_PROXY https_proxy; wget -q --show-progress "https://go.dev/dl/$GO_ARCHIVE") || \
        wget -q --show-progress "https://mirrors.aliyun.com/golang/$GO_ARCHIVE" || \
        wget -q --show-progress "https://golang.google.cn/dl/$GO_ARCHIVE"
    fi

    rm -rf "$GO_DIR"
    tar -C "$HOME/.local" -xzf "$GO_ARCHIVE"

    export PATH="$GO_DIR/bin:$PATH"
    export GOPATH="$HOME/go"
    # 使用国内 Go 代理
    export GOPROXY="https://goproxy.cn,direct"
    mkdir -p "$GOPATH"

    # 添加到 bashrc
    if ! grep -q "$GO_DIR/bin" ~/.bashrc 2>/dev/null; then
        echo "export PATH=\"$GO_DIR/bin:\$PATH\"" >> ~/.bashrc
        echo "export GOPATH=\"$HOME/go\"" >> ~/.bashrc
        echo "export GOPROXY=\"https://goproxy.cn,direct\"" >> ~/.bashrc
    fi

    log_success "Go 安装完成: $($GO_DIR/bin/go version)"
}

# ============================================
# 2. 启动 CLIProxyAPI
# ============================================
start_cliproxy() {
    log_info "准备 CLIProxyAPI..."
    cd "$CLIPROXY_DIR"

    if [ ! -f "config.yaml" ]; then
        if [ -f "config.example.yaml" ]; then
            log_warn "未找到 config.yaml，从示例创建..."
            cp config.example.yaml config.yaml
        fi
    fi

    log_info "构建 CLIProxyAPI..."
    # 使用国内代理，禁用本地 HTTP 代理
    (
        unset HTTP_PROXY http_proxy HTTPS_PROXY https_proxy
        export GOPROXY="https://goproxy.cn,direct"
        go build -o server ./cmd/server 2>&1 | tail -5
    )

    log_info "启动 CLIProxyAPI (端口 8317)..."
    ./server > /tmp/cliproxy.log 2>&1 &
    CLIPROXY_PID=$!

    sleep 2
    if kill -0 $CLIPROXY_PID 2>/dev/null; then
        log_success "CLIProxyAPI 已启动 (PID: $CLIPROXY_PID)"
    else
        log_error "CLIProxyAPI 启动失败，查看 /tmp/cliproxy.log"
        cat /tmp/cliproxy.log | tail -10
        return 1
    fi
}

# ============================================
# 3. 启动 APIHub-Gateway 后端
# ============================================
start_backend() {
    log_info "准备 APIHub-Gateway 后端..."
    cd "$APIHUB_DIR/backend"

    # 使用 pip 直接安装（不用 venv）
    log_info "安装 Python 依赖..."
    pip3 install --user -r requirements.txt -q 2>&1 | tail -3

    if [ ! -f ".env" ]; then
        cp .env.example .env
    fi

    log_info "启动 APIHub 后端 (端口 8000)..."
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/apihub-backend.log 2>&1 &
    BACKEND_PID=$!

    sleep 3
    if kill -0 $BACKEND_PID 2>/dev/null; then
        log_success "APIHub 后端已启动 (PID: $BACKEND_PID)"
    else
        log_error "后端启动失败，查看 /tmp/apihub-backend.log"
        cat /tmp/apihub-backend.log | tail -10
        return 1
    fi
}

# ============================================
# 4. 启动 APIHub-Gateway 前端
# ============================================
start_frontend() {
    log_info "准备 APIHub-Gateway 前端..."
    cd "$APIHUB_DIR/frontend"

    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install --silent 2>&1 | tail -3
    fi

    log_info "启动 APIHub 前端 (端口 3000)..."
    npm run dev > /tmp/apihub-frontend.log 2>&1 &
    FRONTEND_PID=$!

    sleep 3
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        log_success "APIHub 前端已启动 (PID: $FRONTEND_PID)"
    else
        log_error "前端启动失败，查看 /tmp/apihub-frontend.log"
        cat /tmp/apihub-frontend.log | tail -10
        return 1
    fi
}

# ============================================
# 主流程
# ============================================

# 检查并安装 Go
GO_DIR="$HOME/.local/go"
if [ -x "$GO_DIR/bin/go" ]; then
    export PATH="$GO_DIR/bin:$PATH"
    export GOPATH="$HOME/go"
    export GOPROXY="https://goproxy.cn,direct"
    log_success "Go 已安装: $($GO_DIR/bin/go version)"
elif command -v go &> /dev/null; then
    export GOPROXY="https://goproxy.cn,direct"
    log_success "Go 已安装: $(go version)"
else
    install_go_local
fi

# 检查 Python
if command -v python3 &> /dev/null; then
    log_success "Python3 已安装: $(python3 --version)"
else
    log_error "Python3 未安装"
    exit 1
fi

# 检查 Node
if command -v node &> /dev/null; then
    log_success "Node.js 已安装: $(node --version)"
else
    log_error "Node.js 未安装"
    exit 1
fi

echo ""

# 启动服务
start_cliproxy || exit 1
start_backend || exit 1
start_frontend || exit 1

echo ""
echo "================================================"
echo -e "${GREEN}   所有服务已启动！${NC}"
echo "================================================"
echo ""
echo "  CLIProxyAPI:    http://localhost:8317"
echo "  APIHub 后端:    http://localhost:8000"
echo "  APIHub 前端:    http://localhost:3000"
echo "  API 文档:       http://localhost:8000/docs"
echo ""
echo "  默认管理员: admin / admin123"
echo ""
echo "  日志文件:"
echo "    - CLIProxyAPI: /tmp/cliproxy.log"
echo "    - 后端: /tmp/apihub-backend.log"
echo "    - 前端: /tmp/apihub-frontend.log"
echo ""
echo "  按 Ctrl+C 停止所有服务..."
echo ""

wait
