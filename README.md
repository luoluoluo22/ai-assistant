# AI Assistant

一个功能强大的通用型 AI 助手，集成了多种服务和工具，可以帮助您完成各种任务。

## 主要功能

- 🤖 智能对话：集成多种 LLM 模型，支持智能对话和任务处理
- 📧 邮件服务：支持 Gmail、Outlook、QQ 邮箱等多平台邮件管理
- ☁️ 云服务集成：
  - 小米云服务 Token 管理
  - 更多云服务持续集成中...
- 🔍 知识检索：集成 Supabase 向量数据库，支持智能知识检索
- 🌐 网络搜索：集成 SerpAPI，支持实时网络搜索
- 📊 数据存储：支持 MongoDB 和 Redis 数据管理
- 🔐 安全认证：完整的用户认证和权限管理系统

## 快速开始

1. 克隆项目
```bash
git clone https://github.com/luoluoluo22/ai-assistant.git
cd ai_assistant
```

2. 安装依赖
```bash
pip install -r requirements.txt
npm install -g pm2  # 安装进程管理器
```

3. 配置环境变量
```bash
cp .env.example .env
```

4. 启动服务

Windows:
```powershell
cd process_manager
.\manage.ps1 start
```

Linux/MacOS:
```bash
cd process_manager
chmod +x manage.sh
./manage.sh start
```

## 环境配置说明

项目使用 `.env` 文件进行配置管理，以下是主要配置项说明：

### 基础配置
```env
APP_NAME=AI Assistant
APP_VERSION=1.0.0
DEBUG=true
API_PREFIX=/api
API_HOST=0.0.0.0
API_PORT=8000
```

### 安全配置
```env
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=60
API_KEY=your_api_key
```

### 数据库配置
```env
# MongoDB配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=ai_assistant

# Redis配置
REDIS_URL=redis://localhost:6379
REDIS_DB=0
```

### AI模型配置
```env
DEFAULT_MODEL=qwen/qwq-32b:free
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

### 邮箱服务配置

#### QQ邮箱
```env
EMAIL_IMAP_SERVER=imap.qq.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_SERVER=smtp.qq.com
EMAIL_SMTP_PORT=587
EMAIL_USER=your_qq_email
EMAIL_PASSWORD=your_qq_email_password
```

#### Gmail
```env
GMAIL_EMAIL_USER=your_gmail
GMAIL_EMAIL_PASSWORD=your_gmail_app_password
```

#### Outlook
```env
OUTLOOK_EMAIL_USER=your_outlook_email
OUTLOOK_EMAIL_PASSWORD=your_outlook_password
OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_CLIENT_SECRET=your_client_secret
```

### 知识库配置
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 搜索服务配置
```env
SERPAPI_KEY=your_serpapi_key
```

### 小米云服务配置
```env
MICLOUD_COOKIE='your_micloud_cookie'
```

## 服务说明

### 小米云服务 Token 管理

自动管理和刷新小米云服务的 serviceToken，确保服务持续可用。

启动服务：
```bash
python -m app.services.micloud_token_service
```

Token 会每7分钟自动刷新一次，并保存在 `data/micloud_token.json` 文件中。

### 邮件服务

支持多个邮箱平台的邮件收发和管理：
- QQ邮箱
- Gmail
- Outlook

### 知识库服务

基于 Supabase 的向量数据库实现智能知识检索和管理。

### 搜索服务

集成 SerpAPI 实现实时网络搜索功能。

## 开发说明

### 项目结构
```
ai_assistant/
├── app/
│   ├── services/      # 各种服务实现
│   ├── models/        # 数据模型
│   └── utils/         # 工具函数
├── data/              # 数据存储
├── logs/              # 日志文件
├── scripts/           # 脚本工具
├── tests/             # 测试文件
└── docs/              # 文档
```

### 添加新功能

1. 在 `app/services/` 下创建新的服务模块
2. 在 `.env` 中添加相关配置
3. 更新文档和测试用例

## 贡献指南

欢迎提交 Pull Request 或创建 Issue。

## 许可证

MIT License

## 联系方式

- GitHub: [@luoluoluo22](https://github.com/luoluoluo22)
- Email: 1137583371@qq.com

## 进程管理

项目使用 PM2 进行进程管理，支持 Windows、Linux 和 MacOS。

### 快速启动

安装 PM2：
```bash
npm install pm2 -g
```

启动服务：
```bash
pm2 start ./process_manager/ecosystem.config.js
```

### 常用命令

```bash
# 启动服务
pm2 start ./process_manager/ecosystem.config.js

# 停止服务
pm2 stop fastapi-app

# 重启服务
pm2 restart fastapi-app

# 删除服务
pm2 delete fastapi-app

# 查看服务状态
pm2 status

# 查看日志
pm2 logs fastapi-app

# 监控服务
pm2 monit
```

### PM2 配置说明

配置文件位置：`process_manager/ecosystem.config.js`

主要配置项：
```javascript
{
  name: "fastapi-app",        // 服务名称
  script: "run.py",           // 启动脚本
  interpreter: "python",      // 解释器
  args: "--service fastapi",  // 启动参数
  watch: false,              // 是否监视文件变化
  instances: 1,              // 实例数量
  exec_mode: "fork",         // 执行模式
  env: {                     // 环境变量
    NODE_ENV: "development",
    PYTHONUNBUFFERED: "1"
  }
}
```

### 服务器部署

1. 确保服务器已安装 Python 和 Node.js
2. 安装 PM2：`npm install pm2 -g`
3. 克隆项目并安装依赖
4. 配置环境变量
5. 使用 PM2 启动服务

```bash
# 启动服务
pm2 start ./process_manager/ecosystem.config.js

# 设置开机自启
pm2 startup
pm2 save
```

### 日志管理

PM2 日志文件默认位置：
- Linux/MacOS: `~/.pm2/logs/`
- Windows: `%HOMEDRIVE%%HOMEPATH%\.pm2\logs\`

查看日志：
```bash
# 实时查看日志
pm2 logs fastapi-app

# 查看历史日志
pm2 logs fastapi-app --lines 1000

# 清空日志
pm2 flush
```

### 工具使用原则：
1. 只在必要时才使用工具。对于简单的问候、闲聊或不需要查询/操作的问题，直接回答即可。
2. 每次只能返回一个工具调用
3. 任务完成时直接返回自然语言回答，不再使用 task_complete 工具
4. 如果需要使用前一步骤的结果，应该在提示词中说明，由系统重新规划
5. 参数名称必须完全匹配，不能使用其他名称
6. 必须提供所有必需的参数

### 响应格式规范：
1. 如果需要使用工具，返回 JSON 数组格式：
   [
     {
       "tool_name": "工具名称",
       "parameters": {
         "参数名": "参数值"
       }
     }
   ]
2. 如果不需要使用工具或任务已完成，直接返回自然语言回答