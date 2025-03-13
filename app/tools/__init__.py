"""Tool management module."""

from typing import Dict, Type
from .base import BaseTool
from .system import SystemCommandTool
from .web_browser import WebBrowserTool
from .email_tool import EmailTool
from .micloud_tool import MiCloudTool
from .task_complete import TaskCompleteTool

# Tool registry
tools_registry: Dict[str, Type[BaseTool]] = {
    "system_command": SystemCommandTool,
    "web_browser": WebBrowserTool,
    "email": EmailTool,
    "micloud": MiCloudTool,
    "task_complete": TaskCompleteTool
}

"""Tools package for system interactions."""

__all__ = [
    'BaseTool',
    'EmailTool',
    'WebBrowserTool',
    'SystemCommandTool',
    'MiCloudTool',
    'TaskCompleteTool'
] 