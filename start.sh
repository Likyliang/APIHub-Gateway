#!/bin/bash
# APIHub-Gateway - Quick Start Script

set -e

echo "================================================"
echo "   APIHub-Gateway - API 分发管理平台"
echo "================================================"
echo ""

# Check if docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "检测到 Docker，使用 Docker Compose 启动..."
    echo ""
    docker-compose up -d --build
    echo ""
    echo "服务已启动！"
    echo "  - 前端: http://localhost:3000"
    echo "  - 后端 API: http://localhost:8000"
    echo "  - API 文档: http://localhost:8000/docs"
    echo ""
    echo "默认管理员账号: admin / admin123"
    exit 0
fi

# Manual start
echo "未检测到 Docker，使用本地环境启动..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js"
    exit 1
fi

# Start backend
echo "启动后端服务..."
cd backend
if [ ! -d "venv" ]; then
    echo "创建 Python 虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
if [ ! -f ".env" ]; then
    cp .env.example .env
fi
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
echo "启动前端服务..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "================================================"
echo "   服务已启动！"
echo "================================================"
echo ""
echo "  - 前端: http://localhost:3000"
echo "  - 后端 API: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/docs"
echo ""
echo "默认管理员账号: admin / admin123"
echo ""
echo "按 Ctrl+C 停止服务..."

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
