"""Tool manager for handling system tools."""

import sys
import os
import asyncio
import subprocess
import logging
import json
from typing import Dict, Any, List, Optional
from app.tools.knowledge_base import KnowledgeBaseTool
from app.tools.web_browser import WebBrowserTool
from app.tools.email_tool import EmailTool
from app.tools.system import SystemCommandTool
from app.tools.micloud_tool import MiCloudTool

# 配置日志
logger = logging.getLogger(__name__)

class ToolManager:
    """Manager for system tools."""
    
    def __init__(self):
        """Initialize the tool manager."""
        # 初始化所有工具实例
        self.tool_instances = {
            "system_command": SystemCommandTool(),
            "knowledge_base": KnowledgeBaseTool(),
            "web_browser": WebBrowserTool(),
            "email": EmailTool(),
            "micloud": MiCloudTool()
        }
        
        # 设置工具执行函数映射
        self.tools = {
            name: self._create_tool_executor(instance)
            for name, instance in self.tool_instances.items()
        }
        
        self.is_windows = sys.platform == "win32"
        
        # Windows命令映射表
        self.windows_command_map = {
            'date': 'echo %DATE%',
            'time': 'echo %TIME%',
            'ls': 'dir',
            'cat': 'type',
            'clear': 'cls',
            'pwd': 'cd',
            'rm': 'del /Q',
            'cp': 'copy',
            'mv': 'move',
            'touch': 'echo.>',
            'grep': 'findstr',
            'kill': 'taskkill /F /PID',
            'ps': 'tasklist',
            'df': 'wmic logicaldisk get size,freespace,caption',
            'whoami': 'echo %USERNAME%',
            'hostname': 'echo %COMPUTERNAME%',
            'uname': 'ver',
            'more': 'type',  # 替换为非交互式的type命令
            'less': 'type',  # 替换为非交互式的type命令
            'head': lambda f: f'powershell -Command "Get-Content {f} -Head 10"',
            'tail': lambda f: f'powershell -Command "Get-Content {f} -Tail 10"',
        }
        
        logger.info(f"Tool manager initialized. Platform: {sys.platform}")
    
    def _create_tool_executor(self, tool_instance):
        """创建工具执行器函数"""
        async def executor(**kwargs):
            return await tool_instance.execute(**kwargs)
        return executor
    
    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """Get descriptions of available tools."""
        return [
            tool.get_tool_definition()
            for tool in self.tool_instances.values()
        ]
    
    def get_tool_description(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get description of a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool definition dict if found, None otherwise
        """
        if tool_name not in self.tool_instances:
            return None
        return self.tool_instances[tool_name].get_tool_definition()
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool with given parameters."""
        if tool_name not in self.tools:
            logger.error("Tool not found: %s", tool_name)
            return {
                "success": False,
                "message": f"Unknown tool: {tool_name}"
            }
        
        tool_func = self.tools[tool_name]
        try:
            result = await tool_func(**kwargs)
            
            # 如果结果已经是标准格式，直接返回
            if isinstance(result, dict) and "success" in result:
                return result
            
            # 包装结果为标准格式
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error("Tool execution failed: %s", str(e), exc_info=True)
            return {
                "success": False,
                "message": str(e)
            }
    
    def _process_windows_command(self, command: str) -> str:
        """处理Windows特定的命令"""
        # 分割命令和参数
        parts = command.strip().split()
        base_cmd = parts[0].lower()
        
        # 检查是否需要特殊处理
        if base_cmd in self.windows_command_map:
            mapped_cmd = self.windows_command_map[base_cmd]
            if callable(mapped_cmd):
                # 如果是函数，传入剩余参数
                return mapped_cmd(' '.join(parts[1:])) if len(parts) > 1 else mapped_cmd('')
            else:
                # 如果是字符串，替换命令并保留参数
                return f"{mapped_cmd} {' '.join(parts[1:])}" if len(parts) > 1 else mapped_cmd
                
        # 处理管道和重定向
        if '|' in command or '>' in command or '<' in command:
            return f'cmd /c {command}'
            
        return command
    
    async def execute_system_command(self, command: str) -> Dict[str, Any]:
        """Execute a system command."""
        try:
            # 获取当前工作目录
            cwd = os.getcwd()
            logger.info(f"Executing command in directory: {cwd}")
            
            # 处理Windows特定的命令
            if self.is_windows:
                original_command = command
                command = self._process_windows_command(command)
                logger.info(f"Original command: {original_command}")
                logger.info(f"Processed command: {command}")
                
                # 设置环境变量以减少交互
                env = os.environ.copy()
                env['PROMPT'] = '$P$G'
                
                # 使用cmd.exe执行命令
                process = await asyncio.to_thread(
                    subprocess.run,
                    ["cmd.exe", "/c", command],
                    capture_output=True,
                    text=False,
                    cwd=cwd,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=30  # 30秒超时
                )
            else:
                # Unix系统直接执行命令
                process = await asyncio.to_thread(
                    subprocess.run,
                    ["/bin/sh", "-c", command],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=cwd,
                    timeout=30
                )
            
            # 处理输出编码
            if self.is_windows:
                try:
                    stdout_str = process.stdout.decode('gbk', errors='replace') if process.stdout else ""
                    stderr_str = process.stderr.decode('gbk', errors='replace') if process.stderr else ""
                except Exception as e:
                    logger.error(f"Failed to decode output: {str(e)}", exc_info=True)
                    stdout_str = process.stdout.decode('utf-8', errors='replace') if process.stdout else ""
                    stderr_str = process.stderr.decode('utf-8', errors='replace') if process.stderr else ""
            else:
                stdout_str = process.stdout
                stderr_str = process.stderr
            
            logger.info(f"Process completed with return code: {process.returncode}")
            if stdout_str:
                logger.debug(f"Process stdout: {stdout_str}")
            if stderr_str:
                logger.debug(f"Process stderr: {stderr_str}")
            
            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": process.returncode
            }
            
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Command timed out after {e.timeout}s")
            return {
                "stdout": "",
                "stderr": f"Command execution timed out after {e.timeout} seconds",
                "return_code": -1
            }
        except Exception as e:
            logger.error(f"Failed to execute command: {str(e)}", exc_info=True)
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
    
    async def execute_knowledge_base(self, **kwargs) -> Dict[str, Any]:
        """执行知识库工具"""
        operation = kwargs.pop('operation', 'search')  # 默认操作为搜索
        return await self.tool_instances["knowledge_base"].execute(operation, **kwargs)

    async def execute_web_browser(self, **kwargs) -> Dict[str, Any]:
        """执行网页浏览工具"""
        operation = kwargs.pop('operation')  # 操作类型是必需的
        return await self.tool_instances["web_browser"].execute(operation, **kwargs)

    async def execute_micloud(self, **kwargs) -> Dict[str, Any]:
        """执行小米云服务工具操作"""
        try:
            result = await self.tool_instances["micloud"].execute(**kwargs)
            return result
        except Exception as e:
            logger.error("MiCloud tool execution failed: %s", str(e), exc_info=True)
            return {
                "success": False,
                "message": str(e)
            }

    async def execute_email(self, **kwargs) -> Dict[str, Any]:
        """执行邮件工具操作"""
        try:
            result = await self.tool_instances["email"].execute(**kwargs)
            return result
        except Exception as e:
            logger.error("Email tool execution failed: %s", str(e), exc_info=True)
            return {
                "success": False,
                "message": str(e)
            }

    def get_available_tools(self) -> List[str]:
        """获取可用的工具列表"""
        return list(self.tool_instances.keys())