"""
Tests for A2A (Agent-to-Agent) Communication Protocol.

This file tests:
1. A2A message creation and serialization
2. A2A protocol message passing
3. Agent registration and discovery
4. Multi-agent coordination via A2A
"""

import pytest
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.a2a.protocol import (
    A2AMessage,
    A2AProtocol,
    MessageType,
    get_a2a_protocol,
)
from src.a2a.registry import (
    AgentRegistry,
    AgentInfo,
    get_agent_registry,
)


class TestA2AMessage:
    """Tests for A2A message creation and serialization."""
    
    def test_message_creation(self):
        """Test creating a basic A2A message."""
        msg = A2AMessage(
            sender="agent_a",
            recipient="agent_b",
            type=MessageType.QUERY,
            payload={"data": "test"},
        )
        
        assert msg.sender == "agent_a"
        assert msg.recipient == "agent_b"
        assert msg.type == MessageType.QUERY
        assert msg.payload == {"data": "test"}
        assert msg.conversation_id is not None
        assert msg.message_id is not None
        assert msg.timestamp is not None
    
    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = A2AMessage(
            sender="agent_a",
            recipient="agent_b",
            type=MessageType.RESPONSE,
            payload={"result": "success"},
            conversation_id="conv-123",
        )
        
        d = msg.to_dict()
        
        assert d["sender"] == "agent_a"
        assert d["recipient"] == "agent_b"
        assert d["type"] == "response"
        assert d["payload"] == {"result": "success"}
        assert d["conversation_id"] == "conv-123"
    
    def test_message_to_json(self):
        """Test converting message to JSON."""
        msg = A2AMessage(
            sender="test_sender",
            recipient="test_recipient",
            type=MessageType.DATA_REQUEST,
            payload={"key": "value"},
        )
        
        json_str = msg.to_json()
        
        assert "test_sender" in json_str
        assert "test_recipient" in json_str
        assert "data_request" in json_str
    
    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "sender": "agent_x",
            "recipient": "agent_y",
            "type": "query",
            "payload": {"question": "What is the status?"},
            "conversation_id": "conv-456",
        }
        
        msg = A2AMessage.from_dict(data)
        
        assert msg.sender == "agent_x"
        assert msg.recipient == "agent_y"
        assert msg.type == MessageType.QUERY
        assert msg.payload == {"question": "What is the status?"}
    
    def test_message_from_json(self):
        """Test creating message from JSON."""
        json_str = '''
        {
            "sender": "json_sender",
            "recipient": "json_recipient",
            "type": "response",
            "payload": {"data": 123}
        }
        '''
        
        msg = A2AMessage.from_json(json_str)
        
        assert msg.sender == "json_sender"
        assert msg.recipient == "json_recipient"
        assert msg.type == MessageType.RESPONSE


class TestAgentRegistry:
    """Tests for agent registry functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a fresh registry for each test."""
        self.registry = AgentRegistry()
    
    def test_register_agent(self):
        """Test registering an agent."""
        info = self.registry.register(
            name="test_agent",
            description="A test agent",
            capabilities=["cap1", "cap2"],
        )
        
        assert info.name == "test_agent"
        assert info.description == "A test agent"
        assert "cap1" in info.capabilities
        assert "cap2" in info.capabilities
    
    def test_get_agent(self):
        """Test retrieving an agent by name."""
        self.registry.register(
            name="lookup_agent",
            description="Agent for lookup test",
            capabilities=["lookup"],
        )
        
        agent = self.registry.get("lookup_agent")
        
        assert agent is not None
        assert agent.name == "lookup_agent"
    
    def test_get_nonexistent_agent(self):
        """Test retrieving a non-existent agent."""
        agent = self.registry.get("nonexistent")
        assert agent is None
    
    def test_list_agents(self):
        """Test listing all agents."""
        self.registry.register("agent1", "First", ["a"])
        self.registry.register("agent2", "Second", ["b"])
        self.registry.register("agent3", "Third", ["c"])
        
        agents = self.registry.list_agents()
        
        assert len(agents) == 3
        names = [a.name for a in agents]
        assert "agent1" in names
        assert "agent2" in names
        assert "agent3" in names
    
    def test_find_by_capability(self):
        """Test finding agents by capability."""
        self.registry.register("data_agent", "Data handler", ["data", "query"])
        self.registry.register("support_agent", "Support handler", ["support", "tickets"])
        self.registry.register("hybrid_agent", "Hybrid handler", ["data", "support"])
        
        data_agents = self.registry.find_by_capability("data")
        
        assert len(data_agents) == 2
        names = [a.name for a in data_agents]
        assert "data_agent" in names
        assert "hybrid_agent" in names
    
    def test_unregister_agent(self):
        """Test unregistering an agent."""
        self.registry.register("temp_agent", "Temporary", ["temp"])
        
        assert self.registry.get("temp_agent") is not None
        
        result = self.registry.unregister("temp_agent")
        
        assert result is True
        assert self.registry.get("temp_agent") is None


