#!/bin/bash
# APIHub-Gateway 完整配置脚本

set -e

PROJECT_DIR="$HOME/workspace/APIHub-Gateway"
ORIGINAL_DIR="$HOME/workspace/CLIProxyAPI-sastic"

echo "🚀 开始配置 APIHub-Gateway 项目..."

# 创建目录
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
mkdir -p .claude

echo "📝 创建 settings.json..."
cat > .claude/settings.json <<'EOF'
{
  "permissions": {
    "filesystem": {
      "read": true,
      "write": true,
      "create": true,
      "allowedPaths": [
        "/home/solotice/workspace/APIHub-Gateway",
        "/home/solotice/workspace/CLIProxyAPI-sastic"
      ]
    },
    "network": {
      "allow_external": true
    },
    "shell": {
      "allow_commands": true
    }
  },
  "autoApprove": {
    "fileOperations": true,
    "shellCommands": [
      "npm *",
      "go *",
      "git *",
      "mkdir *",
      "node *",
      "python *",
      "pip *"
    ]
  },
  "context": {
    "relatedProjects": [
      "/home/solotice/workspace/CLIProxyAPI-sastic"
    ]
  }
}
EOF

echo "📝 创建 PROJECT.md..."
cat > .claude/PROJECT.md <<'PROJECTEOF'
# APIHub-Gateway - API 分发管理系统

## 🎯 核心目标
为 `CLIProxyAPI-sastic` 项目构建一个**外部 API 分发管理层**，实现：
- API Key 管理与分发
- 用量统计与配额控制
- 美观的用户界面
- 低耦合设计（原项目更新不影响本系统）

---

## �� 原项目位置
**路径**: `/home/solotice/workspace/CLIProxyAPI-sastic`

### 原项目核心组件
1. **入口**: `main.go` - 启动 HTTP 服务器
2. **路由**: `server/routes.go` - API 路由定义
3. **认证**: `auth/` 目录 - OAuth 认证逻辑
4. **翻译器**: `translator/` - 格式转换（OpenAI ↔ Claude ↔ Gemini）
5. **配置**: `config.yaml` - 上游 API 配置

### 原项目架构（从 CLAUDE.md）
