"""
Base Agent class for A2A communication.

All agents inherit from this class to get common functionality
for A2A protocol handling and LangChain integration.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.a2a.protocol import A2AMessage, MessageType, get_a2a_protocol
from src.a2a.registry import get_agent_registry


class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    
    Provides:
    - A2A protocol integration for sending/receiving messages
    - LangChain LLM setup
    - Agent registration
    - Logging utilities
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        capabilities: List[str],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ):
        """
        Initialize the base agent.
        
        Args:
            name: Unique agent name
            description: Human-readable description
            capabilities: List of agent capabilities
            model: OpenAI model to use
            temperature: LLM temperature setting
        """
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self._logs: List[str] = []
        
        # Initialize LangChain LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        # Get A2A protocol and registry
        self.protocol = get_a2a_protocol()
        self.registry = get_agent_registry()
        
        # Register agent
        self._register()
    
    def _register(self) -> None:
        """Register this agent with the registry and protocol."""
        # Register in agent registry
        self.registry.register(
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
        )
        
        # Register message handler with protocol
        self.protocol.register_handler(self.name, self.handle_message)
        
        self.log(f"Agent '{self.name}' registered with capabilities: {self.capabilities}")
    
    def log(self, message: str) -> None:
        """Add a log entry."""
        log_entry = f"[{self.name}] {message}"
        self._logs.append(log_entry)
        print(log_entry)  # Also print for visibility
    
    def get_logs(self) -> List[str]:
        """Get all log entries."""
        return self._logs.copy()
    
    def clear_logs(self) -> None:
        """Clear log entries."""
        self._logs.clear()
    
    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Handle an incoming A2A message.
        
        Args:
            message: The incoming A2A message
            
        Returns:
            Response message, or None
        """
        self.log(f"Received {message.type.value} from {message.sender}")
        
        try:
            # Process the message
            result = await self.process(message)
            
            # Create response message
            if result is not None:
                response = A2AMessage(
                    sender=self.name,
                    recipient=message.sender,
                    type=MessageType.RESPONSE,
                    payload=result,
                    conversation_id=message.conversation_id,
                )
                return response
            return None
            
        except Exception as e:
            self.log(f"Error processing message: {e}")
            return A2AMessage(
                sender=self.name,
                recipient=message.sender,
                type=MessageType.ERROR,
                payload={"error": str(e)},
                conversation_id=message.conversation_id,
            )
    
    @abstractmethod
    async def process(self, message: A2AMessage) -> Optional[Dict[str, Any]]:
        """
        Process an incoming message.
        
        Subclasses must implement this method to handle their specific logic.
        
        Args:
            message: The incoming A2A message
            
        Returns:
            Response payload dictionary, or None
        """
        pass
    
    async def send_to_agent(
        self,
        recipient: str,
        msg_type: MessageType,
        payload: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> Optional[A2AMessage]:
        """
        Send a message to another agent via A2A protocol.
        
        Args:
            recipient: Name of the recipient agent
            msg_type: Type of message
            payload: Message payload
            conversation_id: Optional conversation ID for tracking
            
        Returns:
            Response from the recipient agent
        """
        message = A2AMessage(
            sender=self.name,
            recipient=recipient,
            type=msg_type,
            payload=payload,
            conversation_id=conversation_id or "",
        )
        
        self.log(f"Sending {msg_type.value} to {recipient}")
        
        response = await self.protocol.send_message(message)
        
        if response:
            self.log(f"Received response from {response.sender}")
        
        return response
    
    def call_llm(self, system_prompt: str, user_message: str) -> str:
        """
        Call the LLM with a system prompt and user message.
        
        Args:
            system_prompt: System prompt for the LLM
            user_message: User message to process
            
        Returns:
            LLM response text
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def find_agent_for_capability(self, capability: str) -> Optional[str]:
        """
        Find an agent with a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            Agent name, or None if not found
        """
        agents = self.registry.find_by_capability(capability)
        if agents:
            return agents[0].name
        return None
