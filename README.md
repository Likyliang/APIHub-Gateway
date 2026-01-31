# APIHub-Gateway

API密钥管理与分发平台 - 为CLIProxyAPI提供完整的API密钥管理、代币计费和使用统计功能。

## 功能特性

### 核心功能
- **API密钥管理** - 创建、更新、删除、批量创建API密钥
- **代币/余额系统** - 充值、消费、退款、余额调整
- **折扣系统** - 支持用户级别和API Key级别的折扣
- **使用限制** - 速率限制（每分钟/每日）、Token上限、配额限制
- **使用统计** - 请求统计、Token使用量、费用统计
- **API代理** - 透明代理到上游CLIProxyAPI服务
- **支付集成** - 支持易支付(EPay)接口

### API密钥功能
| 功能 | 描述 |
|------|------|
| 单个创建 | 创建带有自定义限制的API密钥 |
| 批量创建 | 一次创建多个相同配置的密钥 |
| 速率限制 | 每分钟/每日请求限制 |
| Token限制 | 总Token使用上限 |
| 配额限制 | 费用配额限制 |
| 折扣率 | 0.8表示8折优惠 |
| 模型限制 | 限制可使用的模型列表 |
| 过期时间 | 设置密钥过期时间 |

### 代币系统
| 功能 | 描述 |
|------|------|
| 余额查询 | 查询当前余额和统计 |
| 充值 | 支持支付回调自动充值 |
| 消费 | 自动应用折扣扣费 |
| 退款 | 支持退款操作 |
| 交易记录 | 完整的交易历史记录 |
| 折扣设置 | 管理员设置用户折扣率 |

## 技术栈

### 后端
- **FastAPI** - 高性能Python异步Web框架
- **SQLAlchemy** - 异步ORM
- **SQLite/PostgreSQL** - 数据库
- **Pydantic** - 数据验证
- **JWT** - 身份认证

### 前端
- **React 18** - 用户界面
- **Ant Design** - UI组件库
- **Axios** - HTTP客户端
- **React Router** - 路由管理

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- SQLite 或 PostgreSQL

### 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库和上游服务

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

### Docker方式

```bash
docker-compose up -d
```

访问：
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 配置说明

### 环境变量 (.env)

```bash
# 应用设置
APP_NAME=APIHub-Gateway
DEBUG=false

# 服务器
HOST=0.0.0.0
PORT=8000

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./apihub.db
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/apihub

# 安全设置
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# 上游服务
UPSTREAM_URL=http://127.0.0.1:8317
UPSTREAM_API_KEY=your-upstream-api-key

# 管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@apihub.local

# 支付设置 (易支付)
EPAY_URL=https://pay.example.com
EPAY_PID=1000
EPAY_KEY=your_epay_key
```

## API接口

### 认证
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/me` | 获取当前用户信息 |

### API密钥管理
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/keys` | 创建API密钥 |
| GET | `/api/keys` | 获取密钥列表 |
| POST | `/api/keys/batch` | 批量创建密钥 |
| GET | `/api/keys/batch/{batch_id}` | 获取批次密钥 |
| GET | `/api/keys/{key_id}` | 获取密钥详情 |
| PUT | `/api/keys/{key_id}` | 更新密钥 |
| DELETE | `/api/keys/{key_id}` | 删除密钥 |
| POST | `/api/keys/{key_id}/deactivate` | 停用密钥 |
| POST | `/api/keys/{key_id}/reset-usage` | 重置使用量 |

### 代币系统
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/tokens/balance` | 查询余额 |
| GET | `/api/tokens/transactions` | 交易记录 |
| POST | `/api/tokens/check` | 检查余额 |
| POST | `/api/tokens/recharge/callback` | 充值回调 |

### 管理员接口

#### 密钥管理
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/keys/admin/all` | 获取所有密钥 |
| GET | `/api/keys/admin/user/{user_id}` | 获取用户密钥 |
| POST | `/api/keys/admin/user/{user_id}` | 为用户创建密钥 |
| POST | `/api/keys/admin/user/{user_id}/batch` | 批量创建 |

#### 代币管理
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/tokens/admin/user/{user_id}/balance` | 用户余额 |
| POST | `/api/tokens/admin/user/{user_id}/recharge` | 充值 |
| POST | `/api/tokens/admin/user/{user_id}/consume` | 扣费 |
| POST | `/api/tokens/admin/user/{user_id}/refund` | 退款 |
| POST | `/api/tokens/admin/user/{user_id}/adjust` | 调整 |
| POST | `/api/tokens/admin/user/{user_id}/discount` | 设置折扣 |

### API代理
| 方法 | 路径 | 描述 |
|------|------|------|
| * | `/v1/*` | OpenAI兼容接口 |
| GET | `/v1/models` | 获取模型列表 |

## 使用示例

### 创建API密钥

```bash
curl -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API Key",
    "rate_limit": 100,
    "rate_limit_day": 1000,
    "token_limit": 50000,
    "discount_rate": 0.8,
    "allowed_models": ["gpt-4", "gpt-3.5-turbo"]
  }'
```

### 批量创建API密钥

```bash
curl -X POST http://localhost:8000/api/keys/batch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "count": 10,
    "name_prefix": "Customer",
    "rate_limit": 60,
    "discount_rate": 0.9
  }'
```

### 充值代币

```bash
curl -X POST http://localhost:8000/api/tokens/admin/user/1/recharge \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.0,
    "order_no": "ORDER-001",
    "description": "用户充值"
  }'
```

### 使用API密钥调用

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ahg_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 数据模型

### User (用户)
- `token_balance` - 代币余额
- `total_recharged` - 累计充值
- `total_consumed` - 累计消费
- `discount_rate` - 折扣率

### APIKey (API密钥)
- `rate_limit` - 每分钟请求限制
- `rate_limit_day` - 每日请求限制
- `token_limit` - Token总量限制
- `quota_limit` - 配额限制
- `discount_rate` - 折扣率
- `allowed_models` - 允许的模型列表
- `batch_id` - 批量创建标识

### TokenTransaction (代币交易)
- `amount` - 交易金额
- `balance_before` - 交易前余额
- `balance_after` - 交易后余额
- `transaction_type` - 类型 (recharge/consume/refund/adjust)
- `order_no` - 订单号

## 折扣系统说明

折扣率 `discount_rate` 的工作方式：
- `1.0` = 无折扣（原价）
- `0.8` = 8折（20% off）
- `0.5` = 5折（50% off）

消费时自动应用折扣：
```
实际扣费 = 原始费用 × discount_rate
```

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
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## License

MIT License
