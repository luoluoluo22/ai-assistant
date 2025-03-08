"""AI tool execution service."""

import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from ..tools.manager import ToolManager
from ..core.config import settings

# 配置日志
logger = logging.getLogger(__name__)

class AIToolService:
    """Service for AI to interact with tools."""
    
    def __init__(self):
        """Initialize the service."""
        self.tool_manager = ToolManager()
        logger.info("AI tool service initialized")
    
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        timeout: int = 30  # 添加超时参数，默认 30 秒
    ) -> str:
        """Generate text using AI model."""
        try:
            logger.info("发送请求到大模型服务")
            logger.info(f"请求参数: model={model}, temperature={temperature:.2f}, max_tokens={max_tokens}")
            
            headers = {
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.LLM_API_URL,
                    headers=headers,  # 添加认证头
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p,
                        "frequency_penalty": frequency_penalty,
                        "presence_penalty": presence_penalty
                    },
                    timeout=aiohttp.ClientTimeout(total=timeout)  # 设置超时
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"AI 服务返回错误: {response.status} - {response_text}")
                        return f"AI 服务返回错误: {response.status} - {response_text}"
                    
                    try:
                        response_data = json.loads(response_text)
                        # OpenRouter API 返回格式处理
                        if "choices" in response_data:
                            return response_data["choices"][0]["message"]["content"]
                        return response_data.get("response", "")
                    except json.JSONDecodeError:
                        logger.error(f"解析 AI 服务响应失败: {response_text}")
                        return "解析 AI 服务响应失败"
                        
        except asyncio.TimeoutError:
            logger.error("AI 服务请求超时")
            return "AI 服务请求超时，请重试"
        except Exception as e:
            logger.error(f"生成文本失败: {str(e)}", exc_info=True)
            return f"生成文本失败: {str(e)}"
    
    def get_tools_description(self) -> str:
        """Get formatted description of available tools.
        
        Returns:
            JSON string containing tool descriptions
        """
        descriptions = self.tool_manager.get_tool_descriptions()
        return json.dumps(descriptions, indent=2)
    
    async def execute_tool_from_ai(self, tool_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool based on AI's request.
        
        Args:
            tool_request: Tool execution request from AI
            
        Returns:
            Tool execution results
        """
        try:
            tool_name = tool_request.get("tool_name")
            parameters = tool_request.get("parameters", {})
            
            if not tool_name:
                raise ValueError("未指定工具名称")
                
            logger.info("执行工具: %s", tool_name)
            logger.debug("工具参数: %s", json.dumps(parameters, ensure_ascii=False))
            
            result = await self.tool_manager.execute_tool(tool_name, **parameters)
            
            # 记录工具执行结果
            logger.info("工具执行完成")
            logger.debug("执行结果: %s", json.dumps(result, ensure_ascii=False, indent=2))
            
            return result
            
        except Exception as e:
            logger.error("工具执行失败: %s", str(e), exc_info=True)
            return {
                "success": False,
                "message": str(e)
            }
    
    def validate_tool_request(self, tool_request: Dict[str, Any]) -> List[str]:
        """Validate a tool request from AI.
        
        Args:
            tool_request: The tool request to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        if not isinstance(tool_request, dict):
            return ["Tool request must be a dictionary"]
            
        if "tool_name" not in tool_request:
            errors.append("Tool name is required")
            
        tool_name = tool_request.get("tool_name")
        parameters = tool_request.get("parameters", {})
        
        # Get tool description if tool exists
        descriptions = self.tool_manager.get_tool_descriptions()
        tool_desc = next((t for t in descriptions if t["name"] == tool_name), None)
        
        if not tool_desc:
            errors.append(f"Tool '{tool_name}' not found")
            return errors
            
        # Validate required parameters
        for param_name, param_info in tool_desc["parameters"].items():
            if param_info.get("required", False) and param_name not in parameters:
                errors.append(f"Required parameter '{param_name}' is missing")
                
        return errors 