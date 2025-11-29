"""
A2A (Agent-to-Agent) Communication Module.

This module implements the A2A protocol for inter-agent communication.
Each agent is an independent unit that can send and receive messages.
"""

from .protocol import A2AMessage, A2AProtocol, MessageType
from .registry import AgentRegistry

__all__ = [
    "A2AMessage",
    "A2AProtocol", 
    "MessageType",
    "AgentRegistry",
]
