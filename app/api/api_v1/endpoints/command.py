from fastapi import APIRouter, HTTPException
from app.models.command import CommandRequest, CommandResult, CommandHistory
from app.services.command_service import command_service

router = APIRouter()

@router.post("/execute", response_model=CommandResult)
def execute_command(request: CommandRequest):
    """
    执行命令
    """
    try:
        result = command_service.execute_command(
            command=request.command,
            working_directory=request.working_directory,
            is_background=request.is_background
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"命令执行失败: {str(e)}"
        )

@router.post("/cd")
def change_directory(path: str):
    """
    更改工作目录
    """
    try:
        command_service.change_directory(path)
        return {"message": f"当前工作目录: {command_service.current_directory}"}
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.get("/history", response_model=CommandHistory)
def get_command_history():
    """
    获取命令执行历史
    """
    return CommandHistory(
        commands=command_service.get_command_history(),
        working_directory=command_service.current_directory
    ) 