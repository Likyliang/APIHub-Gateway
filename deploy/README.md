# APIHub-Gateway 部署脚本

本目录包含用于云服务器部署的脚本。

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `install.sh` | 首次安装，支持 Docker 和直接安装两种方式 |
| `update.sh` | 更新到最新版本（自动备份） |
| `uninstall.sh` | 卸载并可选保留数据 |
| `rollback.sh` | 回滚到之前的备份 |
| `sync.sh` | 本地开发机使用，快速同步到服务器 |

## 快速开始

### 服务器端首次安装

```bash
# 下载安装脚本
curl -O https://raw.githubusercontent.com/Likyliang/APIHub-Gateway/master/deploy/install.sh
chmod +x install.sh

# 运行安装
sudo ./install.sh
```

### 更新已部署的服务

```bash
cd /opt/apihub
sudo ./apihub/deploy/update.sh
```

### 本地开发后同步

```bash
# 设置服务器信息
export SERVER_HOST=你的服务器IP
export SERVER_USER=root

# 同步
./deploy/sync.sh
```

## 架构说明

```
用户请求 (ahg_xxx API Key)
         │
         ▼
┌─────────────────────────────────────┐
│      APIHub-Gateway (:3000)         │
│  - 用户认证、API密钥管理            │
│  - 配额/速率/模型限制               │
│  - 计费和折扣                       │
└─────────────────────────────────────┘
         │
         ▼ (代理到上游)
┌─────────────────────────────────────┐
│      CLIProxyAPI (:8317)            │
│  - OpenAI/Claude/Gemini 兼容 API    │
│  - 多账户轮询                       │
│  - OAuth 登录支持                   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  实际 AI 服务 (Claude/OpenAI/etc)   │
└─────────────────────────────────────┘
```
