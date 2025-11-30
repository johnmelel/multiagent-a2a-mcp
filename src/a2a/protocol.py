"""
A2A Protocol Implementation using the official a2a-sdk types.

This module uses the official Google A2A SDK types for message format compatibility
while providing simple in-process agent-to-agent communication.

For HTTP-based A2A communication, use the A2AClient from the SDK directly.
"""

import uuid
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

# Official A2A SDK types for compatibility
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    Message,
    TextPart,
)
from a2a.client import A2AClient


class MessageType(str, Enum):
    """Types of A2A messages."""
    QUERY = "query"
    RESPONSE = "response"
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    HANDOFF = "handoff"


@dataclass
class A2AMessage:
    """
    A2A Message wrapper for compatibility with existing agent code.
    
    This wraps the official a2a-sdk Message type while maintaining
    the interface used by our agents.
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
    
    def to_a2a_message(self) -> Message:
        """Convert to official A2A SDK Message."""
        text_content = json.dumps({
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "payload": self.payload,
            "metadata": self.metadata,
        })
        return Message(
            messageId=self.message_id,
            role="user",
            parts=[TextPart(text=text_content)],
        )
    
    @classmethod
    def from_a2a_message(cls, msg: Message, sender: str, recipient: str, conversation_id: str = None) -> "A2AMessage":
        """Create from official A2A SDK Message."""
        # Extract text from parts
        text_content = ""
        for part in msg.parts:
            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                text_content = part.root.text
                break
            elif hasattr(part, 'text'):
                text_content = part.text
                break
        
        # Try to parse as JSON
        try:
            data = json.loads(text_content)
            msg_type = MessageType(data.get("type", "response"))
            payload = data.get("payload", {"text": text_content})
            metadata = data.get("metadata", {})
        except (json.JSONDecodeError, ValueError):
            msg_type = MessageType.RESPONSE
            payload = {"text": text_content}
            metadata = {}
        
        return cls(
            sender=sender,
            recipient=recipient,
            type=msg_type,
            payload=payload,
            conversation_id=conversation_id or str(uuid.uuid4()),
            message_id=msg.messageId or str(uuid.uuid4()),
            metadata=metadata,
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        """Create message from dictionary."""
        msg_type = data.get("type", MessageType.QUERY)
        if isinstance(msg_type, str):
            try:
                msg_type = MessageType(msg_type)
            except ValueError:
                msg_type = MessageType.QUERY
        
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
    A2A Protocol handler using the official a2a-sdk types.
    
    Provides in-process agent-to-agent communication using A2A message formats.
    For HTTP-based communication, agents can be deployed as separate services
    using the A2AClient from the SDK.
    """
    
    def __init__(self, base_port: int = 9000):
        """
        Initialize the protocol.
        
        Args:
            base_port: Starting port for agent servers (for future HTTP support)
        """
        self.base_port = base_port
        self._handlers: Dict[str, Callable] = {}
        self._agent_cards: Dict[str, AgentCard] = {}
        self._agent_urls: Dict[str, str] = {}
        self._clients: Dict[str, A2AClient] = {}
        self._message_history: List[A2AMessage] = []
        self._next_port = base_port
    
    def register_handler(self, agent_name: str, handler: Callable) -> None:
        """
        Register a message handler for an agent.
        
        Args:
            agent_name: Name of the agent
            handler: Async function that processes A2AMessage
        """
        self._handlers[agent_name] = handler
        
        # Assign port for potential HTTP deployment
        port = self._next_port
        self._next_port += 1
        self._agent_urls[agent_name] = f"http://localhost:{port}"
        
        # Create agent card (A2A spec compliant)
        self._agent_cards[agent_name] = AgentCard(
            name=agent_name,
            description=f"A2A Agent: {agent_name}",
            url=self._agent_urls[agent_name],
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False, pushNotifications=False),
            skills=[AgentSkill(id=agent_name, name=agent_name, description=f"{agent_name} agent", tags=[])],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        )
    
    def unregister_handler(self, agent_name: str) -> None:
        """Unregister an agent."""
        self._handlers.pop(agent_name, None)
        self._agent_cards.pop(agent_name, None)
        self._agent_urls.pop(agent_name, None)
        self._clients.pop(agent_name, None)
    
    def get_agent_card(self, agent_name: str) -> Optional[AgentCard]:
        """Get the A2A AgentCard for an agent."""
        return self._agent_cards.get(agent_name)
    
    def get_client(self, agent_name: str) -> Optional[A2AClient]:
        """Get or create A2A client for an agent (for HTTP communication)."""
        if agent_name not in self._agent_urls:
            return None
        
        if agent_name not in self._clients:
            self._clients[agent_name] = A2AClient(
                base_url=self._agent_urls[agent_name]
            )
        
        return self._clients[agent_name]
    
    async def send_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Send a message to another agent.
        
        Uses in-process communication by directly calling the handler.
        
        Args:
            message: The A2A message to send
            
        Returns:
            Response message from the recipient
        """
        self._message_history.append(message)
        
        handler = self._handlers.get(message.recipient)
        if handler is None:
            error_msg = A2AMessage(
                sender="a2a_protocol",
                recipient=message.sender,
                type=MessageType.ERROR,
                payload={"error": f"Agent '{message.recipient}' not found"},
                conversation_id=message.conversation_id,
            )
            self._message_history.append(error_msg)
            return error_msg
        
        try:
            response = await handler(message)
            if response:
                self._message_history.append(response)
            return response
        except Exception as e:
            error_msg = A2AMessage(
                sender="a2a_protocol",
                recipient=message.sender,
                type=MessageType.ERROR,
                payload={"error": str(e)},
                conversation_id=message.conversation_id,
            )
            self._message_history.append(error_msg)
            return error_msg
    
    def send_message_sync(self, message: A2AMessage) -> Optional[A2AMessage]:
        """Synchronous version of send_message."""
        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.send_message(message))
                return future.result()
        except RuntimeError:
            return asyncio.run(self.send_message(message))
    
    def get_message_history(self, conversation_id: Optional[str] = None) -> List[A2AMessage]:
        """Get message history."""
        if conversation_id:
            return [m for m in self._message_history if m.conversation_id == conversation_id]
        return self._message_history.copy()
    
    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()
    
    def get_registered_agents(self) -> List[str]:
        """Get list of registered agent names."""
        return list(self._handlers.keys())
    
    def get_agent_url(self, agent_name: str) -> Optional[str]:
        """Get the URL for an agent."""
        return self._agent_urls.get(agent_name)


# Global protocol instance
_global_protocol: Optional[A2AProtocol] = None


def get_a2a_protocol() -> A2AProtocol:
    """Get or create the global A2A protocol instance."""
    global _global_protocol
    if _global_protocol is None:
        _global_protocol = A2AProtocol()
    return _global_protocol
