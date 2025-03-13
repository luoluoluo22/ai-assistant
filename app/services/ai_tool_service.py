"""AI tool execution service."""

import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
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
        logger.info("当前使用的模型配置: %s", settings.DEFAULT_MODEL)
        logger.info("当前使用的API URL: %s", settings.OPENAI_BASE_URL)
    
    async def chat_completion(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> str:
        """发送聊天补全请求。
        
        Args:
            prompt: 提示词
            system_prompt: 系统提示词
            model: 使用的模型
            temperature: 采样温度
            max_tokens: 最大生成token数
            top_p: 核采样阈值
            frequency_penalty: 频率惩罚
            presence_penalty: 存在惩罚
            
        Returns:
            模型的响应文本
        """
        logger.info("发送请求到大模型服务")
        logger.info("请求参数: model=%s, temperature=%.2f, max_tokens=%s", 
                   model, temperature, max_tokens)
        
        # 打印系统提示词和用户提示词
        if system_prompt:
            logger.info("系统提示词:\n%s", system_prompt)
        logger.info("用户提示词:\n%s", prompt)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            async with aiohttp.ClientSession() as session:
                # 保持模型名称的原始大小写
                model_name = model.strip()
                
                request_data = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "frequency_penalty": frequency_penalty,
                    "presence_penalty": presence_penalty,
                    "stream": False
                }
                
                logger.debug("发送请求数据:\n%s", json.dumps(request_data, ensure_ascii=False, indent=2))
                
                async with session.post(
                    settings.OPENAI_BASE_URL + "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=request_data
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error("API请求失败: %s\n响应内容: %s", response.status, response_text)
                        return f"API请求失败: {response.status}"
                    
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error("解析响应JSON失败: %s\n响应内容: %s", str(e), response_text)
                        return f"解析响应失败: {str(e)}"
                    
                    logger.debug("API原始响应: %s", json.dumps(data, ensure_ascii=False, indent=2))
                    
                    if not data.get("choices"):
                        error_msg = f"API响应中没有choices字段: {json.dumps(data, ensure_ascii=False)}"
                        logger.error(error_msg)
                        return error_msg
                    
                    content = data["choices"][0]["message"]["content"]
                    if not content.strip():
                        logger.warning("API返回了空响应")
                        return "API返回了空响应"
                        
                    logger.info("模型响应内容:\n%s", content)
                    return content
                    
        except aiohttp.ClientError as e:
            error_msg = f"网络请求失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
            
    async def stream_chat_completion(
        self,
        prompt: str,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> AsyncGenerator[str, None]:
        """流式发送聊天补全请求。
        
        Args:
            prompt: 提示词
            model: 使用的模型
            temperature: 采样温度
            max_tokens: 最大生成token数
            top_p: 核采样阈值
            frequency_penalty: 频率惩罚
            presence_penalty: 存在惩罚
            
        Yields:
            模型响应的数据块
        """
        logger.info("发送流式请求到大模型服务")
        logger.info("请求参数: model=%s, temperature=%.2f, max_tokens=%s", 
                   model, temperature, max_tokens)
        logger.info("提示词内容:\n%s", prompt)
        
        messages = [{"role": "user", "content": prompt}]
        full_response = ""
        
        try:
            async with aiohttp.ClientSession() as session:
                # 保持模型名称的原始大小写
                model_name = model.strip()
                
                async with session.post(
                    settings.OPENAI_BASE_URL + "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p,
                        "frequency_penalty": frequency_penalty,
                        "presence_penalty": presence_penalty,
                        "stream": True
                    }
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("流式API请求失败: %s, 错误: %s", response.status, error_text)
                        yield ""
                        return
                        
                    async for line in response.content:
                        if line:
                            try:
                                line = line.decode('utf-8').strip()
                                if line.startswith('data: '):
                                    line = line[6:]  # 移除 "data: " 前缀
                                if line == '[DONE]':
                                    continue
                                    
                                data = json.loads(line)
                                if not data.get("choices"):
                                    continue
                                    
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    full_response += content
                                    yield content
                                    
                            except json.JSONDecodeError:
                                logger.warning("无法解析响应行: %s", line)
                                continue
                            except Exception as e:
                                logger.error("处理响应行时出错: %s", str(e), exc_info=True)
                                continue
                                
        except Exception as e:
            logger.error("流式请求失败: %s", str(e), exc_info=True)
            yield ""
            
        logger.info("流式响应完整内容:\n%s", full_response)
    
    def get_tools_description(self) -> str:
        """Get formatted description of available tools.
        
        Returns:
            JSON string containing tool descriptions
        """
        descriptions = self.tool_manager.get_tool_descriptions()
        return json.dumps(descriptions, indent=2)
    
    async def execute_tool(self, tool_request: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用
        
        Args:
            tool_request: 工具调用请求，包含工具名称和参数
            
        Returns:
            工具执行结果
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
                "status": "error",
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