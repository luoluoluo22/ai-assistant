"""Chat endpoints for interacting with agents."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
from ...agent.manager import AgentManager
from ..deps import verify_api_key
from ...core.config import settings
import json
import asyncio
import time
import logging

router = APIRouter()
agent_manager = AgentManager()
logger = logging.getLogger(__name__)

class Message(BaseModel):
    """单条消息模型。"""
    role: str = Field(..., description="消息角色：system, user, assistant")
    content: str = Field(..., description="消息内容")

class ChatRequest(BaseModel):
    """聊天请求模型。"""
    model: str = Field(default=settings.DEFAULT_MODEL, description="要使用的模型名称")
    messages: List[Message] = Field(..., description="消息列表")
    session_id: Optional[str] = Field(None, description="会话ID")
    temperature: float = Field(default=0.7, description="采样温度", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=800, description="生成的最大token数")
    top_p: float = Field(default=0.95, description="核采样阈值", ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, description="频率惩罚", ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, description="存在惩罚", ge=-2.0, le=2.0)
    stream: bool = Field(default=False, description="是否流式输出")

class ChatResponse(BaseModel):
    """聊天响应模型。"""
    response: str = Field(..., description="AI助手的响应")
    session_id: str = Field(..., description="会话ID")
    conversation_history: List[Dict[str, Any]] = Field(..., description="对话历史")

@router.post("/completions")
async def send_message(
    chat_request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    """发送消息给AI助手。
    
    Args:
        chat_request: 包含消息列表和会话ID的请求
        api_key: 经过验证的API密钥
        
    Returns:
        AI助手的响应和会话信息
    """
    try:
        # 记录接收到的原始请求内容
        logger.info("收到聊天请求:\n%s", json.dumps(chat_request.model_dump(), ensure_ascii=False, indent=2))
        
        # 使用或创建会话ID
        session_id = chat_request.session_id or "default"
        
        # 获取最后一条用户消息
        user_messages = [msg for msg in chat_request.messages if msg.role == "user"]
        if not user_messages:
            return JSONResponse(
                status_code=400,
                content={
                    "code": -1000,
                    "message": "No user message found",
                    "data": None
                }
            )
        
        last_user_message = user_messages[-1].content
        
        if chat_request.stream:
            return StreamingResponse(
                stream_response(
                    session_id,
                    last_user_message,
                    model=chat_request.model,
                    temperature=chat_request.temperature,
                    max_tokens=chat_request.max_tokens,
                    top_p=chat_request.top_p,
                    frequency_penalty=chat_request.frequency_penalty,
                    presence_penalty=chat_request.presence_penalty
                ),
                media_type="text/event-stream"
            )
        
        # 处理消息
        response = await agent_manager.process_message(
            session_id,
            last_user_message,
            model=chat_request.model,
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
            top_p=chat_request.top_p,
            frequency_penalty=chat_request.frequency_penalty,
            presence_penalty=chat_request.presence_penalty,
            stream=chat_request.stream
        )
        
        # 获取会话历史
        agent = agent_manager.get_agent(session_id)
        history = agent.context["conversation_history"]
        
        return JSONResponse(
            content={
                "code": 0,
                "message": "success",
                "data": {
                    "response": response,
                    "session_id": session_id,
                    "conversation_history": history
                }
            }
        )
        
    except Exception as e:
        # 记录详细的错误信息
        logger.error("处理聊天请求时发生错误:", exc_info=True)
        logger.error("错误详情: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={
                "code": -2000,
                "message": str(e),
                "data": None
            }
        )

async def stream_response(
    session_id: str,
    message: str,
    model: str = settings.DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: Optional[int] = 800,
    top_p: float = 0.95,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0
) -> AsyncGenerator[str, None]:
    """生成流式响应。
    
    Args:
        session_id: 会话ID
        message: 用户消息
        model: 模型名称
        temperature: 采样温度
        max_tokens: 最大生成token数
        top_p: 核采样阈值
        frequency_penalty: 频率惩罚
        presence_penalty: 存在惩罚
        
    Yields:
        流式响应数据
    """
    try:
        # 发送角色信息
        response = {
            "id": f"chatcmpl-{session_id}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant"
                    },
                    "finish_reason": None
                }
            ]
        }
        yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
        
        async for chunk in agent_manager.stream_message(
            session_id,
            message,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        ):
            if isinstance(chunk, dict):
                # 转换为 OpenAI API 格式
                response = {
                    "id": f"chatcmpl-{session_id}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": chunk.get("content", "") if chunk.get("type") == "response" else ""
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {chunk}\n\n"
            await asyncio.sleep(0.1)  # 控制输出速率
        
        # 发送完成标记
        response = {
            "id": f"chatcmpl-{session_id}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_response = {
            "error": {
                "message": str(e),
                "type": "internal_error",
                "code": -2000
            }
        }
        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """清除会话。
    
    Args:
        session_id: 要清除的会话ID
        api_key: 经过验证的API密钥
    """
    try:
        agent_manager.clear_session(session_id)
        return JSONResponse(
            content={
                "code": 0,
                "message": "Session cleared successfully",
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": -2000,
                "message": str(e),
                "data": None
            }
        )

@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """获取会话历史。
    
    Args:
        session_id: 会话ID
        api_key: 经过验证的API密钥
        
    Returns:
        会话历史记录
    """
    try:
        agent = agent_manager.get_agent(session_id)
        return JSONResponse(
            content={
                "code": 0,
                "message": "success",
                "data": {
                    "session_id": session_id,
                    "history": agent.context["conversation_history"]
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": -2000,
                "message": str(e),
                "data": None
            }
        )