class TestA2AProtocol:
    """Tests for A2A protocol message passing."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a fresh protocol instance for each test."""
        self.protocol = A2AProtocol()
    
    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test registering a message handler."""
        async def test_handler(msg):
            return A2AMessage(
                sender="responder",
                recipient=msg.sender,
                type=MessageType.RESPONSE,
                payload={"echo": msg.payload},
            )
        
        self.protocol.register_handler("test_agent", test_handler)
        
        assert "test_agent" in self.protocol.get_registered_agents()
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message to a registered agent."""
        # Register a simple echo handler
        async def echo_handler(msg):
            return A2AMessage(
                sender="echo_agent",
                recipient=msg.sender,
                type=MessageType.RESPONSE,
                payload={"received": msg.payload},
                conversation_id=msg.conversation_id,
            )
        
        self.protocol.register_handler("echo_agent", echo_handler)
        
        # Send a message
        msg = A2AMessage(
            sender="test_sender",
            recipient="echo_agent",
            type=MessageType.QUERY,
            payload={"message": "Hello"},
        )
        
        response = await self.protocol.send_message(msg)
        
        assert response is not None
        assert response.sender == "echo_agent"
        assert response.type == MessageType.RESPONSE
        assert response.payload["received"] == {"message": "Hello"}
    
    @pytest.mark.asyncio
    async def test_send_to_unknown_agent(self):
        """Test sending a message to an unknown agent."""
        msg = A2AMessage(
            sender="sender",
            recipient="unknown_agent",
            type=MessageType.QUERY,
            payload={},
        )
        
        response = await self.protocol.send_message(msg)
        
        assert response is not None
        assert response.type == MessageType.ERROR
        assert "not found" in response.payload.get("error", "")
    
    @pytest.mark.asyncio
    async def test_message_history(self):
        """Test message history tracking."""
        async def simple_handler(msg):
            return A2AMessage(
                sender="receiver",
                recipient=msg.sender,
                type=MessageType.RESPONSE,
                payload={},
                conversation_id=msg.conversation_id,
            )
        
        self.protocol.register_handler("receiver", simple_handler)
        
        # Send some messages
        for i in range(3):
            msg = A2AMessage(
                sender="sender",
                recipient="receiver",
                type=MessageType.QUERY,
                payload={"index": i},
                conversation_id="test-conv",
            )
            await self.protocol.send_message(msg)
        
        history = self.protocol.get_message_history()
        
        # Should have 6 messages (3 sent + 3 responses)
        assert len(history) == 6
    
    @pytest.mark.asyncio
    async def test_filter_history_by_conversation(self):
        """Test filtering message history by conversation ID."""
        async def handler(msg):
            return A2AMessage(
                sender="agent",
                recipient=msg.sender,
                type=MessageType.RESPONSE,
                payload={},
                conversation_id=msg.conversation_id,
            )
        
        self.protocol.register_handler("agent", handler)
        
        # Send messages in different conversations
        for conv_id in ["conv-1", "conv-2", "conv-1"]:
            msg = A2AMessage(
                sender="sender",
                recipient="agent",
                type=MessageType.QUERY,
                payload={},
                conversation_id=conv_id,
            )
            await self.protocol.send_message(msg)
        
        # Filter by conversation
        conv1_history = self.protocol.get_message_history(conversation_id="conv-1")
        
        # Should have 4 messages in conv-1 (2 requests + 2 responses)
        assert len(conv1_history) == 4
        assert all(m.conversation_id == "conv-1" for m in conv1_history)


class TestMultiAgentCommunication:
    """Integration tests for multi-agent A2A communication."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup protocol for multi-agent tests."""
        self.protocol = A2AProtocol()
        self.messages_processed = []
    
    @pytest.mark.asyncio
    async def test_chain_of_agents(self):
        """Test message passing through a chain of agents."""
        # Agent A processes and forwards to Agent B
        async def agent_a_handler(msg):
            self.messages_processed.append(("A", msg.payload))
            
            # Forward to Agent B
            forward_msg = A2AMessage(
                sender="agent_a",
                recipient="agent_b",
                type=MessageType.HANDOFF,
                payload={"from_a": msg.payload, "processed_by": "A"},
                conversation_id=msg.conversation_id,
            )
            response_from_b = await self.protocol.send_message(forward_msg)
            
            # Return combined result
            return A2AMessage(
                sender="agent_a",
                recipient=msg.sender,
                type=MessageType.RESPONSE,
                payload={
                    "result_a": "processed",
                    "result_b": response_from_b.payload if response_from_b else None,
                },
                conversation_id=msg.conversation_id,
            )
        
        async def agent_b_handler(msg):
            self.messages_processed.append(("B", msg.payload))
            return A2AMessage(
                sender="agent_b",
                recipient=msg.sender,
                type=MessageType.RESPONSE,
                payload={"processed_by": "B", "original": msg.payload},
                conversation_id=msg.conversation_id,
            )
        
        self.protocol.register_handler("agent_a", agent_a_handler)
        self.protocol.register_handler("agent_b", agent_b_handler)
        
        # Send initial message to Agent A
        initial_msg = A2AMessage(
            sender="user",
            recipient="agent_a",
            type=MessageType.QUERY,
            payload={"query": "test"},
        )
        
        response = await self.protocol.send_message(initial_msg)
        
        # Verify chain processed correctly
        assert len(self.messages_processed) == 2
        assert self.messages_processed[0][0] == "A"
        assert self.messages_processed[1][0] == "B"
        
        assert response is not None
        assert response.payload["result_a"] == "processed"
        assert response.payload["result_b"]["processed_by"] == "B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
