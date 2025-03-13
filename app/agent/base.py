"""Base agent for handling user requests."""

import sys
import json
import logging
import uuid
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from ..services.ai_tool_service import AIToolService
from ..core.config import settings
from ..core.prompts import generate_system_prompt, generate_base_system_prompt, generate_result_summary_prompt
from ..tools.manager import ToolManager

# 配置日志
logger = logging.getLogger(__name__)

class Agent:
    """Base agent class for handling user requests."""
    
    def __init__(self):
        """Initialize the agent."""
        self.tool_service = AIToolService()
        self.tool_manager = ToolManager()
        self.context = {
            "conversation_history": [],
            "tool_results": [],
            "memory": {},
            "os": sys.platform
        }
        self.system_prompt = generate_system_prompt()
        logger.info("Agent initialized with system prompt:\n%s", self.system_prompt)
    
    async def process_message(
        self,
        message: str,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process user message and return response.
        
        Args:
            message: User's natural language input
            model: Model to use for generation
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling threshold
            frequency_penalty: Frequency penalty
            presence_penalty: Presence penalty
            stream: Whether to stream the response
            
        Returns:
            Agent's response
        """
        # 1. 更新对话历史
        self.context["conversation_history"].append({
            "role": "user",
            "content": message
        })
        
        # 2. 处理用户消息并执行工具调用
        logger.info("Processing message: %s", message)
        current_message = message
        all_results = []
        max_iterations = 10  # 防止无限循环
        iteration_count = 0
        
        while iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"Iteration {iteration_count} of {max_iterations}")
            
            # 发送正在思考的提示
            yield {
                "type": "thinking",
                "content": "AI正在思考..."
            }
            
            # 获取模型响应
            response = await self.tool_service.chat_completion(
                current_message,
                system_prompt=self.system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty
            )
            
            logger.info("AI 响应:\n%s", response)
            
            # 尝试从响应中提取工具调用
            tool_call = self._extract_tool_call(response)
            
            # 如果没有工具调用或者是任务完成工具，结束循环
            if not tool_call or tool_call.get("tool_name") == "task_complete":
                break
            
            # 执行工具调用
            logger.info("Executing tool: %s", json.dumps(tool_call, ensure_ascii=False))
            result = await self._execute_step(tool_call)
            all_results.append(result)
            
            # 更新工具执行结果历史
            self.context["tool_results"].append({
                "step": tool_call,
                "result": result
            })
            
            # 将执行结果格式化为易于理解的形式
            result_summary = self._format_step_result(tool_call, result)
            
            # 更新当前消息，包含执行结果
            current_message = f"{message}\n\n已执行工具：\n{json.dumps(tool_call, ensure_ascii=False)}\n\n执行结果：\n{result_summary}\n\n请根据以上结果继续回答或执行下一个工具。如果任务已完成，请直接回答，不要调用工具。"
        
        # 3. 生成最终响应
        final_response = await self._generate_response(
            message,
            all_results,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stream=stream
        )
        
        # 4. 更新对话历史
        self.context["conversation_history"].append({
            "role": "assistant",
            "content": final_response
        })
        
        yield {
            "type": "response",
            "content": final_response
        }
    
    
    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step in the plan.
        
        Args:
            step: Step to execute
            
        Returns:
            Result of tool execution
        """
        try:
            # 记录执行计划
            logger.info("生成的执行计划:\n%s", json.dumps(step, ensure_ascii=False, indent=2))
            
            # 验证工具请求
            errors = self.tool_service.validate_tool_request(step)
            if errors:
                error_msg = f"工具请求验证失败: {', '.join(errors)}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            # 执行工具调用
            result = await self.tool_service.execute_tool(step)
            
            # 记录执行结果
            logger.debug("工具执行结果:\n%s", json.dumps(result, ensure_ascii=False, indent=2))
            
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "message": error_msg
            }
    
    async def _generate_response(
        self,
        message: str,
        results: List[Dict[str, Any]],
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stream: bool = False
    ) -> str:
        """Generate a natural language response."""
        try:
            # 构建系统提示词
            system_prompt = generate_result_summary_prompt()

            # 构建用户提示词
            user_prompt = f"用户问题：{message}\n\n"
            
            if results:
                user_prompt += "工具执行结果：\n"
                for result in results:
                    # 处理网页搜索结果
                    if isinstance(result.get("data"), dict) and "results" in result["data"]:
                        web_results = result["data"]["results"]
                        if web_results:
                            user_prompt += "\n搜索结果：\n"
                            for item in web_results:
                                title = item.get("title", "")
                                url = item.get("url", "")
                                content = item.get("content", "")
                                if content and len(content) > 1000:  # 限制每个结果的内容长度
                                    content = content[:1000] + "...(内容已截断)"
                                user_prompt += f"\n标题：{title}\n链接：{url}\n内容：{content}\n"
                    else:
                        result_str = json.dumps(result, ensure_ascii=False, indent=2)
                        if len(result_str) > 10000:  # 限制结果长度
                            result_str = result_str[:10000] + "...(结果已截断)"
                        user_prompt += result_str + "\n\n"
            else:
                user_prompt += "没有执行任何工具。\n"
            
            # 调用 AI 服务生成回复
            response = await self.tool_service.chat_completion(
                user_prompt,
                system_prompt=system_prompt,  # 添加系统提示词
                model=model,
                temperature=0.2,  # 使用较低的温度以获得更确定的回答
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error("生成回复失败: %s", str(e), exc_info=True)
            return f"生成回复时发生错误：{str(e)}"
    
    def update_memory(self, key: str, value: Any):
        """Update agent's memory.
        
        Args:
            key: Memory key
            value: Memory value
        """
        self.context["memory"][key] = value
    
    def get_memory(self, key: str) -> Optional[Any]:
        """Get value from agent's memory.
        
        Args:
            key: Memory key
            
        Returns:
            Stored value or None if not found
        """
        return self.context["memory"].get(key)
    
    def clear_memory(self):
        """Clear agent's memory."""
        self.context["memory"].clear()

    async def stream_message(
        self,
        message: str,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream process user message and yield response chunks."""
        try:
            # 1. 更新对话历史
            self.context["conversation_history"].append({
                "role": "user",
                "content": message
            })
            
            # 2. 处理用户意图和生成执行计划
            logger.info("Processing message: %s", message)
            current_message = message
            all_results = []
            max_iterations = 10  # 防止无限循环
            iteration_count = 0
            
            while iteration_count < max_iterations:
                iteration_count += 1
                logger.info(f"Iteration {iteration_count} of {max_iterations}")
                
                # 发送正在思考的提示
                yield {
                    "type": "thinking",
                    "content": "\n🤔 AI正在思考...\n"
                }
                
                # 获取模型响应
                response = await self.tool_service.chat_completion(
                    current_message,
                    system_prompt=self.system_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty
                )
                
                logger.info("AI 响应:\n%s", response)
                
                # 尝试从响应中提取工具调用
                tool_call = self._extract_tool_call(response)
                
                # 如果没有工具调用，结束循环
                if not tool_call:
                    break

                # 发送正在执行的步骤信息
                tool_info = f"\n🔧 执行工具: {tool_call['tool_name']}\n"
                tool_info += "📝 参数:\n```json\n"
                tool_info += json.dumps(tool_call.get('parameters', {}), ensure_ascii=False, indent=2)
                tool_info += "\n```\n"
                yield {
                    "type": "step_start",
                    "content": tool_info
                }
                
                # 执行工具调用
                logger.info("Executing tool: %s", json.dumps(tool_call, ensure_ascii=False))
                result = await self._execute_step(tool_call)
                all_results.append(result)
                
                # 更新工具执行结果历史
                self.context["tool_results"].append({
                    "step": tool_call,
                    "result": result
                })
                
                # 处理工具执行结果
                if isinstance(result, dict):
                    # 修改错误判断逻辑
                    has_error = False
                    if result.get("status") == "error":
                        has_error = True
                    elif result.get("return_code", 0) != 0:
                        has_error = True
                    elif tool_call['tool_name'] == 'email' and result.get('success') is False:
                        has_error = True
                    
                    if has_error:
                        error_message = result.get("message", "未知错误")
                        yield {
                            "type": "error",
                            "content": f"\n❌ 错误:\n{error_message}\n"
                        }
                        # 如果是删除邮件失败，继续尝试下一封
                        if tool_call['tool_name'] == 'email' and tool_call.get('parameters', {}).get('action') == 'delete_email':
                            continue
                        break
                    
                    # 格式化结果
                    formatted_result = self._format_step_result(tool_call, result)
                    if formatted_result.strip():
                        yield {
                            "type": "step_result",
                            "content": f"\n✅ 执行结果:\n{formatted_result}\n"
                        }
                elif isinstance(result, str):
                    if result.strip():
                        yield {
                            "type": "step_result",
                            "content": f"\n✅ 执行结果:\n{result}\n"
                        }
                
                # 将执行结果格式化为易于理解的形式
                result_summary = self._format_step_result(tool_call, result)
                
                # 更新当前消息，包含执行结果
                current_message = f"{message}\n\n已执行工具：\n{json.dumps(tool_call, ensure_ascii=False)}\n\n执行结果：\n{result_summary}\n\n请根据以上结果继续回答或执行下一个工具。如果任务已完成，请直接回答，不要调用工具。"
            
            # 如果不是通过 task_complete 结束的，生成最终响应
            if not tool_call or tool_call.get("tool_name") != "task_complete":
                yield {
                    "type": "thinking",
                    "content": "\n🤔 AI正在总结...\n"
                }
                
                response = await self._generate_response(
                    message,
                    all_results,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    stream=True
                )
                
                # 更新对话历史
                self.context["conversation_history"].append({
                    "role": "assistant",
                    "content": response
                })
                
                # 返回最终响应
                yield {
                    "type": "response",
                    "content": f"\n{response}\n"
                }
            
        except Exception as e:
            logger.error("Error in stream_message: %s", str(e), exc_info=True)
            yield {
                "type": "error",
                "content": f"\n❌ 处理消息时发生错误:\n{str(e)}\n"
            }
            
    def _format_step_result(self, step: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Format step execution result as markdown.
        
        Args:
            step: Step definition
            result: Step execution result
            
        Returns:
            Formatted markdown string
        """
        if step['tool_name'] == 'knowledge_base':
            return self._format_knowledge_base_result(step, result)
        elif step['tool_name'] == 'email':
            return self._format_email_result(step, result)
        elif isinstance(result, str):
            return result
        else:
            return self._format_system_command_result(result)
    
    def _format_knowledge_base_result(self, step: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Format knowledge base result as markdown.
        
        Args:
            step: Step definition
            result: Step execution result
            
        Returns:
            Formatted markdown string
        """
        operation = step['parameters'].get('operation')
        success = result.get("success", False)
        message = result.get("message", "")
        data = result.get("data", None)
        
        if not success:
            return f"**错误：** {message}\n"
            
        if operation == 'search':
            if isinstance(data, list):
                md = f"找到 {len(data)} 条相关知识：\n\n"
                for doc in data:
                    md += f"**文档 ID:** `{doc.get('id', 'N/A')}`\n"
                    md += f"**标题:** {doc.get('title', '无标题')}\n"
                    md += f"**内容:** \n```\n{doc.get('content', '无内容')}\n```\n"
                    md += f"**创建时间:** {doc.get('created_at', 'N/A')}\n\n"
                return md
            return "搜索结果格式错误\n\n"
            
        elif operation == 'create':
            if isinstance(data, dict):
                md = "成功创建文档：\n\n"
                md += f"**文档 ID:** `{data.get('id', 'N/A')}`\n"
                md += f"**标题:** {data.get('title', '无标题')}\n"
                md += f"**内容:** \n```\n{data.get('content', '无内容')}\n```\n"
                md += f"**创建时间:** {data.get('created_at', 'N/A')}\n\n"
                return md
            return "创建文档格式错误\n\n"
            
        elif operation == 'update':
            if isinstance(data, dict):
                md = "成功更新文档：\n\n"
                md += f"**文档 ID:** `{data.get('id', 'N/A')}`\n"
                md += f"**标题:** {data.get('title', '无标题')}\n"
                md += f"**内容:** \n```\n{data.get('content', '无内容')}\n```\n"
                md += f"**更新时间:** {data.get('updated_at', 'N/A')}\n\n"
                return md
            return "更新文档格式错误\n\n"
            
        elif operation == 'delete':
            return f"成功删除文档\n\n"
            
        elif operation == 'get':
            if isinstance(data, dict):
                md = "获取到的文档：\n\n"
                md += f"**文档 ID:** `{data.get('id', 'N/A')}`\n"
                md += f"**标题:** {data.get('title', '无标题')}\n"
                md += f"**内容:** \n```\n{data.get('content', '无内容')}\n```\n"
                md += f"**创建时间:** {data.get('created_at', 'N/A')}\n\n"
                return md
            return "获取文档格式错误\n\n"
            
        return f"未知操作类型：{operation}\n\n"
    
    def _format_email_result(self, step: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Format email tool result as markdown.
        
        Args:
            step: Step definition
            result: Step execution result
            
        Returns:
            Formatted markdown string
        """
        action = step['parameters'].get('action')
        
        # 记录原始结果用于调试
        logger.debug("Email result: %s", json.dumps(result, ensure_ascii=False))
        
        if action == 'list_emails':
            # 首先检查是否有 success 和 result 字段
            if result.get('success') and isinstance(result.get('result', {}).get('emails'), list):
                emails = result['result']['emails']
                if not emails:
                    return "没有找到任何邮件"
                
                md = f"找到 {len(emails)} 封邮件：\n\n"
                for email in emails:
                    md += "---\n"
                    message_id = email.get('message_id', 'N/A')
                    subject = email.get('subject', '无主题')
                    sender = email.get('from', '未知')
                    date = email.get('date', '未知')
                    body = email.get('body', '')
                    
                    md += f"📧 邮件 ID: `{message_id}`\n"
                    md += f"📑 主题: {subject}\n"
                    md += f"👤 发件人: {sender}\n"
                    md += f"📅 日期: {date}\n"
                    
                    if body:
                        # 如果是 HTML 内容，尝试提取纯文本
                        if body.strip().startswith('<!DOCTYPE html') or body.strip().startswith('<html'):
                            # 简单提取文本，去除 HTML 标签
                            text_content = body.replace('</div>', '\n').replace('</p>', '\n')
                            for tag in ['<br />', '<br/>', '<br>', '\r\n', '\n\n']:
                                text_content = text_content.replace(tag, '\n')
                                
                            # 移除所有 HTML 标签
                            import re
                            text_content = re.sub(r'<[^>]+>', '', text_content)
                            
                            # 清理空白行和多余空格
                            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                            text_content = '\n'.join(lines)
                            
                            # 限制预览长度
                            preview = text_content[:500] + ('...' if len(text_content) > 500 else '')
                        else:
                            preview = body[:500] + ('...' if len(body) > 500 else '')
                        
                        md += f"📝 内容预览:\n```\n{preview}\n```\n"
                    
                    md += "\n"
                return md
            
            return "邮件列表获取失败或格式错误"
            
        elif action == 'delete_email':
            if result.get('success'):
                return "✅ 邮件已成功删除"
            else:
                error = result.get('message', '未知错误')
                return f"❌ 删除邮件失败：{error}"
        
        # 如果是其他操作或结果格式完全不符合预期，返回原始信息
        return f"工具返回结果：\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"
    
    def _format_system_command_result(self, result: Dict[str, Any]) -> str:
        """Format system command result as markdown.
        
        Args:
            result: Command execution result
            
        Returns:
            Formatted markdown string
        """
        # 直接返回原始结果的JSON字符串
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """从模型响应中提取工具调用信息
        
        Args:
            response: 模型的响应文本
            
        Returns:
            工具调用信息字典，如果没有找到工具调用则返回None
        """
        try:
            # 尝试查找JSON格式的工具调用
            # 1. 查找```json块
            if '```json' in response:
                json_blocks = response.split('```json')
                for block in json_blocks[1:]:  # 跳过第一个分割（前导文本）
                    json_str = block.split('```')[0].strip()
                    try:
                        tool_data = json.loads(json_str)
                        if isinstance(tool_data, dict) and 'tool_name' in tool_data:
                            return tool_data
                        elif isinstance(tool_data, list) and len(tool_data) > 0 and isinstance(tool_data[0], dict) and 'tool_name' in tool_data[0]:
                            return tool_data[0]
                    except json.JSONDecodeError:
                        continue
            
            # 2. 查找```块（可能是其他代码块格式）
            if '```' in response:
                code_blocks = response.split('```')
                for i in range(1, len(code_blocks), 2):  # 只检查代码块内容
                    try:
                        tool_data = json.loads(code_blocks[i].strip())
                        if isinstance(tool_data, dict) and 'tool_name' in tool_data:
                            return tool_data
                        elif isinstance(tool_data, list) and len(tool_data) > 0 and isinstance(tool_data[0], dict) and 'tool_name' in tool_data[0]:
                            return tool_data[0]
                    except json.JSONDecodeError:
                        continue
            
            # 3. 尝试在整个响应中查找JSON对象
            # 查找可能的JSON对象开始和结束位置
            start_pos = response.find('{')
            if start_pos != -1:
                # 尝试解析从这个位置开始的JSON
                try:
                    # 使用简单的括号匹配来找到JSON对象的结束位置
                    brace_count = 0
                    end_pos = start_pos
                    for i in range(start_pos, len(response)):
                        if response[i] == '{':
                            brace_count += 1
                        elif response[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break
                    
                    if end_pos > start_pos:
                        json_str = response[start_pos:end_pos]
                        tool_data = json.loads(json_str)
                        if isinstance(tool_data, dict) and 'tool_name' in tool_data:
                            return tool_data
                except (json.JSONDecodeError, IndexError):
                    pass
            
            # 4. 查找数组形式的JSON
            start_pos = response.find('[')
            if start_pos != -1:
                try:
                    # 使用简单的括号匹配来找到JSON数组的结束位置
                    bracket_count = 0
                    end_pos = start_pos
                    for i in range(start_pos, len(response)):
                        if response[i] == '[':
                            bracket_count += 1
                        elif response[i] == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                end_pos = i + 1
                                break
                    
                    if end_pos > start_pos:
                        json_str = response[start_pos:end_pos]
                        tool_data = json.loads(json_str)
                        if isinstance(tool_data, list) and len(tool_data) > 0 and isinstance(tool_data[0], dict) and 'tool_name' in tool_data[0]:
                            return tool_data[0]
                except (json.JSONDecodeError, IndexError):
                    pass
            
            return None
        except Exception as e:
            logger.error("从响应中提取工具调用失败: %s", str(e), exc_info=True)
            return None