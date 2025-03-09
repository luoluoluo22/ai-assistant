"""Security utilities."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

# API Key认证
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Bearer Token认证
bearer_auth = HTTPBearer(auto_error=False)

async def verify_api_key(
    api_key: str | None = Security(api_key_header),
    bearer_auth: HTTPAuthorizationCredentials | None = Security(bearer_auth)
) -> str:
    """验证API密钥。
    
    支持两种认证方式：
    1. X-API-Key 请求头
    2. Bearer Token 认证
    
    Args:
        api_key: X-API-Key 请求头中的API密钥
        bearer_auth: Bearer Token认证信息
        
    Returns:
        验证通过的API密钥
        
    Raises:
        HTTPException: 当API密钥无效时
    """
    if not settings.API_KEY:
        raise HTTPException(
            status_code=500,
            detail="服务器未配置API密钥"
        )

    # 检查 X-API-Key
    if api_key and api_key == settings.API_KEY:
        return api_key
        
    # 检查 Bearer Token
    if bearer_auth and bearer_auth.credentials == settings.API_KEY:
        return bearer_auth.credentials
        
    raise HTTPException(
        status_code=403,
        detail="请提供有效的API密钥"
    ) 