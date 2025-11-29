"""
Agents Module for Multi-Agent Customer Service System.

This module contains independent agents that communicate via A2A protocol.
Each agent uses LangChain for LLM interactions.
"""

from .base_agent import BaseAgent
from .router_agent import RouterAgent
from .customer_data_agent import CustomerDataAgent
from .support_agent import SupportAgent
from .orchestrator import MultiAgentSystem, create_multi_agent_system, run_query

__all__ = [
    "BaseAgent",
    "RouterAgent",
    "CustomerDataAgent",
    "SupportAgent",
    "MultiAgentSystem",
    "create_multi_agent_system",
    "run_query",
]
