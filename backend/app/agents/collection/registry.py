"""
Collection Agent Registry
Central registry for all OSINT data collection agents
"""

from app.agents.collection.base import BaseCollectionAgent


# Import all collection agents
from app.agents.collection import duckduckgo
from app.agents.collection import telegram
from app.agents.collection import instagram
from app.agents.collection import linkedin
from app.agents.collection import facebook


# Global agent registry
# Maps agent type string -> agent instance
AGENT_REGISTRY = {}


def register_agent(agent_type: str, agent: BaseCollectionAgent):
    """Register a collection agent"""
    AGENT_REGISTRY[agent_type] = agent


def get_agent(agent_type: str) -> BaseCollectionAgent:
    """Get agent by type"""
    agent = AGENT_REGISTRY.get(agent_type)
    if not agent:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_REGISTRY.keys())}")
    return agent


def list_agents() -> list[str]:
    """List all registered agent types"""
    return list(AGENT_REGISTRY.keys())


# Auto-register all agents on module import
def _initialize_agents():
    """Initialize and register all collection agents"""
    
    # DuckDuckGo Search
    ddg_agent = duckduckgo.DuckDuckGoAgent("duckduckgo")
    register_agent("duckduckgo", ddg_agent)
    
    # Telegram
    tg_agent = telegram.TelegramAgent("telegram")
    register_agent("telegram", tg_agent)
    
    # Instagram
    ig_agent = instagram.InstagramAgent("instagram")
    register_agent("instagram", ig_agent)
    
    # LinkedIn
    li_agent = linkedin.LinkedInAgent("linkedin")
    register_agent("linkedin", li_agent)
    
    # Facebook
    fb_agent = facebook.FacebookAgent("facebook")
    register_agent("facebook", fb_agent)


# Initialize on module import
_initialize_agents()


# Convenience exports
__all__ = [
    'AGENT_REGISTRY',
    'register_agent',
    'get_agent',
    'list_agents'
]
