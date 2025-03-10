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
```

3. 配置环境变量
```bash
cp .env.example .env
```

4. 启动服务
```bash
python run.py
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
python scripts/run_micloud_token_service.py
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