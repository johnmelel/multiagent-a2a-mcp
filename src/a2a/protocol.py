"""
A2A Protocol Implementation.

Defines message formats and communication protocol for agent-to-agent communication.
This is a simple, synchronous A2A protocol using HTTP/JSON for demonstration.
"""

import uuid
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(str, Enum):
    """Types of A2A messages."""
    QUERY = "query"           # Request for information or action
    RESPONSE = "response"     # Response to a query
    DATA_REQUEST = "data_request"   # Request for specific data
    DATA_RESPONSE = "data_response" # Response with data
    TASK = "task"             # Task assignment
    RESULT = "result"         # Task result
    ERROR = "error"           # Error message
    HANDOFF = "handoff"       # Handoff to another agent


@dataclass
class A2AMessage:
    """
    A2A Message structure for agent-to-agent communication.
    
    Attributes:
        sender: Name of the sending agent
        recipient: Name of the receiving agent
        type: Message type (query, response, etc.)
        payload: Message content/data
        conversation_id: ID to track multi-step conversations
        message_id: Unique identifier for this message
        timestamp: When the message was created
        metadata: Additional context or routing information
    """
    sender: str
    recipient: str
    type: MessageType
    payload: Dict[str, Any]
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "payload": self.payload,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        """Create message from dictionary."""
        msg_type = data.get("type", MessageType.QUERY)
        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)
        
        return cls(
            sender=data["sender"],
            recipient=data["recipient"],
            type=msg_type,
            payload=data.get("payload", {}),
            conversation_id=data.get("conversation_id", str(uuid.uuid4())),
            message_id=data.get("message_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "A2AMessage":
        """Create message from JSON string."""
        return cls.from_dict(json.loads(json_str))


class A2AProtocol:
    """
    A2A Protocol handler for managing agent communication.
    
    This is a simple in-memory implementation. In production, this could use
    HTTP endpoints, message queues, or other transport mechanisms.
    """
    
    def __init__(self):
        """Initialize the protocol handler."""
        self._message_history: List[A2AMessage] = []
        self._handlers: Dict[str, Any] = {}  # agent_name -> handler function
    
    def register_handler(self, agent_name: str, handler) -> None:
        """
        Register a message handler for an agent.
        
        Args:
            agent_name: Name of the agent
            handler: Async function that processes A2AMessage and returns A2AMessage
        """
        self._handlers[agent_name] = handler
    
    def unregister_handler(self, agent_name: str) -> None:
        """Unregister an agent's handler."""
        if agent_name in self._handlers:
            del self._handlers[agent_name]
    
    async def send_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Send a message to another agent.
        
        Args:
            message: The A2A message to send
            
        Returns:
            Response message from the recipient, or None if no handler
        """
        # Log the message
        self._message_history.append(message)
        
        # Find the recipient's handler
        handler = self._handlers.get(message.recipient)
        if handler is None:
            # Return error message if recipient not found
            error_msg = A2AMessage(
                sender="a2a_protocol",
                recipient=message.sender,
                type=MessageType.ERROR,
                payload={"error": f"Agent '{message.recipient}' not found"},
                conversation_id=message.conversation_id,
            )
            self._message_history.append(error_msg)
            return error_msg
        
        # Invoke the handler and get response
        response = await handler(message)
        
        if response:
            self._message_history.append(response)
        
        return response
    
    def send_message_sync(self, message: A2AMessage) -> Optional[A2AMessage]:
        """Synchronous version of send_message."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.send_message(message))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.send_message(message))
    
    def get_message_history(self, conversation_id: Optional[str] = None) -> List[A2AMessage]:
        """
        Get message history, optionally filtered by conversation.
        
        Args:
            conversation_id: Optional filter for specific conversation
            
        Returns:
            List of messages
        """
        if conversation_id:
            return [m for m in self._message_history if m.conversation_id == conversation_id]
        return self._message_history.copy()
    
    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()
    
    def get_registered_agents(self) -> List[str]:
        """Get list of registered agent names."""
        return list(self._handlers.keys())


# Global protocol instance for simple in-memory communication
_global_protocol: Optional[A2AProtocol] = None


def get_a2a_protocol() -> A2AProtocol:
    """Get or create the global A2A protocol instance."""
    global _global_protocol
    if _global_protocol is None:
        _global_protocol = A2AProtocol()
    return _global_protocol
