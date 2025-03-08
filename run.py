"""Server startup script."""

import logging
import uvicorn
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Start the server."""
    try:
        logger.info("Starting server with settings: %s", {
            'host': settings.HOST,
            'port': settings.PORT,
            'cors_origins': settings.CORS_ORIGINS,
            'mongodb_url': settings.MONGODB_URL,
            'redis_url': settings.REDIS_URL
        })
        
        # 启动服务器，禁用自动重载
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False  # 禁用自动重载
        )
        
    except Exception as e:
        logger.error("Failed to start server", exc_info=True)
        raise

if __name__ == "__main__":
    main() 