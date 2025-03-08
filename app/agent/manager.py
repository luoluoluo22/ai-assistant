"""Agent manager for handling conversations."""

from typing import Dict, Optional, AsyncGenerator, Any
from .base import Agent
from ..core.config import settings

class AgentManager:
    """Manager class for handling agent instances."""
    
    def __init__(self):
        """Initialize the manager."""
        self._agents: Dict[str, Agent] = {}
    
    def get_agent(self, session_id: str) -> Agent:
        """Get or create an agent for the session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Agent instance
        """
        if session_id not in self._agents:
            self._agents[session_id] = Agent()
        return self._agents[session_id]
    
    async def process_message(
        self,
        session_id: str,
        message: str,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 800,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stream: bool = False
    ) -> str:
        """Process a message using the appropriate agent.
        
        Args:
            session_id: Session identifier
            message: User's message
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
        agent = self.get_agent(session_id)
        return await agent.process_message(
            message,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stream=stream
        )
    
    async def stream_message(
        self,
        session_id: str,
        message: str,
        model: str = settings.DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 800,
        top_p: float = 0.95,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0
    ) -> AsyncGenerator[str, None]:
        """Stream a message response using the appropriate agent.
        
        Args:
            session_id: Session identifier
            message: User's message
            model: Model to use for generation
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling threshold
            frequency_penalty: Frequency penalty
            presence_penalty: Presence penalty
            
        Yields:
            Chunks of the agent's response
        """
        agent = self.get_agent(session_id)
        async for chunk in agent.stream_message(
            message,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        ):
            yield chunk
    
    def clear_session(self, session_id: str):
        """Clear a session and its agent.
        
        Args:
            session_id: Session to clear
        """
        if session_id in self._agents:
            del self._agents[session_id] 