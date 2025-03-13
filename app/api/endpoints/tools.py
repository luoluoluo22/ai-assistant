"""Tool execution endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from ...services.ai_tool_service import AIToolService

router = APIRouter()
ai_tool_service = AIToolService()

@router.get("/list")
async def list_tools() -> str:
    """Get list of available tools and their descriptions."""
    return ai_tool_service.get_tools_description()

@router.post("/execute")
async def execute_tool(tool_request: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool based on AI's request.
    
    Args:
        tool_request: Dictionary containing tool name and parameters
        
    Returns:
        Tool execution results
    """
    # Validate request
    errors = ai_tool_service.validate_tool_request(tool_request)
    if errors:
        raise HTTPException(status_code=400, detail=errors)
        
    # Execute tool
    result = await ai_tool_service.execute_tool(tool_request)
    
    # 检查执行结果
    if not result.get("success", False):
        raise HTTPException(
            status_code=500, 
            detail=result.get("message", "Unknown error")
        )
        
    return result 