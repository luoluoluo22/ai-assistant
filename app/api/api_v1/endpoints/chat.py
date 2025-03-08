from fastapi import APIRouter, HTTPException
from typing import List
from app.models.chat import ChatRequest, ChatResponse, Message
from app.services.llm_service import llm_service
from datetime import datetime
from app.config import settings

router = APIRouter()

@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    与AI助手对话
    """
    try:
        # 添加用户消息到上下文
        current_message = Message(
            role="user",
            content=request.message,
            timestamp=datetime.now()
        )
        context = request.context + [current_message]
        
        # 获取AI回复
        response_content = llm_service.get_completion(
            messages=context,
            model=request.model
        )
        
        # 添加AI回复到上下文
        ai_message = Message(
            role="assistant",
            content=response_content,
            timestamp=datetime.now()
        )
        context.append(ai_message)
        
        return ChatResponse(
            message=response_content,
            context=context
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"对话失败: {str(e)}"
        )

@router.get("/models")
def list_models():
    """
    获取支持的模型列表
    """
    return {
        "models": [
            settings.DEFAULT_MODEL
        ]
    } 