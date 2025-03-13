"""Application configuration."""

import os
import json
from typing import List, Optional, Union, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field

class Settings(BaseSettings):
    """Application settings."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 添加调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Settings initialized with DEFAULT_MODEL: %s", self.DEFAULT_MODEL)
        logger.info("Settings initialized with OPENAI_BASE_URL: %s", self.OPENAI_BASE_URL)
        logger.info("Environment variables: %s", dict(os.environ))
    
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Assistant API"
    
    # CORS配置
    CORS_ORIGINS: Union[str, List[str]] = "*"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [i.strip() for i in v.split(",")]
        return v
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    API_KEY: str = "sk-test-123456"
    
    # 数据库配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ai_assistant"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    
    # AI模型配置
    DEFAULT_MODEL: str
    OPENAI_API_KEY: str = "sk-or-v1-..."
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # 其他API密钥
    ANTHROPIC_API_KEY: str = ""
    
    # GitHub配置
    GITHUB_TOKEN: str = ""
    GITHUB_USERNAME: str = "luoluoluo22"
    GITHUB_EMAIL: str = "1137583371@qq.com"
    
    # Supabase 配置
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # 知识库配置
    KNOWLEDGE_API_KEY: str = ""
    KNOWLEDGE_BASE_URL: str = "https://luobiji.netlify.app/Cursor"
    
    # SerpApi 配置
    SERPAPI_KEY: str = ""
    
    # 基本配置
    APP_NAME: str = "AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API 配置
    API_PREFIX: str = "/api"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 邮箱配置
    # 默认邮箱配置（QQ邮箱）
    EMAIL_IMAP_SERVER: str = "imap.qq.com"
    EMAIL_IMAP_PORT: int = 993
    EMAIL_SMTP_SERVER: str = "smtp.qq.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    
    # Gmail配置
    GMAIL_EMAIL_USER: str = ""
    GMAIL_EMAIL_PASSWORD: str = ""
    
    # Outlook配置
    OUTLOOK_EMAIL_IMAP_SERVER: str = "outlook.office365.com"
    OUTLOOK_EMAIL_IMAP_PORT: int = 993
    OUTLOOK_EMAIL_SMTP_SERVER: str = "smtp.office365.com"
    OUTLOOK_EMAIL_SMTP_PORT: int = 587
    OUTLOOK_EMAIL_USER: str = ""
    OUTLOOK_EMAIL_PASSWORD: str = ""
    OUTLOOK_CLIENT_ID: str = ""
    OUTLOOK_CLIENT_SECRET: str = ""
    OUTLOOK_TENANT_ID: str = "common"
    
    # 当前使用的邮箱类型
    CURRENT_EMAIL_TYPE: str = "qq"
    
    # 小米云服务配置
    MICLOUD_COOKIE: str = ""

    def get_micloud_cookies(self) -> Dict[str, str]:
        """获取解析后的小米云服务 cookies"""
        if not self.MICLOUD_COOKIE:
            return {}
            
        try:
            # 尝试解析 JSON
            if self.MICLOUD_COOKIE.startswith('{') and self.MICLOUD_COOKIE.endswith('}'):
                return json.loads(self.MICLOUD_COOKIE)
                
            # 尝试解析 cookie 字符串
            cookies = {}
            for cookie in self.MICLOUD_COOKIE.split(';'):
                cookie = cookie.strip()
                if not cookie or '=' not in cookie:
                    continue
                name, value = cookie.split('=', 1)
                cookies[name.strip()] = value.strip()
            return cookies
        except Exception as e:
            import logging
            logging.error(f"Failed to parse MICLOUD_COOKIE: {e}")
            return {}
    
    class Config:
        """Pydantic config."""
        case_sensitive = True
        env_file = ".env"
        json_encoders = {
            Dict[str, str]: lambda v: json.dumps(v)
        }

settings = Settings() 