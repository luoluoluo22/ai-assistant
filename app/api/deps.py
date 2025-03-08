"""API dependencies."""

from typing import Optional
from fastapi import Header, HTTPException, status
from ..core.config import settings

async def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """验证API密钥。
    
    Args:
        authorization: Authorization header
        
    Returns:
        验证通过的API密钥
        
    Raises:
        HTTPException: 如果验证失败
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "code": -1001,
                "message": "Missing authorization header",
                "data": None
            }
        )
    
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": -1002,
                    "message": "Invalid authorization header format",
                    "data": None
                }
            )
        
        api_key = authorization.replace("Bearer ", "").strip()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": -1003,
                    "message": "Empty API key",
                    "data": None
                }
            )
        
        if api_key != settings.API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": -1004,
                    "message": "Invalid API key",
                    "data": None
                }
            )
        
        return api_key
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "code": -1005,
                "message": f"Authorization error: {str(e)}",
                "data": None
            }
        ) 