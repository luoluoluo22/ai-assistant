"""System command tool implementation."""

import asyncio
from typing import Dict, Any, List
from .base import BaseTool
import logging
import sys

logger = logging.getLogger(__name__)

class SystemCommandTool(BaseTool):
    """系统命令执行工具"""
    
    name: str = "system_command"
    description: str = """系统命令执行工具，用于执行系统命令并获取结果。
    支持常见的系统命令，如：ls、pwd、cd、cat等。
    在Windows系统上会自动转换为对应的命令。
    """
    
    # 添加字段定义
    is_windows: bool = sys.platform == "win32"
    
    def __init__(self):
        """Initialize the tool."""
        super().__init__()
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get the parameters schema for the tool."""
        return {
            "command": {
                "type": "string",
                "description": "要执行的系统命令",
                "required": True
            }
        }
    
    @property
    def examples(self) -> List[str]:
        """Get example usages of the tool."""
        return [
            "ls -l",
            "pwd",
            "cat file.txt",
            "ps aux | grep python"
        ]
    
    async def execute(self, command: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute a system command with timeout.
        
        Args:
            command: Command to execute
            **kwargs: Additional parameters (ignored)
            
        Returns:
            Command execution results
        """
        try:
            # 设置超时时间为 30 秒
            timeout = 30
            
            # 创建子进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # 等待进程完成，带超时
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "return_code": process.returncode
                }
                
            except asyncio.TimeoutError:
                # 如果超时，强制终止进程
                try:
                    process.terminate()
                    await asyncio.sleep(0.1)
                    if process.returncode is None:
                        process.kill()
                except Exception as e:
                    logger.error(f"Failed to terminate process: {e}")
                
                return {
                    "stdout": "",
                    "stderr": f"Command execution timed out after {timeout} seconds",
                    "return_code": -1
                }
                
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """运行工具的方法（必需）"""
        # 这个方法是为了满足 BaseTool 的要求
        # 实际的执行逻辑在 execute 方法中
        raise NotImplementedError("请使用 execute 方法代替")

    def get_tool_definition(self) -> Dict[str, Any]:
        """获取工具定义"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples
        } 