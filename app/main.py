"""Main application module."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.endpoints import chat, tools

app = FastAPI(
    title="AI Assistant API",
    description="智能助手API服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/v1/chat", tags=["对话"])
app.include_router(tools.router, prefix="/v1/tools", tags=["工具"])

@app.get("/")
async def root():
    return {"message": "Welcome to AI Assistant API"} 