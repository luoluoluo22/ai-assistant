"""Test cases for agent functionality."""

import pytest
from app.agent.base import Agent
from app.agent.manager import AgentManager

@pytest.fixture
def agent():
    """Create an agent instance."""
    return Agent()

@pytest.fixture
def agent_manager():
    """Create an agent manager instance."""
    return AgentManager()

@pytest.mark.asyncio
async def test_agent_process_message(agent):
    """Test agent message processing."""
    # Test directory listing
    response = await agent.process_message("请列出当前目录的文件")
    
    # 验证思考过程
    assert "让我思考一下" in response
    assert "请列出当前目录的文件" in response
    
    # 验证执行计划
    assert "📋 我的执行计划" in response
    assert "system_command" in response
    assert "dir" in response or "ls" in response
    
    # 验证执行过程
    assert "⚙️ 正在执行" in response
    assert "✅ 执行成功" in response
    
    # 验证最终结果
    assert "🎉 太好了" in response
    
    # Test unknown command
    response = await agent.process_message("你好")
    assert "🤔 让我思考一下" in response
    assert "抱歉，我不太理解您的请求" in response
    assert "请尝试用更具体的描述" in response
    
    # 验证对话历史格式
    assert "👤 用户：" in response
    assert "🤖 助手：" in response

@pytest.mark.asyncio
async def test_agent_memory(agent):
    """Test agent memory management."""
    # Test memory update
    agent.update_memory("test_key", "test_value")
    assert agent.get_memory("test_key") == "test_value"
    
    # Test memory retrieval
    assert agent.get_memory("non_existent") is None
    
    # Test memory clearing
    agent.clear_memory()
    assert agent.get_memory("test_key") is None

@pytest.mark.asyncio
async def test_agent_manager(agent_manager):
    """Test agent manager functionality."""
    # Test message processing with detailed output
    response = await agent_manager.process_message("session1", "请列出当前目录的文件")
    
    # 验证完整的交互过程
    assert "让我思考一下" in response
    assert "执行计划" in response
    assert "正在执行" in response
    assert "✅ 执行成功" in response
    
    # Test session management
    agent1 = agent_manager.get_agent("session1")
    agent2 = agent_manager.get_agent("session1")
    assert agent1 is agent2  # Same session should return same agent
    
    # Test conversation history persistence
    history = agent1.context["conversation_history"]
    assert len(history) > 2  # Should have multiple interaction steps
    assert any("思考" in msg["content"] for msg in history)
    assert any("计划" in msg["content"] for msg in history)
    assert any("执行" in msg["content"] for msg in history)
    
    # Test session clearing
    agent_manager.clear_session("session1")
    agent3 = agent_manager.get_agent("session1")
    assert agent3 is not agent1  # Should be a new agent after clearing
    assert len(agent3.context["conversation_history"]) == 0  # New agent should have empty history 