"""
Agent Registry for A2A Communication.

Provides discovery and registration services for agents in the system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    name: str
    description: str
    capabilities: List[str]
    endpoint: Optional[str] = None  # URL if agent has HTTP endpoint
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """
    Registry for agent discovery and management.
    
    Allows agents to register themselves and discover other agents
    based on their capabilities.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._agents: Dict[str, AgentInfo] = {}
    
    def register(
        self,
        name: str,
        description: str,
        capabilities: List[str],
        endpoint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentInfo:
        """
        Register an agent in the registry.
        
        Args:
            name: Unique agent name
            description: Human-readable description
            capabilities: List of capabilities (e.g., ["customer_data", "search"])
            endpoint: Optional HTTP endpoint URL
            metadata: Additional agent metadata
            
        Returns:
            AgentInfo for the registered agent
        """
        info = AgentInfo(
            name=name,
            description=description,
            capabilities=capabilities,
            endpoint=endpoint,
            metadata=metadata or {},
        )
        self._agents[name] = info
        return info
    
    def unregister(self, name: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            name: Agent name to unregister
            
        Returns:
            True if agent was removed, False if not found
        """
        if name in self._agents:
            del self._agents[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[AgentInfo]:
        """
        Get agent information by name.
        
        Args:
            name: Agent name
            
        Returns:
            AgentInfo or None if not found
        """
        return self._agents.get(name)
    
    def list_agents(self) -> List[AgentInfo]:
        """
        List all registered agents.
        
        Returns:
            List of AgentInfo for all agents
        """
        return list(self._agents.values())
    
    def find_by_capability(self, capability: str) -> List[AgentInfo]:
        """
        Find agents with a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of agents with the capability
        """
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities
        ]
    
    def get_agent_names(self) -> List[str]:
        """Get list of all registered agent names."""
        return list(self._agents.keys())


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get or create the global agent registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry
