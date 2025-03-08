# AI Assistant API

一个基于 FastAPI 的 AI 助手 API 服务，提供类似 OpenAI API 的接口，支持流式响应和系统命令执行。

## 功能特点

- 兼容 OpenAI API 格式的接口
- 支持流式响应（Server-Sent Events）
- 支持多种模型（通过配置文件设置）
- 支持系统命令执行
- 会话管理和上下文记忆
- 完整的错误处理和日志记录
- 支持 API 密钥验证
- Markdown 格式的消息展示

## 系统要求

- Python 3.8+
- MongoDB
- Redis

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/luoluoluo22/ai-assistant.git
cd ai-assistant
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量：

复制 `.env.example` 文件为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必要的配置项：

```env
# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=true

# 数据库配置
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379

# API 配置
API_KEY=your-api-key-here
DEFAULT_MODEL=Qwen/Qwen2.5-7B-Instruct

# 跨域配置
CORS_ORIGINS=["*"]
```

## 运行服务

```bash
python run.py
```

服务将在 http://localhost:8000 启动。

## API 接口

### 聊天接口

- 路径：`/v1/chat/completions`
- 方法：`POST`
- 功能：发送消息并获取 AI 助手的响应

#### 请求格式

```json
{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
        {
            "role": "user",
            "content": "列出当前目录的文件"
        }
    ],
    "stream": true,
    "temperature": 0.7,
    "max_tokens": 800
}
```

#### 响应格式

非流式响应：

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "response": "执行结果：...",
        "session_id": "default",
        "conversation_history": [...]
    }
}
```

流式响应（使用 Markdown 格式）：

1. 执行计划：
```json
{
    "id": "chatcmpl-xxx",
    "object": "chat.completion.chunk",
    "choices": [{
        "delta": {
            "content": "### 执行计划\n\n```json\n[\n  {\n    \"tool_name\": \"system_command\",\n    \"parameters\": {\n      \"command\": \"dir\"\n    }\n  }\n]\n```\n"
        }
    }]
}
```

2. 执行步骤：
```json
{
    "id": "chatcmpl-xxx",
    "object": "chat.completion.chunk",
    "choices": [{
        "delta": {
            "content": "\n### 执行步骤: `system_command`\n\n**输出：**\n```\n[命令输出内容]\n```\n**返回码：** `0`\n"
        }
    }]
}
```

3. 最终响应：
```json
{
    "id": "chatcmpl-xxx",
    "object": "chat.completion.chunk",
    "choices": [{
        "delta": {
            "content": "\n### 最终响应\n\n[AI 助手的回复内容]"
        }
    }]
}
```

### 会话管理

#### 清除会话

- 路径：`/v1/chat/session/{session_id}`
- 方法：`DELETE`
- 功能：清除指定会话的历史记录

#### 获取会话历史

- 路径：`/v1/chat/sessions/{session_id}/history`
- 方法：`GET`
- 功能：获取指定会话的历史记录

## 开发指南

### 项目结构

```
ai-assistant/
├── app/
│   ├── agent/         # AI 代理实现
│   ├── api/          # API 接口
│   ├── core/         # 核心配置
│   ├── models/       # 数据模型
│   ├── services/     # 业务服务
│   └── tools/        # 工具实现
├── tests/            # 测试用例
├── .env.example      # 环境变量示例
├── requirements.txt  # 项目依赖
└── run.py           # 启动脚本
```

### 添加新功能

1. 在 `app/tools/` 目录下添加新的工具实现
2. 在 `app/agent/base.py` 中的 `SYSTEM_PROMPT` 中添加新工具的说明
3. 在 `app/agent/base.py` 的 `_create_plan` 方法中添加新功能的处理逻辑

### 测试

运行测试用例：

```bash
python -m pytest tests/
```

测试 API：

```bash
python test_api.py
```

## 许可证

MIT License

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request