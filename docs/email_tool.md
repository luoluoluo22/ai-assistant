# 邮件工具使用说明

## 功能介绍

邮件工具支持多种邮箱服务（QQ邮箱、Gmail、Outlook）的邮件管理功能，包括：
1. 查看邮件列表
2. 发送邮件
3. 获取文件夹列表
4. 删除指定邮件

## 配置说明

### 1. 环境变量配置
在 `.env` 文件中配置以下信息：

```env
# QQ邮箱配置
QQ_EMAIL_USER=your_qq@qq.com
QQ_EMAIL_PASSWORD=your_qq_password  # QQ邮箱授权码

# Gmail配置
GMAIL_EMAIL_USER=your_gmail@gmail.com
GMAIL_EMAIL_PASSWORD=your_gmail_password  # Gmail应用专用密码

# Outlook配置
OUTLOOK_EMAIL_USER=your_outlook@outlook.com
OUTLOOK_EMAIL_PASSWORD=your_outlook_password
OUTLOOK_CLIENT_ID=your_client_id  # Azure应用注册ID
OUTLOOK_CLIENT_SECRET=your_client_secret  # 可选，用于服务器端认证
OUTLOOK_TENANT_ID=your_tenant_id  # 可选，默认为 "common"
```

### 2. Outlook特别说明

#### 2.1 本地开发环境
- 首次使用需要进行交互式认证
- 认证后会在 `./token` 目录下生成 `o365_token.txt` 缓存文件

#### 2.2 服务器部署
两种方式：

1. 使用token文件：
   - 在本地完成认证获取token
   - 将 `o365_token.txt` 文件复制到服务器的对应位置

2. 使用客户端凭据：
   - 在Azure门户配置应用为"机密客户端"
   - 配置 `OUTLOOK_CLIENT_SECRET` 和 `OUTLOOK_TENANT_ID`
   - 无需用户交互即可使用

## 使用示例

### 1. 基本用法

```python
from app.tools.email_tool import EmailTool

email_tool = EmailTool()

# 查看QQ邮箱收件箱（默认）
result = await email_tool.execute(
    action="list_emails",
    folder="INBOX",
    limit=10
)

# 使用Gmail发送邮件
result = await email_tool.execute(
    action="send_email",
    email_type="gmail",  # 指定使用Gmail
    to="recipient@example.com",
    subject="测试邮件",
    body="这是一封测试邮件"
)

# 查看Outlook文件夹列表
result = await email_tool.execute(
    action="list_folders",
    email_type="outlook"  # 指定使用Outlook
)
```

### 2. 支持的操作

#### 2.1 查看邮件列表 (list_emails)
```python
result = await email_tool.execute(
    action="list_emails",
    email_type="qq",  # 可选，默认qq
    folder="INBOX",  # 可选，默认INBOX
    limit=10  # 可选，默认10
)
```

#### 2.2 发送邮件 (send_email)
```python
result = await email_tool.execute(
    action="send_email",
    email_type="gmail",  # 可选，默认qq
    to="recipient@example.com",
    subject="邮件主题",
    body="邮件正文"
)
```

#### 2.3 获取文件夹列表 (list_folders)
```python
result = await email_tool.execute(
    action="list_folders",
    email_type="outlook"  # 可选，默认qq
)
```

#### 2.4 删除邮件 (delete_email)
```python
result = await email_tool.execute(
    action="delete_email",
    email_type="qq",  # 可选，默认qq
    folder="INBOX",  # 可选，默认INBOX
    message_id="123"  # 从list_emails返回结果中获取
)
```

## 注意事项

1. 默认使用QQ邮箱，可通过 `email_type` 参数临时切换邮箱类型
2. 使用Gmail需要开启"低安全性应用访问"或使用应用专用密码
3. Outlook首次使用需要进行认证，建议在本地完成认证后将token文件复制到服务器
4. 所有操作都会返回统一格式的结果：
   ```python
   {
       "status": "success/error",
       "message": "操作结果描述",
       # 可能包含其他数据
   }
   ``` 