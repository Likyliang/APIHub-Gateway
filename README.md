# APIHub-Gateway

API 密钥管理与分发平台 - 为 CLIProxyAPI 提供用户管理、配额控制和支付功能。

## 功能特性

- **API Key 管理**: 创建、删除、启用/禁用 API 密钥
- **用量统计**: 实时监控 API 使用情况，按模型、时间统计
- **配额控制**: 用户级别和 Key 级别的配额限制
- **用户系统**: 注册、登录、权限管理
- **支付集成**: 支持支付宝/微信充值（易支付接口）
- **代理转发**: 透明转发请求到上游 CLIProxyAPI
- **低耦合设计**: 独立运行，不影响原项目

## 快速开始

### Docker 方式（推荐）

```bash
# 克隆项目后
./start.sh
```

或手动启动：

```bash
docker-compose up -d
```

访问：
- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 本地开发

**后端（Python）**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置
python -m uvicorn app.main:app --reload
```

**前端（React）**

```bash
cd frontend
npm install
npm run dev
```

## 配置说明

### 后端配置 (backend/.env)

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./apihub.db

# 安全密钥（生产环境必须修改）
SECRET_KEY=your-super-secret-key-change-in-production

# 上游 CLIProxyAPI 地址
UPSTREAM_URL=http://127.0.0.1:8317

# 管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@apihub.local

# 支付配置（易支付）
EPAY_URL=https://pay.example.com
EPAY_PID=1000
EPAY_KEY=your_epay_key
```

### 支付配置

本平台支持易支付（EPay）接口，兼容大多数聚合支付平台：

1. 注册易支付商户账号
2. 获取商户 ID (PID) 和密钥 (KEY)
3. 配置 `EPAY_URL`、`EPAY_PID`、`EPAY_KEY`
4. 设置支付回调地址为 `http://your-domain/api/payment/notify`

## API 使用

### 获取 API Key

1. 注册/登录账号
2. 进入「API Keys」页面
3. 创建新的 API Key
4. 复制并保存 Key（仅显示一次）

### 调用 API

使用获取的 API Key 调用接口：

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy + SQLite
- **前端**: React + TypeScript + Vite + TailwindCSS
- **状态管理**: Zustand + React Query
- **图表**: Recharts

## 项目结构

```
APIHub-Gateway/
├── backend/                 # Python 后端
│   ├── app/
│   │   ├── models/         # 数据模型
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   ├── middleware/     # 中间件
│   │   ├── utils/          # 工具函数
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库
│   │   └── main.py         # 入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/    # 组件
│   │   ├── pages/         # 页面
│   │   ├── services/      # API 服务
│   │   ├── stores/        # 状态管理
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── start.sh
└── README.md
```

## License

MIT
