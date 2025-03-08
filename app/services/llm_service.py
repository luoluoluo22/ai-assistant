from typing import List, Optional
from app.core.config import settings
from app.models.chat import Message
from app.models.command import CommandRequest
from app.services.command_service import command_service
from openai import OpenAI
import json

class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        
    def get_completion(
        self,
        messages: List[Message],
        model: Optional[str] = None
    ) -> str:
        """
        获取AI模型的回复
        """
        # 使用默认模型或指定模型
        model = model or settings.DEFAULT_MODEL
        
        # 添加系统提示,告诉AI如何处理命令
        system_message = {
            "role": "system",
            "content": """你是一个强大的AI助手,可以帮助用户执行命令。
当需要执行命令时,请以以下JSON格式返回:
{
    "type": "command",
    "command": "要执行的命令",
    "working_directory": "工作目录(可选)",
    "is_background": false,
    "require_approval": true,
    "explanation": "命令的解释"
}
对于普通对话,直接返回文本回复即可。"""
        }
        
        formatted_messages = [
            system_message,
            *[{"role": msg.role, "content": msg.content} for msg in messages]
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=formatted_messages
            )
            content = response.choices[0].message.content
            
            # 尝试解析是否为命令JSON
            try:
                command_data = json.loads(content)
                if isinstance(command_data, dict) and command_data.get("type") == "command":
                    # 执行命令
                    result = command_service.execute_command(
                        command=command_data["command"],
                        working_directory=command_data.get("working_directory"),
                        is_background=command_data.get("is_background", False)
                    )
                    return f"""命令执行结果:
命令: {result.command}
输出: {result.output}
错误: {result.error or '无'}
退出码: {result.exit_code}
执行时间: {result.execution_time:.2f}秒
工作目录: {result.working_directory}"""
            except json.JSONDecodeError:
                pass
                
            return content
            
        except Exception as e:
            print(f"API调用错误: {str(e)}")
            raise

llm_service = LLMService() 