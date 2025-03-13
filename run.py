"""Server startup script."""

import argparse
import logging
import uvicorn
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def start_fastapi_server():
    """启动 FastAPI 服务器"""
    logger.info("Starting FastAPI server with settings: %s", {
        'host': settings.HOST,
        'port': settings.PORT,
        'cors_origins': settings.CORS_ORIGINS,
        'mongodb_url': settings.MONGODB_URL,
        'redis_url': settings.REDIS_URL
    })
    
    # 启动 FastAPI 服务器
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False  # 禁用自动重载
    )

def start_token_service():
    """启动 Token 服务"""
    logger.info("Starting Token service")
    # 启动 Token 服务
    import runpy
    runpy.run_module('app.services.micloud_token_service', run_name='__main__')

def main():
    """Start the server."""
    parser = argparse.ArgumentParser(description='Start services')
    parser.add_argument('--service', type=str, required=False, choices=['fastapi', 'token'],
                      default='fastapi',
                      help='Service to start: fastapi (default) or token')
    args = parser.parse_args()

    try:
        if args.service == 'fastapi':
            start_fastapi_server()
        elif args.service == 'token':
            start_token_service()
        
    except Exception as e:
        logger.error("Failed to start service", exc_info=True)
        raise

if __name__ == "__main__":
    main() 