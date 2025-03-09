"""Tool management module."""

from typing import Dict, Type
from .base import BaseTool
from .system import SystemCommandTool
from .web_browser import WebBrowserTool
from .email_tool import EmailTool
from .micloud_tool import MiCloudTool

# Tool registry
tools_registry: Dict[str, Type[BaseTool]] = {
    "system_command": SystemCommandTool,
    "web_browser": WebBrowserTool,
    "email": EmailTool,
    "micloud": MiCloudTool
}

"""Tools package for system interactions.""" 