"""Application configuration."""

import os
import json
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    """Application settings."""
    
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Assistant API"
    
    # CORS配置
    CORS_ORIGINS: Union[str, List[str]] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # 安全配置
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    API_KEY: str
    
    # 数据库配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "ai_assistant"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    
    # AI模型配置
    DEFAULT_MODEL: str = "qwen/qwq-32b:free"
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # LLM服务配置
    LLM_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    LLM_API_KEY: str
    
    # 其他API密钥
    ANTHROPIC_API_KEY: str = ""
    
    # GitHub配置
    GITHUB_TOKEN: str
    GITHUB_USERNAME: str
    GITHUB_EMAIL: str
    
    # Supabase 配置
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # 知识库配置
    KNOWLEDGE_API_KEY: str
    KNOWLEDGE_BASE_URL: str = "https://luobiji.netlify.app/Cursor"
    
    # SerpApi 配置
    SERPAPI_KEY: str
    
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
    
    class Config:
        """Pydantic config."""
        case_sensitive = True
        env_file = ".env"

settings = Settings() 