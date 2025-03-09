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
    ) -> str:
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
        
        # 2. 分析用户意图和需要执行的步骤
        logger.info("Processing message: %s", message)
        max_retries = 3
        retry_count = 0
        current_message = message
        all_results = []
        
        while retry_count < max_retries:
            # 获取下一步计划
            plan = await self._create_plan(
                current_message,
                model=model,
                temperature=0.2,  # 使用较低的温度以获得更确定的计划
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=stream
            )
            
            if not plan:  # 如果没有计划，说明任务完成或不需要执行任何操作
                break
                
            # 只执行计划中的第一步
            step = plan[0]
            logger.info("Executing step: %s", json.dumps(step, ensure_ascii=False))
            
            # 执行工具调用
            result = await self._execute_step(step)
            all_results.append(result)
            
            # 更新工具执行结果历史
            self.context["tool_results"].append({
                "step": step,
                "result": result
            })
            
            # 修改错误判断逻辑
            has_error = False
            if result.get("status") == "error":
                has_error = True
            elif result.get("return_code", 0) != 0:
                has_error = True
            elif step['tool_name'] == 'email' and result.get('success') is False:
                has_error = True
            
            if has_error:
                failure_reason = result.get("message") or result.get("error") or "Unknown error"
                if retry_count < max_retries - 1:
                    current_message = f"{message}\n执行失败原因: {failure_reason}\n请重新规划。"
                    retry_count += 1
                    logger.info(f"Retrying plan generation (attempt {retry_count + 1})")
                    continue
                break
            
            # 将执行结果格式化为易于理解的形式
            result_summary = self._format_step_result(step, result)
            
            # 根据执行结果更新消息，让 AI 规划下一步
            current_message = f"{message}\n\n已执行步骤：\n{json.dumps(step, ensure_ascii=False)}\n\n执行结果：\n{result_summary}\n\n请根据以上结果规划下一步操作。如果任务已完成，请返回空数组 []。"
            
            # 重置重试计数
            retry_count = 0
        
        # 4. 生成最终响应
        response = await self._generate_response(
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
        
        # 5. 更新对话历史
        self.context["conversation_history"].append({
            "role": "assistant",
            "content": response
        })
        
        return response
    
    async def _create_plan(
        self,
        message: str,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stream: bool = False
    ) -> List[Dict[str, Any]]:
        """Create an execution plan based on user's message."""
        try:
            # 如果消息中包含明确的删除邮件指令，直接返回删除邮件的计划
            if any(keyword in message for keyword in ['删除邮件', '删除它', '删除这封邮件']):
                # 从上下文中获取最近的邮件 ID
                recent_results = []
                for item in self.context["tool_results"][::-1]:  # 倒序遍历
                    if item["step"]["tool_name"] == "email" and item["step"]["parameters"].get("action") == "list_emails":
                        if item["result"].get("success") and item["result"].get("result", {}).get("emails"):
                            emails = item["result"]["result"]["emails"]
                            if emails:
                                message_id = emails[0].get("message_id")
                                if message_id:
                                    return [{
                                        "tool_name": "email",
                                        "parameters": {
                                            "action": "delete_email",
                                            "message_id": message_id
                                        }
                                    }]
                        break  # 只检查最近的一次邮件列表结果
                
                logger.warning("未找到要删除的邮件 ID")
                return []
            
            # 构建用户提示词，包含完整对话历史
            history = []
            seen_messages = set()  # 用于去重
            
            for msg in self.context["conversation_history"]:
                msg_content = f"{msg['role']}：{msg['content']}"
                if msg_content not in seen_messages:
                    if msg["role"] == "user":
                        history.append(f"用户：{msg['content']}")
                    else:
                        history.append(f"助手：{msg['content']}")
                    seen_messages.add(msg_content)
            
            # 添加当前消息
            current_msg = f"用户：{message}"
            if current_msg not in seen_messages:
                history.append(current_msg)
                seen_messages.add(current_msg)
            
            # 构建强化的用户提示词
            user_prompt = "当前对话历史：\n" + "\n".join(history) + "\n\n"
            user_prompt += """请仔细分析用户的最新消息并生成下一步的执行计划。

你必须以 JSON 数组格式返回执行计划，格式如下：
[
  {
    "tool_name": "工具名称",
    "parameters": {
      "参数名": "参数值"
    }
  }
]

例如，如果用户要查看邮件，你应该返回：
[
  {
    "tool_name": "email",
    "parameters": {
      "action": "list_emails"
    }
  }
]

如果任务已完成或不需要使用工具，返回空数组 []。
不要返回任何其他格式的内容，必须是合法的 JSON 数组。"""
            
            # 调用 AI 服务生成执行计划
            response = await self.tool_service.chat_completion(
                user_prompt,
                system_prompt=self.system_prompt,  # 添加系统提示词
                model=model,
                temperature=0.2,  # 使用较低的温度以获得更确定的执行计划
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty
            )
            
            logger.info("AI 响应:\n%s", response)
            
            try:
                # 如果响应中包含其他文本，尝试提取 JSON 部分
                if '```json' in response:
                    json_str = response.split('```json')[1].split('```')[0].strip()
                    logger.debug("提取的 JSON:\n%s", json_str)
                else:
                    json_str = response.strip()
                    logger.debug("使用完整响应作为 JSON:\n%s", json_str)
                
                plan = json.loads(json_str)
                if not isinstance(plan, list):
                    logger.warning("响应格式错误，期望 list 但得到: %s", type(plan))
                    return []
                
                # 验证计划中的每个步骤
                valid_plan = []
                for step in plan:
                    if not isinstance(step, dict):
                        continue
                    
                    tool_name = step.get("tool_name")
                    parameters = step.get("parameters", {})
                    
                    # 检查工具是否存在
                    tool_def = self.tool_manager.get_tool_description(tool_name)
                    if not tool_def:
                        logger.warning("未找到工具: %s", tool_name)
                        continue
                    
                    # 验证参数
                    valid_params = {}
                    has_invalid_params = False
                    
                    for param_name, param_info in tool_def["parameters"].items():
                        if param_name in parameters:
                            valid_params[param_name] = parameters[param_name]
                        elif param_info.get("required", False):  # 默认参数为非必需
                            logger.warning("工具 %s 缺少必需参数: %s", tool_name, param_name)
                            has_invalid_params = True
                            break
                    
                    if not has_invalid_params:
                        # 所有参数都有效
                        step["parameters"] = valid_params
                        valid_plan.append(step)
                
                if valid_plan:
                    logger.info("生成的执行计划:\n%s", json.dumps(valid_plan, ensure_ascii=False, indent=2))
                else:
                    logger.warning("没有生成有效的执行计划")
                
                return valid_plan
                
            except json.JSONDecodeError as e:
                logger.error("Failed to parse AI response as JSON: %s\nError: %s", response, str(e))
                return []
            
        except Exception as e:
            logger.error("Failed to create plan: %s", str(e), exc_info=True)
            return []
    
    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step in the plan.
        
        Args:
            step: Step definition including tool name and parameters
            
        Returns:
            Step execution results
        """
        tool_name = step.get("tool_name")
        parameters = step.get("parameters", {})
        
        # 验证工具是否存在
        tool_definitions = self.tool_manager.get_tool_descriptions()
        tool_def = next((t for t in tool_definitions if t["name"] == tool_name), None)
        
        if not tool_def:
            return {
                "success": False,
                "message": f"Unknown tool: {tool_name}"
            }
            
        # 验证参数
        missing_params = []
        for param_name, param_info in tool_def["parameters"].items():
            if param_info.get("required", False) and param_name not in parameters:
                missing_params.append(param_name)
                
        if missing_params:
            return {
                "success": False,
                "message": f"Missing required parameters for {tool_name}: {', '.join(missing_params)}"
            }
            
        # 执行工具
        try:
            result = await self.tool_service.execute_tool_from_ai({
                "tool_name": tool_name,
                "parameters": parameters
            })
            
            # 对特定工具的结果进行处理
            if tool_name == 'micloud':
                try:
                    if result.get("status") == "success" and isinstance(result.get("text"), dict):
                        text_obj = result["text"]
                        if isinstance(text_obj.get("text"), dict):
                            text_data = text_obj["text"]
                            if isinstance(text_data, dict) and "markdown" in text_data:
                                return text_data["markdown"]
                        elif isinstance(text_obj, dict) and "markdown" in text_obj:
                            return text_obj["markdown"]
                except Exception as e:
                    logger.error(f"处理 micloud 结果失败: {str(e)}")
            
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": str(e)
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
            
            # 2. 分析用户意图和生成执行计划
            logger.info("Processing message: %s", message)
            
            # 生成执行计划
            plan = await self._create_plan(
                message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=True
            )
            
            if plan:
                # 生成计划响应
                plan_md = "使用工具：\n\n```json\n" + json.dumps(plan, ensure_ascii=False, indent=2) + "\n```\n"
                yield {
                    "type": "plan",
                    "content": plan_md
                }
                
                # 3. 执行计划中的每个步骤
                results = []
                for step in plan:
                    # 发送正在执行的步骤信息
                    yield {
                        "type": "step_start",
                        "content": f"正在执行: {step['tool_name']}"
                    }
                    
                    # 异步执行步骤
                    result = await self._execute_step(step)
                    results.append(result)
                    
                    # 处理工具执行结果
                    if isinstance(result, dict):
                        if result.get("success") is False:
                            error_message = result.get("result", "未知错误")
                            yield {
                                "type": "error",
                                "content": error_message
                            }
                            continue
                        
                        if "result" in result:
                            yield {
                                "type": "step_result",
                                "content": result["result"]
                            }
                        else:
                            step_md = self._format_step_result(step, result)
                            if step_md.strip():
                                yield {
                                    "type": "step_result",
                                    "content": step_md
                                }
                    elif isinstance(result, str):
                        if result.strip():
                            yield {
                                "type": "step_result",
                                "content": result
                            }
                    
                    # 更新工具执行结果历史
                    self.context["tool_results"].append({
                        "step": step,
                        "result": result
                    })
                
                # 4. 生成最终响应
                yield {
                    "type": "thinking",
                    "content": "##AI总结：\n"
                }
                
                response = await self._generate_response(
                    message,
                    results,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    stream=True
                )
                
                # 5. 更新对话历史
                self.context["conversation_history"].append({
                    "role": "assistant",
                    "content": response
                })
                
                # 6. 返回最终响应
                yield {
                    "type": "response",
                    "content": response
                }
            else:
                # 如果没有执行计划，直接生成响应
                yield {
                    "type": "thinking",
                    "content": "##AI总结：\n"
                }
                
                response = await self._generate_response(
                    message,
                    [],
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
                
                # 返回响应
                yield {
                    "type": "response",
                    "content": response
                }
            
        except Exception as e:
            logger.error("Error in stream_message: %s", str(e), exc_info=True)
            yield {
                "type": "error",
                "content": f"处理消息时发生错误: {str(e)}"
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
                    md += f"**内容:**\n```\n{doc.get('content', '无内容')}\n```\n"
                    md += f"**创建时间:** {doc.get('created_at', 'N/A')}\n\n"
                return md
            return "搜索结果格式错误\n\n"
            
        elif operation == 'create':
            if isinstance(data, dict):
                md = "成功创建文档：\n\n"
                md += f"**文档 ID:** `{data.get('id', 'N/A')}`\n"
                md += f"**标题:** {data.get('title', '无标题')}\n"
                md += f"**内容:**\n```\n{data.get('content', '无内容')}\n```\n"
                md += f"**创建时间:** {data.get('created_at', 'N/A')}\n\n"
                return md
            return "创建文档格式错误\n\n"
            
        elif operation == 'update':
            if isinstance(data, dict):
                md = "成功更新文档：\n\n"
                md += f"**文档 ID:** `{data.get('id', 'N/A')}`\n"
                md += f"**标题:** {data.get('title', '无标题')}\n"
                md += f"**内容:**\n```\n{data.get('content', '无内容')}\n```\n"
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
                md += f"**内容:**\n```\n{data.get('content', '无内容')}\n```\n"
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
            if isinstance(result.get('success'), bool) and result.get('result'):
                result_data = result['result']
                # 检查是否有 status 和 emails 字段
                if result_data.get('status') == 'success' and isinstance(result_data.get('emails'), list):
                    emails = result_data['emails']
                    md = f"找到 {len(emails)} 封邮件：\n\n"
                    
                    for email in emails:
                        md += "---\n"
                        message_id = email.get('message_id', 'N/A')
                        subject = email.get('subject', '无主题')
                        sender = email.get('from', '未知')
                        date = email.get('date', '未知')
                        body = email.get('body', '')
                        
                        md += f"**邮件 ID:** `{message_id}`\n"
                        md += f"**主题:** {subject}\n"
                        md += f"**发件人:** {sender}\n"
                        md += f"**日期:** {date}\n"
                        
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
                            
                            md += f"**内容预览:**\n```\n{preview}\n```\n"
                        
                        # 添加其他可能有用的字段
                        for key, value in email.items():
                            if key not in ['message_id', 'subject', 'from', 'date', 'body']:
                                md += f"**{key}:** {value}\n"
                        
                        md += "\n"
                    return md
            
            # 如果数据格式不是预期的，返回原始信息以供调试
            return f"邮件信息（原始格式）：\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n"
            
        elif action == 'delete_email':
            if result.get('success'):
                return "邮件已成功删除\n\n"
            else:
                error = result.get('error') or result.get('message') or '未知错误'
                return f"删除邮件失败：{error}\n\n"
        
        # 如果是其他操作或结果格式完全不符合预期，返回原始信息
        return f"工具返回结果（原始格式）：\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n"
    
    def _format_system_command_result(self, result: Dict[str, Any]) -> str:
        """Format system command result as markdown.
        
        Args:
            result: Command execution result
            
        Returns:
            Formatted markdown string
        """
        # 直接返回原始结果的JSON字符串
        return json.dumps(result, ensure_ascii=False, indent=2)