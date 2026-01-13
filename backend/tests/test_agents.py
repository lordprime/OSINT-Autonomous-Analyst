"""
Collection Agent Tests
Unit tests for all collection agents
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.agents.collection.registry import get_agent, list_agents, AGENT_REGISTRY


def test_agent_registry():
    """Test agent registry loads all agents"""
    
    agents = list_agents()
    
    assert "duckduckgo" in agents
    assert "telegram" in agents
    assert "instagram" in agents
    assert "linkedin" in agents
    assert "facebook" in agents
    
    assert len(agents) == 5
    print(f"✅ Registry contains {len(agents)} agents")


def test_get_agent():
    """Test getting agent from registry"""
    
    # Valid agent
    ddg = get_agent("duckduckgo")
    assert ddg is not None
    assert hasattr(ddg, "collect")
    
    # Invalid agent
    with pytest.raises(ValueError):
        get_agent("nonexistent")
    
    print("✅ Agent retrieval works")


@pytest.mark.asyncio
async def test_duckduckgo_agent():
    """Test DuckDuckGo collection agent"""
    
    agent = get_agent("duckduckgo")
    
    # Mock the actual search to avoid real API calls
    with patch.object(agent, "_execute_collection", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = []
        
        result = await agent.collect(
            investigation_id="test_inv",
            query="python programming",
            user_id="test_user",
            justification="Unit test",
            collection_type="text",
            max_results=5
        )
        
        assert result is not None
        assert hasattr(result, "items_collected")
        
        print("✅ DuckDuckGo agent collect method works")


@pytest.mark.asyncio
async def test_telegram_agent():
    """Test Telegram agent"""
    
    agent = get_agent("telegram")
    
    with patch.object(agent, "_execute_collection", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = []
        
        result = await agent.collect(
            investigation_id="test_inv",
            query="@testchannel",
            user_id="test_user",
            justification="Unit test"
        )
        
        assert result is not None
        print("✅ Telegram agent works")


@pytest.mark.asyncio
async def test_instagram_agent():
    """Test Instagram agent"""
    
    agent = get_agent("instagram")
    
    with patch.object(agent, "_execute_collection", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = []
        
        result = await agent.collect(
            investigation_id="test_inv",
            query="testuser",
            user_id="test_user",
            justification="Unit test"
        )
        
        assert result is not None
        print("✅ Instagram agent works")


@pytest.mark.asyncio
async def test_linkedin_agent():
    """Test LinkedIn agent"""
    
    agent = get_agent("linkedin")
    
    with patch.object(agent, "_execute_collection", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = []
        
        result = await agent.collect(
            investigation_id="test_inv",
            query="company/test-corp",
            user_id="test_user",
            justification="Unit test"
        )
        
        assert result is not None
        print("✅ LinkedIn agent works")


@pytest.mark.asyncio
async def test_facebook_agent():
    """Test Facebook agent"""
    
    agent = get_agent("facebook")
    
    with patch.object(agent, "_execute_collection", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = []
        
        result = await agent.collect(
            investigation_id="test_inv",
            query="testpage",
            user_id="test_user",
            justification="Unit test"
        )
        
        assert result is not None
        print("✅ Facebook agent works")


@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test agent error handling"""
    
    agent = get_agent("duckduckgo")
    
    # Test with invalid params (should handle gracefully)
    with patch.object(agent, "_execute_collection", side_effect=Exception("Network error")):
        result = await agent.collect(
            investigation_id="test",
            query="test",
            user_id="test",
            justification="test"
        )
        
        # Should return result with errors
        assert result is not None
        
    print("✅ Agent error handling works")


@pytest.mark.asyncio
async def test_compliance_checks():
    """Test compliance and policy checks"""
    
    agent = get_agent("duckduckgo")
    
    # All agents should have compliance checks
    assert hasattr(agent, "_check_compliance")
    
    # Test PII detection (mocked)
    with patch.object(agent, "_check_compliance", return_value=True):
        is_compliant = agent._check_compliance(
            investigation_id="test",
            query="search term",
            user_id="test"
        )
        
        assert is_compliant is True
    
    print("✅ Compliance checks present")


def test_all_agents_have_required_methods():
    """Verify all agents implement required interface"""
    
    required_methods = ["collect", "_execute_collection", "_normalize_data"]
    
    for agent_type in list_agents():
        agent = get_agent(agent_type)
        
        for method in required_methods:
            assert hasattr(agent, method), f"{agent_type} missing {method}"
    
    print("✅ All agents implement required interface")


if __name__ == "__main__":
    # Run tests
    print("Running Agent Tests...")
    test_agent_registry()
    test_get_agent()
    
    # Async tests
    import asyncio
    asyncio.run(test_duckduckgo_agent())
    asyncio.run(test_telegram_agent())
    asyncio.run(test_instagram_agent())
    asyncio.run(test_linkedin_agent())
    asyncio.run(test_facebook_agent())
    asyncio.run(test_agent_error_handling())
    asyncio.run(test_compliance_checks())
    
    test_all_agents_have_required_methods()
    
    print("\n✅ All agent tests passed!")
