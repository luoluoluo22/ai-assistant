"""Base tool class definition."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List

class BaseTool(ABC):
    """Base class for all tools."""
    
    name: str
    description: str
    
    def __init__(self):
        """Initialize the tool."""
        if not hasattr(self, 'name'):
            raise ValueError("Tool must have a name")
        if not hasattr(self, 'description'):
            raise ValueError("Tool must have a description")
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool specific parameters
            
        Returns:
            Dict containing the execution results
        """
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get the parameters schema for the tool.
        
        Returns:
            Dict containing parameter definitions
        """
        return {}
        
    @property
    def examples(self) -> List[str]:
        """Get example usages of the tool.
        
        Returns:
            List of example usage strings
        """
        return []
        
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get the complete tool definition.
        
        Returns:
            Dict containing the tool's complete definition including name,
            description, parameters, and examples.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples
        } 