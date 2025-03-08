from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.config import settings

class Message(BaseModel):
    role: str  # user 或 assistant
    content: str
    timestamp: datetime = datetime.now()

class ChatRequest(BaseModel):
    message: str
    context: Optional[List[Message]] = []
    model: Optional[str] = settings.DEFAULT_MODEL  # 使用配置中的默认模型
    
class ChatResponse(BaseModel):
    message: str
    context: List[Message]
    
class Conversation(BaseModel):
    id: str
    user_id: str
    messages: List[Message]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now() 