from fastapi import APIRouter
from app.api.api_v1.endpoints import chat, code, auth, command

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(chat.router, prefix="/chat", tags=["对话"])
api_router.include_router(code.router, prefix="/code", tags=["代码"])
api_router.include_router(command.router, prefix="/command", tags=["命令执行"]) 