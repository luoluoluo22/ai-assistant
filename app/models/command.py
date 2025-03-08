from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CommandRequest(BaseModel):
    """命令执行请求"""
    command: str
    working_directory: Optional[str] = None
    is_background: bool = False
    require_approval: bool = True
    explanation: Optional[str] = None

class CommandResult(BaseModel):
    """命令执行结果"""
    command: str
    output: str
    error: Optional[str] = None
    exit_code: int
    execution_time: float
    executed_at: datetime = datetime.now()
    working_directory: str

class CommandHistory(BaseModel):
    """命令执行历史"""
    commands: List[CommandResult]
    working_directory: str 