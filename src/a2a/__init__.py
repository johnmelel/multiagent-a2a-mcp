"""
A2A (Agent-to-Agent) Communication Module.

This module implements the A2A protocol for inter-agent communication
using the official Google A2A SDK (a2a-sdk) types.

Each agent is an independent unit that can send and receive messages.
"""

from .protocol import (
    A2AMessage,
    A2AProtocol,
    MessageType,
    get_a2a_protocol,
)
from .registry import AgentRegistry

__all__ = [
    "A2AMessage",
    "A2AProtocol", 
    "MessageType",
    "AgentRegistry",
    "get_a2a_protocol",
]
