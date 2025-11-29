"""
Multi-Agent System Orchestrator.

This module initializes all agents and provides an entry point
for processing user queries through the A2A-based multi-agent system.
"""

import asyncio
from typing import Any, Dict, List, Optional

from src.a2a.protocol import get_a2a_protocol, A2AMessage, MessageType
from src.a2a.registry import get_agent_registry
from src.agents.router_agent import RouterAgent
from src.agents.customer_data_agent import CustomerDataAgent
from src.agents.support_agent import SupportAgent


class MultiAgentSystem:
    """
    Multi-Agent System that coordinates multiple agents via A2A.
    
    This system:
    1. Initializes all agents (Router, CustomerData, Support)
    2. Registers them with the A2A protocol
    3. Provides a unified interface for processing queries
    """
    
    _instance: Optional["MultiAgentSystem"] = None
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the multi-agent system.
        
        Args:
            model: OpenAI model to use for all agents
        """
        self.model = model
        self.protocol = get_a2a_protocol()
        self.registry = get_agent_registry()
        
        # Initialize agents
        self.router: Optional[RouterAgent] = None
        self.customer_data: Optional[CustomerDataAgent] = None
        self.support: Optional[SupportAgent] = None
        
        self._initialized = False
    
    @classmethod
    def get_instance(cls, model: str = "gpt-4o-mini") -> "MultiAgentSystem":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls(model)
        return cls._instance
    
    def initialize(self) -> None:
        """Initialize all agents in the system."""
        if self._initialized:
            return
        
        print("Initializing Multi-Agent System...")
        print("-" * 40)
        
        # Create agents - they auto-register with protocol and registry
        self.router = RouterAgent(model=self.model)
        self.customer_data = CustomerDataAgent(model=self.model)
        self.support = SupportAgent(model=self.model)
        
        self._initialized = True
        
        print("-" * 40)
        print(f"Registered agents: {self.registry.get_agent_names()}")
        print("Multi-Agent System initialized!")
    
    async def process_query_async(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent system (async).
        
        Args:
            query: User query text
            
        Returns:
            Dictionary with response and metadata
        """
        if not self._initialized:
            self.initialize()
        
        # Clear previous logs
        for agent in [self.router, self.customer_data, self.support]:
            if agent:
                agent.clear_logs()
        
        # Process through router agent
        result = await self.router.handle_user_query(query)
        
        # Collect logs from all agents
        all_logs = []
        for agent in [self.router, self.customer_data, self.support]:
            if agent:
                all_logs.extend(agent.get_logs())
        
        result["agent_logs"] = all_logs
        
        return result
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent system (sync).
        
        Args:
            query: User query text
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.process_query_async(query))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.process_query_async(query))
    
    def get_message_history(self) -> List[A2AMessage]:
        """Get the A2A message history."""
        return self.protocol.get_message_history()
    
    def clear_history(self) -> None:
        """Clear message history and agent logs."""
        self.protocol.clear_history()
        for agent in [self.router, self.customer_data, self.support]:
            if agent:
                agent.clear_logs()


def create_multi_agent_system(model: str = "gpt-4o-mini") -> MultiAgentSystem:
    """
    Create and initialize a multi-agent system.
    
    Args:
        model: OpenAI model to use
        
    Returns:
        Initialized MultiAgentSystem
    """
    system = MultiAgentSystem.get_instance(model)
    system.initialize()
    return system


def run_query(query: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Run a single query through the multi-agent system.
    
    Convenience function for simple usage.
    
    Args:
        query: User query text
        model: OpenAI model to use
        
    Returns:
        Response dictionary
    """
    system = create_multi_agent_system(model)
    return system.process_query(query)
