import imaplib
import email
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
import ssl
from O365 import Account, Connection  # 添加 O365 支持
from ..core.config import settings
from .base import BaseTool
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailTool(BaseTool):
    """邮件管理工具"""
    
    name: str = "email"
    description: str = """邮件管理工具，支持以下操作：
    1. 查看邮件列表 (list_emails)
    2. 发送邮件 (send_email)
    3. 获取文件夹列表 (list_folders)
    4. 删除指定邮件 (delete_email)
    5. 切换邮箱类型 (switch_email_type)
    
    支持的邮箱类型：
    - QQ邮箱 (qq)
    - Gmail (gmail)
    - Outlook (outlook)
    """
    
    # 邮箱配置
    email_configs = {
        "qq": {
            "imap_server": settings.EMAIL_IMAP_SERVER,
            "imap_port": settings.EMAIL_IMAP_PORT,
            "smtp_server": settings.EMAIL_SMTP_SERVER,
            "smtp_port": settings.EMAIL_SMTP_PORT,
            "user": settings.EMAIL_USER,
            "password": settings.EMAIL_PASSWORD
        },
        "gmail": {
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "user": settings.GMAIL_EMAIL_USER,
            "password": settings.GMAIL_EMAIL_PASSWORD
        },
        "outlook": {
            "imap_server": settings.OUTLOOK_EMAIL_IMAP_SERVER,
            "imap_port": settings.OUTLOOK_EMAIL_IMAP_PORT,
            "smtp_server": settings.OUTLOOK_EMAIL_SMTP_SERVER,
            "smtp_port": settings.OUTLOOK_EMAIL_SMTP_PORT,
            "user": settings.OUTLOOK_EMAIL_USER,
            "password": settings.OUTLOOK_EMAIL_PASSWORD,
            "client_id": settings.OUTLOOK_CLIENT_ID,
            "client_secret": settings.OUTLOOK_CLIENT_SECRET,
            "tenant_id": settings.OUTLOOK_TENANT_ID
        }
    }
    
    current_email_type: str = settings.CURRENT_EMAIL_TYPE
    imap: Optional[imaplib.IMAP4_SSL] = None
    outlook_account: Optional[Account] = None
    
    def __init__(self):
        """Initialize the tool."""
        super().__init__()
        self._load_current_config()
    
    def _load_current_config(self):
        """加载当前选择的邮箱配置"""
        config = self.email_configs[self.current_email_type]
        
        # 验证基本配置是否完整
        required_fields = {
            "imap_server": "IMAP服务器地址",
            "imap_port": "IMAP端口",
            "smtp_server": "SMTP服务器地址",
            "smtp_port": "SMTP端口",
            "user": "邮箱账号",
            "password": "邮箱密码"
        }
        
        missing_fields = []
        for field, desc in required_fields.items():
            if not config.get(field):
                missing_fields.append(f"{desc}({field})")
        
        if missing_fields:
            error_msg = f"邮箱配置不完整，缺少以下必要信息：{', '.join(missing_fields)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.imap_server = config["imap_server"]
        self.imap_port = config["imap_port"]
        self.smtp_server = config["smtp_server"]
        self.smtp_port = config["smtp_port"]
        self.email = config["user"]
        self.password = config["password"]
        
        # 如果是 Outlook，初始化 O365 Account
        if self.current_email_type == "outlook":
            if not config.get("client_id"):
                raise ValueError("Outlook 配置不完整：缺少 client_id")
                
            credentials = (config["client_id"], config.get("client_secret"))
            # 使用更安全的路径存储 token
            token_path = Path("./data/tokens/outlook").absolute()
            token_file = token_path / "o365_token.txt"
            
            # 确保token目录存在
            token_path.mkdir(parents=True, exist_ok=True)
            
            try:
                # 尝试从文件加载现有的token
                if token_file.exists():
                    logger.info("尝试从缓存加载 token...")
                    self.outlook_account = Account(credentials, token_path=token_file)
                else:
                    logger.info("未找到缓存的 token，开始新的认证流程...")
                    self.outlook_account = Account(credentials)
                
                # 设置必要的权限范围
                scopes = ['offline_access', 'Mail.Read', 'Mail.ReadWrite', 'Mail.Send', 'User.Read']
                
                # 如果未认证，开始认证流程
                if not self.outlook_account.is_authenticated:
                    # 尝试使用客户端凭据流程（适用于服务器端）
                    if config.get("client_secret"):
                        logger.info("使用客户端凭据流程进行认证...")
                        result = self.outlook_account.authenticate(scopes=scopes, tenant_id=config.get("tenant_id", "common"))
                    else:
                        # 如果没有客户端密钥，使用设备代码流程
                        logger.info("使用设备代码流程进行认证...")
                        result = self.outlook_account.authenticate(scopes=scopes)
                    
                    if not result:
                        logger.error("Outlook 认证失败")
                        raise Exception("Outlook 认证失败")
                    
                    # 保存 token 到文件
                    if token_file.exists():
                        logger.info("更新 token 缓存...")
                    else:
                        logger.info("创建新的 token 缓存...")
                    
            except Exception as e:
                logger.error(f"Outlook 认证过程出错: {str(e)}")
                raise Exception(f"Outlook 认证失败: {str(e)}")
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get the parameters schema for the tool."""
        return {
            "action": {
                "type": "string",
                "description": "要执行的操作：list_emails（查看邮件列表）, send_email（发送邮件）, list_folders（查看文件夹）, delete_email（删除邮件）, switch_email_type（切换邮箱类型）",
                "enum": ["list_emails", "send_email", "list_folders", "delete_email", "switch_email_type"],
                "required": True
            },
            "email_type": {
                "type": "string",
                "description": "要使用的邮箱类型：qq（默认）, gmail, outlook",
                "enum": ["qq", "gmail", "outlook"],
                "required": False
            },
            "folder": {
                "type": "string",
                "description": "邮件文件夹名称，默认为INBOX",
                "required": False
            },
            "limit": {
                "type": "integer",
                "description": "要获取的邮件数量限制，默认为10",
                "required": False
            },
            "to": {
                "type": "string",
                "description": "收件人邮箱地址（发送邮件时必需）",
                "required": False
            },
            "subject": {
                "type": "string",
                "description": "邮件主题（发送邮件时必需）",
                "required": False
            },
            "body": {
                "type": "string",
                "description": "邮件正文（发送邮件时必需）",
                "required": False
            },
            "message_id": {
                "type": "string",
                "description": "要删除的邮件ID（删除邮件时必需，可从list_emails的返回结果中获取）",
                "required": False
            }
        }
    
    @property
    def examples(self) -> List[str]:
        """Get example usages of the tool."""
        return [
            "查看收件箱最新邮件",
            "发送新邮件",
            "查看所有邮件文件夹",
            "删除指定邮件",
            "切换到 Gmail 邮箱"
        ]
    
    def connect_imap(self):
        """连接到IMAP服务器"""
        try:
            if self.current_email_type == "outlook":
                if not self.outlook_account.is_authenticated:
                    self.outlook_account.authenticate()
                return
            
            logger.info(f"正在连接到 IMAP 服务器: {self.imap_server}:{self.imap_port}")
            logger.info(f"使用邮箱: {self.email}")
            
            if not self.email or not self.password:
                raise ValueError(f"邮箱配置不完整: 用户名或密码为空")
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            try:
                self.imap = imaplib.IMAP4_SSL(
                    self.imap_server, 
                    self.imap_port,
                    ssl_context=context
                )
            except Exception as e:
                raise ConnectionError(f"无法连接到IMAP服务器 {self.imap_server}:{self.imap_port}: {str(e)}")
            
            logger.info("IMAP 连接已建立，尝试登录...")
            try:
                self.imap.login(self.email, self.password)
                logger.info("IMAP 登录成功")
            except imaplib.IMAP4.error as e:
                error_msg = str(e)
                if "LOGIN command error" in error_msg:
                    if self.current_email_type == "qq":
                        raise ValueError("QQ邮箱登录失败，请确保使用的是授权码而不是邮箱密码")
                    elif self.current_email_type == "gmail":
                        raise ValueError("Gmail登录失败，请确保使用的是应用专用密码，并已开启IMAP访问")
                    else:
                        raise ValueError(f"邮箱登录失败，请检查用户名和密码是否正确: {error_msg}")
                raise
            
        except Exception as e:
            logger.error(f"连接邮箱服务器失败: {str(e)}")
            if hasattr(e, 'args') and len(e.args) > 0:
                logger.error(f"错误详情: {e.args[0]}")
            raise Exception(f"连接邮箱服务器失败: {str(e)}")
        
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """执行邮件操作"""
        action = kwargs.get("action")
        email_type = kwargs.get("email_type", "qq")  # 默认使用 QQ 邮箱
        
        # 如果指定了邮箱类型且与当前类型不同，临时切换邮箱类型
        original_type = self.current_email_type
        if email_type != self.current_email_type:
            self.current_email_type = email_type
            self._load_current_config()
        
        try:
            if action == "list_emails":
                result = await self._list_emails(
                    folder=kwargs.get("folder", "INBOX"),
                    limit=kwargs.get("limit", 10)
                )
            elif action == "send_email":
                result = await self._send_email(
                    to=kwargs["to"],
                    subject=kwargs["subject"],
                    body=kwargs["body"]
                )
            elif action == "list_folders":
                result = await self._list_folders()
            elif action == "delete_email":
                result = await self._delete_email(
                    folder=kwargs.get("folder", "INBOX"),
                    message_id=kwargs.get("message_id")
                )
            elif action == "switch_email_type":
                result = await self._switch_email_type(kwargs.get("email_type"))
            else:
                raise ValueError(f"Unknown action: {action}")
            
            return result
        finally:
            # 如果临时切换了邮箱类型，恢复原来的类型
            if email_type != original_type:
                self.current_email_type = original_type
                self._load_current_config()
    
    async def _switch_email_type(self, email_type: str) -> Dict[str, Any]:
        """切换邮箱类型"""
        if email_type not in self.email_configs:
            return {
                "status": "error",
                "message": f"不支持的邮箱类型: {email_type}"
            }
        
        # 检查新邮箱类型的配置是否完整
        config = self.email_configs[email_type]
        required_fields = ["user", "password"]
        if email_type == "outlook":
            required_fields.append("client_id")
        
        for field in required_fields:
            if not config.get(field):
                return {
                    "status": "error",
                    "message": f"邮箱 {email_type} 的配置不完整，缺少 {field} 配置"
                }
        
        # 更新当前邮箱类型
        self.current_email_type = email_type
        
        # 测试新的邮箱连接
        try:
            self._load_current_config()
            if email_type == "outlook":
                return {
                    "status": "success",
                    "message": f"已切换到 {email_type} 邮箱",
                    "current_email": self.email
                }
            else:
                self.connect_imap()
                if self.imap:
                    self.imap.logout()
                return {
                    "status": "success",
                    "message": f"已切换到 {email_type} 邮箱",
                    "current_email": self.email
                }
        except Exception as e:
            logger.error(f"切换邮箱失败: {str(e)}")
            return {
                "status": "error",
                "message": f"切换邮箱失败: {str(e)}"
            }
    
    async def _list_emails(self, folder: str = "INBOX", limit: int = 10) -> Dict[str, Any]:
        """获取邮件列表"""
        try:
            if self.current_email_type == "outlook":
                mailbox = self.outlook_account.mailbox()
                
                # 根据文件夹名称获取对应的文件夹对象
                if folder.lower() == "sent":
                    outlook_folder = mailbox.sent_folder()
                else:
                    outlook_folder = mailbox.inbox_folder()
                
                # 获取指定文件夹中的邮件
                messages = list(outlook_folder.get_messages(limit=limit))
                email_list = []
                
                for msg in messages:
                    # 获取收件人列表
                    to_list = []
                    if hasattr(msg, 'to'):
                        to_list = [r.address for r in msg.to._recipients] if msg.to._recipients else []
                    
                    email_list.append({
                        "message_id": msg.object_id,
                        "subject": msg.subject or "(无主题)",
                        "from": msg.sender.address if msg.sender else "(无发件人)",
                        "to": to_list,
                        "date": msg.received.strftime("%Y-%m-%d %H:%M:%S") if msg.received else "(无日期)",
                        "body": msg.body or "(无内容)"
                    })
                
                return {"status": "success", "emails": email_list}
            
            self.connect_imap()
            self.imap.select(folder)
            
            _, messages = self.imap.search(None, "ALL")
            email_list = []
            
            for num in messages[0].split()[-limit:]:
                try:
                    _, msg = self.imap.fetch(num, "(RFC822)")
                    email_message = email.message_from_bytes(msg[0][1])
                    
                    # 改进的邮件头解码函数
                    def safe_decode_header(header_value):
                        if not header_value:
                            return ""
                        try:
                            decoded_header = email.header.decode_header(header_value)
                            decoded_parts = []
                            for part, charset in decoded_header:
                                if isinstance(part, bytes):
                                    try:
                                        # 尝试使用指定的字符集
                                        if charset:
                                            decoded_parts.append(part.decode(charset))
                                        # 如果没有指定字符集，尝试常用编码
                                        else:
                                            for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                                                try:
                                                    decoded_parts.append(part.decode(encoding))
                                                    break
                                                except UnicodeDecodeError:
                                                    continue
                                    except Exception:
                                        # 如果所有尝试都失败，使用 ASCII 编码并忽略错误
                                        decoded_parts.append(part.decode('ascii', errors='ignore'))
                                else:
                                    decoded_parts.append(str(part))
                            return ' '.join(decoded_parts)
                        except Exception as e:
                            logger.error(f"解码邮件头时出错: {str(e)}")
                            return str(header_value)
                    
                    subject = safe_decode_header(email_message.get("Subject")) or "(无主题)"
                    from_ = safe_decode_header(email_message.get("From")) or "(无发件人)"
                    date = safe_decode_header(email_message.get("Date")) or "(无日期)"
                    
                    # 改进的邮件正文解码函数
                    def safe_decode_payload(part):
                        try:
                            payload = part.get_payload(decode=True)
                            if not payload:
                                return ""
                            
                            charset = part.get_content_charset()
                            if charset:
                                try:
                                    return payload.decode(charset)
                                except UnicodeDecodeError:
                                    pass
                            
                            # 尝试常用编码
                            for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                                try:
                                    return payload.decode(encoding)
                                except UnicodeDecodeError:
                                    continue
                            
                            # 如果所有尝试都失败，使用 ASCII 编码并忽略错误
                            return payload.decode('ascii', errors='ignore')
                        except Exception as e:
                            logger.error(f"解码邮件正文时出错: {str(e)}")
                            return "(解码失败)"
                    
                    # 获取邮件正文
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                body = safe_decode_payload(part)
                                if body:
                                    break
                    else:
                        body = safe_decode_payload(email_message)
                    
                    email_list.append({
                        "message_id": num.decode(),
                        "subject": subject,
                        "from": from_,
                        "date": date,
                        "body": body or "(无内容)"
                    })
                except Exception as e:
                    logger.error(f"处理单个邮件时出错: {str(e)}")
                    continue
            
            self.imap.close()
            self.imap.logout()
            
            if not email_list:
                return {"status": "success", "message": "没有找到邮件", "emails": []}
                
            return {"status": "success", "emails": email_list}
            
        except Exception as e:
            logger.error(f"获取邮件列表时出错: {str(e)}")
            return {"status": "error", "message": f"获取邮件列表失败: {str(e)}"}
        
    async def _send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """发送邮件"""
        try:
            if self.current_email_type == "outlook":
                if not self.outlook_account.is_authenticated:
                    self.outlook_account.authenticate()
                
                mailbox = self.outlook_account.mailbox()
                message = mailbox.new_message()
                message.to.add(to)
                message.subject = subject
                message.body = body
                message.send()
                
                return {"status": "success", "message": "邮件发送成功"}
            
            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to
            msg["Subject"] = subject
            
            msg.attach(MIMEText(body, "plain"))
            
            logger.info(f"正在连接到 SMTP 服务器: {self.smtp_server}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            
            logger.info(f"尝试 SMTP 登录: {self.email}")
            server.login(self.email, self.password)
            logger.info("SMTP 登录成功")
            
            server.send_message(msg)
            server.quit()
            return {"status": "success", "message": "邮件发送成功"}
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            if hasattr(e, 'args') and len(e.args) > 0:
                logger.error(f"错误详情: {e.args[0]}")
            return {"status": "error", "message": f"发送邮件失败: {str(e)}"}
            
    async def _list_folders(self) -> Dict[str, Any]:
        """获取所有邮件文件夹"""
        try:
            if self.current_email_type == "outlook":
                if not self.outlook_account.is_authenticated:
                    self.outlook_account.authenticate()
                
                mailbox = self.outlook_account.mailbox()
                folders = [f.name for f in mailbox.list_folders()]
                return {"status": "success", "folders": folders}
            
            self.connect_imap()
            _, folders = self.imap.list()
            folder_list = []
            for folder in folders:
                folder_name = folder.decode().split('"')[-2]
                folder_list.append(folder_name)
            self.imap.logout()
            return {"status": "success", "folders": folder_list}
            
        except Exception as e:
            logger.error(f"获取文件夹列表失败: {str(e)}")
            return {"status": "error", "message": f"获取文件夹列表失败: {str(e)}"}
        
    async def _delete_email(self, folder: str, message_id: str) -> Dict[str, Any]:
        """删除指定的邮件"""
        try:
            if self.current_email_type == "outlook":
                if not self.outlook_account.is_authenticated:
                    self.outlook_account.authenticate()
                
                mailbox = self.outlook_account.mailbox()
                message = mailbox.get_message(message_id)
                message.delete()
                
                return {"status": "success", "message": "邮件已成功删除"}
            
            self.connect_imap()
            self.imap.select(folder)
            
            # 标记邮件为删除
            self.imap.store(message_id, '+FLAGS', '\\Deleted')
            # 执行删除操作
            self.imap.expunge()
            
            self.imap.close()
            self.imap.logout()
            
            return {
                "status": "success",
                "message": f"邮件已成功删除"
            }
        except Exception as e:
            logger.error(f"删除邮件失败: {str(e)}")
            return {
                "status": "error",
                "message": f"删除邮件失败: {str(e)}"
            }

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """运行工具的方法（必需）"""
        # 这个方法是为了满足 BaseTool 的要求
        # 实际的执行逻辑在 execute 方法中
        raise NotImplementedError("请使用 execute 方法代替")

    def get_tool_definition(self) -> Dict[str, Any]:
        """获取工具定义"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples
        } 